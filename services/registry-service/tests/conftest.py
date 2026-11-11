import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import database
from main import app

SERVICE_DIR = Path(__file__).resolve().parent.parent
SEED_SCRIPT = SERVICE_DIR / "seed_registry.sh"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """בונה מסד חדש מ-seed לכל בדיקה, כך שהבדיקות לא משנות את registry.db האמיתי."""
    path = tmp_path / "registry.db"
    subprocess.run(["bash", str(SEED_SCRIPT), str(path)], check=True, cwd=SERVICE_DIR, capture_output=True)
    monkeypatch.setattr(database, "DB_PATH", path)
    return path


@pytest.fixture
def client(db_path):
    with TestClient(app) as test_client:
        yield test_client
