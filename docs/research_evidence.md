# Research evidence

Reviewed on 2026-10-09. Sources support engineering choices; local measurements
establish the recorded RideEat results. No external paper establishes accuracy on
this dataset.

## Probability calibration

- Source: [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
- Checked: official documentation, including disjoint fitted-estimator calibration and sigmoid method.
- Claim: calibrators require data independent of base-classifier fitting; SVM scores can be mapped to probabilities.
- Local evidence: split_manifest.json stores disjoint group-held core/calibration IDs; train.py uses FrozenEstimator. validation_metrics.json includes log loss, summed multiclass Brier and ECE.

## Grouped cross-validation

- Source: [StratifiedGroupKFold documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).
- Checked: official class documentation.
- Claim: groups are kept apart between folds while class proportions are approximated.
- Local evidence: training groups are connected components of cosine similarity; every vectorizer resides inside each fitted pipeline. Grouping does not prove that broader synthetic generation templates are independent.

## SQLite concurrent traffic

- Source: [SQLite write-ahead logging](https://www.sqlite.org/wal.html).
- Checked: official documentation.
- Claim: WAL supports reader/writer concurrency, with constraints; it is not a multi-host shared database solution.
- Local evidence: transactional queue admission and commit guards, busy timeout, WAL, single-process lease; concurrent polling and live-prediction tests. Latencies are in benchmark.json.

## Calibration research context

- Source: [Guo et al., On Calibration of Modern Neural Networks (2017)](https://proceedings.mlr.press/v70/guo17a.html).
- Checked: paper landing page and abstract only, not the full paper.
- Claim: neural model confidence can be miscalibrated; this motivates measurement rather than trusting a score.
- Applicability: background only; this project uses sparse linear models and sigmoid calibration. The paper does not prove these choices improve RideEat scores.

Other research candidates in the master document have not been verified or cited
as evidence. No claim is made to have reviewed their full papers.
