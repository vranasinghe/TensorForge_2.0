import json
import time
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Config
from app.schemas import validate, VALIDATORS, ROOT
from tests.conftest import ticket, wait_job


@pytest.mark.parametrize('authorization', [{'X-API-Key': 'test-key'}, {'Authorization': 'Bearer test-key'}])
def test_auth_modes(client, authorization):
    response = client.post('/predict', json=ticket(), headers=authorization)
    assert response.status_code == 200
    validate('PredictResponse', response.json())


@pytest.mark.parametrize('path', ['/predict', '/predict/batch', '/batch/jobs', '/batch/jobs/missing', '/batch/jobs/missing/results'])
@pytest.mark.parametrize('key', [None, 'wrong'])
def test_auth_precedes_invalid_body(client, path, key):
    headers = {'Content-Type': 'text/plain', 'Content-Length': '99999999'}
    if key:
        headers['X-API-Key'] = key
    r = client.post(path, content=b'{', headers=headers)
    assert r.status_code == 401
    assert r.headers['www-authenticate'] == 'Bearer'
    validate('ErrorResponse', r.json())


def test_missing_env_fails_closed(tmp_path, predictor):
    with TestClient(create_app(Config(api_key=None, database=tmp_path/'none.sqlite3'), predictor)) as c:
        assert c.post('/predict', json=ticket(), headers={'X-API-Key': ''}).status_code == 401
        assert c.get('/health').status_code in (200, 503)


@pytest.mark.parametrize('payload', [{}, {'channel': 'chat'}, {'channel': 'bad', 'text': 'hello'}, {'channel': 'chat', 'text': ' \n\t'}, {'channel': 'chat', 'text': 3}, {'channel': 'chat', 'text': None}, {'channel': 'chat', 'text': 'x'*10001}, {'channel': 'email', 'subject': 'x'*501, 'text': 'hello'}])
def test_semantic_errors(client, headers, payload):
    r = client.post('/predict', json=payload, headers=headers)
    assert r.status_code == 422
    validate('ErrorResponse', r.json())


@pytest.mark.parametrize('text', ['Hello refund please', 'මගේ බෑග් එක අමතක වුණා', 'என் உணவு வரவில்லை', 'mage order eka late', 'en order varala refund venum', 'මගේ order එක late', '🍔😢', 'x'*10000])
def test_unicode_and_boundaries(client, headers, text):
    r = client.post('/predict', json={'channel': 'email', 'subject': 'x'*500, 'text': text}, headers=headers)
    assert r.status_code == 200
    validate('PredictResponse', r.json())


@pytest.mark.parametrize('body', [b'{', b'null garbage', b'\xff', b'{"text":NaN}', b'['*1100])
def test_json_errors(client, headers, body):
    r = client.post('/predict', content=body, headers={**headers, 'Content-Type': 'application/json'})
    assert r.status_code == 400
    validate('ErrorResponse', r.json())


@pytest.mark.parametrize('path,size', [('/predict', 1024*1024), ('/predict/batch', 5*1024*1024), ('/batch/jobs', 25*1024*1024)])
def test_sizes_and_content_type(client, headers, path, size):
    assert client.post(path, content=b'{'*(size+1), headers={**headers, 'Content-Type': 'text/plain'}).status_code == 415
    r = client.post(path, content=b' '*(size+1), headers={**headers, 'Content-Type': 'application/json'})
    assert r.status_code == 413
    validate('ErrorResponse', r.json())
    # Generator bodies have no Content-Length, testing streamed byte accounting.
    r = client.post(path, content=iter([b' '*(size//2), b' '*(size//2+2)]), headers={**headers, 'Content-Type': 'application/json'})
    assert r.status_code == 413


def test_error_routes(client, headers):
    for method, path, code in [('get', '/unknown', 404), ('get', '/predict', 405), ('get', '/batch/jobs/unknown', 404)]:
        r = getattr(client, method)(path, headers=headers)
        assert r.status_code == code
        validate('ErrorResponse', r.json())


def test_atomic_indexed_errors(client, headers):
    rows = [ticket(), {'ticket_id': 'ticket-0', 'channel': 'no', 'text': ''}, {'channel': 'chat', 'text': 123}]
    for path in ('/predict/batch', '/batch/jobs'):
        r = client.post(path, json={'tickets': rows}, headers=headers)
        assert r.status_code == 422
        details = r.json()['error']['details']
        assert {d['index'] for d in details if 'index' in d} == {1, 2}
        assert any(d['field'] == 'ticket_id' for d in details)
    with client.app.state.store.connection() as db:
        assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == 0


@pytest.mark.parametrize('count', [0, 101])
def test_bad_sync_batch_size(client, headers, count):
    assert client.post('/predict/batch', json={'tickets': [ticket(i) for i in range(count)]}, headers=headers).status_code == 422


@pytest.mark.parametrize('count', [1, 100])
def test_sync_order(client, headers, count):
    rows = [ticket(i) for i in range(count)]
    r = client.post('/predict/batch', json={'tickets': rows}, headers=headers)
    assert r.status_code == 200
    validate('BatchResponse', r.json())
    assert [p['ticket_id'] for p in r.json()['predictions']] == [t['ticket_id'] for t in rows]


def test_model_consistency(client, headers):
    rows = [ticket(i) for i in range(4)]
    direct = [client.post('/predict', json=t, headers=headers).json() for t in rows]
    batch = client.post('/predict/batch', json={'tickets': rows[::-1]}, headers=headers).json()['predictions'][::-1]
    assert batch == direct
    job = client.post('/batch/jobs', json={'tickets': rows}, headers=headers).json()
    wait_job(client, job['job_id'], headers)
    results = client.get('/batch/jobs/'+job['job_id']+'/results', headers=headers).json()
    assert results['predictions'] == direct
    assert client.get('/health').json()['model_version'] == direct[0]['model_version'] == job['model_version']
    original = client.post('/predict', json=ticket(), headers=headers).json()
    variant = client.post('/predict', json={**ticket(), 'ticket_id': 'other-id', 'language': 'ta', 'category': 'spam_irrelevant'}, headers=headers).json()
    variant['ticket_id'] = original['ticket_id']
    assert original == variant


@pytest.mark.parametrize('count', [1, 100, 2000, 5000])
def test_real_async_sizes(client, headers, count):
    rows = [ticket(i) for i in range(count)]
    started = time.perf_counter()
    r = client.post('/batch/jobs', json={'tickets': rows}, headers=headers)
    assert r.status_code == 202
    assert time.perf_counter()-started < 5
    validate('BatchJobStatus', r.json())
    assert r.headers['location'].endswith(r.json()['job_id'])
    assert 'retry-after' in r.headers
    job_id = r.json()['job_id']
    final = wait_job(client, job_id, headers)
    assert final['processed'] == count
    assert final['expires_at'] > final['finished_at']
    result = client.get('/batch/jobs/'+job_id+'/results', headers=headers)
    assert result.status_code == 200
    validate('BatchJobResults', result.json())
    assert [p['ticket_id'] for p in result.json()['predictions']] == [r['ticket_id'] for r in rows]
    assert result.json()['next_offset'] is None


def test_pagination_delete(client, headers):
    rows = [ticket(i) for i in range(9)]
    job_id = client.post('/batch/jobs', json={'tickets': rows}, headers=headers).json()['job_id']
    wait_job(client, job_id, headers)
    path = '/batch/jobs/'+job_id
    for offset in (0, 3, 6):
        page = client.get(path+'/results', params={'offset': offset, 'limit': 3}, headers=headers).json()
        assert [r['ticket_id'] for r in page['predictions']] == [r['ticket_id'] for r in rows[offset:offset+3]]
        assert page['next_offset'] == (offset+3 if offset < 6 else None)
    for query in ('offset=-1', 'limit=0', 'limit=5001', 'offset=bad'):
        assert client.get(path+'/results?'+query, headers=headers).status_code == 422
    assert client.get(path+'/results?offset=12', headers=headers).json()['predictions'] == []
    assert client.get(path+'/results?offset='+str(10**100), headers=headers).json()['predictions'] == []
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404


def test_request_id_echo(client, headers):
    r = client.post('/predict', json=ticket(), headers={**headers, 'X-Request-ID': 'trace-123'})
    assert r.headers['x-request-id'] == 'trace-123'


def test_official_schema_examples():
    import yaml
    document = yaml.safe_load((ROOT/'API specs and schemas'/'tensorforge-phase2-openapi-v2.yaml').read_text(encoding='utf-8'))
    tested = 0
    for path in document['paths'].values():
        for method, op in path.items():
            if method not in ('get','post','delete'):
                continue
            for response in op.get('responses', {}).values():
                media = response.get('content', {}).get('application/json', {})
                if 'schema' not in media:
                    continue
                schema = media['schema']['$ref'].rsplit('/',1)[1]
                examples = [media['example']] if 'example' in media else [e['value'] for e in media.get('examples', {}).values()]
                for example in examples:
                    validate(schema, example)
                    tested += 1
    assert tested >= 10
