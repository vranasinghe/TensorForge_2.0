"""Reconcile generated baseline documentation with measured follow-up evidence."""
import json
from training.audit import ROOT


def main():
    manifest=json.loads((ROOT/'artifacts/manifest.json').read_text())
    note='''

## Follow-up completion: steps 2–5, Docker deferred

All 82 tests and 15 schema subtests passed, along with network-blocked model
inference. Real Chrome desktop/mobile interaction, CSV download, job deletion,
keyboard focus and no-backend-key browser checks passed. Actual HTTP proxy and
dedicated async lifecycle/version checks also passed on localhost.

Current primary: reference masking, explicitly resolved quote handling, calibrated
word/character LinearSVC with safety weight 2, selected by five training group
folds and synthetic stress tests. Independent urgency preprocessing/class-weight
experiments are retained. Default urgency cutoff 0.45 maximizes training holdout
F1; cutoff 0.10 is a separate recall-first artifact, not the default.

The supplied validation is now reused development data. Current accuracy 0.60000,
macro-F1 0.62912, versus original 0.58625 / 0.60957. Tamil regressed 0.575 to 0.533;
mixed regressed 0.600 to 0.550. Default urgency precision 0.91429, recall 0.80000,
F1 0.85333; recall-first precision 0.51034, recall 0.92500, F1 0.65778. Original
artifact and alternate policy remain selectable in artifacts/legacy and
artifacts/high_recall. Fresh evaluation data is needed for unseen-test claims.

Detailed evidence: experiments/improvement/final_development_metrics.json,
promoted.json, urgency_policy_comparison.json, experiments/browser/verification.json,
and benchmark.json. Original validation_metrics.json remains historical evidence.

Native HTTPS deployment is prepared under deploy/; installer shell syntax and
publication PowerShell syntax passed. Neither installer nor CI has run remotely.
GitHub is signed out, no remote repository/server/DNS access was supplied, and
public deployment/publication/upload/submission remain pending. A short silent
browser recording exists; the narrated fifteen-minute walkthrough is still pending.
The source/artifact release archive excludes local databases, environments and keys.
See docs/non_docker_completion.md for exact next steps. Docker tests remain deferred.
'''
    for name in ('README.md','PROGRESS.md','BUILD_STEPS.md'):
        path=ROOT/name
        text=path.read_text(encoding='utf-8').split('\n## Follow-up completion:')[0]
        text=text.replace('Supplied validation n=800, seed 42, evaluated after train-only selection:',
                          'Reused supplied development split n=800, seed 42:')
        text=text.replace('Supplied validation n=800:', 'Reused development split n=800:')
        text=text.replace('Selected E3 calibrated word+character SVM; C/class-weight experiments retained.',
                          'Original E3 retained; current robust calibrated word+character SVM is described below.')
        text=text.replace('Node/browser automation runtimes remained unavailable.',
                          'Browser automation subsequently succeeded through bundled Playwright and installed Chrome.')
        text=text.replace('GitHub publication, YouTube recording/upload, submission and team signoff are',
                          'GitHub publication, full narrated YouTube recording/upload, submission and team signoff are')
        path.write_text(text+note+'\nCurrent model version: `'+manifest['model_version']+'`.\n',encoding='utf-8')
    path=ROOT/'docs/video_script.md'
    text=path.read_text(encoding='utf-8').replace('Video URL: pending. Recording and upload have not been performed.',
         'Video URL: pending. Short silent browser footage exists at output/rideeat_demo.webm; full narration and upload remain pending.')
    if 'Follow-up results to explain' not in text:
        text+='\n## Follow-up results to explain\n\nShow improve.py, improve_urgency.py and select_urgency_policy.py; explain training-only selection and development reuse. Report 60.0% accuracy, macro-F1 0.62912, Tamil/mixed regressions and the urgency false-alert tradeoff. Show retained baseline and policy artifacts. Do not describe native deployment as Docker verification.\n'
    path.write_text(text,encoding='utf-8')
    print('Reconciled final follow-up documentation.')


if __name__=='__main__':
    main()
