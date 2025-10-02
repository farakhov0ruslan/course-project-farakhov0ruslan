from typing import Iterable, List, Optional

from sqlmodel import Session, select

from core.models import Note, Tag


def _get_or_create_tags(session: Session, tag_names: Iterable[str]) -> List[Tag]:
    result: List[Tag] = []
    for name in {t.strip().lower() for t in tag_names if t.strip()}:
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if not tag:
            tag = Tag(name=name)
            session.add(tag)
        result.append(tag)
    return result


def create_note(
    session: Session, title: str, body: str, tag_names: Iterable[str]
) -> Note:
    note = Note(title=title, body=body)
    note.tags = _get_or_create_tags(session, tag_names)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def get_note(session: Session, note_id: int) -> Optional[Note]:
    return session.get(Note, note_id)


def list_notes(
    session: Session, *, tag: Optional[str] = None, limit: int = 50, offset: int = 0
) -> List[Note]:
    stmt = select(Note)
    if tag:
        stmt = stmt.join(Note.tags).where(Tag.name == tag)
    stmt = stmt.order_by(Note.id.desc()).limit(limit).offset(offset)
    return list(session.exec(stmt).all())


def update_note(
    session: Session,
    note_id: int,
    *,
    title: Optional[str],
    body: Optional[str],
    tags: Optional[List[str]]
) -> Optional[Note]:
    note = session.get(Note, note_id)
    if not note:
        return None
    if title is not None:
        note.title = title
    if body is not None:
        note.body = body
    if tags is not None:
        note.tags = _get_or_create_tags(session, tags)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def delete_note(session: Session, note_id: int) -> bool:
    note = session.get(Note, note_id)
    if not note:
        return False
    session.delete(note)
    session.commit()
    return True
