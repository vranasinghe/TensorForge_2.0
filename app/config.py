import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def artifact_dir():
    override = os.getenv('ARTIFACT_DIR')
    if override:
        return Path(override)
    # Render sets RENDER=true. Free instances are 512 MB and cannot load the vote artifact.
    if os.getenv('RENDER'):
        return ROOT / 'artifacts' / 'baseline'
    return ROOT / 'artifacts'


@dataclass
class Config:
    api_key: str | None = field(default_factory=lambda: os.getenv('API_KEY'))
    artifacts: Path = field(default_factory=artifact_dir)
    database: Path = field(default_factory=lambda: Path(os.getenv('JOB_DB', str(ROOT / 'runtime' / 'jobs.sqlite3'))))
