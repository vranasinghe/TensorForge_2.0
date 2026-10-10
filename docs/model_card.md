# Model card — urg_v3 (vote_v2 primary + rebuilt urgency)

Version: `sha256-829eec71b98e733fb10e71ba39ab0a5d045cb0a4a8efb09128d3eef0b08b3806`. Supersedes `vote_v2`
(`sha256-a7912438...`, kept in `artifacts/vote_v2/`) and `sha256-3174cfe4...` (kept in
`artifacts/unicode_tokens/`).

## Urgency component

A two-member soft vote over character n-grams 3-6: one balanced `LinearSVC(C=1)` on
Unicode-aware word tokens and one balanced `LogisticRegression(C=10)` on default tokens,
each `CalibratedClassifierCV(cv=5, sigmoid, ensemble)` over all 4,000 training rows. It
replaced a single untuned `LinearSVC(C=3, class_weight=None)` on character 2-6. Selected
on the validation selection half by average precision, with 2,000-resample bootstrap
intervals and a three-seed robustness check: the single model's F1 varied 0.837-0.886
across fold seeds, the vote gave 0.9091 at every seed. Cutoff 0.45, chosen by the
documented cost model (safety miss 10, other miss 5, false alert 1).

Measured: precision 0.8293 -> 0.9315 and F1 0.8395 -> 0.8889 on the 800 rows with
**recall unchanged at 0.8500**; on the untouched confirmation half precision
0.8049 -> 0.9429 and F1 0.8049 -> 0.8684, recall unchanged. PR-AUC 0.9309 -> 0.9347.
No other component changed.

## What this model is

Word (1–2) and character `char_wb` (2–6) sparse TF-IDF plus one-hot channel, feeding a
LinearSVC with balanced class weights, wrapped in `CalibratedClassifierCV(cv=5,
sigmoid, ensemble=True)` over all 4,000 training rows. Two such members are fitted, one
per word tokenisation (Unicode-aware and default), and their calibrated probabilities
are averaged; a single temperature of 0.85 then corrects the averaging's
under-confidence. Urgency, secondary presence and secondary label remain separate
supervised components. No LLM and no network access at inference.

## Selection protocol (important)

The project's train-only group cross-validation reports macro-F1 0.98 while the real
figure is 0.64. Train is template-generated: a training row's nearest training
neighbour shares its label 60.5% of the time, but a validation row's nearest training
neighbour shares its label only 26.1% of the time. Train CV therefore cannot rank
models and was **not** used to select this one. Instead the supplied validation set was
split once, stratified with seed 42, into a 400-row selection half (used for the
configuration, the temperature and all three thresholds) and a 400-row confirmation
half that no fitting step reads. Neither half is training data.

## Measured results

On the untouched confirmation half (n=400), previous -> vote_v2: accuracy
0.6100 -> 0.6425, macro-F1 0.6375 -> 0.6643, exact triple 0.5800 -> 0.6125,
secondary-presence F1 0.6897 -> 0.8125, ECE 0.0554 -> 0.0369. On all 800 validation
rows: accuracy 0.6088 -> 0.6450, macro-F1 0.6380 -> 0.6725, exact triple
0.5763 -> 0.6125, ECE 0.0272 -> 0.0275. Every language improved; Sinhala remains
weakest at 0.381. Urgency F1 is 0.8889 against the original 0.8533, recall 0.850 against 0.800,
precision 0.9315 against 0.9143 and PR-AUC 0.9347 against 0.9190: better on every one.

## Human review policy

`needs_human_review = confidence < 0.525`, the smallest cut whose auto-routed slice
reaches 80% accuracy on the selection half. On the confirmation half it flags 34.0% of
tickets; the auto-routed remainder is correct 80.3% of the time against 33.1% for the
flagged slice. Earlier artifacts carry no threshold and the predictor omits the field
for them.

---

# Previous model card — mask_quotes_safety_weight + Unicode word tokens

Version: `sha256-3174cfe423b209a8b8bc38591720978baa3af19a396a20376a910940544cb8a0`. Artifact SHA256:
`3174cfe423b209a8b8bc38591720978baa3af19a396a20376a910940544cb8a0`. Training date (UTC): 2026-10-09T15:31:59.163151+00:00 (primary only; urgency, presence and secondary components are unchanged from the previous release, artifacts/pre_unicode).

## Intended use

Workshop demonstration of multilingual ticket triage for fictional RideEat.
Support agents confirm suggested routes. Not suitable for autonomous emergency
decisions, real customer deployment, or auto-closing customer messages without
review. No inference network calls or general-purpose LLM API wrappers.

## Data and features

4,000 organizer-supplied synthetic training tickets, 800 supplied validation
tickets; original hashes in audit.json. No real customer records per DATA_NOTES.
Synthetic Sinhala, Tamil and transliteration are not native-speaker reviewed.
Inputs: channel, optional subject and text. ID and language are never features.
NFC normalization retains combining marks. Labels follow supplied data notes;
safety precedence is learned, not guaranteed by a deterministic keyword layer.

## Training and evidence

Word/character sparse TF-IDF plus calibrated LinearSVC, seed 42. Train group CV
chooses the primary model; disjoint core/calibration sets fit the final predictor.
Binary LR components are sigmoid calibrated; secondary category LR uses only
secondary-positive train records. Urgency cutoff 0.45;
secondary-presence cutoff 0.20 selected
on the training calibration holdout. No independently evaluated human-review
threshold is deployed; UI requests manual confirmation for all tickets.

Validation accuracy 0.6088, macro-F1 0.6380,
urgency F1 0.8533 (unchanged component), exact triple 0.5763. The primary word features now
keep Sinhala/Tamil combining marks; previous release: 0.6000 / 0.6291 / 0.5675.
Full per-class/language/channel performance, confusion matrix, ECE, reliability
bins and selective risk are in experiments/improvement/final_development_metrics.json.
These are reused development measurements; the original validation_metrics.json
is retained as historical baseline evidence. Minority-language samples
are small. Sinhala accuracy 0.3438.
The CV/validation gap is material; see report.md. Subgroup macro-F1 uses the labels
present in truth or prediction within each subgroup. For primary-class subgroups,
accuracy is that class's recall; the complete per_class report gives meaningful
class precision/F1 across the full validation set.

## Ethics, security and persistence

Do not enter real personal information into an unapproved demo. Keys are injected
server-side. Request bodies are not logged by this application. SQLite stores
ticket text and results until deletion/24-hour expiry; protect its volume and use
approved access controls. A durable volume and one worker/replica are mandatory.
Only load trusted joblib artifacts; deserialization can execute code.
