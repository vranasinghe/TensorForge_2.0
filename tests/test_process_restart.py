"""Kill and restart an actual isolated Uvicorn process with a persisted job."""
import os
import socket
import subprocess
import sys
import time
import httpx
from app.schemas import ROOT


def test_real_process_interruption(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    environment={**os.environ,'API_KEY':'process-test-key','JOB_DB':str(tmp_path/'persistent.sqlite3')}
    command=[sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--workers','1']
    headers={'X-API-Key':'process-test-key'}
    process=None
    def launch():
        p=subprocess.Popen(command,cwd=ROOT,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        start=time.perf_counter()
        while time.perf_counter()-start<30:
            try:
                if httpx.get(f'http://127.0.0.1:{port}/health',timeout=1).status_code==200:
                    return p
            except httpx.RequestError:
                pass
            if p.poll() is not None:
                raise AssertionError('Isolated server exited during startup')
            time.sleep(.05)
        p.kill();p.wait()
        raise AssertionError('Isolated server readiness timeout')
    try:
        process=launch()
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=10) as client:
            rows=[{'ticket_id':f'crash-{i}','channel':'chat','text':'My food has not arrived. I am waiting for delivery. '*60} for i in range(5000)]
            submitted=client.post('/batch/jobs',json={'tickets':rows},headers=headers)
            assert submitted.status_code==202,submitted.text
            job_id=submitted.json()['job_id']
            assert client.get('/batch/jobs/'+job_id,headers=headers).json()['status'] in ('queued','running')
            process.kill();process.wait(timeout=10)
            process=launch()
            status=client.get('/batch/jobs/'+job_id,headers=headers).json()
            assert status['status']=='failed'
            assert status['error']['code']=='interrupted'
            assert client.get('/batch/jobs/'+job_id+'/results',headers=headers).status_code==409
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=10)
