from http import HTTPStatus


def _create_note(client, title="T", body="", tags=None):
    tags = tags or []
    r = client.post("/notes/", json={"title": title, "body": body, "tags": tags})
    assert r.status_code == HTTPStatus.CREATED, r.text
    return r.json()


def test_create_note_201_returns_note_with_tags(client):
    note = _create_note(client, title="My first", body="hello", tags=["py", "fastapi"])
    assert note["id"] > 0
    assert note["title"] == "My first"
    assert sorted([t["name"] for t in note["tags"]]) == ["fastapi", "py"]


def test_get_note_200(client):
    created = _create_note(client, title="Read me")
    note_id = created["id"]

    r = client.get(f"/notes/{note_id}")
    assert r.status_code == HTTPStatus.OK
    got = r.json()
    assert got["id"] == note_id
    assert got["title"] == "Read me"


def test_list_notes_filter_by_tag(client):
    _create_note(client, title="A", tags=["x"])
    _create_note(client, title="B", tags=["y"])
    _create_note(client, title="C", tags=["x", "y"])

    r = client.get("/notes?tag=x")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    titles = sorted([n["title"] for n in data])
    assert titles == ["A", "C"]


def test_list_notes_pagination(client):
    for i in range(5):
        _create_note(client, title=f"n{i}")

    r1 = client.get("/notes?limit=2&offset=0")
    r2 = client.get("/notes?limit=2&offset=2")
    r3 = client.get("/notes?limit=2&offset=4")
    assert r1.status_code == r2.status_code == r3.status_code == HTTPStatus.OK
    assert len(r1.json()) == 2
    assert len(r2.json()) == 2
    assert len(r3.json()) >= 1  # последние остатки


def test_patch_note_update_title_and_tags(client):
    created = _create_note(client, title="old", tags=["a"])
    note_id = created["id"]

    r = client.patch(f"/notes/{note_id}", json={"title": "new", "tags": ["b", "c"]})
    assert r.status_code == HTTPStatus.OK
    updated = r.json()
    assert updated["title"] == "new"
    assert sorted([t["name"] for t in updated["tags"]]) == ["b", "c"]


def test_delete_note_then_404_on_get(client):
    created = _create_note(client, title="to-delete")
    note_id = created["id"]

    r = client.delete(f"/notes/{note_id}")
    assert r.status_code == HTTPStatus.NO_CONTENT

    r = client.get(f"/notes/{note_id}")
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_post_notes_missing_title_422(client):
    r = client.post("/notes/", json={"body": "no title here", "tags": []})
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_note_404_not_found(client):
    r = client.get("/notes/999999")
    assert r.status_code == HTTPStatus.NOT_FOUND
