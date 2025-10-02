from typing import List, Optional

from sqlmodel import SQLModel


class TagRead(SQLModel):
    id: int
    name: str


class TagCreate(SQLModel):
    name: str


class NoteBase(SQLModel):
    title: str
    body: str = ""


class NoteCreate(NoteBase):
    tags: List[str] = []  # tag names


class NoteUpdate(SQLModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteRead(NoteBase):
    id: int
    tags: List[TagRead] = []
