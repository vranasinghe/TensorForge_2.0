"""Exercise the running private demo proxy against the actual local API."""
import json
import os
import time
import httpx
from app.schemas import ROOT, validate


def main():
    record={'base':os.getenv('DEMO_URL','http://127.0.0.1:8501'),'checks':[]}
    credentials=(os.getenv('DEMO_USERNAME','demo'),os.getenv('DEMO_PASSWORD','local-demo-password'))
    with httpx.Client(base_url=record['base'],auth=credentials,timeout=20) as c:
        response=c.get('/')
        assert response.status_code==200, 'Demo login failed; set DEMO_URL, DEMO_USERNAME and DEMO_PASSWORD for the running service.'
        key=os.getenv('API_KEY','local-demo-key')
        assert not key or key not in response.text
        health=c.get('/api/health')
        assert health.status_code==200
        validate('HealthResponse',health.json())
        record['checks'].append('private page, no evaluation/backend key in HTML, real health proxy')
        response=c.post('/api/predict',json={'channel':'chat','text':'My food has not arrived. Please refund me.'})
        assert response.status_code==200
        validate('PredictResponse',response.json())
        record['checks'].append('real ticket classification through server-side credential proxy')
        csv='ticket_id,channel,subject,text\ndemo-1,chat,,"My food is late\nand I need a refund"\ndemo-2,email,Lost bag,මගේ බෑග් එක අමතක වුණා\n'
        imported=c.post('/api/import',content=csv.encode('utf-8'))
        assert imported.status_code==200
        job=c.post('/api/batch/jobs',json=imported.json())
        assert job.status_code==202
        job_id=job.json()['job_id']
        for _ in range(200):
            status=c.get('/api/batch/jobs/'+job_id)
            assert status.status_code==200
            if status.json()['status']=='succeeded':
                break
            time.sleep(.02)
        else:
            raise AssertionError('Demo job timeout')
        results=c.get('/api/batch/jobs/'+job_id+'/results')
        validate('BatchJobResults',results.json())
        assert [p['ticket_id'] for p in results.json()['predictions']]==['demo-1','demo-2']
        assert c.delete('/api/batch/jobs/'+job_id).status_code==204
        record['checks'].append('quoted multiline Unicode CSV import, actual async job, ordered results and DELETE')
    (ROOT/'experiments/local_demo_smoke.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('Real HTTP private-demo proxy smoke passed.')


if __name__=='__main__':
    main()
