"""Measured local timing; these are not reference-hardware guarantees."""
import json
import platform
import tempfile
import time
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app
from training.audit import ROOT, load


def summary(values):
    return {'count':len(values), 'p50_seconds':float(np.percentile(values,50)), 'p95_seconds':float(np.percentile(values,95)), 'max_seconds':float(max(values))}


def main():
    rows = load('validation')
    report = {'environment':platform.platform(), 'cpu':platform.processor(), 'method':'local TestClient on this host, includes ASGI overhead; not Docker/reference hardware', 'jobs':{}}
    headers = {'X-API-Key':'benchmark-key'}
    with tempfile.TemporaryDirectory() as tmp:
        t = time.perf_counter()
        with TestClient(create_app(Config(api_key='benchmark-key', database=Path(tmp)/'jobs.sqlite3'))) as c:
            while c.get('/health').status_code != 200:
                if time.perf_counter()-t > 120:
                    raise RuntimeError('Startup exceeded 120 seconds')
                time.sleep(.01)
            report['cold_readiness_seconds'] = time.perf_counter()-t
            timings=[]
            for row in rows[:100]:
                t=time.perf_counter()
                response=c.post('/predict', json=row,headers=headers)
                assert response.status_code==200,response.text
                timings.append(time.perf_counter()-t)
            report['single']=summary(timings)
            timings=[]
            for i in range(10):
                t=time.perf_counter()
                response=c.post('/predict/batch',json={'tickets':rows[i*50:i*50+100]},headers=headers)
                assert response.status_code==200,response.text
                timings.append(time.perf_counter()-t)
            report['sync_100']=summary(timings)
            for size in (2000,5000):
                tickets=[{**rows[i%len(rows)],'ticket_id':f'benchmark-{i}'} for i in range(size)]
                t=time.perf_counter()
                submitted=c.post('/batch/jobs',json={'tickets':tickets},headers=headers)
                assert submitted.status_code==202,submitted.text
                accepted=time.perf_counter()-t
                job_id=submitted.json()['job_id']
                poll=[]
                live=[]
                last=0
                while True:
                    p=time.perf_counter()
                    status=c.get('/batch/jobs/'+job_id,headers=headers).json()
                    assert last <= status['processed'] <= size
                    last=status['processed']
                    assert c.get('/health').status_code==200
                    poll.append(time.perf_counter()-p)
                    p=time.perf_counter()
                    assert c.post('/predict',json=rows[len(poll)%len(rows)],headers=headers).status_code==200
                    live.append(time.perf_counter()-p)
                    if status['status']=='succeeded':
                        break
                    if status['status']=='failed':
                        raise RuntimeError(status)
                    if time.perf_counter()-t>1800:
                        raise RuntimeError('Job timeout')
                    time.sleep(.03)
                completed=time.perf_counter()-t
                result=c.get('/batch/jobs/'+job_id+'/results',headers=headers)
                assert result.status_code==200
                predictions=result.json()['predictions']
                assert len(predictions)==size
                assert [r['ticket_id'] for r in predictions]==[r['ticket_id'] for r in tickets]
                report['jobs'][str(size)]={'submit_seconds':accepted,'completion_seconds':completed,'poll_and_health':summary(poll),'live_predict':summary(live)}
                c.delete('/batch/jobs/'+job_id,headers=headers)
    (ROOT/'experiments'/'benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
