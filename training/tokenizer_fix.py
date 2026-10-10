"""Single pre-specified change: Unicode-aware word tokens (Sinhala/Tamil combining marks kept).

Same recipe as the promoted primary (mask references, resolved quotes, LinearSVC C=1,
safety weight 2, disjoint sigmoid calibration). Supplied validation is reused development
data, so this is not an unseen-test claim.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import json
import time
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits
from training.robust_features import features


def model(unicode_tokens, weight):
    return Pipeline([('features', features(True, True, unicode_tokens=unicode_tokens)),
                     ('classifier', LinearSVC(C=1., class_weight=weight, random_state=42))])


def main():
    from training.audit import ROOT, load
    from training.improve import fit_primary
    from training.train import group_templates
    rows, validation = load('train'), load('validation')
    y = np.array([r['category'] for r in rows])
    yv = np.array([r['category'] for r in validation])
    weight = {c: 1. for c in set(y)}
    weight['safety_conduct'] = 2.
    groups = group_templates(rows)
    folds = list(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(rows, y, groups))
    results = []
    for name, flag in (('default_tokens', False), ('unicode_tokens', True)):
        t = time.perf_counter()
        pred = np.empty(len(rows), dtype=object)
        for tr, te in folds:
            m = fit_primary(model(flag, weight), [rows[i] for i in tr], y[tr], groups[tr])
            pred[te] = m.predict([rows[i] for i in te])
        pv = fit_primary(model(flag, weight), rows, y, groups).predict(validation)
        by_language = {}
        for lang in sorted({r['language'] for r in validation}):
            mask = np.array([r['language'] == lang for r in validation])
            by_language[lang] = float(np.mean(pv[mask] == yv[mask]))
        results.append({'name': name, 'train_group_cv_accuracy': float(accuracy_score(y, pred)),
                        'train_group_cv_macro_f1': float(f1_score(y, pred, average='macro')),
                        'validation_accuracy': float(accuracy_score(yv, pv)),
                        'validation_macro_f1': float(f1_score(yv, pv, average='macro')),
                        'validation_language_accuracy': by_language, 'seconds': round(time.perf_counter() - t, 1)})
        print(json.dumps(results[-1]), flush=True)
    (ROOT / 'experiments/improvement/tokenizer_fix.json').write_text(json.dumps({
        'note': 'one pre-specified change; supplied validation is reused development data', 'seed': 42, 'results': results}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
