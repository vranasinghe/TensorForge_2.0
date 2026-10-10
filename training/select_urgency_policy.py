"""Keep recall-first artifact separately; choose balanced cutoff from train grid."""
import json
import shutil
import joblib
import numpy as np
from sklearn.metrics import f1_score
from training.audit import ROOT,load,digest
from training.evaluate import binary_metrics


def main():
    candidate=ROOT/'artifacts/candidate'
    high_recall=ROOT/'artifacts/high_recall'
    high_recall.mkdir(exist_ok=True)
    for name in ('model.joblib','manifest.json'):
        shutil.copy2(candidate/name,high_recall/name)
    out=ROOT/'experiments/improvement'
    for name in ('metrics','predictions.jsonl'):
        source=out/('final_development_metrics.json' if name=='metrics' else 'final_development_predictions.jsonl')
        target=out/('high_recall_development_metrics.json' if name=='metrics' else 'high_recall_development_predictions.jsonl')
        shutil.copy2(source,target)
    manifest=json.loads((candidate/'manifest.json').read_text())
    selected=max(manifest['policy']['urgency']['sensitivity'],key=lambda r:(r['f1'],r['recall']))
    model=joblib.load(candidate/'model.joblib')
    model['urgency_threshold']=selected['threshold']
    joblib.dump(model,candidate/'model.joblib',compress=3)
    manifest['sha256']=digest(candidate/'model.joblib');manifest['model_version']='sha256-'+manifest['sha256']
    manifest['policy']['urgency']['threshold']=selected['threshold']
    manifest['policy']['urgency']['selection_split']='max F1 on train-only heldout reference-shift/resolved-quote stress calibration set; high-recall alternative stored separately'
    manifest['source_hashes']['training/select_urgency_policy.py']=digest(ROOT/'training/select_urgency_policy.py')
    (candidate/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    from app.predictor import Predictor
    rows=load('validation');predictions=Predictor(candidate).predict_many(rows)
    metrics=json.loads((out/'final_development_metrics.json').read_text())
    scores=model['urgency'].predict_proba(rows)[:,1]
    metrics['urgency']=binary_metrics([r['is_urgent'] for r in rows],scores,selected['threshold'])
    metrics['urgency']['end_to_end_f1']=f1_score([r['is_urgent'] for r in rows],[r['is_urgent'] for r in predictions])
    metrics['exact_triple_match']=float(np.mean([all(r[k]==p[k] for k in ('category','secondary_category','is_urgent')) for r,p in zip(rows,predictions)]))
    for key,values in metrics['subgroups'].items():
        for value,info in values.items():
            indexes=[i for i,r in enumerate(rows) if r[key]==value]
            info['urgency']=binary_metrics([rows[i]['is_urgent'] for i in indexes],scores[indexes],selected['threshold'])
    (out/'final_development_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (out/'final_development_predictions.jsonl').write_text('\n'.join(json.dumps(p,ensure_ascii=False) for p in predictions)+'\n',encoding='utf-8')
    high=json.loads((out/'high_recall_development_metrics.json').read_text())
    (out/'urgency_policy_comparison.json').write_text(json.dumps({'balanced':metrics['urgency'],'recall_first':high['urgency'],
       'selection_note':'cutoffs derived from training grid; development diagnostics informed the decision to retain separate profiles, not an independent test'},indent=2),encoding='utf-8')
    print('BALANCED PROFILE DEVELOPMENT',metrics['urgency'],flush=True)


if __name__=='__main__':
    main()
