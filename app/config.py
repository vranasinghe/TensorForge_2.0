import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Config:
    api_key: str | None = field(default_factory=lambda: os.getenv('API_KEY'))
    artifacts: Path = field(default_factory=lambda: Path(os.getenv('ARTIFACT_DIR', str(ROOT / 'artifacts'))))
    database: Path = field(default_factory=lambda: Path(os.getenv('JOB_DB', str(ROOT / 'runtime' / 'jobs.sqlite3'))))
