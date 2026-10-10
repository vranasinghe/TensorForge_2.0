"""Candidate structural preprocessing; legacy features remain unchanged."""
import re
import unicodedata
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from training.features import ChannelInput

REFERENCE = re.compile(r'\bSIM[A-Z]-[A-Z0-9]+\b|\b[A-Z]{2,8}-[A-Z0-9]{5,}\b')


def clean_text(text, mask_references=False, resolved_quotes=False):
    text=unicodedata.normalize('NFC',text)
    if resolved_quotes:
        boundary=re.search(r'(?im)^\s*on\b[^\n]*(?:earlier|previous|old)[^\n]*wrote\s*:',text)
        if boundary and re.search(r'(?i)\b(?:resolved|unrelated|closed)\b',text[boundary.start():]):
            text=text[:boundary.start()]
        else:
            quoted='\n'.join(line for line in text.splitlines() if re.match(r'^\s*>',line))
            if re.search(r'(?i)\b(?:resolved|unrelated|closed)\b',quoted):
                text='\n'.join(line for line in text.splitlines() if not re.match(r'^\s*>',line))
    if mask_references:
        text=REFERENCE.sub('[REFERENCE]',text)
    return text


class RobustText(BaseEstimator,TransformerMixin):
    def __init__(self,mask_references=False,resolved_quotes=False):
        self.mask_references=mask_references
        self.resolved_quotes=resolved_quotes

    def fit(self,x,y=None):
        return self

    def transform(self,x):
        return ['[SUBJECT] '+clean_text(r.get('subject',''),self.mask_references,self.resolved_quotes)+'\n[BODY] '+clean_text(r['text'],self.mask_references,self.resolved_quotes) for r in x]


# The default token pattern uses \w, which excludes Sinhala/Tamil combining vowel signs
# and virama (categories Mn/Mc), so native-script words were shredded into fragments.
UNICODE_TOKEN=r'(?u)(?:[\w඀-෿஀-௿‌‍]){2,}'


def features(mask=False,quotes=False,char_range=(2,5),c_norm='l2',unicode_tokens=False):
    token_pattern=UNICODE_TOKEN if unicode_tokens else r'(?u)\b\w\w+\b'
    return FeatureUnion([
        ('channel',Pipeline([('input',ChannelInput()),('vectorizer',DictVectorizer())])),
        ('word',Pipeline([('input',RobustText(mask,quotes)),('vectorizer',TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=20000,sublinear_tf=True,token_pattern=token_pattern))])),
        ('char',Pipeline([('input',RobustText(mask,quotes)),('vectorizer',TfidfVectorizer(analyzer='char_wb',ngram_range=char_range,min_df=2,max_features=50000,sublinear_tf=True,norm=c_norm))])),
    ])
