import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient


def _uuid4():
    return str(uuid.uuid4())


def test_404_returns_problem_details_with_corr_id(client):
    rid = _uuid4()
    r = client.get("/__no_such_route__", headers={"X-Request-ID": rid})
    assert r.status_code == HTTPStatus.NOT_FOUND

    body = r.json()
    assert body["status"] == 404
    assert "title" in body and isinstance(body["title"], str)
    assert "type" in body
    assert "instance" in body
    # проверяем, что библиотека приняла наш header (валидный UUIDv4)
    assert body.get("correlation_id") == rid


def test_422_validation_returns_problem_details_and_errors(client):
    rid = _uuid4()
    r = client.get("/tags?limit=5000", headers={"X-Request-ID": rid})
    assert r.status_code in (HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.BAD_REQUEST)

    body = r.json()
    assert body["status"] in (422, 400)
    assert body.get("title") in ("Unprocessable Entity", "Bad Request")
    assert "errors" in body and isinstance(body["errors"], list)
    assert body.get("correlation_id") == rid


def test_500_unhandled_exception_mapped_to_problem_details(client):
    # Для проверки 500 создаём отдельный клиент, чтобы НЕ поднимать исключение наружу
    app = client.app

    def boom():
        raise RuntimeError("kaboom")

    app.add_api_route("/boom", boom, methods=["GET"])

    # ключ: raise_server_exceptions=False
    with TestClient(app, raise_server_exceptions=False) as c:
        rid = _uuid4()
        r = c.get("/boom", headers={"X-Request-ID": rid})
        assert r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        body = r.json()
        assert body["status"] == 500
        assert body["title"] in ("Internal Server Error", "Server Error")
        assert "detail" in body and isinstance(body["detail"], str)
        assert "instance" in body
        assert body.get("correlation_id") == rid


def test_correlation_id_generated_when_header_missing(client):
    r = client.get("/__no_route__")
    assert r.status_code == HTTPStatus.NOT_FOUND
    body = r.json()
    # библиотека сгенерирует UUID, если заголовка нет
    assert isinstance(body.get("correlation_id"), str)
    assert body["correlation_id"] != ""
