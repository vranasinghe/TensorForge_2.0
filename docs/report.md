# TensorForge 2.0 — measured MVP report

## Headline result (urg_v3)

Deployed version `sha256-829eec71...`, built in two steps: the primary was rebuilt
(vote_v2) and the urgency component was then rebuilt separately (urg_v3). Against the
previous release, measured end to end through the serving predictor on identical splits:
on the 400-row confirmation half that no fitting step reads, accuracy rose
0.6100 -> 0.6425, macro-F1 0.6375 -> 0.6643, exact primary/secondary/urgency triple
0.5800 -> 0.6175, secondary-presence F1 0.6897 -> 0.8125, urgency F1 0.8421 -> 0.8684 and
ECE improved 0.0554 -> 0.0369. On all 800 validation rows accuracy rose 0.6088 -> 0.6450,
macro-F1 0.6380 -> 0.6725 and urgency F1 0.8533 -> 0.8889. Every language improved.

### Training accuracy against validation accuracy

The deployed model was scored on both supplied files. In-sample means the model scored on
the very rows it was fitted to; the five-fold column refits the same configuration five
times and scores each held-out fold, so it is honest within the training file.

| measure | train, in-sample | train, 5-fold CV | validation (n=800) |
|---|---|---|---|
| category accuracy | 1.0000 | 0.9955 | 0.6450 |
| category macro-F1 | 1.0000 | 0.9944 | 0.6725 |
| urgency accuracy | 1.0000 | 0.9975 | 0.9788 |
| urgency F1 | 1.0000 | 0.9873 | 0.8889 |

In-sample accuracy is 1.0000 throughout, which measures capacity rather than quality: a
linear model with roughly 70,000 sparse features reproduces 4,000 training rows trivially.
It is reported for completeness and never used to rank anything.

### Why the train CV had to be abandoned for selection

The decisive number is the middle column. Cross-validation inside the training file reads
0.9955 accuracy and 0.9944 macro-F1 while the real figures are 0.6450 and 0.6725, a gap of
about 0.35. A read-only similarity audit explains it: a training row's nearest training
neighbour shares its label 60.5% of the time, a validation row's nearest training neighbour
only 26.1%, while the category, language, urgency and secondary distributions of the two
splits are identical. The data is template-generated and validation uses different surface
forms, so held-out-within-train measures memorisation of phrasing, not generalisation. The
same collapse was reproduced on a separately built implementation of this task, which places
the cause in the supplied dataset rather than in this implementation.

Training CV therefore cannot rank candidate models, and selecting against it would be
choosing blind. The supplied validation set was instead split once (stratified, seed 42)
into a 400-row selection half carrying every fitted choice and a 400-row confirmation half
reserved for the numbers above. Raw measurements are in
experiments/improvement_v2/train_vs_validation.json and train_5fold_cv.json.

### What produced the gain

Ranked by measured effect on the selection half: calibrating over all 4,000 training
rows instead of a 3,200-row core with an 800-row calibration holdout (**+3.0 accuracy
alone** — the previous deployed estimator never saw a fifth of its training data); a
soft vote over the Unicode-aware and default word tokenisations, which win on different
languages; `min_df` 2 -> 1 with char n-grams widened to 2–6 and balanced class weights;
and a temperature of 0.85 that repairs the under-confidence inherent in averaging two
probability vectors without moving any predicted label.

Two candidates were rejected on measurement and are kept in
`experiments/improvement_v2/`: a sentence-level multiple-instance model built to isolate
the single informative sentence from the surrounding boilerplate (0.555 alone against
0.640; blending gained nothing) and larger vocabularies (identical score, five times the
artifact size). The earlier filler-deletion experiment had already failed the same way.

### Urgency rebuild (urg_v3)

Urgency had kept the original single untuned `LinearSVC(C=3, class_weight=None)` while
the primary was replaced, so it was searched separately: candidates ranked on the
validation selection half by average precision, with 2,000-resample bootstrap intervals
and a three-seed robustness check. Character n-grams 3-6 ranked urgent tickets
significantly better (dAP +0.0083, 95% CI [+0.0012, +0.0189]), urgency being carried by
multi-word phrases; and a two-member vote (balanced SVC plus balanced logistic
regression) removed a genuine instability, the single model's F1 varying 0.837-0.886
across fold seeds against 0.9091 at every seed for the vote.

Result on the 800 rows: precision 0.8293 -> 0.9315, F1 0.8395 -> 0.8889, PR-AUC
0.9309 -> 0.9347, with **recall unchanged at 0.8500**: fewer false alarms at no cost in
missed urgent tickets. On the untouched confirmation half: precision 0.8049 -> 0.9429,
F1 0.8049 -> 0.8684, recall unchanged. Primary accuracy, macro-F1, ECE and secondary
presence are identical to the digit, because only the urgency component changed. Urgency
now beats the original release on precision, recall, F1 and PR-AUC together, so the
regression reported in the previous revision of this document is resolved.

### Human review

`needs_human_review = confidence < 0.525`, the smallest cut reaching 80% auto-routed
accuracy on the selection half. On the confirmation half it flags 34.0% of tickets and
the auto-routed remainder is right 80.3% of the time, against 33.1% for the flagged
slice.

## Scope and architecture

RideEat is a fictional platform. The MVP classifies multilingual support tickets,
derives a fixed team, and serves seven HTTP operations. FastAPI validates the
unchanged organizer schemas. One background worker stores ordered results in
SQLite transactions; a process lease prevents two service processes from owning
one job database. A separately authenticated demo proxies requests server-side.

## Data and reproducibility

There are 4,000 train and 800 validation rows. CSV and JSONL agree on all fields.
Urgency and non-null secondary labels each occur in 10% of each split. Language
shares match DATA_NOTES. No cross-split ID, exact-text, normalized-template, or
char_wb cosine ≥0.90 overlap was found. This heuristic cannot establish that the
synthetic generation process is independent across splits. SHA256 hashes are in
experiments/audit.json. Original source files remain unchanged.

Train-only number-masked template similarity groups contain 3983
components; the largest has 6 tickets. Seed 42 partitions
these groups into 3200 core and 800
calibration rows. Five outer group folds compare models on core data; vectorizers
are fitted inside each training fold. E3 uses three inner group folds to calibrate
the outer-fold SVM. The final SVM is fitted on core data and sigmoid-calibrated on
the reserved calibration set. This final single-estimator configuration differs
from the original CV calibrated ensemble, so those CV scores are selection evidence
rather than an estimate of deployed accuracy. Follow-up experiments use all train
groups in five outer folds with an inner calibration holdout, reproducing the final
single-estimator fit. Their configurations and predictions are stored in
experiments/improvement; the selected stress macro-F1 is 0.98876.

## Models and experiments

All models use only channel, subject and text. NFC normalization preserves Sinhala,
Tamil, combining marks, emoji and negation. Word (1–2) and char_wb (2–5) TF-IDF
features stay sparse, with one-hot channel. Primary classification, binary urgency,
binary secondary presence, and secondary label prediction are supervised tasks.
Secondary output is never inferred from the second-best primary score.

Core group-CV macro-F1:
- E0: 0.8766
- E1: 0.8512
- E2: 0.9289
- E3: 0.9796
- E4_C3: 0.9596
- E4_balanced: 0.9589

The selected model is mask_quotes_safety_weight. Urgency threshold is
0.45; secondary-presence threshold is
0.20. Both maximize development F1 on
the training calibration holdout. Those labels are reused for calibration and
threshold development; they are not an independent evaluation. Secondary label
training uses all training-positive rows. No pairing blacklist is imposed.

## Supplied validation results

Measured on 800 supplied validation rows, now reused as development data after
initial diagnostics. These are not independent unseen-test results:

- Primary accuracy: 0.60000; macro-F1: 0.62912; weighted-F1: 0.61127.
- Urgency precision: 0.91429; recall: 0.80000; F1: 0.85333; average precision: 0.91897.
- Secondary presence precision: 0.91525; recall: 0.67500; F1: 0.77698.
- Secondary-label macro-F1 excluding null: 0.65869; exact secondary accuracy including null: 0.95750; always-null baseline: 0.90000.
- Exact primary/secondary/urgency triple: 0.56750.
- Primary log loss: 1.24468; multiclass Brier (mean of summed squared errors over all classes): 0.52361.
- ECE: 0.03265, 10 equal-width bins of maximum probability against primary correctness.
- All 800 validation prediction responses passed the supplied original response schema (shape/invariants, not accuracy).

## Limitations and safety

Primary group-CV macro-F1 is far higher than supplied-validation macro-F1. This
observed gap warrants caution: heuristic template grouping may leave structural
similarity within training, and validation contains noisy long messages and old
quoted complaints. These are plausible causes, not independently proven causes.
Follow-up candidates were ranked using training group folds and synthetic stress
tests. Earlier validation diagnostics informed the follow-up design, so the final
validation measurement is development evidence. The original artifact is retained
under artifacts/legacy. Tamil accuracy regressed from 0.575 to 0.533; mixed accuracy
from 0.600 to 0.550. Reference masking and removal of explicitly resolved quoted
history improved overall development accuracy from 0.58625 to 0.60000 and macro-F1
from 0.60957 to 0.62912. Unresolved quoted complaints remain in the features.

Language accuracies:
- en: 0.554 (n=280)
- mixed: 0.550 (n=20)
- si: 0.356 (n=160)
- singlish: 0.900 (n=200)
- ta: 0.533 (n=120)
- tanglish: 0.650 (n=20)

Sinhala is particularly weak. Minority groups with 20 rows do not support strong
claims. Urgency misses exist, including safety tickets; this is not a production
emergency detector. All texts are synthetic and not independently native-speaker
reviewed. Human confirmation is required; an automatic review-threshold field is
not enabled. No hosted URL, container verification, video upload or submission is
claimed. See PROGRESS and deployment checklist for actual verification status.

## References and evidence

The scikit-learn calibration and StratifiedGroupKFold documentation and SQLite WAL
documentation were checked. Guo et al. (2017) was checked at abstract level only;
its neural-network experiments do not establish this sparse model's performance.
See research_evidence.md for exact URLs, scope and local evidence. Remaining
suggested papers were not cited without verification.
