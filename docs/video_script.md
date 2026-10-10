# Fifteen-minute demonstration script

Timing and length follow the master file; official guideline PDF is still absent.
Use the current artifact and recorded results. Do not claim a deployed URL or an
uploaded video until those actions are completed.

- 0:00–1:00: introduce fictional RideEat and the support-triage task; explain human confirmation.
- 1:00–3:00: show original files, exact API operations, language-input discrepancy, data audit and SHA256 hashes.
- 3:00–5:00: show train.py, train-only group folds, six experiment results and reserved calibration split.
- 5:00–7:00: show measured validation metrics, language weaknesses, CV/validation gap, confusion matrix and reliability figure. State that synthetic data is not real-world evidence.
- 7:00–9:00: start API and private demo, classify English/Sinhala/Tamil and mixed messages, and inspect primary/team/secondary/urgency/confidence.
- 9:00–11:00: upload a CSV, show real job progress, download ordered results; demonstrate a 5,000-ticket job using scripts/benchmark.py or an equivalent submitted file.
- 11:00–12:30: show both auth methods, invalid JSON, whitespace text, duplicate IDs, capacity response and schema tests.
- 12:30–13:30: demonstrate DELETE and restart failure using an isolated job database; do not delete evaluation jobs.
- 13:30–14:30: demonstrate Docker offline smoke only after Docker is available and the image has actually passed. Otherwise state it is pending.
- 14:30–15:00: show reproducibility commands and actual submission links, clearly distinguishing pending hosting/video/publication.

Video URL: pending. Short silent browser footage exists at output/rideeat_demo.webm; full narration and upload remain pending.

## Follow-up results to explain

Show improve.py, improve_urgency.py and select_urgency_policy.py; explain training-only selection and development reuse. Report 60.0% accuracy, macro-F1 0.62912, Tamil/mixed regressions and the urgency false-alert tradeoff. Show retained baseline and policy artifacts. Do not describe native deployment as Docker verification.
