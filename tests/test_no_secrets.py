"""The organizers' key must never be committed, baked into an image or shipped in a release.

PSF section 4 and the OpenAPI Authorization section forbid hard-coding it. Keys are shaped
`tf2_` followed by a long hex-like token; the local `.env` is the only place one may live.
"""
import re
from pathlib import Path
import pytest
from app.schemas import ROOT

KEY_SHAPE = re.compile(rb'tf2_[A-Za-z0-9]{32,}')
SKIP_DIRS = {'.venv', '.git', 'node_modules', '__pycache__', '.pytest_cache', 'runtime', 'tmp', 'output'}
SKIP_SUFFIXES = {'.joblib', '.npz', '.png', '.webm', '.sqlite3', '.pdf', '.zip', '.exe', '.pyc'}


def tracked_candidates():
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.name.startswith('.env'):
            continue
        parts = path.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in parts) or path.suffix in SKIP_SUFFIXES:
            continue
        if path.stat().st_size > 5_000_000:
            continue
        yield path


def test_no_organizer_key_in_any_source_file():
    leaks = [str(p.relative_to(ROOT)) for p in tracked_candidates() if KEY_SHAPE.search(p.read_bytes())]
    assert not leaks, f'Organizer-style API key found in: {leaks}'


def test_env_files_are_excluded_from_git_docker_and_release():
    assert '.env' in (ROOT / '.gitignore').read_text(encoding='utf-8').split()
    assert '.env*' in (ROOT / '.dockerignore').read_text(encoding='utf-8').split()
    assert "startswith('.env')" in (ROOT / 'scripts' / 'package_release.py').read_text(encoding='utf-8')


def test_dockerfile_never_sets_an_api_key():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    assert not re.search(r'(?im)^\s*(ENV|ARG)\s+API_KEY', dockerfile)
    assert 'COPY .env' not in dockerfile


@pytest.mark.skipif(not (ROOT / '.env').exists(), reason='no local .env on this machine')
def test_local_env_holds_a_nonempty_key():
    line = next((l for l in (ROOT / '.env').read_text(encoding='utf-8').splitlines() if l.startswith('API_KEY=')), '')
    assert line.split('=', 1)[1].strip(), '.env exists but API_KEY is empty, so the service would answer 401 to everything'
