"""Promote a measured development candidate while retaining the original release."""
import json
import shutil
from training.audit import ROOT,digest


def main():
    original=ROOT/'artifacts/legacy'
    if original.exists():
        raise RuntimeError('A legacy release already exists; do not silently replace it')
    original.mkdir()
    for name in ('model.joblib','manifest.json'):
        shutil.copy2(ROOT/'artifacts'/name,original/name)
    candidate=ROOT/'artifacts/candidate'
    manifest=json.loads((candidate/'manifest.json').read_text())
    if digest(candidate/'model.joblib')!=manifest['sha256']:
        raise ValueError('Candidate digest mismatch')
    old=json.loads((ROOT/'experiments/validation_metrics.json').read_text())
    new=json.loads((ROOT/'experiments/improvement/final_development_metrics.json').read_text())
    if new['macro_f1'] <= old['macro_f1']:
        raise ValueError('No macro-F1 improvement; candidate not promoted')
    if new['urgency']['f1'] < old['urgency']['f1']:
        raise ValueError('Balanced default urgency F1 regressed; preserve baseline')
    # This development acceptance gate is explicitly not an unbiased test claim.
    for name in ('model.joblib','manifest.json'):
        shutil.copy2(candidate/name,ROOT/'artifacts'/name)
    note={'active_artifact':manifest['model_version'],'initial_accuracy':old['accuracy'],'development_accuracy':new['accuracy'],
          'initial_macro_f1':old['macro_f1'],'development_macro_f1':new['macro_f1'],
          'development_acceptance':'train stress CV chose candidate; reused validation confirms macro-F1 gain and no default urgency-F1 loss; not independent test evidence',
          'regressions':{lang:{'initial':info['accuracy'],'new':new['subgroups']['language'][lang]['accuracy']} for lang,info in old['subgroups']['language'].items() if new['subgroups']['language'][lang]['accuracy']<info['accuracy']},
          'original_preserved':'artifacts/legacy','recall_first_alternative':'artifacts/high_recall'}
    (ROOT/'experiments/improvement/promoted.json').write_text(json.dumps(note,indent=2),encoding='utf-8')
    print(json.dumps(note,indent=2))


if __name__=='__main__':
    main()
