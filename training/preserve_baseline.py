"""Retain a deployable E0 fallback without evaluating validation again."""
import json
import copy
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from threadpoolctl import threadpool_limits
from training.audit import ROOT, load, digest
from training.train import make_model


def main():
    rows={r['ticket_id']:r for r in load('train')}
    split=json.loads((ROOT/'experiments/split_manifest.json').read_text())
    core=[rows[i] for i in split['core_ids']]
    calibration=[rows[i] for i in split['calibration_ids']]
    primary=make_model('word').fit(core,[r['category'] for r in core])
    primary=CalibratedClassifierCV(FrozenEstimator(primary),method='sigmoid').fit(calibration,[r['category'] for r in calibration])
    bundle=joblib.load(ROOT/'artifacts/model.joblib')
    bundle['primary']=primary
    destination=ROOT/'artifacts/baseline'
    destination.mkdir(exist_ok=True)
    joblib.dump(bundle,destination/'model.joblib',compress=3)
    manifest=json.loads((ROOT/'artifacts/manifest.json').read_text())
    manifest['sha256']=digest(destination/'model.joblib')
    manifest['model_version']='sha256-'+manifest['sha256']
    manifest['selected_experiment']='E0_fallback'
    manifest['configuration']={'kind':'word','svm':False,'C':1.,'class_weight':None}
    manifest['limitations'].append('Fallback primary is E0; urgency/secondary reuse selected bundle. Fallback has no separate final validation measurement.')
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    from app.predictor import Predictor
    Predictor(destination).predict_one({'channel':'chat','text':'My food is late.'})
    print('Preserved deployable E0 primary fallback; no validation reevaluation.')


if __name__=='__main__':
    with threadpool_limits(limits=1):
        main()
