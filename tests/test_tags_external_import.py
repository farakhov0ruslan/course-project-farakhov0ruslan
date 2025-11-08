import asyncio
import types
from http import HTTPStatus

import pytest


def test_fetch_popular_tags_parses_names(monkeypatch):
    from infrastructure import http_client
    from infrastructure.external import stackexchange_tags

    async def fake_get_json(url, params=None, retries=3):
        assert "api.stackexchange.com" in url
        # ровно 3 элемента, проверим ограничение limit ниже
        return {"items": [{"name": "python"}, {"name": "go"}, {"name": "sql"}]}

    monkeypatch.setattr(http_client.safe_http, "get_json", fake_get_json)

    names = asyncio.run(stackexchange_tags.fetch_popular_tags(limit=2))
    assert names == ["python", "go"]


def test_fetch_popular_tags_blocks_disallowed_host(monkeypatch):
    from infrastructure.external import stackexchange_tags

    monkeypatch.setattr(
        stackexchange_tags, "SE_TAGS_URL", "https://evil.example.com/tags"
    )

    with pytest.raises(ValueError, match="Host not allowed"):
        asyncio.run(stackexchange_tags.fetch_popular_tags(limit=5))


def test_import_external_tags_success(client, monkeypatch):
    import app.routers.tags as tags_router

    async def fake_fetch(limit: int = 10):
        assert limit == 3
        return ["python", "go", "sql"]

    monkeypatch.setattr(tags_router, "fetch_popular_tags", fake_fetch)

    from infrastructure.repositories import tags as repo_mod

    created = []

    async def fake_create(self, name: str):
        created.append(name)
        return types.SimpleNamespace(id=len(created), name=name)

    monkeypatch.setattr(repo_mod.TagsRepository, "create", fake_create, raising=False)

    r = client.post("/tags/import/external?limit=3")
    assert r.status_code in (HTTPStatus.CREATED, HTTPStatus.OK), r.text
    data = r.json()

    assert data["imported"] == 3
    assert set(created) == {"python", "go", "sql"}


def test_import_external_tags_abuse_long_names(client, monkeypatch):
    from infrastructure.external import stackexchange_tags
    from infrastructure.repositories import tags as repo_mod

    async def fake_fetch(limit: int = 10):
        return ["A" * 5000, "B" * 1000]

    monkeypatch.setattr(stackexchange_tags, "fetch_popular_tags", fake_fetch)

    seen = []

    async def fake_create(self, name: str):
        seen.append(name)
        return types.SimpleNamespace(id=len(seen), name=name)

    monkeypatch.setattr(repo_mod.TagsRepository, "create", fake_create, raising=False)

    r = client.post("/tags/import/external?limit=2")
    # обработчик не должен падать на длинных строках
    assert r.status_code in (HTTPStatus.CREATED, HTTPStatus.OK), r.text
    assert len(seen) == 2
