"""Validate using the unchanged original Draft 2020-12 schema bundle."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas' / 'tensorforge-schemas.json'
if not SCHEMA_PATH.exists():
    SCHEMA_PATH = ROOT / 'API specs and schemas' / 'tensorforge-schemas.json'
BUNDLE = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
Draft202012Validator.check_schema(BUNDLE)
VALIDATORS = {name: Draft202012Validator({'$ref': f'#/$defs/{name}', '$defs': BUNDLE['$defs']}, format_checker=FormatChecker()) for name in BUNDLE['$defs']}


def validate(name, value):
    VALIDATORS[name].validate(value)


def problems(name, value):
    issues = []
    for error in VALIDATORS[name].iter_errors(value):
        path = list(error.absolute_path)
        detail = {'field': '.'.join(map(str, path)) or 'body', 'issue': error.message}
        if len(path) > 1 and path[0] == 'tickets' and isinstance(path[1], int):
            detail['index'] = path[1]
        issues.append(detail)
    if name in ('BatchRequest', 'BatchJobRequest') and isinstance(value, dict) and isinstance(value.get('tickets'), list):
        seen = set()
        for index, item in enumerate(value['tickets']):
            tid = item.get('ticket_id') if isinstance(item, dict) else None
            if not isinstance(tid, str):
                continue
            if tid in seen:
                issues.append({'index': index, 'field': 'ticket_id', 'issue': 'must be unique within the batch'})
            seen.add(tid)
    return issues
