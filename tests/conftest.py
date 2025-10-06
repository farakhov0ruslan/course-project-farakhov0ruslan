# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("db")
    db_file = Path(db_dir) / "test.db"
    url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = url
    return url


@pytest.fixture(scope="session")
def client(test_db_url):
    from app.main import app

    with TestClient(app) as c:
        yield c
