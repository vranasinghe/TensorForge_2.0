# Build steps and current status

Latest update: Docker offline model inference, real container API operations and
persistent mid-job kill/start recovery passed on 2026-10-09. Batch polling race
and configurable smoke-test login were fixed. Earlier deferred Docker checklist
entries below are superseded by experiments/docker_verification.json and the
latest PROGRESS.md section.

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

Current model version: `sha256-3174cfe423b209a8b8bc38591720978baa3af19a396a20376a910940544cb8a0`.
