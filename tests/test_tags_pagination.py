from http import HTTPStatus


def _seed_tags(client, n=60):
    for i in range(n):
        client.post("/tags/", json={"name": f"t{i:03d}"})


def test_tags_default_limit_le_50(client):
    _seed_tags(client, n=55)
    r = client.get("/tags/")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert isinstance(data, list)
    # по NFR: default limit <= 50
    assert len(data) <= 50


def test_tags_pagination_windows(client):
    _seed_tags(client, n=7)
    r1 = client.get("/tags?limit=3&offset=0")
    r2 = client.get("/tags?limit=3&offset=3")
    r3 = client.get("/tags?limit=3&offset=6")
    assert r1.status_code == r2.status_code == r3.status_code == HTTPStatus.OK

    page1 = [t["name"] for t in r1.json()]
    page2 = [t["name"] for t in r2.json()]
    page3 = [t["name"] for t in r3.json()]

    assert len(page1) == 3
    assert len(page2) == 3
    assert 1 <= len(page3) <= 3
    assert set(page1).isdisjoint(page2)
    assert set(page1).isdisjoint(page3)
    assert set(page2).isdisjoint(page3)


def test_tags_limit_validation_over_200_returns_422(client):
    # FastAPI при нарушении ограничений Query(le=200) отдаст 422
    r = client.get("/tags?limit=5000")
    assert r.status_code in (HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.BAD_REQUEST)
    # Дополнительно можно проверить тело ошибки в формате RFC 7807, если у тебя включён envelope


def test_tags_offset_validation_negative_returns_422(client):
    r = client.get("/tags?limit=10&offset=-1")
    assert r.status_code in (HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.BAD_REQUEST)
