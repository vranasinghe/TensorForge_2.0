# TensorForge 2.0 — Phase 2 Codex Master Build Instructions

> **Purpose:** Paste this file into the root of a Codex workspace as `AGENTS.md` (or ask Codex to read it). Build a complete, scientifically evaluated, API-compliant, offline-capable RideEat multilingual support-ticket classification and routing MVP. **Do not treat this file as proof that the system is implemented.** Every completion claim must be demonstrated by code, tests, and actual metrics.
>
> **Deadline:** 2026-10-10 18:00 Asia/Colombo. Prioritize a functioning tested submission over speculative upgrades. Reserve time for the deliverables.
>
> **Authority order:** (1) `tensorforge-phase2-openapi-v2.yaml` and ten JSON Schema files including the master `tensorforge-schemas.json` for service behavior; (2) Phase 2 official guidelines and `DATA_NOTES.md` for deliverables and labeling policy; (3) `TensorForge2_Build_Guide.pdf` for nonbinding implementation suggestions; (4) this instruction document and external research. Where sources disagree, explicitly document the discrepancy and prefer the authoritative contract rather than silently guessing.

## 0. Codex mission and working rules

Build actual executable files, not mockups, pseudocode, promises, or a design-only response. Inspect the existing workspace first. If source assets are not in the Codex workspace, request them instead of inventing their content. Work iteratively, run tests, fix defects, and report evidence. Do not claim an experiment succeeded unless it was actually run. Keep a concise `PROGRESS.md` with completed work, command outputs, decisions, blockers, and remaining tasks. Never fabricate accuracy, F1, calibration, latency, research findings, deployment URLs, or video links. Do not expose the evaluation `API_KEY` to frontend JavaScript, committed files, Docker image layers, logs, artifacts, or reports.

**Definition of Done:** Tests validate all required API operations and schemas; own trained model produces predictions in English/Sinhala/Tamil/Singlish/Tanglish/mixed text; async jobs survive service restarts with correct terminal state; offline Docker startup and hosted HTTPS API work; real UI calls the backend; training and validation artifacts, README, report, and video preparation materials exist. Final external actions (hosting, GitHub publication, YouTube upload, submission) require credentials and must be reported as pending if not executed.

## 1. What the project does

Create an AI-assisted classification and routing system for the *fictional* RideEat ride-hailing and food-delivery platform. It receives a support ticket via `email`, `chat`, or `call_transcript`, using only the **guaranteed inference inputs** `channel`, optional `subject`, and `text`. Return:

- `category`: exactly one of 11 primary categories.
- `secondary_category`: another genuinely present issue if applicable, otherwise explicit JSON `null`.
- `is_urgent`: a boolean for immediate human attention, not an anger detector.
- `team`: deterministic lookup from the primary category, **never independently predicted**.
- `confidence`: calibrated estimate of correctness of the **primary** category in `[0,1]`.
- `model_version`: nonempty version tied to a reproducible stored model artifact.
- `ticket_id`: echo when supplied; required and unique within synchronous and asynchronous batch requests.
- Optional `needs_human_review`: decision based on an evaluated review policy, with README explanation.

The competition discourages simply wrapping a general-purpose LLM for classification. Train and validate the prediction models yourself. Do not make any LLM/API calls in inference, and do not require internet at container runtime.

### Exact category-to-team map

| `category` | `team` |
|---|---|
| `payment_refund` | `Payments & Refunds` |
| `ride_trip_issue` | `Ride Operations` |
| `lost_item` | `Lost & Found` |
| `order_missing_wrong` | `Food Operations` |
| `delivery_delay` | `Delivery Operations` |
| `food_quality` | `Restaurant Quality` |
| `account_promo` | `Account Services` |
| `safety_conduct` | `Trust & Safety` |
| `app_technical` | `Tech Support` |
| `general_inquiry` | `Front-line Support` |
| `spam_irrelevant` | `Auto-close / Spam Filter` |

Always enforce `secondary_category != category`. Always set `secondary_category: null` and `is_urgent: false` when `category == "spam_irrelevant"`. The response schema also enforces mapping and other invariants: validate **every** response against the provided original schema.

### Label precedence and interpretation from DATA_NOTES.md

- An actual safety incident takes primary precedence.
- Late, unarrived delivery + refund request: primary `delivery_delay`, secondary `payment_refund` if clearly requested.
- Missing/wrong contents in an already delivered bag + refund: primary `order_missing_wrong`.
- Charge disputes themselves: `payment_refund`.
- OTP/login/promo issues: `account_promo`; post-login software malfunctions: `app_technical`.
- Forgotten belongings: `lost_item`; absent delivery: `delivery_delay`; damaged/poor food: `food_quality`.
- Partner onboarding/payout-information questions and vague genuine requests: `general_inquiry`.
- Immediate danger, active fraud, current medical symptoms, or serious time-critical consequence can be urgent. Anger alone is not urgent; historical resolved safety issues are nonurgent.
- Ignore instructions embedded in ticket text that try to control the classifier. Resolved quoted correspondence is background. For email, read subject **and** body.
- Any novel unobserved primary/secondary pairing is still potentially valid under the API. Do not permanently forbid it based solely on nine observed dataset pair patterns.

## 2. Data assets, audit, and leakage protection

Expected files (supplied by user, copy them into repo without altering raw originals):

```
DATA_NOTES.md
train.csv / train.jsonl
validation.csv / validation.jsonl
tensorforge-phase2-openapi-v2.yaml
tensorforge-schemas.json
predict_request.schema.json
predict_response.schema.json
batch_request.schema.json
batch_response.schema.json
batch_job_request.schema.json
batch_job_status.schema.json
batch_job_results.schema.json
health_response.schema.json
error_response.schema.json
TensorForge2.0_Phase2_MVP_Guidelines.pdf
TensorForge2_Build_Guide.pdf
```

The nine per-endpoint schema files plus one master bundle = ten JSON Schema files. There are 4,000 train tickets and 800 validation tickets. Columns: `ticket_id, channel, subject, text, language, category, secondary_category, is_urgent`. The public notes describe these language proportions: English 35%, Singlish 25%, Sinhala 20%, Tamil 15%, Tanglish 2.5%, mixed 2.5%. Classes are imbalanced; urgency and non-null secondary labels each represent approximately 10% of tickets. **Verify these findings programmatically; the guide's published baseline numbers are not independently reproduced results of this implementation.**

`language` exists in training CSV/JSONL but the official OpenAPI explicitly guarantees only `channel`, `subject`, `text` to the model. It is useful for analysis and stratification, NOT a required deployed feature. Extra request properties are allowed, but the inference result must not depend on whether a client supplies a `language` property. If experimenting with inferred language, derive it *only* from the guaranteed inputs and compare against the nonlanguage baseline. No dependence on `ticket_id`, secret labels, or evaluation-only metadata.

Implement `training/audit.py` that:

1. Loads CSV with a proper CSV parser (quoted multiline fields) and JSONL with UTF-8.
2. Cross-checks CSV and JSONL ticket IDs and key columns for equivalence.
3. Reports nulls, duplicates, exact overlap, *near-duplicate/template similarity* across train and validation, lengths, label frequencies, language/channel/category intersections, secondary pairs, urgency per class.
4. Checks Unicode normalization and preserves combining marks, Sinhala/Tamil scripts, transliteration, emoji, mixed-script contents, newlines and speaker labels.
5. Computes SHA256 dataset hashes and saves an audit report and manifest.
6. Notes datasets are synthetic; Sinhala/Tamil/transliteration was not independently reviewed by native speakers, so benchmark scores are not claims about real customer support.

Prevent leakage: never include labels or ticket ID as inference features; fit vectorizers inside each CV training fold; fit calibration and thresholds without peeking at corresponding evaluation labels; keep final validation minimally touched. Split by template group if near-duplicates are substantial. Document limitations.

## 3. Model roadmap: measured experiments before selection

Implement a shared, deterministic `predict_one({channel,subject,text,ticket_id?})` function, used identically by all API paths. Train separate supervised components for:

1. **Primary class:** multiclass classifier over 11 categories.
2. **Urgency:** binary classifier; tune recall/precision and threshold; analyze high-cost safety false negatives.
3. **Secondary:** first classify whether a genuinely distinct second issue exists, then predict its category; compare against a multilabel issue model if time permits. Do **not** treat the second-highest primary class score as proof of a second issue. Training set contains relatively few secondary-positive examples, so report minority-label uncertainty.
4. **Routing:** pure fixed map, not an ML target.
5. **Calibration:** use held-out or out-of-fold calibration; `confidence` must refer only to primary classification; optional human review on validated threshold.

### Experiment schedule

- E0: word TF-IDF (1–2 grams) + LogisticRegression; one-hot channel; subject/body composed clearly without losing information.
- E1: character `char_wb` TF-IDF (2–5 grams) + LogisticRegression.
- E2: word + character sparse TF-IDF + LogisticRegression.
- E3: word + character TF-IDF + LinearSVC, with Platt/sigmoid `CalibratedClassifierCV` fitted correctly.
- E4: tune `C`, class weights, char and word n-gram ranges, min_df and features using consistent folds.
- E5: optional subject/body-separated features, sentence-level pooling, inferred language, codebook-informed postprocessing; ablate one component at a time.
- E6: optional frozen multilingual encoder or fine-tuned XLM-R **only if local compute/time allow, own data measurements beat the CPU baseline, and its full weights/tokenizer work offline within memory and job throughput requirements**.
- E7: optional ensemble only if rigorous validation demonstrates gain.

Suggested first vectorizers: word `(1,2)` and character `(2,5)` with Unicode-aware processing; do not ASCII-fold Sinhala/Tamil, indiscriminately remove punctuation/emojis/stopwords, or use English-only stemming across languages. Keep word and character features sparse. Preserve important negation and subject/body boundaries. Check if numbers/order IDs cause overfitting and only mask after an ablation. Use class weights as a **tested choice**, not a default fact.

Train with fixed random seeds and preferably 5-fold stratified CV on training. Consider grouping if templates are reused. Save fold predictions, configuration YAML/JSON, confusion matrix, per-language/per-class tables, metrics and test-set predictions. The supplied `validation` split can support a documented development check, but avoid repeated model selection against it. Do not present a tuned validation number as an independent unseen test result.

### Metrics and acceptance evidence

- Primary: accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, confusion matrix.
- Secondary: positive-presence precision/recall/F1, secondary-label F1, exact-match including null; compare against always-null 90% accuracy trivial baseline.
- Urgency: precision, recall, F1, PR-AUC; by primary class, language, channel; threshold sensitivity.
- Calibration: multiclass log loss, Brier (state exact definition), expected calibration error (number of bins stated), reliability diagram, selective risk/coverage curves.
- End-to-end: exact triple match `(primary,secondary,urgency)`, correct team mapping, contract-pass rate.
- Robustness: per-language, per-channel; English, Sinhala, Tamil, Singlish, Tanglish, mixed; typos, quoted old complaints, code-switching, short/long, emoji-only, mixed scripts, transcript filler, prompt injections, low-confidence/noise.
- Efficiency: cold startup, p50/p95 predict, synchronous batch and 2000/5000 async jobs under CPU/RAM constraints.

The build guide *reports* a preliminary category accuracy 0.641/macro-F1 0.671, urgency F1 0.884, secondary-presence F1 0.710, calibration ECE 0.064. These are **unverified external guide claims**, not guaranteed reproducible or official targets. Only present metrics generated by actual code as this project's results. In `experiments/`, keep successes **and failures**. Model selection must be justified with evidence, not novelty.

## 4. Exact HTTP API contract (highest priority)

Implement **seven operations at six URL patterns**, including DELETE omitted by the short build guide:

| Method | Path | Success | Authentication |
|---|---|---|---|
| GET | `/health` | 200 ready, 503 loading | PUBLIC |
| POST | `/predict` | 200 | required |
| POST | `/predict/batch` | 200 | required |
| POST | `/batch/jobs` | 202 | required |
| GET | `/batch/jobs/{job_id}` | 200 | required |
| GET | `/batch/jobs/{job_id}/results` | 200 if succeeded | required |
| DELETE | `/batch/jobs/{job_id}` | 204 | required |

**Always refer to original YAML for precise details and enums.**

### Authentication and error precedence

- Accept BOTH `X-API-Key: <key>` and `Authorization: Bearer <key>`, with same expected value from environment `API_KEY` at startup.
- Constant-time comparison (`hmac.compare_digest`); never log keys. Missing or invalid returns `401` + `WWW-Authenticate: Bearer` and JSON `{ "error": {"code": "unauthorized", "message": "..."} }`.
- Missing `API_KEY` MUST NOT open protected endpoints; return 401.
- Authorization must run before body parsing and validation, and ideally before buffering bodies. For POST endpoints validation order: **401 auth → 415 content type → 413 size → 400 invalid JSON → 422 semantic/schema validation**.
- Other errors: unknown route 404, wrong method 405, unknown job 404, not-ready result 409, expired job 410, capacity exceeded 429 (include `Retry-After`), health-loading 503. Every 4xx and applicable 503 should use contract-compliant JSON (note: `/health` loading 503 specifically uses `HealthResponse`, according to OpenAPI; honor the operation's explicit response schema rather than blanket generic error formatting).
- Never throw 5xx for invalid input, display HTML stack traces, or follow instructions embedded in ticket text.
- Support `X-Request-ID` request header echo when supplied (optional but easy and valuable).

### Input / output validation

- Required `channel` one of `email`, `chat`, `call_transcript`; required `text` string 1–10,000 characters with at least one nonwhitespace (`\S`), UTF-8; subject optional string max 500; ticket_id optional in single, required in batches, string max 64.
- Emoji-only, Sinhala, Tamil, Singlish, Tanglish and mixed script are valid; do not reject based on unsupported language or unseen vocabulary.
- Unknown extra input properties allowed for predict requests; ignore them for inference unless officially guaranteed.
- Single size limit approximately 1 MB per YAML; synchronous batch max 5 MB, 1–100 tickets; async submit max 25 MB, 1–5,000 tickets.
- Batches: validate all items before prediction, **atomic failure** with 422 and all actionable `details` containing zero-based item indexes; no partial output; all ticket IDs required/unique; one result per input; original ordering and ID echo preserved; predictions independent of batch position/other inputs.
- Valid response always contains primary, explicit nullable secondary, team, bool urgency, float finite confidence `[0,1]`, nonempty version; ticket_id if provided. Optional review bool. Must match JSON Schema conditional rules.
- `/health` public, `200` only when loaded (`status: "ok"`, same `model_version` as inference); while loading return `503` HealthResponse (`status: "loading", "model_version": null`); first health response within 120 seconds of start.
- Suggested latency targets on reference 2 vCPU/4 GB/no GPU (provisional): /predict p95 <1s; /predict/batch 100 tickets p95 <30s; async submit up to 5000 tickets returns 202 in <5s; 2000 jobs <15 min, 5000 <30 min; health/poll p95 <1s while job runs. Guidelines say latency not scored; still engineer toward explicit YAML targets.

### Example `POST /predict`

Request:
```json
{"ticket_id":"TF-TEST-001","channel":"chat","subject":"","text":"My food has not arrived and I want a refund."}
```
Illustrative response *shape*, not actual model output:
```json
{"ticket_id":"TF-TEST-001","category":"delivery_delay","secondary_category":"payment_refund","team":"Delivery Operations","is_urgent":false,"confidence":0.78,"model_version":"sha256-EXAMPLE","needs_human_review":false}
```

## 5. Async batch job engine — mandatory correctness

Use SQLite for a **single-instance** persistent deployment; enable foreign keys, WAL when appropriate, busy timeouts, safe transactions, and indexed ordered access. Separate background inference from HTTP request threads/process handling. Avoid web request hangs while jobs run. Run same model/inference pipeline as `/predict`. Use a single CPU-aware worker for predictably limited resources. If deploying multiple replicas/workers, use truly shared durable job state/results and mutually safe job reservation; a local SQLite file isolated per replica is NOT sufficient.

Minimum conceptual tables:

```sql
CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
  total INTEGER NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, started_at TEXT,
  finished_at TEXT, expires_at TEXT,
  model_version TEXT NOT NULL,
  error_code TEXT, error_message TEXT,
  idempotency_key TEXT UNIQUE,
  payload_digest TEXT
);
CREATE TABLE job_items (
  job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  idx INTEGER NOT NULL, ticket_id TEXT NOT NULL,
  channel TEXT NOT NULL, subject TEXT NOT NULL DEFAULT '', text TEXT NOT NULL,
  PRIMARY KEY(job_id, idx), UNIQUE(job_id, ticket_id)
);
CREATE TABLE job_results (
  job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  idx INTEGER NOT NULL, prediction_json TEXT NOT NULL,
  PRIMARY KEY(job_id, idx)
);
```

This is an **implementation suggestion**, not an organizer-supplied schema. Design/delete/retention persistence requires more logic than DDL alone. Consider a lightweight tombstones table for expired IDs so they return 410 rather than 404 after results cleanup.

Behavior:

1. POST with valid 1–5000 tickets creates persisted job *only after validating every item*, returns `202`, job UUID, `Location: /batch/jobs/{job_id}`, `Retry-After` seconds. Respect optional `Idempotency-Key` (same key returns original `job_id`, no new work). For same idempotency key with different payload, document a safe handling policy; do not silently replace prior job.
2. Limit to at least one running + three queued jobs; excess returns 429 and `Retry-After`.
3. Worker runs jobs in small chunks, persists results in `idx` order, updates `processed` monotonically and never above `total`; state `queued -> running -> succeeded` or `failed/cancelled`. Ensure finished job has at least 6-hour retention; 24 hours is safe if resources permit.
4. On process startup find orphaned `queued`/`running` jobs and mark `failed` with `error.code: "interrupted"` and appropriate timestamps; never silently lose jobs. Note queued jobs after restart: contract says container restarting mid-job should end as failed; choose conservative interrupted marking and document behavior.
5. `GET /batch/jobs/{id}` returns required fields plus meaningful timestamps/model version/progress. Polling while ongoing includes Retry-After (2–5 seconds is suggested).
6. Results endpoint only when `succeeded`, otherwise 409; page using `offset >= 0`, `1 <= limit <= 5000`, default whole result, stable order and `next_offset` or `null`.
7. DELETE queued/running cancels/discards; DELETE finished discards; return `204`, then subsequent lookup returns `404` as specified. Make cancellation race-safe; workers must not commit results after delete. Handle unknown IDs 404.
8. Expired IDs return `410`, unknown IDs `404`; retain a lightweight expiry tombstone as necessary.
9. Idempotency, background jobs, status, results, and direct prediction must use the same **artifact/version**; predictions for identical tickets must not change with batch size or order.
10. Avoid test-only shortcuts (e.g., return fake 202 then synchronous processing on request thread).

## 6. Repo architecture to create

```text
.
├── AGENTS.md                       # this master specification (copy or symlink)
├── README.md
├── PROGRESS.md
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI startup, lifecycle, routes
│   ├── auth.py                     # both header mechanisms, 401 precedence
│   ├── request_validation.py       # content-type, limits, JSON, schemas
│   ├── models.py                   # request/response contracts
│   ├── errors.py                   # JSON errors including 404/405
│   ├── predictor.py                # single shared deterministic inference
│   ├── contract.py                 # fixed mapping, rules, validation
│   ├── storage.py                  # SQLite durable data model
│   ├── jobs.py                     # worker, queue, cancellation, polling
│   └── config.py                   # env vars, paths, versions
├── training/
│   ├── audit.py
│   ├── features.py                 # shared feature code with inference
│   ├── train.py
│   ├── experiment.py
│   ├── evaluate.py
│   ├── calibrate.py
│   └── error_analysis.py
├── schemas/                        # original user-supplied schemas
├── data/                           # raw files, keep intact
├── artifacts/                      # versioned model(s), manifest.json
├── experiments/                    # reproducible configs, metrics, plots
├── tests/
│   ├── test_contract.py
│   ├── test_auth.py
│   ├── test_predict.py
│   ├── test_batch.py
│   ├── test_jobs.py
│   ├── test_errors.py
│   ├── test_consistency.py
│   ├── test_unicode.py
│   ├── test_concurrency.py
│   └── test_restarts.py
├── frontend/                       # Streamlit fast demo OR compact HTML UI
├── docs/
│   ├── model_card.md
│   ├── report.md
│   ├── video_script.md
│   └── deployment_checklist.md
└── scripts/
    ├── test_local.sh
    ├── test_offline.sh
    ├── benchmark.sh
    └── smoke_hosted.sh
```

For deadline speed, choose Python 3.11, FastAPI, Pydantic v2, Uvicorn, numpy/pandas/scikit-learn/scipy/joblib, jsonschema, pytest/httpx, SQLite; frontend Streamlit or a simple static page. Do not add React/Postgres/Supabase unless already built and demonstrably beneficial. Pin tested versions in requirements and record environment. Avoid an authentication-insecure frontend: keep `API_KEY` server-side and proxy dashboard predictions through a private/backend session, or use a separate demo credential appropriately isolated from evaluation. Document allowed CORS origins.

## 7. Implement in the following passes (do not skip tests)

### Pass 1 — Contract and data audit

- Read the YAML + JSON bundle; write `CONTRACT_MATRIX.md` with all routes, request/response schema references, statuses, auth, headers, body limits, batch rules.
- Implement canonical enums and exact team map; validate static example responses against `tensorforge-schemas.json` with Draft202012Validator.
- Implement raw input audit and report. Identify missing `language` guarantee.
- **Exit test:** all contract example/negative fixtures pass correctly, all data format checks reproducible.

### Pass 2 — Trained baseline model

- Write `training/features.py` as reusable transform with no private labels or IDs.
- Run E0–E3 and fold validation; store results and one chosen artifact.
- Train independent urgency and secondary tasks, calibrate primary confidence, select policy threshold.
- Export `artifacts/manifest.json` with SHA256, model ID/version, training dataset hashes, hyperparameters, package versions, evaluation date; use exact version in all response modes.
- **Exit test:** predictions repeat across runs, comply with consistency rules, no dependency on `language`/ticket_id; real measured metrics are saved.

### Pass 3 — Contract-compliant API

- Implement startup model loading and public health readiness.
- Auth before parsing; correct content type/size/JSON/schema sequence; structured errors.
- Single and 1–100 ticket synchronous batch paths using same predictor.
- Exhaustive response schema validation.
- **Exit test:** 200/401/413/415/400/422 tests and Unicode edge cases pass.

### Pass 4 — Persistent async jobs

- Create durable SQLite schema and background worker; add submit, status, results, DELETE routes.
- Add queue capacity 429, idempotency, request-order results, pagination, six-hour retention, 410 tombstones, restart handling and cancellation race guards.
- **Exit test:** 1, 100, 2000 and 5000 ticket jobs complete in correct order, polling stays responsive, restart is represented, delete works, pagination stable.

### Pass 5 — Improve the model systematically

- Run ablation experiments on primary and diagnostic tests on safety, minority categories, Sinhala, Tamil, Tanglish, mixed, secondary presence and urgency.
- Upgrade only when macro-F1 and meaningful subgroup results improve with acceptable CPU/RAM cost; preserve baseline fallback.
- Produce plots/report tables from files generated by running code.
- **Exit test:** final model choice justified by real results, no imaginary improvements.

### Pass 6 — Docker and real UI

- Bake weights, vectorizer, all dependencies into a Docker image. Listen `0.0.0.0:8000`.
- Docker command exactly: `docker run -p 8000:8000 -e API_KEY=<key> <image>`.
- Test zero network dependencies **inside container**. Caution: `docker run --network none -p 8000:8000` cannot serve as an ordinary host-port API check; do offline-dependency and networked-port integration checks separately. An offline smoke test may use `docker exec` or a Python in-container localhost test while network is disabled.
- Create working demo with ticket entry, results, confidence, review state, CSV batch, async progress and export; optionally metrics charts from genuine evaluation results. No fake counters.
- Deploy exactly same image/model to stable HTTPS URL with valid TLS. Persist SQLite on mounted volume if hosted environment is ephemeral; one replica unless shared DB implemented.
- **Exit test:** local and hosted API contract smoke tests pass; `/health` reports exact artifact version; Docker needs no internet at runtime.

### Pass 7 — Deliver and demonstrate

- Complete README (setup, training, inference, auth header examples, Docker, jobs, known limitations, threshold, test commands).
- `docs/model_card.md`: data provenance, synthetic-language limitations, training setup, group-level metrics, intended and prohibited uses, ethics.
- `docs/report.md`: at most five pages when exported; method, results, architecture, robust API, limitations, references.
- `docs/video_script.md`: 15-minute walkthrough, architecture, actual training validation, experiments, dashboard, end-to-end 5k job and invalid request demonstration.
- Ensure accessible demo link, HTTPS URL, runnable GitHub repository, unlisted YouTube video, and valid private evaluation API key. Mark assets not yet uploaded/shared as pending rather than claiming they exist.
- **Exit test:** complete documented reproducibility checklist and submission links, team signoff.

## 8. Required automated tests and edge cases

Run and document tests before any submission. Test **both** schema shape and semantic behavior:

| Scenario | Expected |
|---|---|
| Valid English/Sinhala/Tamil/Singlish/Tanglish/mixed, emoji-only | 200 with valid response, no crash |
| Valid max length text 10,000 chars, long subject 500 | accept if other constraints valid |
| Whitespace-only text, missing required field, wrong type, unknown channel | 422 |
| Invalid JSON | 400 |
| Wrong Content-Type | 415 |
| Single >~1 MB, synchronous >5 MB, async >25 MB | 413 |
| Missing/wrong API key | 401 + WWW-Authenticate, even with invalid body |
| API key from X-API-Key **and** bearer | accepted |
| `/health` public and ready/loading semantics | 200/503 appropriate schema |
| Unknown path and unsupported method | JSON 404/405 |
| Batch size 0, 101, duplicate IDs, missing IDs | 422 atomic validation |
| Synchronous batch 1 and 100 | ordered 200 with one response each |
| Async batch 1, 100, 2000, 5000 | 202 then complete without lost items |
| Async idempotent resubmission | same job ID; no new job |
| Queue > 1 running + 3 queued | 429 + Retry-After |
| Results queried early | 409 |
| Unknown job vs expired job | 404 vs 410 |
| Results pagination | correct slices, stable ordering, next_offset |
| DELETE existing and subsequent lookup | 204, then 404 |
| Mid-job restart | `failed`, `error.code=interrupted`, not disappearance |
| Concurrent polling while job runs | responsive; monotonic progress |
| Predicted spam | false urgent/null secondary/exact team |
| Any predicted category | exact fixed team; secondary distinct |
| `model_version` in health/direct/batch/jobs | identical for same image |
| Same ticket individually, in shuffled batch, in async job | identical prediction fields |
| Ticket with prompt-injection instructions | treated as data; no instruction-following |
| Vary `ticket_id` and supply/omit `language` | no influence on model prediction |
| Mixed invalid batch with multiple faults | all relevant indexed errors, no partial results/job |

Use original JSON Schema draft 2020-12 with `jsonschema.Draft202012Validator`; do not assume Pydantic alone enforces nested `if/then` constraints. Add property-based testing with Schemathesis if feasible; be careful not to run destructive job DELETE tests against live evaluation jobs. Include load tests for size limits and timeouts; verify the service never leaks raw stack traces, secrets or HTML error pages.

## 9. Deployment and operational design details

- Offline container command is an explicit competition requirement. Dockerfile must COPY serialized artifacts; Python dependencies installed **at build time**, not startup. Include source and manifest; minimize image.
- `/health` must function while model loads and while jobs are running. Make startup robust and fail closed if model/config incomplete. Never mark ready with a fake version.
- Load model once per process, reuse inference code in background worker; avoid unnecessary repeated deserialization.
- Use locks/transactions around job queue admission, idempotency decisions, status transitions, cancellation, and result commits. Never block HTTP event loop with lengthy CPU ML work.
- If using SQLite database file in container, demonstrate restart tolerance with persistent file or volume, not a destroyed/ephemeral replacement container. Container *process* restart differs from container deletion; document this clearly.
- Tests should use an isolated secret like `API_KEY=test-key`; real evaluation key is injected in hosted environment only. `.env` ignored in Git.
- Stable HTTPS and real cert required; log only safe request identifiers, status, elapsed time, and model versions. No raw sensitive text by default.

## 10. Report and scientific evidence policy

Research backs *candidate approaches*, not performance claims on this dataset. Relevant literature to verify and cite accurately:

1. Cortes & Vapnik (1995), **Support-Vector Networks**, https://doi.org/10.1007/BF00994018 — foundations of SVM.
2. Joulin et al. (2017), **Bag of Tricks for Efficient Text Classification**, https://aclanthology.org/E17-2068/ — efficient text classifiers (not direct proof of TF-IDF superiority).
3. Conneau et al. (2020), **Unsupervised Cross-lingual Representation Learning at Scale**, https://aclanthology.org/2020.acl-main.747/ — XLM-R multilingual representation.
4. Guo et al. (2017), **On Calibration of Modern Neural Networks**, https://proceedings.mlr.press/v70/guo17a.html — why confidence calibration needs measurement.
5. Saito & Rehmsmeier (2015), **The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets**, https://doi.org/10.1371/journal.pone.0118432 — urgency/secondary PR metrics.
6. Kohavi (1995), **A Study of Cross-Validation and Bootstrap for Accuracy Estimation and Model Selection**, https://www.ijcai.org/Proceedings/95-2/Papers/016.pdf — cross-validation.
7. Niculescu-Mizil & Caruana (2005), **Predicting Good Probabilities With Supervised Learning** — calibrated outputs; verify exact publication URL and applicability before citing.
8. Mitchell et al. (2019), **Model Cards for Model Reporting**, https://dl.acm.org/doi/10.1145/3287560.3287596 — subgroup reporting and limitations.
9. Kapoor & Narayanan (2023), **Leakage and the Reproducibility Crisis in Machine-Learning-based Science**, https://doi.org/10.1016/j.patter.2023.100804 — data leakage; verify exact bibliographic details before final report.
10. Geifman & El-Yaniv (2017), **Selective Classification for Deep Neural Networks** — selective risk/coverage; verify setting, assumptions and bibliographic entry.
11. Additional research candidates cited in build guide: Breck et al. ML Test Score; Amershi et al. Software Engineering for ML; Bojanowski et al. subword representations; Dhananjaya et al. BERTifying Sinhala; Chakravarthi et al. Tamil-English code-mixing; Hatfield-Dodds/Dygalo Schemathesis. Verify original papers, **do not claim char n-gram TF-IDF is directly proved by a subword-embedding paper**, and do not cite search snippets as if full papers were reviewed.

Create a `docs/research_evidence.md` table recording each engineering claim, exact source, whether abstract/full paper/official docs were checked, and actual experiment supporting applicability to RideEat. Do not claim official rubric weights or full marks; organizers only specify correctness, schema compliance and robustness. Respect benchmark uncertainty and synthetic dataset limitations.

## 11. Readable delivery/report instructions for Codex

For every phase, communicate:

- Files created/changed.
- Exact tests/commands run and pass/fail counts.
- Actual experimental metric values with split definitions and seed.
- Any deviations from original YAML or unresolved ambiguity.
- Blockers requiring user credentials/hosting/upload actions.
- Next 1–3 highest-priority tasks before deadline.

**Do not stop at documentation:** start creating repository files immediately once input files are available. After each step, run verification, fix regressions, and keep the simple baseline deployable. If time runs short, finish contract+API+jobs+Docker+minimal UI and required deliverables before expensive neural experiments.

## 12. First instruction to execute right now

> Inspect all provided artifacts, particularly the official OpenAPI v2.1.0 and JSON Schema bundle. Produce a short contract checklist, then initialize the Python/FastAPI repository and implement a verifiably valid `/health`, `/predict`, and `/predict/batch` with real trained baseline inference. Continue to persistent async jobs including DELETE; run official-schema tests; then improve the model and complete Docker/UI/reports. Never use fabricated measurements or endpoint behavior. If input files are unavailable, ask me to copy them into the workspace.
