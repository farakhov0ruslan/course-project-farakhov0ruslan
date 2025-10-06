from contextlib import contextmanager
from typing import Iterator, Optional

from sqlmodel import Session, SQLModel, create_engine

from infrastructure.config import settings

_engine = None


def get_engine(override_url: Optional[str] = None):
    global _engine
    url = override_url or settings.DATABASE_URL
    if _engine is not None:
        return _engine
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    _engine = create_engine(url, echo=False, connect_args=connect_args)
    return _engine


def init_db(engine=None):
    engine = engine or get_engine()
    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine=None) -> Iterator[Session]:
    engine = engine or get_engine()
    with Session(engine) as session:
        yield session
