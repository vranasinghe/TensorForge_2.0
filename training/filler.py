"""Filler-sentence removal experiment.

Tickets are boilerplate heavy: frequent sentences that occur across many unrelated
categories ("I have kept the confirmation") dilute the TF-IDF vectors while the one
signal sentence is often a paraphrase unseen in training. FillerText learns, inside
each training fit only, which normalised sentences are frequent and label-uninformative
(df >= min_df and label entropy >= min_entropy) and drops them before vectorisation.
Unseen sentences are always kept. Nothing here uses labels at inference time.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import collections
import json
import math
import re
import sys
import time
from pathlib import Path
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from threadpoolctl import threadpool_limits
from training.features import ChannelInput
from training.robust_features import RobustText, clean_text

SENTENCE = re.compile(r'[^.!?]+[.!?]*')
NOISE = re.compile(r'\b[A-Za-z]{2,8}-[A-Za-z0-9]{5,}\b|\[REFERENCE\]|\d+(?:\.\d+)?k?')


def normal(sentence):
    return re.sub(r'\s+', ' ', NOISE.sub('N', sentence.casefold())).strip(' .!?')


def pieces(text):
    return [p for p in SENTENCE.findall(re.sub(r'\s+', ' ', text)) if p.strip()]


def entropy(counts):
    n = sum(counts.values())
    return -sum(v / n * math.log2(v / n) for v in counts.values())


class FillerText(RobustText):
    def __init__(self, mask_references=False, resolved_quotes=False, min_df=20, min_entropy=2.0):
        super().__init__(mask_references, resolved_quotes)
        self.min_df = min_df
        self.min_entropy = min_entropy

    def _fields(self, row):
        return [clean_text(row.get('subject', ''), self.mask_references, self.resolved_quotes),
                clean_text(row['text'], self.mask_references, self.resolved_quotes)]

    def fit(self, x, y=None):
        seen = collections.defaultdict(collections.Counter)
        for row, label in zip(x, y):
            for key in {normal(p) for field in self._fields(row) for p in pieces(field)}:
                seen[key][label] += 1
        self.filler_ = frozenset(k for k, c in seen.items() if sum(c.values()) >= self.min_df and entropy(c) >= self.min_entropy)
        return self

    def _strip(self, text):
        kept = [p for p in pieces(text) if normal(p) not in self.filler_]
        return ' '.join(kept) if kept else text

    def transform(self, x):
        return ['[SUBJECT] ' + self._strip(s) + '\n[BODY] ' + self._strip(b) for s, b in (self._fields(r) for r in x)]


def features(mask=True, quotes=True, min_df=20, min_entropy=2.0):
    def text():
        return FillerText(mask, quotes, min_df, min_entropy)
    return FeatureUnion([
        ('channel', Pipeline([('input', ChannelInput()), ('vectorizer', DictVectorizer())])),
        ('word', Pipeline([('input', text()), ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True))])),
        ('char', Pipeline([('input', text()), ('vectorizer', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), min_df=2, max_features=50000, sublinear_tf=True))])),
    ])


VARIANTS = [  # fixed before any validation measurement of the filler idea
    ('baseline_no_filler', None),
    ('filler_df20_h2.0', (20, 2.0)),
    ('filler_df10_h1.5', (10, 1.5)),
    ('filler_df40_h2.5', (40, 2.5)),
]


def model(spec, weight):
    from sklearn.svm import LinearSVC
    from training.robust_features import features as base_features
    feats = base_features(True, True) if spec is None else features(True, True, *spec)
    return Pipeline([('features', feats), ('classifier', LinearSVC(C=1., class_weight=weight, random_state=42))])


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
    for name, spec in VARIANTS:
        t = time.perf_counter()
        pred = np.empty(len(rows), dtype=object)
        for tr, te in folds:
            m = fit_primary(model(spec, weight), [rows[i] for i in tr], y[tr], groups[tr])
            pred[te] = m.predict([rows[i] for i in te])
        final = fit_primary(model(spec, weight), rows, y, groups)
        pv = final.predict(validation)
        langs = {lang: float(np.mean(pv[[r['language'] == lang for r in validation]] == yv[[r['language'] == lang for r in validation]])) for lang in sorted({r['language'] for r in validation})}
        result = {'name': name, 'spec': spec, 'train_group_cv_accuracy': float(accuracy_score(y, pred)),
                  'train_group_cv_macro_f1': float(f1_score(y, pred, average='macro')),
                  'validation_accuracy': float(accuracy_score(yv, pv)), 'validation_macro_f1': float(f1_score(yv, pv, average='macro')),
                  'validation_language_accuracy': langs, 'seconds': round(time.perf_counter() - t, 1)}
        results.append(result)
        print(json.dumps(result), flush=True)
    out = ROOT / 'experiments/improvement'
    (out / 'filler_experiment.json').write_text(json.dumps({
        'note': 'supplied validation is reused development data (see PROGRESS.md); four variants fixed in advance, all reported; not an unseen-test claim',
        'seed': 42, 'results': results}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
