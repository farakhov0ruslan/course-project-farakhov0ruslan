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


@pytest.fixture()
def log_capture():
    import io
    import json
    import logging

    from utils_library.logger import JsonFormatter

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    prev_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    def read_last_json():
        handler.flush()
        data = stream.getvalue().strip().splitlines()
        assert data, "no log lines captured"
        return json.loads(data[-1])

    try:
        yield read_last_json
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)


@pytest.fixture(scope="session")
def client(test_db_url):
    from app.main import app

    with TestClient(app) as c:
        yield c
