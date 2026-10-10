import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'API specs and schemas'
spec = yaml.safe_load((SOURCE / 'tensorforge-phase2-openapi-v2.yaml').read_text(encoding='utf-8'))
bundle = json.loads((SOURCE / 'tensorforge-schemas.json').read_text(encoding='utf-8'))
print('OpenAPI version:', spec['info']['version'])
for path, operations in spec['paths'].items():
    for method, op in operations.items():
        if method not in ('get', 'post', 'delete'):
            continue
        request = op.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
        print(method.upper(), path, 'request:', request, 'responses:', op['responses'])
print('Bundle keys:', list(bundle))
for name in ('PredictRequest', 'BatchRequest', 'BatchJobRequest', 'BatchJobStatus', 'BatchJobResults', 'HealthResponse', 'ErrorResponse'):
    print(name, json.dumps(bundle['$defs'][name], ensure_ascii=True))
