# Official API contract checklist

Source: unchanged supplied OpenAPI 2.1.0 and Draft 2020-12 JSON schemas.

## GET `/health`

- Authentication: public.
- 200: `HealthResponse`; Service is ready.
- 503: `HealthResponse`; Model not loaded yet.

## POST `/predict`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- Request: `PredictRequest`.
- 200: `PredictResponse`; Prediction returned.
- Headers: `X-Request-ID`.
- 400: `ErrorResponse`; Request body is not valid JSON.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 413: `ErrorResponse`; Request body larger than the allowed size. Limit is about **1 MB** for `/predict`,
**5 MB** for `/predict/batch` and **25 MB** for `/batch/jobs`.
.
- 415: `ErrorResponse`; Content type is not application/json.
- 422: `ErrorResponse`; Valid JSON that fails validation. Examples: missing `channel` or `text`; `channel` not
one of `email`, `chat`, `call_transcript`; `text` empty or whitespace only; `text`
or `subject` not a string; `text` longer than 10,000 characters; `null` for a required
field.
.

## POST `/predict/batch`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- Request: `BatchRequest`.
- 200: `BatchResponse`; One prediction per ticket, same order as the request.
- Headers: `X-Request-ID`.
- 400: `ErrorResponse`; Request body is not valid JSON.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 413: `ErrorResponse`; Request body larger than the allowed size. Limit is about **1 MB** for `/predict`,
**5 MB** for `/predict/batch` and **25 MB** for `/batch/jobs`.
.
- 415: `ErrorResponse`; Content type is not application/json.
- 422: `ErrorResponse`; Valid JSON that fails validation. In addition to the single-ticket rules: `tickets`
missing, not an array, empty, or longer than 100; any item missing `ticket_id`; duplicate
`ticket_id` values. `details` must list every failing item with its `index`. No partial
results are returned.
.

## POST `/batch/jobs`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- Request: `BatchJobRequest`.
- 202: `BatchJobStatus`; Job accepted.
- Headers: `Location`, `Retry-After`, `X-Request-ID`.
- 400: `ErrorResponse`; Request body is not valid JSON.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 413: `ErrorResponse`; Request body larger than the allowed size. Limit is about **1 MB** for `/predict`,
**5 MB** for `/predict/batch` and **25 MB** for `/batch/jobs`.
.
- 415: `ErrorResponse`; Content type is not application/json.
- 422: `ErrorResponse`; Valid JSON that fails validation. In addition to the single-ticket rules: `tickets`
missing, not an array, empty, or longer than 100; any item missing `ticket_id`; duplicate
`ticket_id` values. `details` must list every failing item with its `index`. No partial
results are returned.
.
- 429: `ErrorResponse`; Too many active or queued jobs. Retry after the delay in `Retry-After`..
- Headers: `Retry-After`.

## GET `/batch/jobs/{job_id}`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- 200: `BatchJobStatus`; Current job state.
- Headers: `Retry-After`, `X-Request-ID`.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 404: `ErrorResponse`; No job with this id.
- 410: `ErrorResponse`; The job's retention period has passed and its results were discarded..

## DELETE `/batch/jobs/{job_id}`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- 204: `no body`; Job cancelled or discarded.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 404: `ErrorResponse`; No job with this id.

## GET `/batch/jobs/{job_id}/results`

- Authentication: X-API-Key or Bearer; API_KEY from environment; constant-time comparison.
- 200: `BatchJobResults`; Predictions for the requested page.
- Headers: `X-Request-ID`.
- 401: `ErrorResponse`; API key missing or invalid.
- Headers: `WWW-Authenticate`.
- 404: `ErrorResponse`; No job with this id.
- 409: `ErrorResponse`; The job has not succeeded yet (still queued or running), or it failed or was cancelled and has no results..
- 410: `ErrorResponse`; The job's retention period has passed and its results were discarded..
- 422: `ErrorResponse`; Valid JSON that fails validation. Examples: missing `channel` or `text`; `channel` not
one of `email`, `chat`, `call_transcript`; `text` empty or whitespace only; `text`
or `subject` not a string; `text` longer than 10,000 characters; `null` for a required
field.
.

## Cross-cutting checks

- POST order: auth 401 → content type 415 → byte limit 413 → JSON 400 → schema 422.
- Limits interpreted as 1, 5, 25 MiB respectively. YAML says approximately 1 MB and 5/25 MB without exact byte counts.
- Batch counts: 1–100 sync; 1–5,000 async. All IDs required and unique. Atomic validation; errors carry zero-based indexes.
- Every response validates against original JSON Schema; response conditionals enforce routing, distinct secondary, and nonurgent/null-secondary spam.
- All paths share the same stored artifact and predictor. Input extras are accepted but excluded from features.
- Results pagination: offset ≥0, limit 1–5,000; default whole result, stable order, next_offset or null.
- Four active jobs maximum, transactional admission; retention 24 hours; expiry tombstones; pending jobs fail as interrupted on restart.

## Source discrepancies and explicit extensions

- DATA_NOTES names language as an input; OpenAPI explicitly guarantees only channel/subject/text. OpenAPI wins; language is analysis only.
- Master file refers to a YAML filename containing v2, whose actual info.version is 2.1.0.
- Same Idempotency-Key with a different payload returns 409 idempotency_conflict. This safe policy is not specified by the YAML.
- Valid protected requests before readiness return 503 ErrorResponse as an operational extension. The YAML lists 503 only for health; clients should wait for public health 200.
- DELETE removes the row and returns 204, then 404, as the explicit DELETE description requires; cancelled is not subsequently pollable.
- Official guideline and build-guide PDFs were not supplied. Deadline, report page limit, and video length are taken from the master document and await PDF verification.
