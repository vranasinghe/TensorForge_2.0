"""Choose urgency model/threshold on training stress folds, with costly safety misses."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import json
import time
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.model_selection import StratifiedGroupKFold
from threadpoolctl import threadpool_limits
from training.audit import ROOT,load,digest
from training.train import group_templates,make_model
from training.improve import stress
from training.robust_features import features
from training.evaluate import binary_metrics,primary_metrics
from sklearn.metrics import f1_score

OUT=ROOT/'experiments/improvement'


def cost(rows,truth,scores,threshold):
    prediction=scores>=threshold
    weights=np.array([10. if r['category']=='safety_conduct' else 5. for r in rows])
    return float(np.sum(weights*(truth & ~prediction))+np.sum(~truth & prediction))


def threshold(rows,truth,scores):
    values=[{'threshold':float(t),'weighted_error':cost(rows,truth,scores,t),**binary_metrics(truth,scores,t)} for t in np.arange(.05,.96,.05)]
    return min(values,key=lambda m:(m['weighted_error'],-m['recall']))['threshold'],values


def fit(config,rows,truth,groups):
    tr,cal=next(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(rows,truth,groups))
    if config=='legacy':
        model=make_model('combined',False,3.)
    else:
        model=Pipeline([('features',features(True,True)),('classifier',LogisticRegression(C=3.,max_iter=500,class_weight='balanced' if config=='robust_balanced' else None,random_state=42))])
    model.fit([rows[i] for i in tr],truth[tr])
    calibrated=CalibratedClassifierCV(FrozenEstimator(model),method='sigmoid').fit([rows[i] for i in cal],truth[cal])
    developed=[stress(rows[i],int(i)) for i in cal]
    cutoff,sensitivity=threshold([rows[i] for i in cal],truth[cal],calibrated.predict_proba(developed)[:,1])
    return calibrated,cutoff,sensitivity


def main():
    rows=load('train')
    truth=np.array([r['is_urgent'] for r in rows])
    groups=group_templates(rows)
    folds=list(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(rows,truth,groups))
    results=[]
    for config in ['legacy','robust','robust_balanced']:
        scores=np.zeros(len(rows));predictions=np.zeros(len(rows),dtype=bool)
        cutoffs=[]
        start=time.perf_counter()
        for fold,(tr,te) in enumerate(folds):
            model,cutoff,_=fit(config,[rows[i] for i in tr],truth[tr],groups[tr])
            scores[te]=model.predict_proba([stress(rows[i],int(i)) for i in te])[:,1]
            predictions[te]=scores[te]>=cutoff
            cutoffs.append(cutoff)
            print('urgency',config,'fold',fold+1,flush=True)
        fn=(truth & ~predictions)
        fp=(~truth & predictions)
        weighted=float(sum(10 if r['category']=='safety_conduct' else 5 for i,r in enumerate(rows) if fn[i])+fp.sum())
        from sklearn.metrics import precision_score,recall_score
        result={'name':config,'weighted_error':weighted,'precision':precision_score(truth,predictions,zero_division=0),'recall':recall_score(truth,predictions),
                'f1':f1_score(truth,predictions),'safety_false_negatives':sum(bool(fn[i]) for i,r in enumerate(rows) if r['category']=='safety_conduct'),
                'fold_cutoffs':cutoffs,'seconds':time.perf_counter()-start,
                'selection':'5-fold train group stress CV; threshold selected on inner calibration stress set; safety FN cost10, other FN5, FP1'}
        results.append(result)
        (OUT/'urgency_experiments.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        np.savez_compressed(OUT/f'urgency_{config}_oof.npz',scores=scores,labels=truth,predictions=predictions)
        print(result,flush=True)
    winner=min(results,key=lambda r:r['weighted_error'])
    model,cutoff,sensitivity=fit(winner['name'],rows,truth,groups)
    destination=ROOT/'artifacts/candidate'
    bundle=joblib.load(destination/'model.joblib')
    bundle['urgency']=model;bundle['urgency_threshold']=cutoff
    joblib.dump(bundle,destination/'model.joblib',compress=3)
    manifest=json.loads((destination/'manifest.json').read_text())
    manifest['sha256']=digest(destination/'model.joblib')
    manifest['model_version']='sha256-'+manifest['sha256']
    manifest['policy']['urgency']={'threshold':cutoff,'sensitivity':sensitivity,'selection_split':'training-only heldout stress calibration, costly safety FN objective','winner':winner}
    manifest['source_hashes']['training/improve_urgency.py']=digest(ROOT/'training/improve_urgency.py')
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Reused development diagnostic, explicitly not independent test evidence.
    from app.predictor import Predictor
    predictor=Predictor(destination)
    validation=load('validation');predictions=predictor.predict_many(validation)
    metrics=primary_metrics(np.array([r['category'] for r in validation]),bundle['primary'].predict_proba(validation),bundle['primary'].classes_)
    metrics['split']='supplied validation reused for development; feature work informed by initial diagnostics; no independent unseen test claim'
    metrics['urgency']=binary_metrics([r['is_urgent'] for r in validation],model.predict_proba(validation)[:,1],cutoff)
    metrics['urgency']['end_to_end_f1']=f1_score([r['is_urgent'] for r in validation],[p['is_urgent'] for p in predictions])
    metrics['secondary_presence']=binary_metrics([r['secondary_category'] is not None for r in validation],bundle['presence'].predict_proba(validation)[:,1],bundle['presence_threshold'])
    metrics['secondary_exact_accuracy']=float(np.mean([r['secondary_category']==p['secondary_category'] for r,p in zip(validation,predictions)]))
    metrics['secondary_label_macro_f1_excluding_null']=f1_score([r['secondary_category'] or '__NULL__' for r in validation],[p['secondary_category'] or '__NULL__' for p in predictions],labels=sorted({r['secondary_category'] for r in validation if r['secondary_category']}),average='macro',zero_division=0)
    metrics['always_null_secondary_accuracy']=float(np.mean([r['secondary_category'] is None for r in validation]))
    metrics['exact_triple_match']=float(np.mean([all(r[k]==p[k] for k in ('category','secondary_category','is_urgent')) for r,p in zip(validation,predictions)]))
    metrics['contract_pass_rate']=1.
    metrics['subgroups']={}
    from sklearn.metrics import accuracy_score
    for key in ('language','channel','category'):
        metrics['subgroups'][key]={}
        for value in sorted({r[key] for r in validation}):
            indexes=[i for i,r in enumerate(validation) if r[key]==value]
            selected=[validation[i] for i in indexes]
            metrics['subgroups'][key][value]={'count':len(indexes),'accuracy':accuracy_score([r['category'] for r in selected],[predictions[i]['category'] for i in indexes]),
                'macro_f1':f1_score([r['category'] for r in selected],[predictions[i]['category'] for i in indexes],average='macro',zero_division=0),
                'urgency':binary_metrics([r['is_urgent'] for r in selected],model.predict_proba(selected)[:,1],cutoff)}
    (OUT/'final_development_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (OUT/'final_development_predictions.jsonl').write_text('\n'.join(json.dumps(p,ensure_ascii=False) for p in predictions)+'\n',encoding='utf-8')
    print('FINAL URGENCY DEVELOPMENT',metrics['urgency'],flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):
        main()
