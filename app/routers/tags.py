from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.notes import LOGGER
from core.schemas import TagCreate, TagRead
from infrastructure.db import session_scope
from infrastructure.external.stackexchange_tags import fetch_popular_tags
from infrastructure.repositories.tags import TagsRepository

router = APIRouter(prefix="/tags", tags=["tags"])


def get_repo():
    with session_scope() as s:
        yield TagsRepository(s)


@router.get("/", response_model=List[TagRead])
def list_tags(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: TagsRepository = Depends(get_repo),
):
    rows = repo.list(limit=limit, offset=offset)
    LOGGER.info("tags.listed", count=len(rows), limit=limit, offset=offset)
    return [TagRead.model_validate(t) for t in rows]


@router.post("/", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreate, repo: TagsRepository = Depends(get_repo)):
    tag = repo.create(payload.name.strip().lower())
    LOGGER.info("tag.created", name=tag.name)
    return TagRead.model_validate(tag)


@router.delete("/{name}", status_code=204)
def delete_tag(name: str, repo: TagsRepository = Depends(get_repo)):
    ok = repo.delete(name)
    if not ok:
        LOGGER.warning("tag.not_found", tag=name)
        raise HTTPException(status_code=404, detail="Tag not found")
    LOGGER.info("tag.deleted", name=name)
    return None


@router.post("/import/external", status_code=201)
async def import_external_tags(
    limit: int = Query(10, ge=1, le=100),
    repo: TagsRepository = Depends(get_repo),
):
    names = await fetch_popular_tags(limit=limit)
    created = 0
    for n in names:
        try:
            await repo.create(n)
            created += 1
        except Exception:
            pass
    return {"imported": created, "source": "stackexchange", "requested": limit}
