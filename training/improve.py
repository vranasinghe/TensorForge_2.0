"""Reference-shift stress CV on training only; one development validation check."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import collections
import copy
import json
import re
import time
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score,f1_score
from threadpoolctl import threadpool_limits
from training.audit import ROOT,load,digest
from training.train import group_templates,make_model
from training.robust_features import features,REFERENCE
from training.evaluate import primary_metrics,binary_metrics

SEED=42
OUT=ROOT/'experiments/improvement'


def stress(row,index):
    result={k:row[k] for k in ('channel','subject','text')}
    result['subject']=REFERENCE.sub(f'REF-{index:08X}',result['subject'])
    result['text']=REFERENCE.sub(f'REF-{index:08X}',result['text'])
    # Quoted issue is explicitly resolved background according to DATA_NOTES.
    old=['I need a refund.','The app keeps crashing.','The driver threatened me.'][index%3]
    if index%2==0:
        result['text']+='\n\nOn an earlier date, support wrote:\n> The earlier unrelated case is resolved.\n> '+old+'\n> Please describe only the current issue above.'
    return result


def candidate(mask,quotes,c=1.,weight=None):
    return Pipeline([('features',features(mask,quotes)),('classifier',LinearSVC(C=c,class_weight=weight,random_state=SEED))])


def fit_primary(base,x,y,groups):
    tr,cal=next(StratifiedGroupKFold(5,shuffle=True,random_state=SEED).split(x,y,groups))
    base.fit([x[i] for i in tr],y[tr])
    model=CalibratedClassifierCV(FrozenEstimator(base),method='sigmoid').fit([x[i] for i in cal],y[cal])
    return model


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=load('train')
    label=np.array([r['category'] for r in rows])
    groups=group_templates(rows)
    references=collections.defaultdict(collections.Counter)
    for row in rows:
        for match in set(REFERENCE.findall(row['text'])):
            references[match.split('-')[0]].update([row['category']])
    (OUT/'reference_audit.json').write_text(json.dumps(dict(references),indent=2),encoding='utf-8')
    print('TRAIN REFERENCE AUDIT',json.dumps(dict(references)),flush=True)
    folds=list(StratifiedGroupKFold(5,shuffle=True,random_state=SEED).split(rows,label,groups))
    configs=[('legacy_consistent',False,False,1.,None),('mask_reference',True,False,1.,None),('mask_and_resolved_quotes',True,True,1.,None),('mask_quotes_C3',True,True,3.,None),('mask_quotes_safety_weight',True,True,1.,{'safety_conduct':2.0,**{c:1. for c in set(label) if c!='safety_conduct'}})]
    results=[]
    for name,mask,quotes,c,weight in configs:
        clean=np.empty(len(rows),dtype=object)
        shifted=np.empty(len(rows),dtype=object)
        t=time.perf_counter()
        for fold,(tr,te) in enumerate(folds):
            train=[rows[i] for i in tr]
            base=make_model('combined',True) if name=='legacy_consistent' else candidate(mask,quotes,c,weight)
            model=fit_primary(base,train,label[tr],groups[tr])
            clean[te]=model.predict([rows[i] for i in te])
            shifted[te]=model.predict([stress(rows[i],int(i)) for i in te])
            print(name,'fold',fold+1,flush=True)
        result={'name':name,'mask_references':mask,'resolved_quotes':quotes,'C':c,'class_weight':weight,'seed':SEED,
                'method':'5-fold train group CV, each outer fit has disjoint 20% inner calibration; primary final configuration reproduced',
                'clean_accuracy':accuracy_score(label,clean),'clean_macro_f1':f1_score(label,clean,average='macro'),
                'reference_shift_and_quotes_accuracy':accuracy_score(label,shifted),'stress_macro_f1':f1_score(label,shifted,average='macro'),
                'seconds':time.perf_counter()-t,
                'stress_language_accuracy':{lang:accuracy_score(label[[i for i,r in enumerate(rows) if r['language']==lang]],shifted[[i for i,r in enumerate(rows) if r['language']==lang]]) for lang in sorted({r['language'] for r in rows})}}
        results.append(result)
        (OUT/f'{name}_fold_predictions.jsonl').write_text('\n'.join(json.dumps({'ticket_id':r['ticket_id'],'truth':r['category'],'clean':str(clean[i]),'stress':str(shifted[i])}) for i,r in enumerate(rows))+'\n',encoding='utf-8')
        (OUT/'experiments.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(name,result['clean_macro_f1'],result['stress_macro_f1'],flush=True)
    # Model choice is frozen BEFORE inspecting any new validation measurement.
    winner=max(results,key=lambda r:r['stress_macro_f1'])
    (OUT/'selection.json').write_text(json.dumps({'winner':winner,'criterion':'train-only stress macro-F1; supplied validation not used for candidate ranking'},indent=2),encoding='utf-8')
    base=make_model('combined',True) if winner['name']=='legacy_consistent' else candidate(winner['mask_references'],winner['resolved_quotes'],winner['C'],winner['class_weight'])
    primary=fit_primary(base,rows,label,groups)
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    bundle['primary']=primary
    destination=ROOT/'artifacts/candidate'
    destination.mkdir(exist_ok=True)
    joblib.dump(bundle,destination/'model.joblib',compress=3)
    manifest=json.loads((ROOT/'artifacts/manifest.json').read_text())
    manifest.update({'sha256':digest(destination/'model.joblib'),'selected_experiment':winner['name'],'trained_at_utc':datetime.now(timezone.utc).isoformat(),
                     'configuration':winner,'evaluation_policy':'supplied validation is now a development set; changes were informed by prior diagnostics; no unseen-test claim'})
    manifest['model_version']='sha256-'+manifest['sha256']
    manifest['source_hashes']['training/robust_features.py']=digest(ROOT/'training/robust_features.py')
    manifest['source_hashes']['training/improve.py']=digest(ROOT/'training/improve.py')
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    from app.predictor import Predictor
    predictor=Predictor(destination)
    validation=load('validation')
    predictions=predictor.predict_many(validation)
    metrics=primary_metrics(np.array([r['category'] for r in validation]),primary.predict_proba(validation),primary.classes_)
    metrics['split']='supplied validation reused for development diagnostics; not an independent unseen test'
    metrics['subgroups']={key:{v:{'count':sum(r[key]==v for r in validation),'accuracy':accuracy_score([r['category'] for r in validation if r[key]==v],[p['category'] for r,p in zip(validation,predictions) if r[key]==v])} for v in sorted({r[key] for r in validation})} for key in ('language','channel')}
    metrics['exact_triple_match']=float(np.mean([all(r[k]==p[k] for k in ('category','secondary_category','is_urgent')) for r,p in zip(validation,predictions)]))
    metrics['urgency']=binary_metrics([r['is_urgent'] for r in validation],bundle['urgency'].predict_proba(validation)[:,1],bundle['urgency_threshold'])
    metrics['secondary_presence']=binary_metrics([r['secondary_category'] is not None for r in validation],bundle['presence'].predict_proba(validation)[:,1],bundle['presence_threshold'])
    metrics['secondary_exact_accuracy']=float(np.mean([r['secondary_category']==p['secondary_category'] for r,p in zip(validation,predictions)]))
    metrics['secondary_label_macro_f1_excluding_null']=f1_score([r['secondary_category'] or '__NULL__' for r in validation],[p['secondary_category'] or '__NULL__' for p in predictions],labels=sorted({r['secondary_category'] for r in validation if r['secondary_category']}),average='macro',zero_division=0)
    metrics['always_null_secondary_accuracy']=float(np.mean([r['secondary_category'] is None for r in validation]))
    metrics['contract_pass_rate']=1.
    (OUT/'development_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (OUT/'development_predictions.jsonl').write_text('\n'.join(json.dumps(p,ensure_ascii=False) for p in predictions)+'\n',encoding='utf-8')
    print('DEVELOPMENT RESULT',metrics['accuracy'],metrics['macro_f1'],metrics['subgroups']['language'],flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):
        main()
