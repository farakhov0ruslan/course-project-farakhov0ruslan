from typing import List

from fastapi import APIRouter, Depends, HTTPException

from core.schemas import TagCreate, TagRead
from infrastructure.db import session_scope
from infrastructure.repositories.tags import TagsRepository

router = APIRouter(prefix="/tags", tags=["tags"])


def get_repo():
    with session_scope() as s:
        yield TagsRepository(s)


@router.get("/", response_model=List[TagRead])
def list_tags(repo: TagsRepository = Depends(get_repo)):
    return [TagRead.model_validate(t) for t in repo.list()]


@router.post("/", response_model=TagRead, status_code=201)
def create_tag(payload: TagCreate, repo: TagsRepository = Depends(get_repo)):
    tag = repo.create(payload.name.strip().lower())
    return TagRead.model_validate(tag)


@router.delete("/{name}", status_code=204)
def delete_tag(name: str, repo: TagsRepository = Depends(get_repo)):
    ok = repo.delete(name)
    if not ok:
        raise HTTPException(status_code=404, detail="Tag not found")
    return None
