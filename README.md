# TensorForge 2.0 - RideEat ticket triage

This repository contains a trained multilingual MVP, the seven required API
operations, durable async jobs, a private demo, and measured evaluation artifacts.
It is not a completed hosted submission: hosting,
publication, video upload and official-PDF review remain pending. Local Docker
offline inference, API operations and actual mid-job persistent crash recovery
passed; reproduce with `python -m scripts.docker_verify` while Docker is running.

## Quick start on Windows (Python 3.11)

The project-local environment has already been created. To recreate it:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Start the API:

```powershell
$env:API_KEY = 'choose-a-local-test-key'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
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
.\.venv\Scripts\python.exe -m uvicorn frontend.server:app --host 127.0.0.1 --port 8501 --workers 1
```

Open `http://127.0.0.1:8501` and sign in with the demo credentials. The browser
never receives API_KEY. Public deployment must use HTTPS for both services.
Ticket entry, confidence, urgency, secondary issue, team route, CSV batch import,
real job progress, deletion and CSV export are implemented. Browser visual/interaction
automation was unavailable because its runtime failed; real HTTP proxy and CSV/job
flows were verified, and browser JavaScript passed Node syntax checking.

## API key handling (PSF section 4)

The organizers issue one evaluation key per team and the judges use that exact key.
The contract forbids hard-coding it, so it lives only in the environment:

- The service reads `API_KEY` at startup (`app/config.py`). Unset or empty means every
  protected endpoint answers 401; it never runs open. Comparison is constant-time and
  the key is never logged or returned.
- Locally, put the key in the git-ignored `.env` (template: `.env.example`).
  `.gitignore`, `.dockerignore` and `scripts/package_release.py` all exclude `.env*`, so it
  cannot reach git, an image layer or the release zip.
- `scripts\run_local.ps1` and `scripts\run_docker.ps1` load `.env` into the process
  environment and start the API. The Docker script runs exactly the PSF command
  (`docker run -p 8000:8000 -e API_KEY ...`) but passes the variable by name, so the
  value never appears on a command line or in shell history.
- `python -m scripts.key_check --base <url>` proves the exact key works the way the
  judges will use it, on the local container or on the hosted HTTPS URL: both header
  styles accepted, wrong/truncated/extended/missing keys rejected with 401 and
  `WWW-Authenticate: Bearer`, auth before body parsing, and 300 concurrent requests all
  succeeding. It never prints the key.
- `tests/test_no_secrets.py` fails the suite if anything shaped like an organizer key
  appears in a tracked file.
- On the hosting server, set the same value in the server environment only
  (`deploy/api.env.example`, mode 600). Never put it in the demo's browser code; the
  private demo proxies with it server-side.

Verified with the real key on the built image: 15/15 key checks passed, and a search of
the image history, every file inside the image, the container logs, the working tree and
the release zip found no copy of the key.

## API usage

```powershell
$requestHeaders = @{ 'X-API-Key' = $env:API_KEY }
$ticketBody = '{"ticket_id":"demo-1","channel":"chat","text":"My food has not arrived. Please refund me."}'
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Headers $requestHeaders -ContentType application/json -Body $ticketBody
$bearerHeaders = @{ Authorization = "Bearer $env:API_KEY" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -Headers $bearerHeaders -ContentType application/json -Body $ticketBody
```

The original contract checklist is in CONTRACT_MATRIX.md. Paths:

- GET /health (public).
- POST /predict and POST /predict/batch (1-100 tickets).
- POST /batch/jobs (1-5,000 tickets), GET /batch/jobs/{job_id},
  GET /batch/jobs/{job_id}/results, DELETE /batch/jobs/{job_id}.

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
.\.venv\Scripts\python.exe -m training.audit
.\.venv\Scripts\python.exe -m training.train          # E0-E4 history; writes artifacts/
.\.venv\Scripts\python.exe -m training.train_final urg_v3   # deployed model -> artifacts/urg_v3
.\.venv\Scripts\python.exe -m scripts.compare_artifacts
.\.venv\Scripts\python.exe -m training.preserve_baseline
.\.venv\Scripts\python.exe -m scripts.verify
.\.venv\Scripts\python.exe -m scripts.benchmark
.\.venv\Scripts\python.exe -m scripts.generate_docs
```

`training/train_final.py` builds the deployed artifact and is the only trainer whose
output is promoted. Copy `artifacts/urg_v3/{model.joblib,manifest.json}` over
`artifacts/` to deploy it; earlier releases stay byte-identical in `artifacts/vote_v2/`
and `artifacts/unicode_tokens/`, so promotion is reversible.

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

- Final verification: 86 passed, 1 warning, 15 subtests passed in 107.2s on the `urg_v3` artifact.
- Local single p95 0.0689s; 100-ticket batch p95 1.1158s; 2,000-ticket job 28.6s; 5,000-ticket job 67.6s; cold readiness 4.6s. Every figure is inside the contract target (single <1s, 100-batch <30s, 5,000 submit <5s, 5,000 job <30 min). The vote evaluates ten calibrated pipelines per ticket, so it is roughly 5x slower than the previous single-pipeline release and still 26x inside the job limit. TestClient measurements on this Windows host are not reference-hardware or hosted measurements.

### Measured change from the previous release

Both artifacts were re-measured end to end through `app/predictor.py` on identical
splits by `python -m scripts.compare_artifacts`; raw output is in
`experiments/improvement_v2/artifact_comparison.json`. The supplied validation set is
split once, stratified with seed 42, into a 400-row **selection half** (used to choose
the configuration, the temperature and all three thresholds) and a 400-row
**confirmation half** that no fitting step reads. The confirmation column is the only
unbiased one; the 800-row column exists for comparability with earlier releases.

| metric | previous | **vote_v2** | confirmation half (previous -> new) |
|---|---|---|---|
| accuracy | 0.6088 | **0.6450** | 0.6100 -> **0.6425** |
| macro-F1 | 0.6380 | **0.6725** | 0.6375 -> **0.6643** |
| exact triple match | 0.5763 | **0.6125** | 0.5800 -> **0.6125** |
| secondary-presence F1 (end to end) | 0.7669 | **0.8671** | 0.6897 -> **0.8125** |
| urgency F1 | 0.8533 | **0.8889** | 0.8421 -> **0.8684** |
| urgency recall | 0.8000 | **0.8500** | 0.7805 -> **0.8049** |
| urgency precision | 0.9143 | **0.9315** | 0.9143 -> **0.9429** |
| urgency PR-AUC | 0.9190 | **0.9347** | — |
| ECE (10 equal-width bins) | 0.0272 | 0.0275 | 0.0554 -> **0.0369** |

Per-language accuracy on the 800 rows, previous -> new: en 0.554 -> 0.561,
si 0.344 -> 0.381, ta 0.617 -> 0.658, singlish 0.900 -> 0.960, tanglish 0.600 -> 0.750,
mixed 0.550 -> 0.600. No language regressed, unlike the previous promotion.

**Urgency was then rebuilt in its own right (`urg_v3`).** It had kept the original
single untuned `LinearSVC(C=3, class_weight=None)` while the primary was replaced, so it
had obvious headroom. A search on the validation selection half, ranked by average
precision with 2,000-resample bootstrap intervals and a three-seed robustness check,
replaced it with a two-member soft vote over **character n-grams 3-6** (one balanced
`LinearSVC(C=1)`, one balanced `LogisticRegression(C=10)`). Longer character n-grams rank
urgent tickets better because urgency is carried by multi-word phrases, and the vote
removed a real instability: the single model's F1 swung 0.837-0.886 across fold seeds
while the vote returned 0.9091 at every seed tried.

The effect is the ideal one - **precision rose 0.8293 -> 0.9315 on the 800 rows
(+10.2 points) with recall unchanged at 0.8500**, so the service stopped raising false
alarms without missing a single extra urgent ticket. Nothing else moved: primary
accuracy, macro-F1, ECE and secondary presence are identical to the digit. Urgency F1 is
now above the original release too (0.8889 against 0.8533), so the earlier regression is
resolved rather than merely explained. The deployed cutoff is 0.45, still chosen by the
project's documented cost model (a missed safety ticket costs 10, any other missed urgent
ticket 5, a false alert 1); the full grid is in `artifacts/manifest.json` under
`policy.urgency.sensitivity`.

### Human review policy (`needs_human_review`)

The optional bonus field is now emitted. The rule is
`needs_human_review = confidence < 0.525`.

The cut was chosen on the selection half as the **smallest** confidence at which the
auto-routed slice reaches 80% accuracy, so the threshold is a measured operating point
rather than a guess. Measured on the untouched confirmation half it flags 34.0% of
tickets; the auto-routed 66.0% are correct **80.3%** of the time, against 33.1% for the
flagged remainder. That is the point of the field: it separates a slice that can be
routed automatically from one a human should read. The full coverage/accuracy curve is
in `experiments/improvement_v2/review_curve.json`, and the policy is recorded in
`artifacts/manifest.json` under `review_policy`. Artifacts trained before this policy
(`artifacts/legacy`, `artifacts/unicode_tokens`) carry no threshold, and the predictor
then omits the field entirely rather than inventing a cutoff.

Primary cross-validation substantially overestimates supplied-validation accuracy;
train group CV reads macro-F1 0.98 against a real 0.64, so it was **not** used to select
this model (see the report for why). Sinhala remains the weakest language at 0.381.
Urgency still has false negatives, including safety cases. Synthetic text is not
independently native-speaker reviewed. All predictions need human confirmation.
Thresholds: urgency 0.45, secondary presence 0.08, human review 0.525, temperature 0.85,
all fitted on the validation selection half.

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
GitHub publication, full narrated YouTube recording/upload, submission and team signoff are
pending; none of their links or credentials have been fabricated.


## Follow-up completion: steps 2–5, Docker deferred

All 82 tests and 15 schema subtests passed, along with network-blocked model
inference. Real Chrome desktop/mobile interaction, CSV download, job deletion,
keyboard focus and no-backend-key browser checks passed. Actual HTTP proxy and
dedicated async lifecycle/version checks also passed on localhost.

Current primary: reference masking, explicitly resolved quote handling, calibrated
word/character LinearSVC with safety weight 2, selected by five training group
folds and synthetic stress tests. Independent urgency preprocessing/class-weight
experiments are retained. Default urgency cutoff 0.45 maximizes training holdout
F1; cutoff 0.10 is a separate recall-first artifact, not the default.

The supplied validation is now reused development data. Current accuracy 0.60875,
macro-F1 0.63802 (Unicode-aware word tokens, primary only; previous release 0.60000 / 0.62912), versus original 0.58625 / 0.60957. Tamil regressed 0.575 to 0.533;
mixed regressed 0.600 to 0.550. Default urgency precision 0.91429, recall 0.80000,
F1 0.85333; recall-first precision 0.51034, recall 0.92500, F1 0.65778. Original
artifact and alternate policy remain selectable in artifacts/legacy and
artifacts/high_recall. Fresh evaluation data is needed for unseen-test claims.

Detailed evidence: experiments/improvement/final_development_metrics.json,
promoted.json, urgency_policy_comparison.json, experiments/browser/verification.json,
and benchmark.json. Original validation_metrics.json remains historical evidence.

Native HTTPS deployment is prepared under deploy/; installer shell syntax and
publication PowerShell syntax passed. Neither installer nor CI has run remotely.
GitHub is signed out, no remote repository/server/DNS access was supplied, and
public deployment/publication/upload/submission remain pending. A short silent
browser recording exists; the narrated fifteen-minute walkthrough is still pending.
The source/artifact release archive excludes local databases, environments and keys.
See docs/non_docker_completion.md for exact next steps. Docker tests remain deferred.

Current model version: `sha256-829eec71b98e733fb10e71ba39ab0a5d045cb0a4a8efb09128d3eef0b08b3806`
(`urg_v3` = the `vote_v2` primary with the rebuilt urgency component). `vote_v2` is kept
in `artifacts/vote_v2/` and the pre-rebuild release in `artifacts/unicode_tokens/`, both
byte-identical, so either promotion is reversible.


## vote_v2: what changed and why

Four changes, in descending order of measured effect on the selection half:

1. **Calibrate over all 4,000 training rows.** The previous trainer fitted the primary on
   a 3,200-row core split and sigmoid-calibrated it on a reserved 800-row holdout, so the
   deployed estimator never saw a fifth of the training data.
   `CalibratedClassifierCV(cv=5, ensemble=True)` keeps every calibration prediction
   out-of-fold while using every row and averaging five fold estimators. Worth **+3.0
   accuracy on its own** and by far the largest single effect found.
2. **Soft vote over two tokenisations.** The widened Unicode token pattern keeps Sinhala
   and Tamil combining marks attached; the default `\w` pattern wins on Sinhala. Each
   pattern wins a different language, so the primary averages one calibrated member per
   pattern instead of choosing.
3. **`min_df` 2 -> 1 and char n-grams 2-5 -> 2-6** with `class_weight='balanced'`. Raising
   the vocabulary caps beyond 20k word / 50k char changed the score by exactly zero, so
   they stay small and the artifact stays at 34 MB.
4. **Temperature 0.85 on the vote's output.** Averaging two probability vectors always
   produces something flatter than either input, and the vote came out measurably
   under-confident. The rescale is monotone and identical across classes, so predicted
   labels and every accuracy figure are unchanged by construction; only ECE and log loss
   move (confirmation-half ECE 0.0459 -> 0.0369).

Two ideas were tested and **rejected on measurement**, both recorded in
`experiments/improvement_v2/`: a sentence-level multiple-instance model intended to
isolate the one informative sentence from the surrounding boilerplate (0.555 alone
against 0.640, and blending it in gained nothing), and larger vocabularies (identical
scores for five times the artifact size). Filler-sentence deletion had already been
tried and rejected in `experiments/improvement/filler_experiment.json`.
