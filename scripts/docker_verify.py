"""Verify a real image with disposable storage; never interrupt existing jobs."""
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
import httpx
from app.schemas import ROOT, validate


def main():
    image=os.getenv('DOCKER_IMAGE','tensorforge:local')
    suffix=uuid.uuid4().hex[:12]
    name='tensorforge-check-'+suffix
    volume=name+'-jobs'
    environment={**os.environ,'API_KEY':'isolated-docker-check-key'}
    record={'time_utc':datetime.now(timezone.utc).isoformat(),'image':image,'checks':[]}

    def docker(*args,input=None):
        result=subprocess.run(['docker',*args],input=input,text=True,capture_output=True,
                              encoding='utf-8',errors='replace',env=environment,timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def ready(client):
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            try:
                response=client.get('/health',timeout=2,headers={'Connection':'close'})
                if response.status_code==200:
                    validate('HealthResponse',response.json())
                    return response.json()
            except httpx.RequestError:
                pass
            time.sleep(.25)
        raise RuntimeError('Container readiness exceeded 120 seconds')

    try:
        record['image_id']=docker('image','inspect',image,'--format','{{.Id}}')
        source="from app.predictor import Predictor\nfrom app.schemas import ROOT\np=Predictor(ROOT/'artifacts')\nfor text in ['Food is late','මගේ බෑග් එක අමතක වුණා','எனது உணவு வரவில்லை','😟']:\n print(p.predict_one({'channel':'chat','text':text}))\n"
        offline=docker('run','--rm','-i','--network','none','--entrypoint','python',image,'-',input=source)
        assert offline.count("'model_version':")==4
        record['checks'].append('network-disabled image: actual load and four Unicode predictions')
        docker('volume','create',volume)
        docker('run','-d','--name',name,'-p','127.0.0.1::8000','-e','API_KEY',
               '-v',volume+':/srv/runtime',image)
        base='http://'+docker('port',name,'8000/tcp').splitlines()[0]
        headers={'X-API-Key':environment['API_KEY']}
        with httpx.Client(base_url=base,timeout=60) as client:
            health=ready(client)
            assert health['model_version']==json.loads((ROOT/'artifacts/manifest.json').read_text())['model_version']
            assert client.post('/predict',content=b'bad').status_code==401
            ticket={'ticket_id':'docker-check','channel':'chat','text':'My food has not arrived and I want a refund.'}
            direct=client.post('/predict',json=ticket,headers=headers)
            assert direct.status_code==200
            validate('PredictResponse',direct.json())
            batch=client.post('/predict/batch',json={'tickets':[ticket]},headers=headers)
            assert batch.status_code==200
            assert batch.json()['predictions']==[direct.json()]
            record['checks'].append('public health/version, auth precedence, direct/sync equality')
            # Valid large job stays running long enough to interrupt real CPU work.
            text=ticket['text']*60
            tickets=[{**ticket,'ticket_id':str(i),'text':text} for i in range(5000)]
            submit=client.post('/batch/jobs',json={'tickets':tickets},headers=headers)
            assert submit.status_code==202, submit.text
            job=submit.json()['job_id']
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                status=client.get('/batch/jobs/'+job,headers=headers).json()
                if status['status']=='running':
                    break
                assert status['status']=='queued', status
                time.sleep(.05)
            else:
                raise RuntimeError('No running job observed before interruption')
            docker('kill',name)
            docker('start',name)
            # Docker may assign a new ephemeral host port when starting again.
            client.base_url='http://'+docker('port',name,'8000/tcp').splitlines()[0]
            restarted=ready(client)
            status=client.get('/batch/jobs/'+job,headers=headers)
            validate('BatchJobStatus',status.json())
            assert status.json()['status']=='failed', status.text
            assert status.json()['error']['code']=='interrupted', status.text
            assert restarted['model_version']==health['model_version']
            assert client.delete('/batch/jobs/'+job,headers=headers).status_code==204
            assert client.get('/batch/jobs/'+job,headers=headers).status_code==404
            record['checks'].append('actual running 5000-ticket job killed; durable failed/interrupted recovery; DELETE')
            record['interrupted_job']=status.json()
        record['passed']=True
        print('Docker offline, API and persistent mid-job restart checks passed.')
    except Exception as exc:
        record['passed']=False
        record['error']=str(exc)
        raise
    finally:
        # These random names belong exclusively to this invocation.
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)
        subprocess.run(['docker','volume','rm',volume],capture_output=True,timeout=30)
        (ROOT/'experiments/docker_verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        with (ROOT/'experiments/docker_verification_history.jsonl').open('a',encoding='utf-8') as history:
            history.write(json.dumps(record)+'\n')


if __name__=='__main__':
    main()
