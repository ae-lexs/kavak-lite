from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from kavak_lite.infra.db.config import database_url

# Lazy initialization - only create engine/session when needed
_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url(),
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_local() -> sessionmaker[Session]:
    """Get or create the session factory (lazy initialization)."""
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
        )
    return _session_local


@contextmanager
def get_session() -> Iterator[Session]:
    """Get a database session with automatic commit/rollback."""
    session = get_session_local()()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
