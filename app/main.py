import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from app.config import Config
from app.errors import APIError, error_response
from app.jobs import Worker
from app.predictor import Predictor
from app.request_validation import Guard, parse_request
from app.schemas import validate
from app.storage import Store, ServiceLease


def checked(schema, value, status=200, headers=None):
    validate(schema, value)
    return JSONResponse(value, status_code=status, headers=headers)


def create_app(config=None, predictor=None, start_worker=True):
    config = config or Config()
    worker = None
    loading = threading.Event()

    @asynccontextmanager
    async def lifespan(app):
        nonlocal worker
        lease = ServiceLease(config.database)
        app.state.store = Store(config.database)
        app.state.store.recover()

        def load_model():
            nonlocal worker
            try:
                model = predictor or Predictor(config.artifacts)
                if not loading.is_set():
                    app.state.predictor = model
                    if start_worker:
                        worker = Worker(app.state.store, model)
                        worker.start()
            except Exception:
                logging.exception('Model could not be loaded; service remains unready.')

        loader = threading.Thread(target=load_model, name='model-loader', daemon=True)
        loader.start()
        yield
        loading.set()
        loader.join(timeout=10)
        if worker:
            await run_in_threadpool(worker.stop)
        lease.close()

    app = FastAPI(title='TensorForge RideEat', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
    app.state.predictor = None
    app.add_middleware(Guard, api_key=config.api_key)

    @app.exception_handler(APIError)
    async def api_error(request, exc):
        return error_response(exc)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(APIError(exc.status_code, {404: 'not_found', 405: 'method_not_allowed'}.get(exc.status_code, 'http_error'), str(exc.detail), headers=exc.headers))

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logging.error('Internal request error; details suppressed.')
        return error_response(APIError(500, 'internal_error', 'Internal service error.'))

    def model():
        if app.state.predictor is None:
            # Contract defines 503 only for health: clients must await health readiness.
            raise APIError(503, 'model_loading', 'Wait for /health readiness before predicting.')
        return app.state.predictor

    @app.api_route('/health', methods=['GET', 'HEAD'])
    async def health(request: Request):
        p = app.state.predictor
        status_code = 200 if p else 503
        # HEAD: return status code only — no body. Render uses HEAD for health checks.
        if request.method == 'HEAD':
            return Response(status_code=status_code)
        return checked('HealthResponse', {'status': 'ok' if p else 'loading', 'model_version': p.version if p else None, 'model_loaded': p is not None}, status_code)

    @app.post('/predict')
    async def predict(request: Request):
        data = await parse_request(request, 'PredictRequest')
        return checked('PredictResponse', await run_in_threadpool(model().predict_one, data))

    @app.post('/predict/batch')
    async def batch(request: Request):
        data = await parse_request(request, 'BatchRequest')
        results = await run_in_threadpool(model().predict_many, data['tickets'])
        return checked('BatchResponse', {'predictions': results, 'meta': {'count': len(results), 'model_version': model().version}})

    @app.post('/batch/jobs')
    async def submit(request: Request):
        data = await parse_request(request, 'BatchJobRequest')
        key = request.headers.get('idempotency-key')
        if key is not None and len(key) > 128:
            raise APIError(422, 'validation_error', 'Idempotency-Key must be at most 128 characters.')
        result = await run_in_threadpool(app.state.store.submit, data['tickets'], model().version, key)
        return checked('BatchJobStatus', result, 202, {'Location': '/batch/jobs/' + result['job_id'], 'Retry-After': '3'})

    @app.get('/batch/jobs/{job_id}')
    async def status(job_id: str):
        result = await run_in_threadpool(app.state.store.status, job_id)
        return checked('BatchJobStatus', result, headers={'Retry-After': '3'} if result['status'] in ('queued', 'running') else {})

    @app.delete('/batch/jobs/{job_id}')
    async def delete(job_id: str):
        await run_in_threadpool(app.state.store.delete, job_id)
        return Response(status_code=204)

    @app.get('/batch/jobs/{job_id}/results')
    async def results(job_id: str, request: Request):
        try:
            offset = int(request.query_params.get('offset', '0'))
            limit = int(request.query_params['limit']) if 'limit' in request.query_params else None
            if offset < 0 or (limit is not None and not 1 <= limit <= 5000):
                raise ValueError()
        except ValueError:
            raise APIError(422, 'validation_error', 'offset must be >=0; limit must be an integer from 1 to 5000.')
        value = await run_in_threadpool(app.state.store.results, job_id, offset, limit)
        return checked('BatchJobResults', value)

    return app


app = create_app()
