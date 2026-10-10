"""Features use exclusively the three guaranteed inputs, preserving Unicode."""
import unicodedata
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion


def compose(row):
    return unicodedata.normalize('NFC', '[SUBJECT] ' + row.get('subject', '') + '\n[BODY] ' + row['text'])


class TextInput(BaseEstimator, TransformerMixin):
    def fit(self, x, y=None):
        return self

    def transform(self, x):
        return [compose(r) for r in x]


class ChannelInput(BaseEstimator, TransformerMixin):
    def fit(self, x, y=None):
        return self

    def transform(self, x):
        return [{'channel': r['channel']} for r in x]


def features(kind='combined'):
    parts = [('channel', Pipeline([('input', ChannelInput()), ('vectorizer', DictVectorizer())]))]
    if kind in ('word', 'combined'):
        parts.append(('word', Pipeline([('input', TextInput()), ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=20000))])))
    if kind in ('char', 'combined'):
        parts.append(('char', Pipeline([('input', TextInput()), ('vectorizer', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=50000))])))
    return FeatureUnion(parts)
