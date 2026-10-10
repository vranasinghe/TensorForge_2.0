import pytest
from app.storage import Store
from app.errors import APIError
from tests.conftest import ticket


def test_idempotency_capacity_and_restart(tmp_path):
    store = Store(tmp_path/'state.sqlite3')
    first = store.submit([ticket()], 'v1', 'same-key')
    assert store.submit([ticket()], 'v1', 'same-key')['job_id'] == first['job_id']
    with pytest.raises(APIError) as conflict:
        store.submit([ticket(2)], 'v1', 'same-key')
    assert conflict.value.status == 409
    for i in range(3):
        store.submit([ticket(i+1)], 'v1')
    with pytest.raises(APIError) as capacity:
        store.submit([ticket(7)], 'v1')
    assert capacity.value.status == 429
    assert capacity.value.headers['Retry-After'] == '3'
    store.claim()
    restarted = Store(tmp_path/'state.sqlite3')
    restarted.recover()
    result = restarted.status(first['job_id'])
    assert result['status'] == 'failed'
    assert result['error']['code'] == 'interrupted'
    assert result['finished_at'] and result['expires_at']
    with pytest.raises(APIError) as early:
        restarted.results(first['job_id'])
    assert early.value.status == 409


@pytest.mark.parametrize('running', [False, True])
def test_delete_wins_commit_race(tmp_path, predictor, running):
    store = Store(tmp_path/'state.sqlite3')
    job = store.submit([ticket()], predictor.version)
    if running:
        store.claim()
    store.delete(job['job_id'])
    assert not store.commit_chunk(job['job_id'], 0, predictor.predict_many([ticket()]))
    with store.connection() as db:
        assert db.execute('SELECT count(*) FROM job_results').fetchone()[0] == 0
    with pytest.raises(APIError) as missing:
        store.status(job['job_id'])
    assert missing.value.status == 404


def test_expiry_tombstone(tmp_path):
    store = Store(tmp_path/'state.sqlite3')
    job = store.submit([ticket()], 'v1')
    with store.connection() as db:
        db.execute("UPDATE jobs SET status='failed',expires_at='2000-01-01T00:00:00+00:00' WHERE job_id=?", (job['job_id'],))
        store.cleanup(db)
    for operation in (store.status, store.results):
        with pytest.raises(APIError) as expired:
            operation(job['job_id'])
        assert expired.value.status == 410
