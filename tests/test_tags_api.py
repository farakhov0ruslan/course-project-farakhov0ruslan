from http import HTTPStatus


def test_create_tag_201(client):
    r = client.post("/tags/", json={"name": "algorithms"})
    assert r.status_code == HTTPStatus.CREATED, r.text
    tag = r.json()
    assert tag["id"] > 0
    assert tag["name"] == "algorithms"


def test_list_tags_200(client):
    # создадим пару тегов
    client.post("/tags/", json={"name": "ts"})
    client.post("/tags/", json={"name": "py"})

    r = client.get("/tags/")
    assert r.status_code == HTTPStatus.OK
    names = sorted([t["name"] for t in r.json()])
    # порядок может быть по имени — нормализуем
    assert set(names) >= {"py", "ts"}


def test_delete_tag_204_then_404(client):
    r = client.post("/tags/", json={"name": "temp"})
    assert r.status_code == HTTPStatus.CREATED
    # удаляем по имени
    r = client.delete("/tags/temp")
    assert r.status_code == HTTPStatus.NO_CONTENT

    # повторное удаление — 404
    r = client.delete("/tags/temp")
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_create_tag_idempotent_same_id(client):
    r1 = client.post("/tags/", json={"name": "unique"})
    assert r1.status_code == HTTPStatus.CREATED
    t1 = r1.json()

    r2 = client.post("/tags/", json={"name": "unique"})
    # роутер отдаёт 201 и для существующего — проверим, что ID тот же
    assert r2.status_code == HTTPStatus.CREATED
    t2 = r2.json()
    assert t1["id"] == t2["id"]
    assert t2["name"] == "unique"
