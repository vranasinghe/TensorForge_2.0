import json
import math
from pathlib import Path
import joblib
from training.audit import digest
from app.contract import route_category
from app.schemas import validate


class Predictor:
    def __init__(self, artifact_dir):
        path = Path(artifact_dir)
        manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        if digest(path / 'model.joblib') != manifest['sha256']:
            raise ValueError('Model artifact digest mismatch')
        self.version = manifest['model_version']
        self.model = joblib.load(path / 'model.joblib')
        self.review_threshold = self.model.get('review_threshold')

    def predict_many(self, tickets):
        if not tickets:
            return []
        # Never pass extra client properties or identifiers to supervised components.
        inputs = [{k: t.get(k, '') for k in ('channel', 'subject', 'text')} for t in tickets]
        m = self.model
        probabilities = m['primary'].predict_proba(inputs)
        urgent = m['urgency'].predict_proba(inputs)[:, 1]
        presence = m['presence'].predict_proba(inputs)[:, 1]
        secondary = m['secondary'].predict(inputs)
        predictions = []
        for i, ticket in enumerate(tickets):
            best = int(probabilities[i].argmax())
            category = str(m['primary'].classes_[best])
            second = str(secondary[i]) if presence[i] >= m['presence_threshold'] else None
            if second == category or category == 'spam_irrelevant':
                second = None
            confidence = float(probabilities[i, best])
            if not math.isfinite(confidence):
                raise ValueError('Nonfinite model confidence')
            result = {'category': category, 'secondary_category': second, 'team': route_category(category),
                      'is_urgent': bool(urgent[i] >= m['urgency_threshold']) if category != 'spam_irrelevant' else False,
                      'confidence': round(confidence, 12), 'model_version': self.version}
            # Optional bonus field; artifacts trained before the review policy omit the key
            # entirely, and then the field stays absent rather than guessing a threshold.
            if self.review_threshold is not None:
                result['needs_human_review'] = bool(confidence < self.review_threshold)
            if 'ticket_id' in ticket:
                result['ticket_id'] = ticket['ticket_id']
            validate('PredictResponse', result)
            predictions.append(result)
        return predictions

    def predict_one(self, ticket):
        return self.predict_many([ticket])[0]
