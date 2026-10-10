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
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY scripts/start_api.sh /usr/local/bin/start-api
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /usr/local/bin/start-api
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start-api"]
