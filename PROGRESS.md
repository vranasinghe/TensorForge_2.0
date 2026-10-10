# Build progress - 2026-10-09 Asia/Colombo

## Latest run and fixes — 2026-10-09

- Started Docker Desktop and resumed tensorforge-api on http://127.0.0.1:8001.
- Ran isolated local API on port 8010 and private demo on port 8510. Existing
  port-8000/8501 services were preserved; their credentials were not assumed.
- Full verification: 82 tests passed, 15 schema subtests; offline model loading,
  seven Unicode predictions and pip dependency checks passed.
- Fixed the demo smoke script's hard-coded URL/credentials: DEMO_URL,
  DEMO_USERNAME and DEMO_PASSWORD now configure the actual service under test.
- Fixed late polling replies restoring discarded batch state. Real Chrome
  regression delays a status reply until DELETE finishes and confirms stale
  progress/results are ignored. All nine browser checks passed.
- Added scripts/docker_verify.py: disposable container/storage, no networking
  inference, health/auth/direct/batch consistency and real 5000-item running-job
  kill/start recovery. Persistent job status returned failed/interrupted and
  DELETE then returned 404. Existing user jobs were untouched.
- The initial restart harness timed out because Docker reassigned its random
  host port. Rediscovering the port fixed the harness; the corrected run passed.
- Docker checks are now performed, superseding earlier deferred/absent status.
  HTTPS deployment/publication and full narrated video remain pending.
- Incorrect classifications on some short English/Tamil texts remain an explicitly
  documented model limitation; this run does not claim new model accuracy gains.

Current local private demo: http://127.0.0.1:8510 (username demo, password
local-demo-password; local test credentials only). API: http://127.0.0.1:8010.
Docker API: http://127.0.0.1:8001. Exact Docker evidence is in
experiments/docker_verification.json; browser evidence in experiments/browser/verification.json.

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
- Original E3 retained; current robust calibrated word+character SVM is described below.
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
- `python -m scripts.verify`: 82 passed, 1 warning, 15 subtests passed in 61.81s (0:01:01). Offline load/prediction check passed
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

Reused supplied development split n=800, seed 42:
accuracy 0.60000, macro-F1 0.62912, weighted-F1
0.61127, urgency F1 0.85333, urgency recall
0.80000, secondary-presence F1
0.77698, secondary exact accuracy
0.95750 (always-null baseline 0.90000), exact
triple 0.56750, ECE-10 0.03265.
All 800 prediction response shapes/invariants validated; this is not accuracy.

Local benchmark: cold readiness 1.202s,
single p95 0.0132s, 100-ticket sync p95
0.5142s; 2,000-ticket job
9.83s; 5,000-ticket job
25.62s. Submission for 5,000 took
0.717s. Host/TestClient timings are not
Docker, network/HTTPS or reference-2-vCPU results. See benchmark.json for polling
and live traffic while jobs run.

## Failures retained and resolved

- Initial sandbox runtime setup refresh failed; reviewed escalated terminal
  execution succeeded. Browser automation subsequently succeeded through bundled Playwright and installed Chrome.
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

The supplied validation is now reused development data. Current accuracy 0.60000,
macro-F1 0.62912, versus original 0.58625 / 0.60957. Tamil regressed 0.575 to 0.533;
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

Current model version: `sha256-d86933b2e9c48d1543487df63da48b5174579430f81a3011c4e894163c34e02b`.


## 2026-10-09 diagnostic session: CV gap, filler removal, tokenizer defect

Active artifact is unchanged (`sha256-d86933b2...`). All 82 tests / 15 subtests still pass.
Supplied validation is reused development data throughout; none of this is unseen-test evidence.

- **CV gap explained, not closed.** Train group-CV is 0.99 but validation is 0.60. Tighter or looser
  similarity grouping (radius 0.1-0.4) and cluster-held-out CV (k=25-400, held-out-to-train median
  similarity matched to validation at ~0.63) all stay at 0.97-0.99, so train CV cannot rank models.
  Validation sentences are only 42% seen in train (train-in-train 59%). Scripts were scratch-only.
- **Filler-sentence removal: hypothesis refuted** (`training/filler.py`,
  `experiments/improvement/filler_experiment.json`). Four variants fixed in advance; all three filler
  settings scored below baseline (validation accuracy 0.578-0.589 vs 0.600). Not adopted.
- **Defect found: default word tokenizer deletes Sinhala/Tamil combining marks** (category Mn/Mc are not
  `\w`), turning words into colliding fragments. `char_wb` features were unaffected. Affects primary,
  urgency, presence (secondary not inspected). Fix: `UNICODE_TOKEN` in `training/robust_features.py`
  (`features(..., unicode_tokens=True)`; default False keeps existing artifacts identical).
- **Controlled result** (`training/tokenizer_fix.py`, `experiments/improvement/tokenizer_fix.json`; primary only):
  accuracy 0.600 -> 0.609, macro-F1 0.629 -> 0.638, Tamil 0.533 -> 0.617, Sinhala 0.356 -> 0.344,
  Tanglish 0.65 -> 0.60, ECE 0.0327 -> 0.0272, log loss 1.245 -> 1.263. Gain is within the +/-1.7-point
  sampling error of n=800, so treat it as a correctness fix with a small, uncertain benefit.
- **Candidate artifact `artifacts/unicode_tokens/`** (primary only; urgency/presence/secondary unchanged),
  built by `training/build_unicode_candidate.py`. NOT promoted: promotion changes model_version and would
  invalidate `experiments/docker_verification.json`, the release manifest, model card and README figures.
- **Open, unresolved:** Sinhala validation accuracy 0.34-0.36 vs Singlish 0.90. The model over-predicts
  `lost_item` (46 predicted / 8 true) and `order_missing_wrong` (42 / 20) for Sinhala and misses signal
  sentences such as "charged more than the receipt". Not a tokenizer problem. Safety recall remains
  0.56 overall (32 validation tickets; per-language counts of 1-11 are too small to interpret).
- Not retrained with the fixed tokenizer: urgency, presence, secondary (safety-critical thresholds would
  need re-selection).


## 2026-10-09 promotion: Unicode-token primary is now the active artifact

- Active model_version: `sha256-3174cfe423b209a8b8bc38591720978baa3af19a396a20376a910940544cb8a0`
  (artifacts/model.joblib + manifest.json, copied byte-for-byte from artifacts/unicode_tokens; digest verified).
- Previous active release preserved at `artifacts/pre_unicode/` (`sha256-d86933b2...`). Older fallbacks
  (`legacy`, `high_recall`, `baseline`) are unchanged; `high_recall` still embeds the previous primary.
- Development metrics (reused validation, n=800): accuracy 0.6088, macro-F1 0.6380, exact triple 0.5763,
  ECE 0.0272, log loss 1.2633. Urgency/secondary-presence unchanged (0.8533 / 0.7770). Tamil 0.617,
  Sinhala 0.344, Tanglish 0.600. Not an unseen-test result; gain is within sampling noise.
- 82 tests / 15 subtests pass; API restarted and `/health` reports the new version.
- **Stale and must be redone before submission:** `experiments/docker_verification.json` (and history),
  `output/release/release_manifest.json` and `tensorforge_submission.zip`, `experiments/browser/predictions.csv`,
  `experiments/benchmark.json`, and any built Docker image or hosted deployment all reference the previous
  version. Rebuild the image, rerun `scripts/docker_verify.py`, `scripts/benchmark.py` and
  `scripts/package_release.py`.


## 2026-10-09 Docker rebuild and verification for the promoted model

- Rebuilt `tensorforge:local` from the promoted artifact (`sha256-3174cfe4...`); the previous image is kept as
  `tensorforge:pre-unicode`.
- `scripts/docker_verify.py` passed (experiments/docker_verification.json, history appended): network-disabled
  model load and four Unicode predictions; public /health version equals artifacts/manifest.json; 401 before
  body parsing; direct and sync-batch predictions equal; a real running 5,000-ticket job was killed and
  restarted on a persistent volume and came back failed/interrupted; DELETE 204 then 404.
- Still stale (previous model version): `experiments/benchmark.json`, `output/release/release_manifest.json` and
  `tensorforge_submission.zip`, `experiments/browser/predictions.csv`, and any hosted deployment.


## 2026-10-09 benchmark rerun and release repackaged (promoted model)

- `scripts/benchmark` rerun (local TestClient, Windows host, uncontrolled load): cold readiness 1.25s, single p95 0.0129s,
  100-ticket sync p95 0.2201s, 5,000-ticket job 12.28s (previous model run: 0.0132s / 0.5142s / 25.62s). Poll/health
  and live /predict p95 stayed under 0.05s during jobs. Not reference-hardware or hosted numbers.


## 2026-10-09 browser check rerun (promoted model)

- Installed the pinned Playwright 1.62.1 from package.json (`npm install --no-package-lock`; node_modules is excluded
  from the release) and ran `scripts/browser_test.cjs` in installed Chrome 154 against the live demo + API on
  `sha256-3174cfe4...`: all 9 checks passed, zero browser errors (readiness, no backend key in the browser, keyboard
  focus, English/Sinhala/Tamil entry, multiline Unicode CSV upload + async progress + CSV download, discard, invalid
  input, 390px layout without overflow, late poll after DELETE). Screenshots and predictions.csv regenerated;
  predictions.csv carries the new model_version.
- Added a `NO_VIDEO=1` option to the script. The run skipped video because recording needs Playwright's ffmpeg
  download, which was not approved. `output/rideeat_demo.webm` is therefore still the earlier silent recording of
  the previous model and should be re-recorded before it is used.
- Observation: the Tamil probe "my food has not arrived, return my money" is shown as payment_refund (98.1%), where
  DATA_NOTES precedence suggests delivery_delay with a payment_refund secondary. One short out-of-distribution
  probe, not a measurement; consistent with the documented Tamil/Sinhala weakness.


## 2026-10-09 independent black-box validation of the live API

- Wrote an independent validator (not part of the repo; imports no project code) that checks the running service
  against the ORIGINAL schemas in `API specs and schemas/`: 150 checks, 150 passed, 0 failed. Covered: public health;
  both auth styles; 401 before 415/413/400/422 and WWW-Authenticate; 415/413/400/422 ordering; 404/405 JSON;
  English/Sinhala/Tamil/Singlish/Tanglish/mixed/emoji/10,000-char/500-char-subject inputs; extra properties,
  `language` and `ticket_id` not affecting predictions; prompt-injection text not obeyed; X-Request-ID echo;
  batch 0/1/100/101, duplicate/missing IDs, multi-fault batch with indexed details, >5MB; async 1/100/2000/5000
  tickets in order with pagination, Location/Retry-After, 409 early results, idempotency, DELETE then 404, unknown
  jobs 404, queue limit (1 running + 3 queued, then 429 + Retry-After); poll and live /predict p95 under 1s during
  the 5,000-ticket job (13.0s wall time); single, shuffled-batch and async predictions identical.
- 800 validation tickets sent through the live API reproduce the stored metrics exactly (accuracy 0.6088, macro-F1 0.6380,
  urgency F1 0.8533, exact triple 0.5763). **Correction:** end-to-end secondary-presence F1 is 0.7669; the
  0.7770 quoted earlier is the presence component alone (precision 0.915, recall 0.675). README updated.
- Not covered by this live run (covered by repo tests only): 410 expired jobs (tests/test_storage.py), 503 while loading
  (tests/test_robustness.py), restart to failed/interrupted (Docker verification and tests/test_process_restart.py).


## 2026-10-10 vote_v2: accuracy work and the needs_human_review policy

**Diagnosis first.** A read-only similarity audit (no fitting) showed why train group CV
reads macro-F1 0.98 against a real 0.64: a train row's nearest train neighbour shares its
label 60.5% of the time, a validation row's nearest train neighbour only 26.1%, while the
category/language/urgency/secondary distributions of the two splits are identical. The
data is template-generated and validation uses different surface forms, so train CV
measures memorised phrasing and cannot rank models. Selection moved to a seed-42
stratified split of the supplied validation set: a 400-row selection half carrying every
fitted choice, and a 400-row confirmation half that no fitting step reads.

**Changes, ranked by measured effect on the selection half.**
1. `CalibratedClassifierCV(cv=5, ensemble=True)` over all 4,000 train rows, replacing a
   3,200-row core fit with an 800-row calibration holdout. **+3.0 accuracy alone**; the
   previous deployed estimator never saw a fifth of its training data.
2. Soft vote over the Unicode-aware and default word tokenisations (they win on different
   languages). New `training/ensemble.py`.
3. `min_df` 2->1, char n-grams 2-5 -> 2-6, `class_weight='balanced'`.
4. Temperature 0.85 fitted on the selection half. Monotone and class-independent, so no
   predicted label moves; it only repairs the under-confidence caused by averaging.

**Rejected on measurement, kept as evidence.** Sentence-level multiple-instance model to
isolate the signal sentence from boilerplate: 0.555 alone against 0.640, blending gained
nothing. Larger vocabularies (word 120k / char 200k): identical score, 5x artifact size,
so caps stay at 20k/50k and the artifact is 34 MB.

**Results**, both artifacts re-measured through `app/predictor.py` on identical splits by
`python -m scripts.compare_artifacts` (`experiments/improvement_v2/artifact_comparison.json`):

| split | metric | previous | vote_v2 |
|---|---|---|---|
| confirmation (n=400, unbiased) | accuracy | 0.6100 | **0.6425** |
| confirmation | macro-F1 | 0.6375 | **0.6643** |
| confirmation | exact triple | 0.5800 | **0.6125** |
| confirmation | secondary-presence F1 | 0.6897 | **0.8125** |
| confirmation | ECE | 0.0554 | **0.0369** |
| full 800 | accuracy / macro-F1 | 0.6088 / 0.6380 | **0.6450 / 0.6725** |
| full 800 | exact triple | 0.5763 | **0.6125** |
| full 800 | ECE | 0.0272 | 0.0275 |

Per-language (800), previous -> new: en 0.554->0.561, si 0.344->0.381, ta 0.617->0.658,
singlish 0.900->0.960, tanglish 0.600->0.750, mixed 0.550->0.600. No language regressed.

**Honest regression.** Urgency F1 0.8533 -> 0.8395. The model improved (PR-AUC
0.9190 -> 0.9309); the cutoff now minimises the project's documented cost model (safety
miss 10, other miss 5, false alert 1) instead of raw F1, which is flat from 0.40 to 0.80
and so chose 0.80 - perfect precision bought by missing a fifth of urgent tickets. Recall
rose 0.800 -> 0.850; deployed cutoff 0.40. Full grid in `artifacts/manifest.json`.

**needs_human_review (PSF E9) is now emitted.** Rule: `confidence < 0.525`, the smallest
cut whose auto-routed slice reaches 80% accuracy on the selection half. On the
confirmation half it flags 34.0%; the auto-routed 66.0% are right 80.3% of the time
against 33.1% for the flagged slice. Curve in
`experiments/improvement_v2/review_curve.json`, policy in the manifest under
`review_policy`. Artifacts without the key (legacy, unicode_tokens) omit the field.

**Verification after promotion.** 82 passed + 15 subtests (103.6s). Docker image rebuilt
and `scripts/docker_verify.py` passed: network-disabled load with Unicode predictions,
auth precedence, direct/sync equality, a real 5,000-ticket job killed mid-run and
recovered as failed/interrupted, DELETE then 404. Benchmarks: cold readiness 4.5s, single
p95 0.0597s, 100-batch p95 0.9971s, 2,000-job 27.5s, 5,000-job 69.4s - all inside contract
targets. The vote runs ten pipelines per ticket, so it is ~5x slower than the previous
single-pipeline release and still 26x inside the job limit.

**Still pending (unchanged):** hosted HTTPS URL, GitHub publication, narrated video,
submission. `output/release/` and `experiments/browser/` still reference the previous
model version and should be regenerated before submission.


## 2026-10-10 organizer API key wired in (PSF section 4)

The key from the organizers' letter is configured WITHOUT hard-coding it, as the contract requires.
- `.env` (git-ignored; also excluded by `.dockerignore` and `scripts/package_release.py`) holds `API_KEY`;
  `.env.example` is the blank template.
- `scripts/load_env.ps1`, `run_local.ps1`, `run_docker.ps1` load it into the process environment only.
  `run_docker.ps1` runs the PSF command with `-e API_KEY` (by name, so the value is never on a command line),
  refuses a busy port, and only ever replaces a container with its own name (`tensorforge-eval`).
- `scripts/key_check.py` proves the exact key works as judges will use it (usable against the hosted URL too).
  Real image, real key: 15/15 checks passed - both header styles, wrong/truncated/extended/missing keys -> 401 +
  `WWW-Authenticate: Bearer`, auth before body parsing, 300/300 concurrent requests OK, key never in a response.
- Leak audit with the real key: image history/config, every file inside the image, container logs, the working
  tree and `output/release/tensorforge_submission.zip` - zero copies. `.env` is not tracked or staged.
- `tests/test_no_secrets.py` fails the suite if an organizer-shaped key appears in any source file (negative control
  verified with a planted fake). Full suite: 86 passed + 15 subtests.
- Bug caught while testing: dot-sourced PowerShell loop variables are case-insensitive and overwrote the caller's
  `$Name`. Renamed; defaults changed so the script can never remove an unrelated container.
- Still to do on the host: set the same value in the server environment only (`deploy/api.env.example`, mode 600).


## 2026-10-10 urg_v3: urgency component rebuilt

The primary was replaced in vote_v2 but urgency still ran the original single untuned
`LinearSVC(C=3, class_weight=None)` on character 2-6, so it was searched on its own.

**Protocol.** Candidates fitted on train only, scored on the validation selection half and
ranked by **average precision** rather than F1, because the selection half holds just 39
urgent tickets and F1 at a fitted threshold is far noisier than a ranking metric. Each
candidate also got a 2,000-resample bootstrap interval on its AP difference from the
incumbent, and the finalists were refitted under three fold seeds. The confirmation half
was not read during the search.

**Findings.**
- Character n-grams **3-6** beat the incumbent's 2-6 with the only bootstrap interval that
  excluded zero: dAP +0.0083, 95% CI [+0.0012, +0.0189], P(better) 0.99. Urgency is carried
  by multi-word phrases, which longer character spans capture.
- The seed check then overruled the single best model. `char36_balC1` had the better AP but
  its cost-threshold F1 swung **0.837 / 0.886 / 0.868** across seeds, while the two-member
  vote returned **0.9091 at all three**. Averaging a balanced `LinearSVC(C=1)` against a
  balanced `LogisticRegression(C=10)` removes that variance.
- Selected: `URGENCY_MEMBERS` in `training/train_final.py`, cutoff 0.45, still chosen by the
  documented cost model (safety FN 10, other FN 5, FP 1) with the 15% near-tie F1 rule.

**Result** (`python -m scripts.compare_artifacts vote_v2 urg_v3`):

| split | metric | vote_v2 | urg_v3 |
|---|---|---|---|
| confirmation (n=400, unbiased) | urgency precision | 0.8049 | **0.9429** |
| confirmation | urgency recall | 0.8049 | 0.8049 (unchanged) |
| confirmation | urgency F1 | 0.8049 | **0.8684** |
| confirmation | exact triple | 0.6125 | **0.6175** |
| full 800 | urgency precision | 0.8293 | **0.9315** |
| full 800 | urgency recall | 0.8500 | 0.8500 (unchanged) |
| full 800 | urgency F1 | 0.8395 | **0.8889** |
| full 800 | urgency PR-AUC | 0.9309 | **0.9347** |

Precision rose ~10 points with recall identical: the service stopped raising false alarms
without missing one extra urgent ticket. Primary accuracy, macro-F1, ECE, secondary
presence and the review policy are unchanged to the digit, because only urgency moved.
Urgency now beats the ORIGINAL release on all four of precision (0.9315 vs 0.9143), recall
(0.850 vs 0.800), F1 (0.8889 vs 0.8533) and PR-AUC (0.9347 vs 0.9190), so the regression
flagged in the vote_v2 notes is resolved, not merely explained.

**Verification after promotion.** 86 passed + 15 subtests. Docker rebuilt and
`scripts/docker_verify.py` passed on the new version (offline Unicode load, auth
precedence, direct/sync equality, real 5,000-ticket job killed mid-run and recovered as
failed/interrupted, DELETE then 404). Benchmarks: cold 4.6s, single p95 0.0689s, 100-batch
p95 1.1158s, 2,000-job 28.6s, 5,000-job 67.6s - all inside contract targets. Artifact
36.6 MB (was 33.6). `artifacts/vote_v2/` and `artifacts/unicode_tokens/` retained, so
promotion is reversible. Report PDF re-exported, 4 pages.

Note: Docker Desktop was not running mid-session; the first `docker_verify` attempt wrote a
failed record to `experiments/docker_verification.json` and its history. It was restarted
and the passing record above is the current one.


## 2026-10-10 urgency: attempt to overtake KDU, and why it was reverted

Goal: raise is_urgent F1/MCC/accuracy/precision to at least KDU's. Outcome: **not achieved,
and the attempt was reverted.** Recorded here because the negative result is the finding.

**What was tried.** A third vote member, `ComplementNB(alpha=0.3)` (built for imbalanced
text, generative bias against two discriminative members), plus switching the threshold
criterion from the cost model to maximum F1. On the selection half this looked like a clear
win and was stable: best-F1 0.9167 against 0.9091, identically at four fold seeds, with
precision 1.000, recall 0.846, MCC 0.912, accuracy 0.9850 - beating KDU on all five.

**Why it was rejected.** On the untouched confirmation half it was *worse*: urgency F1
**0.8333 against urg_v3's 0.8684** (full 800: 0.8750 against 0.8889). The selection-half
gain did not generalise; the max-F1 threshold overfitted 39 positives. Artifacts reverted to
`urg_v3`; the candidate stays in `artifacts/urg_v4/` and its search in
`experiments/improvement_v2/urgency_round4_nb_search.json`.

**Why no threshold can close the gap either.** Across the whole grid on the 800 rows the
deployed 0.45 is already TF's best F1 (0.8889). Raising the cutoff to 0.75 reaches precision
1.000 (above KDU's 0.971) but drops F1 to 0.8652 and recall to 0.762, i.e. seven more missed
urgent tickets. No threshold beats KDU on F1, MCC and accuracy together.

**What the gap actually is** (paired bootstrap, 4,000 resamples of the same 800 rows,
`experiments/improvement_v2/urgency_vs_kdu_paired_bootstrap.json`):

| metric | TF | KDU | diff | 95% CI | P(TF>=KDU) |
|---|---|---|---|---|---|
| F1 | 0.8889 | 0.8919 | -0.0030 | [-0.0381, +0.0325] | 0.44 |
| MCC | 0.8783 | 0.8845 | -0.0062 | [-0.0443, +0.0307] | 0.42 |
| Accuracy | 0.9788 | 0.9800 | -0.0012 | [-0.0075, +0.0050] | 0.43 |
| Precision | 0.9315 | 0.9706 | -0.0391 | [-0.0898, +0.0004] | 0.04 |
| Recall | 0.8500 | 0.8250 | +0.0250 | [-0.0227, +0.0778] | 0.90 |
| PR-AUC | 0.9347 | 0.9268 | +0.0078 | [-0.0071, +0.0239] | 0.84 |
| ROC-AUC | 0.9794 | 0.9734 | +0.0061 | [+0.0010, +0.0122] | 0.99 |

Raw counts: TF catches 68 of 80 urgent tickets with 5 false alarms; KDU catches 66 with 2.
F1, MCC and accuracy differ by about one ticket and their intervals straddle zero, so those
three are statistically indistinguishable. Only two differences are real: TF is genuinely
better at **ranking** (ROC-AUC interval excludes zero) and KDU is genuinely better on
**precision**. It is a precision-versus-recall trade, not a quality gap.

Pushing further would mean selecting on the 800 rows that already contain the 400-row
selection half - the leakage the PSF warns about - and would not transfer to the judges'
hidden holdout. Deployed model is unchanged: `sha256-829eec71...` (urg_v3). 86 tests +
15 subtests still pass after the revert.


## 2026-10-10 urgency: further improvement attempts, all rejected on evidence

Asked to raise is_urgent accuracy using the 4,000 training rows only. About 49 configurations
were tried across five rounds; **none beat the deployed model**, so it is unchanged.

**Error analysis first** (all 17 errors on the 800 rows, `urgency_error_analysis`): 8 of the 12
missed urgent tickets are `safety_conduct` and 9 of 12 are English, while Sinhala, Tamil and
Singlish miss almost none (1, 0, 1). All 5 false alarms are long English billing disputes.
Scores are strongly bimodal (urgent median 0.981, non-urgent mean 0.034), so the misses are
not borderline: they score 0.002-0.353. Inspecting them, the urgent phrase is one short span
buried in 300-800 characters of boilerplate, often with typos ("the drivr appears drunk and is
unable to keep the car in its lane" scores 0.175; an assault report scores 0.002).

**Rejected candidates.**
- *Sentence-level max-pooling* (the natural fix for a localised binary signal, and the
  hypothesis the error analysis suggested): AP 0.78 alone against 0.95 for the document vote;
  every blend weight matched or lost to the document model. The urgent phrases in validation
  are novel paraphrases with typos, so a sentence model cannot match them either.
- *ComplementNB as a third voter + maximum-F1 threshold*: best on the selection half
  (F1 0.9167 at four seeds) but **worse on the held-out confirmation half, 0.8333 against
  0.8684**. Reverted. This is the clearest example in the project of why the confirmation half
  is reserved.
- *Larger character vocabulary (200k, 400k), larger word vocabulary, stripping transcript
  speaker labels, character-only features, urgent-class weights 3x and 5x*: all identical to
  the baseline (AP 0.9529) or worse. The vocabulary caps were never binding.
- *Isotonic calibration, SGD modified-huber voter, word 1-3 grams, subject repetition*: all
  below the baseline on average precision.

**Not adopted by decision.** Training urgency on train + the 400-row selection half does help
(confirmation F1 0.8684 -> 0.9067, precision 1.000, errors 10 -> 7), but the user chose to keep
training to the 4,000 supplied training rows only, so validation data is never used for fitting.
Evidence kept in `experiments/improvement_v2/urgency_moredata.json`.

**Reproducibility note.** `training/train_final.py` was reverted to the state that produced the
deployed artifact and re-run as a check: all 800 predicted labels are identical and the maximum
absolute difference in both confidence and urgency score is exactly 0. The serialized bytes
nevertheless differ, so the sha256-derived `model_version` changes on a retrain even though the
model is numerically identical. **Ship the stored artifact rather than retraining**, or the
version string in the manifest and in every API response will no longer match the submission.

Deployed, unchanged: `sha256-829eec71...` urgency = two-member vote, char 3-6, threshold 0.45,
full-800 F1 0.8889 / precision 0.9315 / recall 0.8500 / accuracy 0.9788.


## 2026-10-10 training vs validation measured for both projects

Both shipped models were scored on the same splits (4,000 train rows, 800 validation rows).
Evidence: `experiments/improvement_v2/train_vs_validation.json` and `train_5fold_cv.json`.

| metric | split | KDU | TF |
|---|---|---|---|
| category accuracy | train (in-sample) | 1.0000 | 1.0000 |
| | train (5-fold CV) | 0.9912 | **0.9955** |
| | validation | 0.6375 | **0.6450** |
| category macro-F1 | train (5-fold CV) | 0.9900 | **0.9944** |
| | validation | 0.6650 | **0.6725** |
| urgency accuracy | train (5-fold CV) | 0.9948 | **0.9975** |
| | validation | **0.9800** | 0.9788 |
| urgency F1 | train (5-fold CV) | 0.9731 | **0.9873** |
| | validation | **0.8919** | 0.8889 |

In-sample accuracy is 1.0000 everywhere: a linear model with ~70k sparse features reproduces
4,000 rows trivially, so it measures capacity, not quality.

The finding that matters: **five-fold cross-validation on the training file reads 0.99 while
the real figure is 0.64, for BOTH projects** (gap 0.354 KDU, 0.351 TF). The cause is the data,
not either team - the training tickets are template-generated, so a held-out training row is a
near-paraphrase of rows the model just saw. Measured earlier: a training row's nearest training
neighbour shares its label 60.5% of the time, a validation row's nearest training neighbour only
26.1%. Any team that selected models against training CV was choosing blind; this project moved
selection onto a held-out half of the supplied validation set after measuring it.


## 2026-10-10 report PDF updated with train vs validation

`docs/report.md` and the exported PDF now carry the training-versus-validation evidence.

- New section **"Training accuracy against validation accuracy"** with the measured table
  (in-sample 1.0000 / 5-fold CV 0.9955 / validation 0.6450 for category accuracy, and the
  same three columns for category macro-F1, urgency accuracy and urgency F1).
- The **"Why the train CV had to be abandoned for selection"** section now cites the exact
  five-fold numbers instead of the approximate "0.98 against 0.64", and notes that the same
  collapse was reproduced on a separately built implementation of this task, which places the
  cause in the supplied dataset rather than in this implementation. The other team is not named.
- Headline corrected: it still said `vote_v2` / `sha256-a7912438...`, which stopped being the
  deployed artifact when urgency was rebuilt. It now reads `urg_v3` / `sha256-829eec71...` and
  includes the urgency F1 movement (0.8533 -> 0.8889 on the 800 rows).

Two exporter defects fixed in `scripts/export_report.py` while doing this:
- **Markdown tables were not supported.** A `|...|` block fell through to the paragraph branch
  and would have printed raw pipes. Added `markdown_table()`, which renders a real reportlab
  table with a header rule and row separators.
- **`###` headings printed literally.** Only `#` and `##` were handled, so every h3 in the
  report (for example "### Urgency rebuild") appeared in the body text with its hashes. Added an
  h3 branch with a matching style. This was pre-existing and affected the previous PDF too.
- Footer date was hard-coded to 2026-10-09; it now uses the export date.

PDF is 4 pages against the 5-page limit, which the exporter asserts. 86 tests + 15 subtests
still pass. No model, artifact or API behaviour changed in this step.


## 2026-10-10 demo UI rebuilt as an operations dashboard

`frontend/index.html` replaced with a dark dashboard: sticky header with a live status badge, a
backend connection bar, a measured-metrics strip, single-ticket prediction with one-click
multilingual samples, synchronous 1-100 batch, the async job lifecycle, the category-to-team
table, and an "about the model" section. Every figure shown is a measured project number
(64.5% accuracy, 67.3% macro-F1, 97.9% urgency accuracy, 88.9% urgency F1, per-language
accuracies, p95 latencies, the 0.525 review cut). Nothing is a placeholder counter.

**Connection state is now first-class**, which was the point of the rebuild. Three states, each
with its own colour, shown in the header badge and the connection bar, with the live
`model_version` and a last-checked timestamp: green *API ready / Connected*, amber *Model
loading*, red *API unavailable / Disconnected*. The action buttons disable themselves unless the
backend is ready. A 15-second poll plus a manual "Test connection" button drive it.

**The API-key box from the reference design was deliberately not copied.** This demo keeps the
evaluation key server-side and proxies every call, so the browser must never hold it. A
connection panel gives the operator the same reassurance without putting a secret in client
JavaScript.

**Two real defects found by driving the UI in a browser, not by reading it:**
1. *Dead page when the URL carries credentials.* Opening `http://user:pass@host/` made every
   relative `fetch()` inherit those credentials, and the browser refuses to build such a
   Request - the whole page failed with no visible cause. Requests are now built from
   `location.origin`, which never carries credentials.
2. *A down backend reported itself as "Model loading".* The demo proxy answers 502 with a JSON
   error body rather than throwing, so the failure branch never ran and the UI implied the
   service was starting up. Status is now derived from three explicit cases.
Mobile also had 77px of horizontal overflow (the version chip and the `docker run` string);
fixed, and 375px now reports zero overflow and no offending element.

**Verified against the real services**, API on one port and the private demo on another:
single prediction (safety sample -> urgent, confidence bar), 7-ticket synchronous batch in
request order, a 300-ticket async job polled to `succeeded` with results in submitted order and
`needs_human_review` present, discard then 404, CSV download, recovery from a killed backend
without a reload, and the 375px layout. `scripts/local_demo_smoke.py` passes against it
(`experiments/local_demo_smoke.json`). Full suite: 86 passed + 15 subtests.


## 2026-10-10 demo UI restyled: light professional theme

Feedback was that the dark neon styling read as generic template work. Re-themed as restrained
light enterprise UI; **only the stylesheet and six decorative glyphs changed** - markup, element
ids and the whole script block are untouched, so behaviour is identical.

- Neutral light surfaces (#f4f6f9 page, white cards) with a single deep-blue accent (#1b4f8f)
  replacing the purple/cyan pair. Every gradient removed: flat buttons, flat badges, flat logo.
- Decorative diamond bullets dropped from the about-card headings, which now use a rule instead.
- Stat strip rebuilt as bordered cells with dark numerals and tabular figures rather than oversized
  cyan text; card headers are a light grey band with an outlined step number.
- Status colours are now semantic rather than decorative: green/amber/red only ever indicate
  connection state, which keeps the one thing an operator must notice visually distinct.

**Accessibility fix found by measuring, not eyeballing.** The first light palette put the small
uppercase labels (stat captions, table headers, the connection label) at 3.2-3.3:1, under the 4.5:1
WCAG AA minimum for normal text. The `--dim` token was darkened #7d8fa3 -> #5a6b7e; those elements
now measure 5.2-5.5:1 and every sampled text/background pair passes.

Re-verified live against the running API: connected state with model version, single prediction,
7-ticket ordered batch, a 250-ticket async job to success, the disconnected state after the backend
was killed, recovery after restart, and 375px with zero horizontal overflow.
`tests/test_frontend.py` and `scripts/local_demo_smoke.py` both pass.
