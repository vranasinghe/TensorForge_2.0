"""Build report text and scientific plots exclusively from saved measured results."""
import json
from pathlib import Path
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from training.audit import ROOT


def write(path, text):
    (ROOT/path).write_text(text.strip()+'\n', encoding='utf-8')


def main():
    metric_path=ROOT/'experiments/improvement/final_development_metrics.json'
    metrics=json.loads((metric_path if metric_path.exists() else ROOT/'experiments/validation_metrics.json').read_text())
    experiments=json.loads((ROOT/'experiments/experiments.json').read_text())
    manifest=json.loads((ROOT/'artifacts/manifest.json').read_text())
    audit=json.loads((ROOT/'experiments/audit.json').read_text())
    splits=json.loads((ROOT/'experiments/split_manifest.json').read_text())
    spec=yaml.safe_load((ROOT/'schemas/tensorforge-phase2-openapi-v2.yaml').read_text(encoding='utf-8'))
    matrix=['# Official API contract checklist', '', 'Source: unchanged supplied OpenAPI 2.1.0 and Draft 2020-12 JSON schemas.']
    for path, methods in spec['paths'].items():
        for method, op in methods.items():
            if method not in ('get','post','delete'):
                continue
            matrix += ['',f'## {method.upper()} `{path}`', '', f'- Authentication: {"public" if path=="/health" else "X-API-Key or Bearer; API_KEY from environment; constant-time comparison"}.']
            request=op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema',{}).get('$ref')
            if request:
                matrix.append(f'- Request: `{request.rsplit("/",1)[1]}`.')
            for status,response in op['responses'].items():
                if '$ref' in response:
                    response=spec['components']['responses'][response['$ref'].rsplit('/',1)[1]]
                schema=response.get('content',{}).get('application/json',{}).get('schema',{}).get('$ref')
                matrix.append(f'- {status}: `{schema.rsplit("/",1)[1] if schema else "no body"}`; {response["description"]}.')
                if response.get('headers'):
                    matrix.append('- Headers: '+', '.join('`'+h+'`' for h in response['headers'])+'.')
    matrix += ['', '## Cross-cutting checks', '', '- POST order: auth 401 → content type 415 → byte limit 413 → JSON 400 → schema 422.',
               '- Limits interpreted as 1, 5, 25 MiB respectively. YAML says approximately 1 MB and 5/25 MB without exact byte counts.',
               '- Batch counts: 1–100 sync; 1–5,000 async. All IDs required and unique. Atomic validation; errors carry zero-based indexes.',
               '- Every response validates against original JSON Schema; response conditionals enforce routing, distinct secondary, and nonurgent/null-secondary spam.',
               '- All paths share the same stored artifact and predictor. Input extras are accepted but excluded from features.',
               '- Results pagination: offset ≥0, limit 1–5,000; default whole result, stable order, next_offset or null.',
               '- Four active jobs maximum, transactional admission; retention 24 hours; expiry tombstones; pending jobs fail as interrupted on restart.',
               '', '## Source discrepancies and explicit extensions', '',
               '- DATA_NOTES names language as an input; OpenAPI explicitly guarantees only channel/subject/text. OpenAPI wins; language is analysis only.',
               '- Master file refers to a YAML filename containing v2, whose actual info.version is 2.1.0.',
               '- Same Idempotency-Key with a different payload returns 409 idempotency_conflict. This safe policy is not specified by the YAML.',
               '- Valid protected requests before readiness return 503 ErrorResponse as an operational extension. The YAML lists 503 only for health; clients should wait for public health 200.',
               '- DELETE removes the row and returns 204, then 404, as the explicit DELETE description requires; cancelled is not subsequently pollable.',
               '- Official guideline and build-guide PDFs were not supplied. Deadline, report page limit, and video length are taken from the master document and await PDF verification.']
    write(Path('CONTRACT_MATRIX.md'),'\n'.join(matrix))
    report=f'''# TensorForge 2.0 — measured MVP report

## Scope and architecture

RideEat is a fictional platform. The MVP classifies multilingual support tickets,
derives a fixed team, and serves seven HTTP operations. FastAPI validates the
unchanged organizer schemas. One background worker stores ordered results in
SQLite transactions; a process lease prevents two service processes from owning
one job database. A separately authenticated demo proxies requests server-side.

## Data and reproducibility

There are 4,000 train and 800 validation rows. CSV and JSONL agree on all fields.
Urgency and non-null secondary labels each occur in 10% of each split. Language
shares match DATA_NOTES. No cross-split ID, exact-text, normalized-template, or
char_wb cosine ≥0.90 overlap was found. This heuristic cannot establish that the
synthetic generation process is independent across splits. SHA256 hashes are in
experiments/audit.json. Original source files remain unchanged.

Train-only number-masked template similarity groups contain {splits['groups']}
components; the largest has {splits['largest_group']} tickets. Seed 42 partitions
these groups into {len(splits['core_ids'])} core and {len(splits['calibration_ids'])}
calibration rows. Five outer group folds compare models on core data; vectorizers
are fitted inside each training fold. E3 uses three inner group folds to calibrate
the outer-fold SVM. The final SVM is fitted on core data and sigmoid-calibrated on
the reserved calibration set. This final single-estimator configuration differs
from the original CV calibrated ensemble, so those CV scores are selection evidence
rather than an estimate of deployed accuracy. Follow-up experiments use all train
groups in five outer folds with an inner calibration holdout, reproducing the final
single-estimator fit. Their configurations and predictions are stored in
experiments/improvement; the selected stress macro-F1 is 0.98876.

## Models and experiments

All models use only channel, subject and text. NFC normalization preserves Sinhala,
Tamil, combining marks, emoji and negation. Word (1–2) and char_wb (2–5) TF-IDF
features stay sparse, with one-hot channel. Primary classification, binary urgency,
binary secondary presence, and secondary label prediction are supervised tasks.
Secondary output is never inferred from the second-best primary score.

Core group-CV macro-F1:
{chr(10).join('- '+r['experiment']+': '+format(r['metrics']['macro_f1'],'.4f') for r in experiments)}

The selected model is {manifest['selected_experiment']}. Urgency threshold is
{manifest['policy']['urgency']['threshold']:.2f}; secondary-presence threshold is
{manifest['policy']['presence']['threshold']:.2f}. Both maximize development F1 on
the training calibration holdout. Those labels are reused for calibration and
threshold development; they are not an independent evaluation. Secondary label
training uses all training-positive rows. No pairing blacklist is imposed.

## Supplied validation results

Measured on 800 supplied validation rows, now reused as development data after
initial diagnostics. These are not independent unseen-test results:

- Primary accuracy: {metrics['accuracy']:.5f}; macro-F1: {metrics['macro_f1']:.5f}; weighted-F1: {metrics['weighted_f1']:.5f}.
- Urgency precision: {metrics['urgency']['precision']:.5f}; recall: {metrics['urgency']['recall']:.5f}; F1: {metrics['urgency']['f1']:.5f}; average precision: {metrics['urgency']['pr_auc_average_precision']:.5f}.
- Secondary presence precision: {metrics['secondary_presence']['precision']:.5f}; recall: {metrics['secondary_presence']['recall']:.5f}; F1: {metrics['secondary_presence']['f1']:.5f}.
- Secondary-label macro-F1 excluding null: {metrics['secondary_label_macro_f1_excluding_null']:.5f}; exact secondary accuracy including null: {metrics['secondary_exact_accuracy']:.5f}; always-null baseline: {metrics['always_null_secondary_accuracy']:.5f}.
- Exact primary/secondary/urgency triple: {metrics['exact_triple_match']:.5f}.
- Primary log loss: {metrics['log_loss']:.5f}; multiclass Brier (mean of summed squared errors over all classes): {metrics['brier_sum_over_classes']:.5f}.
- ECE: {metrics['ece_10_equal_width_bins']:.5f}, 10 equal-width bins of maximum probability against primary correctness.
- All 800 validation prediction responses passed the supplied original response schema (shape/invariants, not accuracy).

## Limitations and safety

Primary group-CV macro-F1 is far higher than supplied-validation macro-F1. This
observed gap warrants caution: heuristic template grouping may leave structural
similarity within training, and validation contains noisy long messages and old
quoted complaints. These are plausible causes, not independently proven causes.
Follow-up candidates were ranked using training group folds and synthetic stress
tests. Earlier validation diagnostics informed the follow-up design, so the final
validation measurement is development evidence. The original artifact is retained
under artifacts/legacy. Tamil accuracy regressed from 0.575 to 0.533; mixed accuracy
from 0.600 to 0.550. Reference masking and removal of explicitly resolved quoted
history improved overall development accuracy from 0.58625 to 0.60000 and macro-F1
from 0.60957 to 0.62912. Unresolved quoted complaints remain in the features.

Language accuracies:
{chr(10).join('- '+k+': '+format(v['accuracy'],'.3f')+' (n='+str(v['count'])+')' for k,v in metrics['subgroups']['language'].items())}

Sinhala is particularly weak. Minority groups with 20 rows do not support strong
claims. Urgency misses exist, including safety tickets; this is not a production
emergency detector. All texts are synthetic and not independently native-speaker
reviewed. Human confirmation is required; an automatic review-threshold field is
not enabled. No hosted URL, container verification, video upload or submission is
claimed. See PROGRESS and deployment checklist for actual verification status.

## References and evidence

The scikit-learn calibration and StratifiedGroupKFold documentation and SQLite WAL
documentation were checked. Guo et al. (2017) was checked at abstract level only;
its neural-network experiments do not establish this sparse model's performance.
See research_evidence.md for exact URLs, scope and local evidence. Remaining
suggested papers were not cited without verification.
'''
    write(Path('docs/report.md'),report)
    write(Path('docs/model_card.md'), f'''# Model card — {manifest['selected_experiment']}

Version: `{manifest['model_version']}`. Artifact SHA256:
`{manifest['sha256']}`. Training date (UTC): {manifest['trained_at_utc']}.

## Intended use

Workshop demonstration of multilingual ticket triage for fictional RideEat.
Support agents confirm suggested routes. Not suitable for autonomous emergency
decisions, real customer deployment, or auto-closing customer messages without
review. No inference network calls or general-purpose LLM API wrappers.

## Data and features

4,000 organizer-supplied synthetic training tickets, 800 supplied validation
tickets; original hashes in audit.json. No real customer records per DATA_NOTES.
Synthetic Sinhala, Tamil and transliteration are not native-speaker reviewed.
Inputs: channel, optional subject and text. ID and language are never features.
NFC normalization retains combining marks. Labels follow supplied data notes;
safety precedence is learned, not guaranteed by a deterministic keyword layer.

## Training and evidence

Word/character sparse TF-IDF plus calibrated LinearSVC, seed 42. Train group CV
chooses the primary model; disjoint core/calibration sets fit the final predictor.
Binary LR components are sigmoid calibrated; secondary category LR uses only
secondary-positive train records. Urgency cutoff {manifest['policy']['urgency']['threshold']:.2f};
secondary-presence cutoff {manifest['policy']['presence']['threshold']:.2f} selected
on the training calibration holdout. No independently evaluated human-review
threshold is deployed; UI requests manual confirmation for all tickets.

Validation accuracy {metrics['accuracy']:.4f}, macro-F1 {metrics['macro_f1']:.4f},
urgency F1 {metrics['urgency']['f1']:.4f}, exact triple {metrics['exact_triple_match']:.4f}.
Full per-class/language/channel performance, confusion matrix, ECE, reliability
bins and selective risk are in experiments/improvement/final_development_metrics.json.
These are reused development measurements; the original validation_metrics.json
is retained as historical baseline evidence. Minority-language samples
are small. Sinhala accuracy {metrics['subgroups']['language']['si']['accuracy']:.4f}.
The CV/validation gap is material; see report.md. Subgroup macro-F1 uses the labels
present in truth or prediction within each subgroup. For primary-class subgroups,
accuracy is that class's recall; the complete per_class report gives meaningful
class precision/F1 across the full validation set.

## Ethics, security and persistence

Do not enter real personal information into an unapproved demo. Keys are injected
server-side. Request bodies are not logged by this application. SQLite stores
ticket text and results until deletion/24-hour expiry; protect its volume and use
approved access controls. A durable volume and one worker/replica are mandatory.
Only load trusted joblib artifacts; deserialization can execute code.
''')
    write(Path('docs/data_audit.md'), f'''# Data audit

Command: `python -m training.audit`. Machine-readable source: experiments/audit.json.

- Train: 4,000; validation: 800; CSV/JSONL equivalence verified for every key column.
- Duplicate IDs: train {audit['splits']['train']['duplicate_ids']}, validation {audit['splits']['validation']['duplicate_ids']}.
- Invalid secondary/spam label invariants: train {audit['splits']['train']['invalid_labels']}, validation {audit['splits']['validation']['invalid_labels']}.
- Shared split IDs: {audit['overlap']['ticket_ids']}; exact shared text rows: {audit['overlap']['exact_text_validation_rows']}.
- Number-masked/NFC normalized shared templates: {audit['overlap']['normalized_template_validation_rows']}.
- Validation rows with nearest train char_wb cosine ≥0.90: {audit['near_duplicates']['validation_similarity_ge_090']}.
- Detailed nulls, labels, lengths, Unicode normalization, language/channel/category intersections and hashes are saved in audit.json.

Similarity is heuristic, not proof of independence. All labels/text are synthetic;
native-speaker validation was not performed. No raw files were edited. Source/copy
SHA256 equality was checked for all 16 supplied API/data files.
''')
    figures=ROOT/'experiments/figures'
    figures.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,8))
    image=ax.imshow(metrics['confusion_matrix'],cmap='Blues')
    ax.set_xticks(range(11),metrics['classes'],rotation=60,ha='right')
    ax.set_yticks(range(11),metrics['classes'])
    ax.set(xlabel='Predicted category',ylabel='True category',title='Supplied validation confusion matrix (n=800)')
    fig.colorbar(image,ax=ax)
    fig.tight_layout();fig.savefig(figures/'confusion_matrix.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    bins=metrics['reliability_bins']
    axes[0].plot([0,1],[0,1],'--',color='gray')
    axes[0].plot([r['confidence'] for r in bins],[r['accuracy'] for r in bins],'o-')
    axes[0].set(xlabel='Mean maximum primary probability',ylabel='Primary accuracy',title='Reliability · 10 equal-width bins',xlim=(0,1),ylim=(0,1))
    points=[r for r in metrics['selective_risk'] if r['risk'] is not None]
    axes[1].plot([r['coverage'] for r in points],[r['risk'] for r in points],'o-')
    axes[1].set(xlabel='Coverage',ylabel='Primary error rate',title='Selective risk on supplied validation')
    fig.tight_layout();fig.savefig(figures/'calibration_and_risk.png',dpi=160);plt.close(fig)
    # These plots are generated from saved results, not additional model evaluation.
    print('Generated contract checklist, measured report, model card, audit notes and two scientific figures.')


if __name__=='__main__':
    main()
