from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kavak_lite.infra.db.config import database_url


ENGINE = create_engine(
    database_url(),
    pool_pre_ping=True,
    future=True,
)


SessionLocal = sessionmaker(
    bind=ENGINE,
    class_=Session,
    expire_on_commit=False,
)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
