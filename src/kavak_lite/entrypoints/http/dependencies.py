"""
Dependency injection for FastAPI routes.

Key principle: Database sessions should be per-request, not cached.
Only stateless singletons should use lru_cache.
"""

from __future__ import annotations

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from kavak_lite.adapters.postgres_car_catalog_repository import (
    PostgresCarCatalogRepository,
)
from kavak_lite.infra.db.session import get_session
from kavak_lite.use_cases.search_car_catalog import SearchCarCatalog


def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for a single request.

    FastAPI will:
    1. Call this function when a request starts
    2. Inject the session into the route
    3. Commit/rollback and close the session when the request ends

    The underlying get_session() is a context manager that handles:
    - Session creation
    - Auto-commit on success
    - Auto-rollback on exception
    - Session cleanup

    Yields:
        Session: SQLAlchemy database session (per-request)
    """
    with get_session() as session:
        yield session


def get_search_catalog_use_case(db: Session = Depends(get_db)) -> SearchCarCatalog:
    """
    Factory function that returns a configured SearchCarCatalog use case.

    This function is called per-request, ensuring each request gets:
    - Fresh repository instance
    - Fresh use case instance
    - Isolated database session

    Args:
        db: Database session (injected by FastAPI via Depends(get_db))

    Returns:
        SearchCarCatalog: Configured use case instance
    """
    repository = PostgresCarCatalogRepository(session=db)
    return SearchCarCatalog(car_catalog_repository=repository)
