"""Build artifacts/unicode_tokens: active bundle with only the primary retrained using
Unicode-aware word tokens. Does NOT touch the active artifact; promotion is a separate,
explicit decision because it changes model_version and invalidates container evidence.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import json
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from threadpoolctl import threadpool_limits
from training.audit import ROOT, digest, load
from training.evaluate import primary_metrics
from training.improve import fit_primary
from training.tokenizer_fix import model
from training.train import group_templates


def main():
    rows, validation = load('train'), load('validation')
    y = np.array([r['category'] for r in rows])
    weight = {c: 1. for c in set(y)}
    weight['safety_conduct'] = 2.
    primary = fit_primary(model(True, weight), rows, y, group_templates(rows))
    bundle = joblib.load(ROOT / 'artifacts/model.joblib')
    active = json.loads((ROOT / 'artifacts/manifest.json').read_text())
    bundle['primary'] = primary
    out = ROOT / 'artifacts/unicode_tokens'
    out.mkdir(exist_ok=True)
    joblib.dump(bundle, out / 'model.joblib', compress=3)
    manifest = dict(active)
    manifest.update({'sha256': digest(out / 'model.joblib'), 'trained_at_utc': datetime.now(timezone.utc).isoformat(),
                     'selected_experiment': 'mask_quotes_safety_weight+unicode_word_tokens',
                     'derived_from_model_version': active['model_version'],
                     'change': 'primary only: word TF-IDF token_pattern keeps Sinhala/Tamil combining marks; urgency, presence and secondary unchanged',
                     'evaluation_policy': 'supplied validation is reused development data; not an unseen-test claim'})
    manifest['model_version'] = 'sha256-' + manifest['sha256']
    manifest['source_hashes']['training/robust_features.py'] = digest(ROOT / 'training/robust_features.py')
    manifest['source_hashes']['training/build_unicode_candidate.py'] = digest(ROOT / 'training/build_unicode_candidate.py')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    from app.predictor import Predictor
    predictions = Predictor(out).predict_many(validation)
    yv = np.array([r['category'] for r in validation])
    metrics = primary_metrics(yv, primary.predict_proba(validation), primary.classes_)
    pc = np.array([p['category'] for p in predictions])
    metrics['subgroups'] = {key: {v: {'count': int(sum(r[key] == v for r in validation)),
                                      'accuracy': float(np.mean(pc[[r[key] == v for r in validation]] == yv[[r[key] == v for r in validation]]))}
                                  for v in sorted({r[key] for r in validation})} for key in ('language', 'channel')}
    metrics['exact_triple_match'] = float(np.mean([all(r[k] == p[k] for k in ('category', 'secondary_category', 'is_urgent')) for r, p in zip(validation, predictions)]))
    metrics['split'] = 'supplied validation reused for development diagnostics; not an independent unseen test'
    (out / 'development_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    (out / 'development_predictions.jsonl').write_text('\n'.join(json.dumps(p, ensure_ascii=False) for p in predictions) + '\n', encoding='utf-8')
    old = json.loads((ROOT / 'experiments/improvement/final_development_metrics.json').read_text())
    summary = {k: {'active': old[k], 'unicode_tokens': metrics[k]} for k in ('accuracy', 'macro_f1', 'log_loss', 'ece_10_equal_width_bins', 'exact_triple_match')}
    summary['language_accuracy'] = {l: {'active': old['subgroups']['language'][l]['accuracy'], 'unicode_tokens': metrics['subgroups']['language'][l]['accuracy']} for l in metrics['subgroups']['language']}
    print(json.dumps(summary, indent=2))
    (out / 'comparison.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
