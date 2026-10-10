FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 JOB_DB=/srv/runtime/jobs.sqlite3
WORKDIR /srv
COPY requirements-runtime-lock.txt ./
RUN pip install --no-cache-dir -r requirements-runtime-lock.txt && useradd --create-home tensorforge
COPY app ./app
COPY training ./training
COPY artifacts ./artifacts
COPY schemas ./schemas
RUN mkdir -p /srv/runtime && chown -R tensorforge:tensorforge /srv/runtime
USER tensorforge
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
