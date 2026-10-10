import copy
import pytest
from jsonschema.exceptions import ValidationError
from app.schemas import validate


@pytest.mark.parametrize('changes', [
    {'team':'Tech Support'}, {'secondary_category':'spam_irrelevant'},
    {'secondary_category':'payment_refund'}, {'is_urgent':True},
    {'confidence':1.01}, {'model_version':''},
])
def test_original_response_schema_rejects_semantic_violations(changes):
    example={'category':'spam_irrelevant','secondary_category':None,'team':'Auto-close / Spam Filter', 'is_urgent':False,'confidence':.5,'model_version':'test'}
    example.update(changes)
    with pytest.raises(ValidationError):
        validate('PredictResponse',example)


def test_required_nullable_secondary_key():
    with pytest.raises(ValidationError):
        validate('PredictResponse',{'category':'spam_irrelevant','team':'Auto-close / Spam Filter','is_urgent':False,'confidence':.5,'model_version':'test'})
