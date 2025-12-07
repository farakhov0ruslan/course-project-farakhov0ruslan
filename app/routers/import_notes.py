import csv
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from core.schemas import NoteCreate
from infrastructure.db import session_scope
from infrastructure.repositories.notes import NotesRepository
from utils_library.file_security import parse_json_array, validate_and_prepare

router = APIRouter(prefix="/import", tags=["import"])


def get_repo():
    with session_scope() as s:
        yield NotesRepository(s)


@router.post("/notes", status_code=status.HTTP_202_ACCEPTED)
async def import_notes(
    file: UploadFile = File(...), repo: NotesRepository = Depends(get_repo)
) -> dict:
    mem, fmt = validate_and_prepare(file.file, file.content_type)

    items: List[NoteCreate] = []

    if fmt == "json":
        for obj in parse_json_array(mem):
            try:

                items.append(NoteCreate(**obj))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid item: {e}") from e

    elif fmt == "csv":
        # Простейший CSV: ожидаем колонки title, body, tags (tags через ;)
        reader = csv.DictReader((line.decode("utf-8") for line in mem))
        for i, row in enumerate(reader, start=1):
            if not row.get("title"):
                raise HTTPException(
                    status_code=400, detail=f"Row {i}: title is required"
                )
            tags_raw = row.get("tags") or ""
            obj = {
                "title": row["title"],
                "body": row.get("body", ""),
                "tags": [t.strip() for t in tags_raw.split(";") if t.strip()],
            }
            try:
                items.append(NoteCreate(**obj))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Row {i}: {e}") from e
    else:
        raise HTTPException(status_code=415, detail="Unsupported format")

    created = []
    for i in items:
        note = repo.create(i.title, i.body, i.tags)
        created.append(note)

    return {"imported": len(created)}
