from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.schemas import NoteCreate, NoteRead, NoteUpdate
from infrastructure.db import session_scope
from infrastructure.repositories.notes import NotesRepository

router = APIRouter(prefix="/notes", tags=["notes"])


def get_repo():
    with session_scope() as s:
        yield NotesRepository(s)


@router.post("/", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, repo: NotesRepository = Depends(get_repo)):
    note = repo.create(payload.title, payload.body, payload.tags)
    return NoteRead.model_validate(note)


@router.get("/", response_model=List[NoteRead])
def list_notes(
    tag: Optional[str] = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: NotesRepository = Depends(get_repo),
):
    notes = repo.list(tag=tag, limit=limit, offset=offset)
    return [NoteRead.model_validate(n) for n in notes]


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, repo: NotesRepository = Depends(get_repo)):
    note = repo.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead)
def patch_note(
    note_id: int, payload: NoteUpdate, repo: NotesRepository = Depends(get_repo)
):
    note = repo.update(
        note_id, title=payload.title, body=payload.body, tags=payload.tags
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteRead.model_validate(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, repo: NotesRepository = Depends(get_repo)):
    ok = repo.delete(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    return None
