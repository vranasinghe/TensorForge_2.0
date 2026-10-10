"""Single-instance durable jobs with transactional admission and cancellation."""
import hashlib
import json
import sqlite3
import uuid
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.errors import APIError


def now():
    return datetime.now(timezone.utc).isoformat()


def expiry():
    return (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


class ServiceLease:
    """Refuse a second process on the same SQLite file before orphan recovery."""
    def __init__(self, database):
        path = Path(str(database) + '.lock')
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('a+b')
        if path.stat().st_size == 0:
            self.file.write(b'0')
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Another service process owns this database; use one worker/replica.')

    def close(self):
        if os.name == 'nt':
            import msvcrt
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs (
              job_id TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
              total INTEGER NOT NULL, processed INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, expires_at TEXT,
              model_version TEXT NOT NULL, error_code TEXT, error_message TEXT,
              idempotency_key TEXT UNIQUE, payload_digest TEXT);
            CREATE TABLE IF NOT EXISTS job_items (
              job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
              idx INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(job_id,idx));
            CREATE TABLE IF NOT EXISTS job_results (
              job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
              idx INTEGER NOT NULL, prediction TEXT NOT NULL, PRIMARY KEY(job_id,idx));
            CREATE TABLE IF NOT EXISTS tombstones (job_id TEXT PRIMARY KEY);
            CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status,created_at);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=10000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def cleanup(self, db):
        db.execute('INSERT OR IGNORE INTO tombstones SELECT job_id FROM jobs WHERE expires_at IS NOT NULL AND expires_at<=?', (now(),))
        db.execute('DELETE FROM jobs WHERE expires_at IS NOT NULL AND expires_at<=?', (now(),))

    def recover(self):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='failed',finished_at=?,expires_at=?,error_code='interrupted',error_message='Service restarted while work was pending.' WHERE status IN ('queued','running')", (now(), expiry()))

    def lookup(self, db, job_id):
        self.cleanup(db)
        row = db.execute('SELECT * FROM jobs WHERE job_id=?', (job_id,)).fetchone()
        if row is None:
            if db.execute('SELECT 1 FROM tombstones WHERE job_id=?', (job_id,)).fetchone():
                raise APIError(410, 'job_expired', 'Job retention expired.')
            raise APIError(404, 'job_not_found', 'Unknown job ID.')
        return row

    @staticmethod
    def status_value(row):
        result = {k: row[k] for k in ('job_id', 'status', 'total', 'processed', 'created_at', 'started_at', 'finished_at', 'expires_at', 'model_version')}
        result['error'] = {'code': row['error_code'], 'message': row['error_message']} if row['status'] == 'failed' else None
        return result

    def submit(self, tickets, version, key=None):
        canonical = json.dumps(tickets, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self.cleanup(db)
            if key is not None:
                existing = db.execute('SELECT * FROM jobs WHERE idempotency_key=?', (key,)).fetchone()
                if existing:
                    if existing['payload_digest'] != digest:
                        raise APIError(409, 'idempotency_conflict', 'Idempotency key was already used with a different payload.')
                    return self.status_value(existing)
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 4:
                raise APIError(429, 'too_many_jobs', 'Job capacity is full.', headers={'Retry-After': '3'})
            job_id = str(uuid.uuid4())
            db.execute("INSERT INTO jobs(job_id,status,total,created_at,model_version,idempotency_key,payload_digest) VALUES (?,'queued',?,?,?,?,?)", (job_id, len(tickets), now(), version, key, digest))
            db.executemany('INSERT INTO job_items VALUES (?,?,?)', [(job_id, i, json.dumps(t, ensure_ascii=False)) for i, t in enumerate(tickets)])
            return self.status_value(db.execute('SELECT * FROM jobs WHERE job_id=?', (job_id,)).fetchone())

    def status(self, job_id):
        with self.connection() as db:
            return self.status_value(self.lookup(db, job_id))

    def delete(self, job_id):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self.lookup(db, job_id)
            db.execute('DELETE FROM jobs WHERE job_id=?', (job_id,))

    def results(self, job_id, offset=0, limit=None):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self.lookup(db, job_id)
            if row['status'] != 'succeeded':
                raise APIError(409, 'job_not_ready', 'Results are available only after success.')
            limit = row['total'] if limit is None else limit
            items = [] if offset >= row['total'] else db.execute('SELECT prediction FROM job_results WHERE job_id=? AND idx>=? ORDER BY idx LIMIT ?', (job_id, offset, limit)).fetchall()
            next_offset = offset + len(items)
            return {'job_id': job_id, 'status': 'succeeded', 'total': row['total'], 'offset': offset, 'limit': limit,
                    'next_offset': next_offset if next_offset < row['total'] else None, 'model_version': row['model_version'],
                    'predictions': [json.loads(item[0]) for item in items]}

    def claim(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            self.cleanup(db)
            row = db.execute("SELECT job_id FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running',started_at=? WHERE job_id=?", (now(), row[0]))
            return row[0]

    def items(self, job_id, offset, limit=64):
        with self.connection() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT payload FROM job_items WHERE job_id=? AND idx>=? ORDER BY idx LIMIT ?', (job_id, offset, limit))]

    def commit_chunk(self, job_id, offset, predictions):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,processed,total FROM jobs WHERE job_id=?', (job_id,)).fetchone()
            if row is None or row['status'] != 'running':
                return False  # DELETE won the race; never recreate its state/results.
            if row['processed'] != offset or offset + len(predictions) > row['total']:
                raise ValueError('Invalid worker progress')
            db.executemany('INSERT INTO job_results VALUES (?,?,?)', [(job_id, offset+i, json.dumps(p, ensure_ascii=False)) for i, p in enumerate(predictions)])
            db.execute('UPDATE jobs SET processed=? WHERE job_id=?', (offset+len(predictions), job_id))
            if offset+len(predictions) == row['total']:
                db.execute("UPDATE jobs SET status='succeeded',finished_at=?,expires_at=? WHERE job_id=?", (now(), expiry(), job_id))
            return True

    def fail(self, job_id):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='failed',finished_at=?,expires_at=?,error_code='inference_failed',error_message='Background inference failed.' WHERE job_id=? AND status='running'", (now(), expiry(), job_id))
