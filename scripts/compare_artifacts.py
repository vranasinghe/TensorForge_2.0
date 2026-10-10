"""Evaluate two artifacts through the same Predictor path on the same splits.

Earlier releases wrote metrics files with different shapes, so a like-for-like
before/after table cannot be assembled by reading them. This re-measures both
artifacts end to end (every contract rule applied) and writes one comparison file.
"""
import json
import sys
import numpy as np
from sklearn.metrics import f1_score, precision_recall_fscore_support
from app.predictor import Predictor
from training.audit import ROOT, load
from training.train_final import validation_halves

SPLITS = ('confirmation_half', 'full_validation')


def measure(artifact, validation, confirmation):
    predictor = Predictor(ROOT / 'artifacts' / artifact)
    out = {'model_version': predictor.version}
    for name in SPLITS:
        subset = [validation[i] for i in confirmation] if name == 'confirmation_half' else validation
        predictions = predictor.predict_many(subset)
        truth = [r['category'] for r in subset]
        got = [p['category'] for p in predictions]
        urgency = precision_recall_fscore_support([r['is_urgent'] for r in subset],
                                                  [p['is_urgent'] for p in predictions],
                                                  average='binary', zero_division=0)
        presence = precision_recall_fscore_support([r['secondary_category'] is not None for r in subset],
                                                   [p['secondary_category'] is not None for p in predictions],
                                                   average='binary', zero_division=0)
        confidence = np.array([p['confidence'] for p in predictions])
        correct = np.array([a == b for a, b in zip(truth, got)])
        ece = 0.
        for low in np.arange(0., 1., .1):
            mask = (confidence >= low) & ((confidence < low + .1) if low < .9 else (confidence <= 1.))
            if mask.any():
                ece += mask.mean() * abs(confidence[mask].mean() - correct[mask].mean())
        flagged = np.array([p.get('needs_human_review') for p in predictions], dtype=object)
        has_review = flagged[0] is not None
        out[name] = {
            'count': len(subset), 'accuracy': float(correct.mean()),
            'macro_f1': float(f1_score(truth, got, average='macro', zero_division=0)),
            'weighted_f1': float(f1_score(truth, got, average='weighted', zero_division=0)),
            'exact_triple_match': float(np.mean([all(r[k] == p[k] for k in ('category', 'secondary_category', 'is_urgent'))
                                                 for r, p in zip(subset, predictions)])),
            'secondary_exact_accuracy': float(np.mean([(r['secondary_category'] or '') == (p['secondary_category'] or '')
                                                       for r, p in zip(subset, predictions)])),
            'ece_10_equal_width_bins': float(ece), 'mean_confidence': float(confidence.mean()),
            'urgency': {'precision': float(urgency[0]), 'recall': float(urgency[1]), 'f1': float(urgency[2])},
            'secondary_presence': {'precision': float(presence[0]), 'recall': float(presence[1]), 'f1': float(presence[2])},
            'needs_human_review_emitted': bool(has_review),
            'review': ({'flagged_fraction': float(np.mean(flagged.astype(bool))),
                        'auto_routed_accuracy': float(correct[~flagged.astype(bool)].mean()),
                        'flagged_accuracy': float(correct[flagged.astype(bool)].mean())} if has_review else None),
            'by_language': {lang: {'count': sum(1 for r in subset if r['language'] == lang),
                                   'accuracy': float(np.mean([correct[i] for i, r in enumerate(subset) if r['language'] == lang]))}
                            for lang in sorted({r['language'] for r in subset})},
        }
    return out


def main(previous='unicode_tokens', current='vote_v2'):
    validation = load('validation')
    _, confirmation = validation_halves(validation)
    report = {'note': 'Both artifacts measured through app.predictor on identical splits. '
                      'The confirmation half is the only split never used to fit the new model or its thresholds.',
              'previous_artifact': previous, 'current_artifact': current,
              'previous': measure(previous, validation, confirmation),
              'current': measure(current, validation, confirmation)}
    target = ROOT / 'experiments' / 'improvement_v2' / 'artifact_comparison.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for split in SPLITS:
        print(f'\n=== {split}')
        before, after = report['previous'][split], report['current'][split]
        print(f'{"metric":26s} {"previous":>10s} {"current":>10s} {"delta":>9s}')
        for key in ('accuracy', 'macro_f1', 'weighted_f1', 'exact_triple_match',
                    'secondary_exact_accuracy', 'ece_10_equal_width_bins'):
            print(f'{key:26s} {before[key]:10.4f} {after[key]:10.4f} {after[key]-before[key]:+9.4f}')
        for group in ('urgency', 'secondary_presence'):
            for key in ('precision', 'recall', 'f1'):
                label = f'{group}.{key}'
                print(f'{label:26s} {before[group][key]:10.4f} {after[group][key]:10.4f} {after[group][key]-before[group][key]:+9.4f}')
        print(f'{"languages":26s}', {k: f"{before['by_language'][k]['accuracy']:.3f}->{v['accuracy']:.3f}"
                                     for k, v in after['by_language'].items()})
    print(f'\nwrote {target}')


if __name__ == '__main__':
    main(*sys.argv[1:])
