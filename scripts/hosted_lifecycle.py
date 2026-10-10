"""Test only dedicated newly-created async jobs on an authenticated hosted API."""
import os
import time
import httpx
from app.schemas import validate


def main():
    base=os.environ['BACKEND_URL'].rstrip('/')
    key=os.environ['API_KEY']
    if not base.startswith('https://') and not base.startswith('http://127.0.0.1'):
        raise ValueError('Use valid HTTPS for hosted checks')
    headers={'X-API-Key':key,'Idempotency-Key':'tensorforge-smoke-'+str(time.time_ns())}
    ticket={'ticket_id':'smoke-'+str(time.time_ns()),'channel':'chat','text':'My food is late and I want a refund.'}
    with httpx.Client(base_url=base,timeout=30,verify=True) as client:
        health=client.get('/health');assert health.status_code==200
        direct=client.post('/predict',json=ticket,headers=headers);assert direct.status_code==200
        job=client.post('/batch/jobs',json={'tickets':[ticket]},headers=headers);assert job.status_code==202
        validate('BatchJobStatus',job.json())
        job_id=job.json()['job_id']
        try:
            repeat=client.post('/batch/jobs',json={'tickets':[ticket]},headers=headers)
            assert repeat.status_code==202 and repeat.json()['job_id']==job_id
            for _ in range(60):
                status=client.get('/batch/jobs/'+job_id,headers=headers)
                validate('BatchJobStatus',status.json())
                if status.json()['status']=='succeeded':
                    break
                assert status.json()['status'] in ('queued','running')
                time.sleep(3)
            else:
                raise RuntimeError('Dedicated smoke job timeout')
            result=client.get('/batch/jobs/'+job_id+'/results',params={'offset':0,'limit':1},headers=headers)
            assert result.status_code==200
            validate('BatchJobResults',result.json())
            assert result.json()['predictions']==[direct.json()]
            assert health.json()['model_version']==direct.json()['model_version']==result.json()['model_version']
        finally:
            assert client.delete('/batch/jobs/'+job_id,headers=headers).status_code==204
        assert client.get('/batch/jobs/'+job_id,headers=headers).status_code==404
    print('Dedicated async submit/idempotency/poll/results/version/delete lifecycle passed.')


if __name__=='__main__':
    main()
