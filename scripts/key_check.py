"""Prove the organizers' key works the way the judges will use it, locally or on the hosted URL.

    $env:API_KEY = '...'      (or dot-source scripts/load_env.ps1)
    python -m scripts.key_check --base http://127.0.0.1:8000

Checks (PSF section 4 and OpenAPI Authorization):
  * the exact key is accepted as X-API-Key and as Authorization: Bearer
  * a wrong, truncated, extended and missing key are all 401 with WWW-Authenticate: Bearer
  * authorization comes before body parsing (a 401 even with a garbage body)
  * /health stays public
  * the key keeps working under concurrent load, on both header styles, with no failures
  * the key never appears in any response body or header

The key is read from the environment and is never printed.
"""
import argparse
import concurrent.futures
import os
import sys
import time
import httpx

BODY = {'ticket_id': 'key-check', 'channel': 'chat', 'text': 'My food has not arrived. Please refund me.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8000')
    parser.add_argument('--requests', type=int, default=300, help='total requests in the load phase')
    parser.add_argument('--workers', type=int, default=16)
    args = parser.parse_args()
    key = os.environ.get('API_KEY', '')
    if not key:
        sys.exit('API_KEY is not set in this shell. Run scripts/load_env.ps1 first.')
    base = args.base.rstrip('/')
    failures, leaked = [], []

    def check(name, ok):
        print(('PASS ' if ok else 'FAIL ') + name)
        if not ok:
            failures.append(name)

    def scan(response):
        if key in response.text or any(key in v for v in response.headers.values()):
            leaked.append(response.request.url.path)

    with httpx.Client(base_url=base, timeout=60) as client:
        health = client.get('/health')
        scan(health)
        check('GET /health is public and ready', health.status_code == 200 and health.json().get('status') == 'ok')

        for label, headers in (('X-API-Key', {'X-API-Key': key}), ('Bearer', {'Authorization': 'Bearer ' + key})):
            r = client.post('/predict', json=BODY, headers=headers)
            scan(r)
            check(f'exact key via {label} -> 200 with a prediction', r.status_code == 200 and 'category' in r.json())

        for label, headers in (('missing key', {}), ('wrong key', {'X-API-Key': 'wrong'}),
                               ('truncated key', {'X-API-Key': key[:-1]}), ('key + extra char', {'X-API-Key': key + 'x'}),
                               ('wrong bearer', {'Authorization': 'Bearer nope'})):
            r = client.post('/predict', json=BODY, headers=headers)
            scan(r)
            check(f'{label} -> 401 + WWW-Authenticate: Bearer',
                  r.status_code == 401 and r.headers.get('www-authenticate') == 'Bearer' and 'error' in r.json())

        r = client.post('/predict', content=b'{not json', headers={'Content-Type': 'text/plain'})
        scan(r)
        check('no key + garbage body -> 401 (auth precedes parsing)', r.status_code == 401)

        r = client.post('/predict/batch', json={'tickets': [dict(BODY)]}, headers={'X-API-Key': key})
        scan(r)
        check('exact key on /predict/batch -> 200', r.status_code == 200)
        r = client.post('/batch/jobs', json={'tickets': [dict(BODY)]}, headers={'Authorization': 'Bearer ' + key})
        scan(r)
        job = r.json().get('job_id') if r.status_code == 202 else None
        check('exact key on /batch/jobs -> 202', job is not None)
        if job:
            check('exact key on GET job status -> 200', client.get(f'/batch/jobs/{job}', headers={'X-API-Key': key}).status_code == 200)
            check('exact key on DELETE job -> 204 (own disposable job only)', client.delete(f'/batch/jobs/{job}', headers={'X-API-Key': key}).status_code == 204)

    def hit(i):
        headers = {'X-API-Key': key} if i % 2 else {'Authorization': 'Bearer ' + key}
        with httpx.Client(base_url=base, timeout=120) as c:
            return c.post('/predict', json={**BODY, 'ticket_id': f'load-{i}'}, headers=headers).status_code

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        codes = list(pool.map(hit, range(args.requests)))
    elapsed = time.perf_counter() - start
    good = sum(code == 200 for code in codes)
    check(f'{args.requests} concurrent requests ({args.workers} workers, both header styles): {good}/{args.requests} returned 200 in {elapsed:.1f}s', good == len(codes))
    check('the key never appeared in any response body or header', not leaked)
    print(f'\n{"ALL CHECKS PASSED" if not failures else str(len(failures)) + " CHECK(S) FAILED"}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
