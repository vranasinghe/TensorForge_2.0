"""Soft-vote primary classifier over complementary tokenisations.

Sinhala and Tamil disagree about what a "word" is. The default scikit-learn token
pattern uses \\w, which drops the combining vowel signs and virama that Sinhala and
Tamil spell with, so native-script words are shredded into fragments. The widened
UNICODE_TOKEN pattern keeps them whole. Measured on the validation selection half,
each pattern wins on a different language (Unicode tokens help Tamil, the default
pattern helps Sinhala), so the deployed primary averages the calibrated probabilities
of one member per pattern instead of choosing between them.

This module is imported when artifacts/model.joblib is unpickled, so it must stay
importable with no optional dependencies.
"""
from sklearn.base import BaseEstimator
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from training.features import ChannelInput
from training.robust_features import UNICODE_TOKEN, RobustText

# Vocabulary caps are deliberately small: raising word 20k->120k and char 50k->200k
# changed the selection-half score by exactly zero while making the artifact 5x bigger.
WORD_MAX = 20000
CHAR_MAX = 50000


def vote_features(unicode_tokens=True, mask=True, quotes=True, char_range=(2, 6),
                  word_min_df=1, char_min_df=1, word_max=WORD_MAX, char_max=CHAR_MAX):
    """Channel + word + character features over the three guaranteed inputs only."""
    token_pattern = UNICODE_TOKEN if unicode_tokens else r'(?u)\b\w\w+\b'
    return FeatureUnion([
        ('channel', Pipeline([('input', ChannelInput()), ('vectorizer', DictVectorizer())])),
        ('word', Pipeline([('input', RobustText(mask, quotes)),
                           ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), min_df=word_min_df,
                                                          max_features=word_max, sublinear_tf=True,
                                                          token_pattern=token_pattern))])),
        ('char', Pipeline([('input', RobustText(mask, quotes)),
                           ('vectorizer', TfidfVectorizer(analyzer='char_wb', ngram_range=char_range,
                                                          min_df=char_min_df, max_features=char_max,
                                                          sublinear_tf=True))])),
    ])


class VoteEnsemble(BaseEstimator):
    """Average the calibrated class probabilities of members that share a class order."""

    def __init__(self, members=()):
        self.members = list(members)
        if self.members:
            first = list(self.members[0].classes_)
            for other in self.members[1:]:
                if list(other.classes_) != first:
                    raise ValueError('Vote members disagree about class order')
            self.classes_ = self.members[0].classes_

    def predict_proba(self, rows):
        total = self.members[0].predict_proba(rows)
        for member in self.members[1:]:
            total = total + member.predict_proba(rows)
        return total / len(self.members)

    def predict(self, rows):
        return self.classes_[self.predict_proba(rows).argmax(axis=1)]


class TemperatureScaled(BaseEstimator):
    """Sharpen or soften an already-calibrated model by one scalar.

    Averaging two probability vectors always produces something flatter than either
    input, so the vote came out systematically under-confident: on the validation
    selection half its 0.8 bin was right 94% of the time. Rescaling by
    ``p ** (1 / temperature)`` and renormalising is strictly monotone and identical
    across classes, so the predicted label and therefore every accuracy figure are
    unchanged by construction; only the reported confidence moves. Temperature below
    one sharpens. Fitted on held-out rows, never on the training set the base model saw.
    """

    def __init__(self, base=None, temperature=1.0):
        self.base = base
        self.temperature = float(temperature)
        if base is not None:
            self.classes_ = base.classes_

    def predict_proba(self, rows):
        return self.rescale(self.base.predict_proba(rows))

    def rescale(self, probabilities):
        import numpy as np
        sharpened = np.clip(probabilities, 1e-12, None) ** (1.0 / self.temperature)
        return sharpened / sharpened.sum(axis=1, keepdims=True)

    def predict(self, rows):
        return self.classes_[self.predict_proba(rows).argmax(axis=1)]


def fit_temperature(probabilities, truth, classes, grid=None):
    """Pick the temperature minimising held-out log loss. Returns (temperature, table)."""
    import numpy as np
    index = {c: i for i, c in enumerate(classes)}
    target = np.array([index[t] for t in truth])
    scaler = TemperatureScaled(None, 1.0)
    table = []
    for temperature in (grid if grid is not None else np.arange(.30, 2.01, .05)):
        scaler.temperature = float(temperature)
        scaled = scaler.rescale(probabilities)
        loss = float(-np.log(np.clip(scaled[np.arange(len(target)), target], 1e-12, None)).mean())
        table.append({'temperature': round(float(temperature), 3), 'log_loss': loss})
    best = min(table, key=lambda row: row['log_loss'])
    return best['temperature'], table
