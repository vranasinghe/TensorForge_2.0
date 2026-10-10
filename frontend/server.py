import csv
import io
import hmac
import os
import re
from pathlib import Path
import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse, Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
auth = HTTPBasic(auto_error=False)
BASE = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')
KEY = os.getenv('API_KEY')
USERNAME = os.getenv('DEMO_USERNAME')
PASSWORD = os.getenv('DEMO_PASSWORD')


@app.middleware('http')
async def same_origin_mutations(request: Request, call_next):
    origin=request.headers.get('origin')
    expected=f'{request.url.scheme}://{request.headers.get("host", "")}'
    if request.method in ('POST','DELETE') and origin and origin.rstrip('/') != expected:
        return JSONResponse({'error':{'message':'Cross-origin demo requests are not allowed.'}},status_code=403)
    return await call_next(request)


def private_session(credentials: HTTPBasicCredentials | None = Depends(auth)):
    if not USERNAME or not PASSWORD or not credentials:
        return False
    return hmac.compare_digest(credentials.username.encode(), USERNAME.encode()) and hmac.compare_digest(credentials.password.encode(), PASSWORD.encode())


def unauthorized():
    return JSONResponse({'error': {'code': 'unauthorized', 'message': 'Private demo credentials required.'}}, status_code=401, headers={'WWW-Authenticate': 'Basic realm="RideEat demo"'})


@app.get('/')
async def index(ok=Depends(private_session)):
    if not ok:
        return unauthorized()
    return HTMLResponse(Path(__file__).with_name('index.html').read_text(encoding='utf-8'), headers={'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'"})


async def limited_body(request, limit=25*1024*1024):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


@app.post('/api/import')
async def import_csv(request: Request, ok=Depends(private_session)):
    if not ok:
        return unauthorized()
    body = await limited_body(request)
    if body is None:
        return JSONResponse({'error': {'message': 'CSV exceeds 25 MB.'}}, status_code=413)
    try:
        reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig'), newline=''))
        if not {'ticket_id', 'channel', 'text'} <= set(reader.fieldnames or []):
            raise ValueError('CSV needs ticket_id, channel and text columns.')
        tickets = []
        for row in reader:
            tickets.append({k: row[k] for k in ('ticket_id', 'channel', 'text')} | {'subject': row.get('subject', '')})
            if len(tickets) > 5000:
                raise ValueError('CSV must contain at most 5,000 tickets.')
        if not tickets:
            raise ValueError('CSV has no tickets.')
    except (ValueError, UnicodeDecodeError, csv.Error) as exc:
        return JSONResponse({'error': {'message': str(exc)}}, status_code=422)
    return {'tickets': tickets}


@app.api_route('/api/{path:path}', methods=['GET', 'POST', 'DELETE'])
async def proxy(path: str, request: Request, ok=Depends(private_session)):
    if not ok:
        return unauthorized()
    if not re.fullmatch(r'health|predict(?:/batch)?|batch/jobs(?:/[a-f0-9-]+(?:/results)?)?', path):
        return JSONResponse({'error': {'message': 'Unknown demo operation.'}}, status_code=404)
    if not KEY:
        return JSONResponse({'error': {'message': 'Demo backend credential is not configured.'}}, status_code=503)
    body = await limited_body(request)
    if body is None:
        return JSONResponse({'error': {'message': 'Payload exceeds 25 MB.'}}, status_code=413)
    try:
        async with httpx.AsyncClient(timeout=35, follow_redirects=False) as client:
            response = await client.request(request.method, BASE+'/'+path, params=request.query_params,
                content=body, headers={'X-API-Key': KEY, 'Content-Type': 'application/json'})
    except httpx.RequestError:
        return JSONResponse({'error': {'message': 'Backend unavailable. Check that the API is running.'}}, status_code=502)
    return Response(response.content, status_code=response.status_code, headers={k: response.headers[k] for k in ('content-type', 'retry-after', 'location') if k in response.headers})
