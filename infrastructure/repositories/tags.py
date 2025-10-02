from typing import List

from sqlmodel import Session

from core.models import Tag
from core.services import tags as svc


class TagsRepository:
    def __init__(self, session: Session):

        self.session = session

    def list(self) -> List[Tag]:
        return svc.list_tags(self.session)

    def create(self, name: str) -> Tag:
        return svc.create_tag(self.session, name)

    def delete(self, name: str) -> bool:
        return svc.delete_tag(self.session, name)
