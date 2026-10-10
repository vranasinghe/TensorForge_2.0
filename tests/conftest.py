import time
import pytest
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app
from app.predictor import Predictor
from app.schemas import ROOT


@pytest.fixture(scope='session')
def predictor():
    return Predictor(ROOT / 'artifacts')


@pytest.fixture
def client(tmp_path, predictor):
    app = create_app(Config(api_key='test-key', database=tmp_path / 'jobs.sqlite3'), predictor=predictor)
    with TestClient(app) as c:
        for _ in range(200):
            if c.get('/health').status_code == 200:
                break
            time.sleep(.01)
        else:
            pytest.fail('Model readiness timed out')
        yield c


@pytest.fixture
def headers():
    return {'X-API-Key': 'test-key'}


def ticket(i=0):
    return {'ticket_id': f'ticket-{i}', 'channel': 'chat', 'text': 'My food order has not arrived. Please refund me.'}


def wait_job(client, job_id, headers, timeout=120):
    start = time.perf_counter()
    progress = 0
    while time.perf_counter() - start < timeout:
        response = client.get('/batch/jobs/' + job_id, headers=headers)
        assert response.status_code == 200, response.text
        status = response.json()
        assert progress <= status['processed'] <= status['total']
        progress = status['processed']
        if status['status'] not in ('queued', 'running'):
            assert status['status'] == 'succeeded', status
            return status
        time.sleep(.02)
    pytest.fail('Async job did not finish in test timeout')
