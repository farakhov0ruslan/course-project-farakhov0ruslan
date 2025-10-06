import datetime as dt
from typing import List, Optional

from sqlalchemy import Column, DateTime, String, event
from sqlalchemy.orm import Mapper
from sqlmodel import Field, Relationship, SQLModel


class NoteTagLink(SQLModel, table=True):
    note_id: Optional[int] = Field(
        default=None, foreign_key="note.id", primary_key=True
    )
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class Note(SQLModel, table=True):
    __tablename__ = "note"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(sa_column=Column(String(200), nullable=False, index=True))
    body: str = Field(sa_column=Column(String(10000), nullable=False, default=""))
    created_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.utcnow(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.utcnow(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    tags: List["Tag"] = Relationship(back_populates="notes", link_model=NoteTagLink)


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        sa_column=Column(String(32), unique=True, index=True, nullable=False)
    )

    notes: List[Note] = Relationship(back_populates="tags", link_model=NoteTagLink)


def _set_updated_at(mapper: Mapper, connection, target):  # type: ignore[no-redef]
    target.updated_at = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)


event.listen(Note, "before_update", _set_updated_at)
