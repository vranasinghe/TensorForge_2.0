"""E0-E3 train-only CV; independent calibration split; validation once at end."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import csv
import json
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from scipy.sparse.csgraph import connected_components
from threadpoolctl import threadpool_limits
from training.audit import ROOT, load, template, digest
from training.features import features
from training.evaluate import primary_metrics, binary_metrics

SEED = 42
OUT = ROOT / 'experiments'


def group_templates(rows):
    vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=30000)
    x = vec.fit_transform([template(r) for r in rows])
    graph = NearestNeighbors(metric='cosine', algorithm='brute', radius=.10).fit(x).radius_neighbors_graph(x, mode='connectivity')
    return connected_components(graph.maximum(graph.T), directed=False)[1]


def make_model(kind, svm=False, c=1., weight=None):
    return Pipeline([('features', features(kind)), ('classifier', LinearSVC(C=c, class_weight=weight, random_state=SEED) if svm else LogisticRegression(C=c, class_weight=weight, max_iter=500, random_state=SEED))])


def calibrated(model, x, y, groups):
    inner = list(StratifiedGroupKFold(3, shuffle=True, random_state=SEED).split(x, y, groups))
    return CalibratedClassifierCV(model, cv=inner, method='sigmoid', n_jobs=1)


def best_threshold(y, scores):
    choices = [binary_metrics(y, scores, t) for t in np.arange(.05, .96, .05)]
    return max(choices, key=lambda m: (m['f1'], m['recall']))['threshold'], choices


def main():
    OUT.mkdir(exist_ok=True)
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    rows = load('train')
    groups = group_templates(rows)
    y = np.array([r['category'] for r in rows])
    # Entire template clusters stay on one side of the calibration boundary.
    core, calibration = next(StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(rows, y, groups))
    x = [rows[i] for i in core]
    labels, core_groups = y[core], groups[core]
    classes = np.unique(y)
    split_manifest = {'seed': SEED, 'grouping': 'connected components of train-only char_wb cosine >=0.90 after NFC/number masking',
                      'groups': len(set(groups)), 'largest_group': int(np.bincount(groups).max()),
                      'core_ids': [rows[i]['ticket_id'] for i in core], 'calibration_ids': [rows[i]['ticket_id'] for i in calibration]}
    (OUT / 'split_manifest.json').write_text(json.dumps(split_manifest, indent=2), encoding='utf-8')
    folds = list(StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(x, labels, core_groups))
    configurations = [('E0', 'word', False, 1., None), ('E1', 'char', False, 1., None), ('E2', 'combined', False, 1., None), ('E3', 'combined', True, 1., None),
                      ('E4_C3', 'combined', False, 3., None), ('E4_balanced', 'combined', False, 1., 'balanced')]
    results = []
    for name, kind, svm, c, weight in configurations:
        start = time.perf_counter()
        oof = np.zeros((len(x), len(classes)))
        for fold, (tr, te) in enumerate(folds):
            estimator = make_model(kind, svm, c, weight)
            train_x = [x[i] for i in tr]
            if svm:
                estimator = calibrated(estimator, train_x, labels[tr], core_groups[tr])
            estimator.fit(train_x, labels[tr])
            oof[te] = estimator.predict_proba([x[i] for i in te])
            print(f'{name} fold {fold+1}/5 done', flush=True)
        metrics = primary_metrics(labels, oof, classes)
        result = {'experiment': name, 'kind': kind, 'svm': svm, 'C': c, 'class_weight': weight,
                  'split': '5-fold stratified group CV on train core; calibration holdout excluded',
                  'seconds': time.perf_counter()-start, 'metrics': metrics}
        results.append(result)
        np.savez_compressed(OUT / f'{name}_oof.npz', probabilities=oof, labels=labels, classes=classes)
        (OUT / 'experiments.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(name, metrics['accuracy'], metrics['macro_f1'], flush=True)
    winner = max(results, key=lambda r: r['metrics']['macro_f1'])
    base = make_model(winner['kind'], winner['svm'], winner['C'], winner['class_weight'])
    base.fit(x, labels)
    cal_x = [rows[i] for i in calibration]
    primary = CalibratedClassifierCV(FrozenEstimator(base), method='sigmoid').fit(cal_x, y[calibration])
    urgent_y = np.array([r['is_urgent'] for r in rows])
    presence_y = np.array([r['secondary_category'] is not None for r in rows])
    binary = {}
    policy = {}
    for name, target in [('urgency', urgent_y), ('presence', presence_y)]:
        base_binary = make_model(winner['kind'], False, 3.)
        base_binary.fit(x, target[core])
        model = CalibratedClassifierCV(FrozenEstimator(base_binary), method='sigmoid').fit(cal_x, target[calibration])
        scores = model.predict_proba(cal_x)[:, 1]
        threshold, sensitivity = best_threshold(target[calibration], scores)
        policy[name] = {'threshold': threshold, 'sensitivity': sensitivity,
                        'selection_split': 'training calibration holdout, reused for threshold development; not unbiased evaluation'}
        binary[name] = model
    positive_rows = [r for r in rows if r['secondary_category']]
    secondary = make_model(winner['kind'], False, 3.).fit(positive_rows, [r['secondary_category'] for r in positive_rows])
    bundle = {'primary': primary, 'urgency': binary['urgency'], 'presence': binary['presence'], 'secondary': secondary,
              'urgency_threshold': policy['urgency']['threshold'], 'presence_threshold': policy['presence']['threshold']}
    joblib.dump(bundle, artifacts / 'model.joblib', compress=3)
    model_hash = digest(artifacts / 'model.joblib')
    audit = json.loads((OUT / 'audit.json').read_text(encoding='utf-8'))
    manifest = {'model_version': 'sha256-' + model_hash, 'sha256': model_hash, 'seed': SEED,
                'trained_at_utc': datetime.now(timezone.utc).isoformat(), 'selected_experiment': winner['experiment'],
                'dataset_hashes': audit['hashes'], 'policy': policy, 'features': ['channel', 'subject', 'text'],
                'packages': {p: version(p) for p in ['scikit-learn', 'numpy', 'scipy', 'joblib', 'fastapi', 'jsonschema']},
                'training_design': split_manifest['grouping'], 'configuration': {k: winner[k] for k in ('kind', 'svm', 'C', 'class_weight')},
                'limitations': ['Synthetic languages not reviewed by native speakers', 'Calibration holdout also used for binary threshold tuning', 'Final primary uses core training plus calibration; secondary uses all train positives']}
    (artifacts / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    from app.predictor import Predictor
    predictor = Predictor(artifacts)
    validation = load('validation')
    probabilities = primary.predict_proba(validation)
    predictions = predictor.predict_many(validation)
    metrics = primary_metrics(np.array([r['category'] for r in validation]), probabilities, primary.classes_)
    metrics['split'] = 'supplied validation, evaluated once after train-only model selection; synthetic overlap limitations in audit'
    metrics['urgency'] = binary_metrics([r['is_urgent'] for r in validation], binary['urgency'].predict_proba(validation)[:, 1], bundle['urgency_threshold'])
    metrics['secondary_presence'] = binary_metrics([r['secondary_category'] is not None for r in validation], binary['presence'].predict_proba(validation)[:, 1], bundle['presence_threshold'])
    from sklearn.metrics import f1_score, accuracy_score
    true_secondary = [r['secondary_category'] or '__NULL__' for r in validation]
    pred_secondary = [r['secondary_category'] or '__NULL__' for r in predictions]
    metrics['secondary_exact_accuracy'] = accuracy_score(true_secondary, pred_secondary)
    metrics['secondary_label_macro_f1_excluding_null'] = f1_score(true_secondary, pred_secondary, labels=sorted({v for v in true_secondary if v != '__NULL__'}), average='macro', zero_division=0)
    metrics['always_null_secondary_accuracy'] = float(np.mean([r['secondary_category'] is None for r in validation]))
    metrics['exact_triple_match'] = float(np.mean([all(r[k] == p[k] for k in ('category', 'secondary_category', 'is_urgent')) for r, p in zip(validation, predictions)]))
    metrics['contract_pass_rate'] = 1.0  # predictor validates each original schema; any failure aborts this run
    metrics['subgroups'] = {}
    for key in ('language', 'channel', 'category'):
        metrics['subgroups'][key] = {}
        for value in sorted({r[key] for r in validation}):
            indexes = [i for i, r in enumerate(validation) if r[key] == value]
            truth = [validation[i]['category'] for i in indexes]
            pred = [predictions[i]['category'] for i in indexes]
            metrics['subgroups'][key][value] = {'count': len(indexes), 'accuracy': accuracy_score(truth, pred), 'macro_f1': f1_score(truth, pred, average='macro', zero_division=0),
              'urgency': binary_metrics([validation[i]['is_urgent'] for i in indexes], binary['urgency'].predict_proba([validation[i] for i in indexes])[:, 1], bundle['urgency_threshold'])}
    (OUT / 'validation_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    (OUT / 'validation_predictions.jsonl').write_text('\n'.join(json.dumps(p, ensure_ascii=False) for p in predictions) + '\n', encoding='utf-8')
    errors = [{'ticket_id': r['ticket_id'], 'language': r['language'], 'actual': {k: r[k] for k in ('category','secondary_category','is_urgent')}, 'prediction': p} for r, p in zip(validation, predictions) if any(r[k] != p[k] for k in ('category','secondary_category','is_urgent'))]
    (OUT / 'errors.json').write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding='utf-8')
    print('FINAL VALIDATION', metrics['accuracy'], metrics['macro_f1'], metrics['exact_triple_match'], flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
