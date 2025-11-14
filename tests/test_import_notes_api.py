import csv
import io
import json
from http import HTTPStatus


# Позитив: валидный JSON
def test_import_notes_json_success(client):
    payload = [
        {"title": "Ok 1", "body": "Hello", "tags": ["py", "fastapi"]},
        {"title": "Ok 2", "body": "", "tags": []},
    ]
    f = io.BytesIO(json.dumps(payload).encode("utf-8"))
    r = client.post(
        "/import/notes",
        files={"file": ("notes.json", f, "application/json")},
    )
    assert r.status_code == HTTPStatus.ACCEPTED, r.text
    data = r.json()
    assert data["imported"] >= 1


# Позитив: валидный CSV
def test_import_notes_csv_success(client):
    f = io.StringIO()
    writer = csv.DictWriter(f, fieldnames=["title", "body", "tags"])
    writer.writeheader()
    writer.writerow({"title": "csv1", "body": "b", "tags": "a;b"})
    writer.writerow({"title": "csv2", "body": "", "tags": ""})
    f.seek(0)
    r = client.post(
        "/import/notes",
        files={"file": ("notes.csv", f.read().encode("utf-8"), "text/csv")},
    )
    assert r.status_code == HTTPStatus.ACCEPTED, r.text
    data = r.json()
    assert data["imported"] >= 1


# Негатив: плохая схема — ничего не импортировано
def test_import_notes_bad_schema(client):
    # некорректная форма JSON
    payload = [{"title": "", "body": 123, "tags": "not-a-list"}]
    f = io.BytesIO(json.dumps(payload).encode("utf-8"))
    r = client.post(
        "/import/notes",
        files={"file": ("bad.json", f, "application/json")},
    )
    assert r.status_code == HTTPStatus.BAD_REQUEST, r.text


#  Негатив: >MAX размер — 413 (симулируем через monkeypatch на валидатор)
def test_import_notes_too_large_413(client, monkeypatch):
    from utils_library import file_security

    monkeypatch.setattr(file_security, "MAX_FILE_SIZE", 1)

    payload = [
        {"title": "Ok 1", "body": "Hello", "tags": ["py", "fastapi"]},
        {"title": "Ok 2", "body": "", "tags": []},
    ]
    f = io.BytesIO(json.dumps(payload).encode("utf-8"))
    r = client.post(
        "/import/notes",
        files={"file": ("notes.json", f, "application/json")},
    )
    assert r.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
