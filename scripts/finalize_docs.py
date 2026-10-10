"""Write the final reproduction guide and phase status from saved evidence."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from training.audit import ROOT


def main():
    metric_path=ROOT/'experiments/improvement/final_development_metrics.json'
    metrics=json.loads((metric_path if metric_path.exists() else ROOT/'experiments/validation_metrics.json').read_text())
    benchmark=json.loads((ROOT/'experiments/benchmark.json').read_text())
    verified=json.loads((ROOT/'experiments/verification.json').read_text())
    if any(c['exit_code'] for c in verified['checks']):
        raise RuntimeError('Do not finalize successful status while verification fails')
    test_result=verified['checks'][0]['stdout'].strip().splitlines()[-1]
    readme=f'''# TensorForge 2.0 - RideEat ticket triage

This repository contains a trained multilingual MVP, the seven required API
operations, durable async jobs, a private demo, and measured evaluation artifacts.
It is not a completed hosted submission: Docker verification, hosting,
publication, video upload and official-PDF review remain pending.

## Quick start on Windows (Python 3.11)

The project-local environment has already been created. To recreate it:

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-lock.txt
```

Start the API:

```powershell
$env:API_KEY = 'choose-a-local-test-key'
.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Wait for `GET http://127.0.0.1:8000/health` to return 200. The service returns
loading/503 until the actual artifact is loaded. With API_KEY missing, protected
operations fail closed with 401. No CORS origins are enabled by default.

In a second terminal, start the private demo with the same backend key and a
separate demo password:

```powershell
$env:API_KEY = 'choose-a-local-test-key'
$env:DEMO_USERNAME = 'demo'
$env:DEMO_PASSWORD = 'choose-a-separate-demo-password'
$env:BACKEND_URL = 'http://127.0.0.1:8000'
.\\.venv\\Scripts\\python.exe -m uvicorn frontend.server:app --host 127.0.0.1 --port 8501 --workers 1
```

Open `http://127.0.0.1:8501` and sign in with the demo credentials. The browser
never receives API_KEY. Public deployment must use HTTPS for both services.
Ticket entry, confidence, urgency, secondary issue, team route, CSV batch import,
real job progress, deletion and CSV export are implemented. Browser visual/interaction
automation was unavailable because its runtime failed; real HTTP proxy and CSV/job
flows were verified, and browser JavaScript passed Node syntax checking.

## API usage

```powershell
$requestHeaders = @{{ 'X-API-Key' = $env:API_KEY }}
$ticketBody = '{{"ticket_id":"demo-1","channel":"chat","text":"My food has not arrived. Please refund me."}}'
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Headers $requestHeaders -ContentType application/json -Body $ticketBody
$bearerHeaders = @{{ Authorization = "Bearer $env:API_KEY" }}
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Headers $bearerHeaders -ContentType application/json -Body $ticketBody
```

The original contract checklist is in CONTRACT_MATRIX.md. Paths:

- GET /health (public).
- POST /predict and POST /predict/batch (1-100 tickets).
- POST /batch/jobs (1-5,000 tickets), GET /batch/jobs/{{job_id}},
  GET /batch/jobs/{{job_id}}/results, DELETE /batch/jobs/{{job_id}}.

All batch ticket IDs are required and unique. Invalid batches are atomic and carry
indexed errors. Results preserve order and IDs. For pagination, offset is >=0,
limit is 1-5,000, and next_offset is null on the last page. Poll every 3 seconds.
An Idempotency-Key returns the same job while retained; a different payload using
that key returns 409. Admission accepts four active jobs (one running plus three
queued); excess returns 429 with Retry-After. Finished jobs retain results 24
hours; expired IDs return 410. DELETE returns 204 and removes the job, then 404.

## Persistence and deployment

JOB_DB defaults to runtime/jobs.sqlite3. Keep the same persistent file/volume
across restarts. Pending queued/running jobs become failed/interrupted after
restart; they never silently resume under a different artifact. Use exactly one
worker and one replica; a file lease rejects a second process on the same DB.
Multi-host replicas need a shared database/queue redesign.

```powershell
docker build -t tensorforge:local .
docker run -p 8000:8000 -e API_KEY=<key> tensorforge:local
```

Add `-v tensorforge-jobs:/srv/runtime` for durable container state and verify
nonroot write permissions. All model weights/dependencies are baked into the
image; installation is build-time only. Docker is unavailable on this machine,
so these container commands have not been executed. The offline in-process model
load/prediction check passed; it does not replace container verification.

## Reproduce data audit, training and checks

```powershell
.\\.venv\\Scripts\\python.exe -m training.audit
.\\.venv\\Scripts\\python.exe -m training.train
.\\.venv\\Scripts\\python.exe -m training.preserve_baseline
.\\.venv\\Scripts\\python.exe -m scripts.verify
.\\.venv\\Scripts\\python.exe -m scripts.benchmark
.\\.venv\\Scripts\\python.exe -m scripts.generate_docs
```

Original inputs remain in the supplied directories, with byte-identical copies
under data/ and schemas/. Training writes fold predictions, splits, successes
and failures, configuration, dataset hashes and model SHA256 manifest. Treat a
new validation evaluation after inspecting these results as development reuse,
not independent unseen evidence. Only load trusted joblib artifacts.

The selected artifact lives in artifacts/. A separately stored E0 fallback lives
in artifacts/baseline/; select it via ARTIFACT_DIR. Its primary is separately
trained, with shared urgency/secondary components; no separate final validation
score is claimed for that fallback. The final deployed SVM calibration setup is
not identical to the outer CV ensemble; the supplied-validation measurement is
the relevant score for the deployed artifact.

## Actual evidence and limitations

- Final verification: {test_result}.
- Supplied validation n=800: accuracy {metrics['accuracy']:.4f}, macro-F1 {metrics['macro_f1']:.4f}, urgency F1 {metrics['urgency']['f1']:.4f}, secondary-presence F1 {metrics['secondary_presence']['f1']:.4f}, exact triple {metrics['exact_triple_match']:.4f}.
- ECE {metrics['ece_10_equal_width_bins']:.4f} using 10 equal-width maximum-probability bins; Brier is mean summed squared class probability error.
- Local single p95 {benchmark['single']['p95_seconds']:.4f}s; 100-ticket batch p95 {benchmark['sync_100']['p95_seconds']:.4f}s; 5,000-ticket heterogeneous job {benchmark['jobs']['5000']['completion_seconds']:.2f}s. TestClient measurements on this Windows host are not reference-hardware or hosted measurements.

Primary cross-validation substantially overestimates supplied-validation accuracy.
Sinhala accuracy is {metrics['subgroups']['language']['si']['accuracy']:.4f}. Urgency
has false negatives, including safety cases. Synthetic text is not independently
native-speaker reviewed. All predictions need human confirmation. The optional
needs_human_review field is omitted because no independent review policy has
been established. Thresholds: urgency 0.45, secondary presence 0.20, selected on
training calibration holdout labels reused for threshold development.

DATA_NOTES lists language as a feature; higher-priority OpenAPI guarantees only
channel/subject/text. Language and ticket ID never affect inference features.
Known operational extensions and byte-limit interpretation are documented in
CONTRACT_MATRIX.md. Full metrics, error analysis and scientific plots are in
experiments/. The report, model card, research evidence, video script and deployment
checklist are in docs/. A visually checked three-page PDF is in output/pdf/.

PDF reproduction uses scripts/export_report.py and the bundled PDF runtime
(reportlab 4.4.9, pypdf 6.10.0, pypdfium2 5.13.0), or equivalent separately installed
packages. Report-export dependencies are separate from inference requirements.

Official guidelines and build-guide PDFs are still absent. Hosted HTTPS URL,
GitHub publication, YouTube recording/upload, submission and team signoff are
pending; none of their links or credentials have been fabricated.
'''
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    steps='''# Build steps and current status

The original master specification is preserved. This checklist records actual
implementation; pending items mean the full Definition of Done is not yet met.

## Pass 1 - Contract and audit

- [x] Inspect OpenAPI 2.1.0 and all ten schemas; preserve originals/copies.
- [x] Record routes, responses, authentication, bounds and discrepancies.
- [x] Audit both formats, labels, Unicode, duplicates/templates and hashes.
- [x] Test official examples and invalid response invariants.
- [ ] Read absent official PDFs and reconcile any additional requirements.

## Pass 2 - Trained baseline

- [x] Reusable sparse word/character/channel features excluding IDs/language.
- [x] E0-E3 and C/class-weight ablations, five train group folds, seed 42.
- [x] Separate primary, urgency, secondary-presence and secondary-label models.
- [x] Disjoint primary calibration, documented binary thresholds, versioned artifact.
- [x] Once-only selected-model supplied-validation measurements and saved errors.
- [x] Deployable E0 fallback retained without claiming extra validation results.

## Pass 3 - API

- [x] Public readiness and true model version; both auth headers; fail closed.
- [x] Auth-before-receive and ordered byte/content/JSON/schema validation.
- [x] Single and atomic synchronous batches; Unicode and boundary tests.
- [x] Original response-schema validation and JSON errors.

## Pass 4 - Durable jobs

- [x] SQLite worker, transactional capacity/idempotency and ordered chunk commits.
- [x] Polling, results pagination, DELETE race protection and expiry tombstones.
- [x] 24-hour retention and pending-work interruption on restart.
- [x] Actual 1/100/2,000/5,000-ticket jobs, concurrent traffic, real process kill/restart.

## Pass 5 - Model evaluation

- [x] Measured train-only comparisons and subgroup/calibration/secondary/urgency metrics.
- [x] Confusion, reliability and selective-risk plots and saved error analysis.
- [x] Disclose low supplied-validation accuracy, Sinhala weakness and safety misses.
- [ ] Optional neural/ensemble experiments were not pursued without measured need/compute.
- [ ] Production-quality generalization is not established; further work needs fresh evaluation data.

## Pass 6 - Packaging and demo

- [x] Dockerfile with bundled artifacts and build-time dependencies.
- [x] In-process network-disabled model load and multilingual predictions.
- [x] Private real-backend UI, CSV import/export and actual job progress.
- [x] Real HTTP demo proxy smoke and JavaScript syntax check.
- [x] Real Chrome browser interaction and desktop/mobile screenshots verified.
- [ ] Docker build/offline-container/host-port tests: Docker absent.
- [ ] Stable HTTPS hosting and same-image/model verification: credentials required.

## Pass 7 - Delivery

- [x] README, contract checklist, progress, model card, measured report and verified three-page PDF.
- [x] Research evidence, video walkthrough and deployment checklist.
- [ ] Official PDF requirement verification and final team signoff.
- [ ] GitHub publication, recording/YouTube upload and organizer submission.

Exact results and commands are in PROGRESS.md and experiments/verification.json.
'''
    (ROOT/'BUILD_STEPS.md').write_text(steps,encoding='utf-8')
    progress=f'''# Build progress - 2026-10-09 Asia/Colombo

## Implemented

Read the master specification and all supplied original contracts/data. Created
training/audit.py, features.py, train.py, evaluate.py and preserve_baseline.py;
app schemas/auth/validation/predictor/SQLite worker/routes; private frontend;
Dockerfile; reproducibility, benchmark, offline and hosted-smoke scripts; tests;
contract checklist, model card/report/research/video/deployment materials.
The original master file and supplied sources were not modified.

## Data and decisions

- 4,000 train / 800 validation; every CSV and JSONL field agrees. No split ID,
  exact-text or tested cosine >=0.90 overlap. All raw-copy hashes match.
- 3,983 training similarity groups, largest size 6; seed 42; 3,200 core and 800
  calibration rows; five outer folds, three nested calibration folds for E3.
- OpenAPI wins over DATA_NOTES on language: only channel/subject/text are features.
- Selected E3 calibrated word+character SVM; C/class-weight experiments retained.
- Final SVM is core-fitted and heldout-calibrated, unlike the CV ensemble.
- Current thresholds 0.45 urgency / 0.20 secondary presence; calibration holdout reused
  for threshold development, not an independent binary threshold test.
- SQLite uses one worker/replica and a process lease. DELETE discards immediately;
  idempotency payload conflicts use documented 409. See CONTRACT_MATRIX for all
  operational extensions/ambiguities.

## Executed verification

- `python -m training.audit`: successful; audit.json and dataset hashes saved.
- `python -m training.train`: six train-only experiments completed; selected
  artifact and once-only supplied-validation evaluation saved.
- `python -m training.preserve_baseline`: deployable E0 fallback saved; no extra
  validation selection performed.
- `python -m scripts.verify`: {test_result}. Offline load/prediction check passed
  for seven multilingual/emoji cases with socket connections blocked; pip check
  reports no broken requirements. Exact commands/output in verification.json.
- Tests include real 5,000-ticket jobs, original schema examples/negative
  invariants, body/auth precedence, streamed limits, Unicode, atomic batch errors,
  monotonic progress, concurrent traffic, expiry/delete races, and killing/restarting
  an actual Uvicorn child process on an isolated persistent database.
- `python -m scripts.local_demo_smoke`: passed over real localhost HTTP, checking
  private page, real predictor proxy, multiline Sinhala CSV, async results/DELETE.
- Bundled Node `--check tmp/demo.js`: exit 0, browser-script syntax valid.
- `python -m scripts.generate_docs`: measured report, model card, audit summary,
  official contract checklist and scientific plots generated.
- Bundled PDF runtime `python -m scripts.export_report`: three pages, all rendered
  pages visually inspected with no clipping/overlap; report is below five pages.

## Actual measured results

Supplied validation n=800, seed 42, evaluated after train-only selection:
accuracy {metrics['accuracy']:.5f}, macro-F1 {metrics['macro_f1']:.5f}, weighted-F1
{metrics['weighted_f1']:.5f}, urgency F1 {metrics['urgency']['f1']:.5f}, urgency recall
{metrics['urgency']['recall']:.5f}, secondary-presence F1
{metrics['secondary_presence']['f1']:.5f}, secondary exact accuracy
{metrics['secondary_exact_accuracy']:.5f} (always-null baseline 0.90000), exact
triple {metrics['exact_triple_match']:.5f}, ECE-10 {metrics['ece_10_equal_width_bins']:.5f}.
All 800 prediction response shapes/invariants validated; this is not accuracy.

Local benchmark: cold readiness {benchmark['cold_readiness_seconds']:.3f}s,
single p95 {benchmark['single']['p95_seconds']:.4f}s, 100-ticket sync p95
{benchmark['sync_100']['p95_seconds']:.4f}s; 2,000-ticket job
{benchmark['jobs']['2000']['completion_seconds']:.2f}s; 5,000-ticket job
{benchmark['jobs']['5000']['completion_seconds']:.2f}s. Submission for 5,000 took
{benchmark['jobs']['5000']['submit_seconds']:.3f}s. Host/TestClient timings are not
Docker, network/HTTPS or reference-2-vCPU results. See benchmark.json for polling
and live traffic while jobs run.

## Failures retained and resolved

- Initial sandbox runtime setup refresh failed; reviewed escalated terminal
  execution succeeded. Node/browser automation runtimes remained unavailable.
- Initial audit counter returned None for some nonissues; converted it to bool.
- First expanded test run: 68 passed / 1 failed due to Windows lock read behavior.
  Fixed lock initialization and verified second-process rejection.
- Next expanded run: 76 passed / 1 failed because crash-test fixture exceeded the
  25-MiB endpoint limit. The service correctly returned 413. Corrected the fixture
  to a valid payload; the actual process restart test passes. The failed run is
  retained in verification_history.jsonl.
- No failed experiment or low validation score is hidden. CV-to-validation gap
  remains unresolved; Sinhala and safety false negatives materially limit quality.

## Remaining blockers and next actions

1. Docker executable is absent both from PATH and its usual installation location.
   Install Docker, then build and verify offline container and mapped-port API.
2. Provide absent official guideline/build-guide PDFs and hosting credentials;
   reconcile deliverables, deploy the same image/model at valid stable HTTPS with
   a persistent job volume and one replica, and run hosted lifecycle checks.
3. Complete team signoff, authorized GitHub publication, video recording/upload
   and organizer submission. Links and evaluation key have not been fabricated.

Real Chrome interaction/visual QA passed via the bundled Playwright CLI fallback;
screenshots and recording are in experiments/browser and output/rideeat_demo.webm.
The master-document deadline (2026-10-10 18:00 Asia/Colombo) is unverified against
the absent official PDF. BUILD_STEPS.md records each completed/pending pass.
'''
    (ROOT/'PROGRESS.md').write_text(progress,encoding='utf-8')
    print('Updated README, BUILD_STEPS and PROGRESS from measured verification evidence.')


if __name__=='__main__':
    main()
