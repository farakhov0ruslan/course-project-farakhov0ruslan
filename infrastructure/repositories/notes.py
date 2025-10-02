from typing import Iterable, List, Optional

from sqlmodel import Session

from core.models import Note
from core.services import notes as svc


class NotesRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, title: str, body: str, tags: Iterable[str]) -> Note:
        return svc.create_note(self.session, title, body, tags)

    def get(self, note_id: int) -> Optional[Note]:
        return svc.get_note(self.session, note_id)

    def list(self, *, tag: Optional[str], limit: int, offset: int) -> List[Note]:
        return svc.list_notes(self.session, tag=tag, limit=limit, offset=offset)

    def update(
        self,
        note_id: int,
        *,
        title: Optional[str],
        body: Optional[str],
        tags: Optional[List[str]]
    ):
        return svc.update_note(self.session, note_id, title=title, body=body, tags=tags)

    def delete(self, note_id: int) -> bool:
        return svc.delete_note(self.session, note_id)
