from typing import List

from sqlmodel import Session, select

from core.models import Tag


def list_tags(session: Session, limit: int, offset: int) -> List[Tag]:
    stmt = select(Tag).order_by(Tag.name).offset(offset).limit(limit)
    return session.exec(stmt).all()


def create_tag(session: Session, name: str) -> Tag:
    existing = session.exec(select(Tag).where(Tag.name == name)).first()
    if existing:
        return existing
    tag = Tag(name=name)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def delete_tag(session: Session, name: str) -> bool:
    tag = session.exec(select(Tag).where(Tag.name == name)).first()
    if not tag:
        return False
    session.delete(tag)
    session.commit()
    return True
