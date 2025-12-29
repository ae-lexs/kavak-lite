"""
Unit tests for FastAPI dependency injection functions.

This test suite verifies the dependency wiring logic per the Database Session Per-Request ADR:
- get_db() yields a database session per request
- get_search_catalog_use_case() creates properly wired use case with repository
- No caching of sessions or stateful objects
- Each request gets fresh instances

Tests use mocks to verify wiring without requiring a real database.

See: docs/ADR/12-29-25-database-session-per-request.md
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


from kavak_lite.adapters.postgres_car_catalog_repository import (
    PostgresCarCatalogRepository,
)
from kavak_lite.entrypoints.http.dependencies import (
    get_db,
    get_search_catalog_use_case,
)
from kavak_lite.use_cases.search_car_catalog import SearchCarCatalog


# ==============================================================================
# get_db() - Database Session Provider
# ==============================================================================


def test_get_db_yields_session_from_get_session() -> None:
    """get_db() yields a session from the get_session context manager."""
    # Mock get_session to return a context manager
    mock_session = Mock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_session
    mock_context_manager.__exit__.return_value = None

    with patch("kavak_lite.entrypoints.http.dependencies.get_session") as mock_get_session:
        mock_get_session.return_value = mock_context_manager

        # Call get_db and consume the generator
        generator = get_db()
        session = next(generator)

        # Verify get_session was called
        mock_get_session.assert_called_once()

        # Verify the yielded value is the session
        assert session is mock_session

        # Complete the generator (simulates FastAPI cleanup)
        try:
            next(generator)
        except StopIteration:
            pass  # Expected

        # Verify context manager was entered and exited
        mock_context_manager.__enter__.assert_called_once()
        mock_context_manager.__exit__.assert_called_once()


def test_get_db_is_generator() -> None:
    """get_db() is a generator function (required for FastAPI dependency)."""
    from types import GeneratorType

    with patch("kavak_lite.entrypoints.http.dependencies.get_session"):
        result = get_db()
        assert isinstance(result, GeneratorType)


def test_get_db_properly_closes_session_on_exception() -> None:
    """get_db() ensures session is closed even if exception occurs."""
    mock_session = Mock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_session

    with patch("kavak_lite.entrypoints.http.dependencies.get_session") as mock_get_session:
        mock_get_session.return_value = mock_context_manager

        generator = get_db()
        next(generator)  # Get the session

        # Simulate exception during request processing
        try:
            generator.throw(Exception("Simulated error during request"))
        except Exception:
            pass  # Expected

        # Verify context manager __exit__ was called (cleanup happened)
        mock_context_manager.__exit__.assert_called_once()


def test_get_db_creates_new_session_each_call() -> None:
    """get_db() creates a new session for each call (not cached)."""
    mock_session_1 = Mock()
    mock_session_2 = Mock()

    mock_cm_1 = MagicMock()
    mock_cm_1.__enter__.return_value = mock_session_1
    mock_cm_1.__exit__.return_value = None

    mock_cm_2 = MagicMock()
    mock_cm_2.__enter__.return_value = mock_session_2
    mock_cm_2.__exit__.return_value = None

    with patch("kavak_lite.entrypoints.http.dependencies.get_session") as mock_get_session:
        # First call
        mock_get_session.return_value = mock_cm_1
        gen1 = get_db()
        session1 = next(gen1)

        # Second call
        mock_get_session.return_value = mock_cm_2
        gen2 = get_db()
        session2 = next(gen2)

        # Verify get_session called twice (not cached)
        assert mock_get_session.call_count == 2

        # Verify different sessions
        assert session1 is not session2


# ==============================================================================
# get_search_catalog_use_case() - Use Case Factory
# ==============================================================================


def test_get_search_catalog_use_case_creates_use_case_with_repository() -> None:
    """Factory creates SearchCarCatalog use case with PostgresCarCatalogRepository."""
    mock_session = Mock()

    # Call the factory
    use_case = get_search_catalog_use_case(db=mock_session)

    # Verify use case is correct type
    assert isinstance(use_case, SearchCarCatalog)

    # Verify use case has repository
    assert hasattr(use_case, "_car_catalog_repository")
    repository = use_case._car_catalog_repository

    # Verify repository is correct type
    assert isinstance(repository, PostgresCarCatalogRepository)

    # Verify repository has the session
    assert hasattr(repository, "_session")
    assert repository._session is mock_session


def test_get_search_catalog_use_case_creates_fresh_instance_each_call() -> None:
    """Factory creates new use case instance for each call (not cached)."""
    mock_session_1 = Mock()
    mock_session_2 = Mock()

    # First call
    use_case_1 = get_search_catalog_use_case(db=mock_session_1)

    # Second call
    use_case_2 = get_search_catalog_use_case(db=mock_session_2)

    # Verify different instances
    assert use_case_1 is not use_case_2

    # Verify different repositories
    assert use_case_1._car_catalog_repository is not use_case_2._car_catalog_repository

    # Verify each has correct session
    assert use_case_1._car_catalog_repository._session is mock_session_1
    assert use_case_2._car_catalog_repository._session is mock_session_2


def test_get_search_catalog_use_case_wires_dependencies_correctly() -> None:
    """Factory wires dependencies in correct order: Session → Repository → UseCase."""
    mock_session = Mock()

    use_case = get_search_catalog_use_case(db=mock_session)

    # Verify dependency chain: Session → Repository → UseCase
    # 1. UseCase exists
    assert isinstance(use_case, SearchCarCatalog)

    # 2. UseCase has Repository
    repository = use_case._car_catalog_repository
    assert isinstance(repository, PostgresCarCatalogRepository)

    # 3. Repository has Session
    assert repository._session is mock_session


def test_get_search_catalog_use_case_accepts_session_parameter() -> None:
    """Factory accepts db parameter (injected by FastAPI via Depends(get_db))."""
    mock_session = Mock()

    # Should accept session as parameter
    use_case = get_search_catalog_use_case(db=mock_session)

    # Verify it was used
    assert use_case._car_catalog_repository._session is mock_session


# ==============================================================================
# Integration - Dependency Chain
# ==============================================================================


def test_dependency_chain_get_db_to_use_case() -> None:
    """Verify complete dependency chain: get_db() → get_search_catalog_use_case()."""
    mock_session = Mock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_session
    mock_context_manager.__exit__.return_value = None

    with patch("kavak_lite.entrypoints.http.dependencies.get_session") as mock_get_session:
        mock_get_session.return_value = mock_context_manager

        # Simulate FastAPI dependency injection flow
        # 1. FastAPI calls get_db()
        db_generator = get_db()
        session = next(db_generator)

        # 2. FastAPI passes session to get_search_catalog_use_case()
        use_case = get_search_catalog_use_case(db=session)

        # Verify use case has the session from get_db
        assert use_case._car_catalog_repository._session is session
        assert use_case._car_catalog_repository._session is mock_session


# ==============================================================================
# Isolation and Per-Request Behavior
# ==============================================================================


def test_multiple_requests_get_isolated_dependencies() -> None:
    """Each request gets isolated session, repository, and use case (no sharing)."""
    # Simulate two concurrent requests
    mock_session_1 = Mock()
    mock_session_2 = Mock()

    # Request 1
    use_case_1 = get_search_catalog_use_case(db=mock_session_1)

    # Request 2
    use_case_2 = get_search_catalog_use_case(db=mock_session_2)

    # Verify complete isolation
    assert use_case_1 is not use_case_2  # Different use cases
    assert (
        use_case_1._car_catalog_repository is not use_case_2._car_catalog_repository
    )  # Different repos
    assert (
        use_case_1._car_catalog_repository._session
        is not use_case_2._car_catalog_repository._session
    )  # Different sessions

    # Verify each request has its own session
    assert use_case_1._car_catalog_repository._session is mock_session_1
    assert use_case_2._car_catalog_repository._session is mock_session_2


def test_dependencies_are_not_cached() -> None:
    """Dependencies are not cached with @lru_cache (per-request instances)."""

    # Verify get_db is not decorated with lru_cache
    assert not hasattr(get_db, "__wrapped__")  # lru_cache adds __wrapped__

    # Verify get_search_catalog_use_case is not decorated with lru_cache
    assert not hasattr(get_search_catalog_use_case, "__wrapped__")


# ==============================================================================
# Type Verification
# ==============================================================================


def test_get_db_return_type_annotation() -> None:
    """get_db() has correct return type annotation (Generator)."""
    from typing import get_type_hints

    hints = get_type_hints(get_db)
    assert "return" in hints

    # Check it's a Generator type
    return_type = str(hints["return"])
    assert "Generator" in return_type


def test_get_search_catalog_use_case_return_type_annotation() -> None:
    """get_search_catalog_use_case() has correct return type annotation."""
    from typing import get_type_hints

    hints = get_type_hints(get_search_catalog_use_case)
    assert "return" in hints
    assert hints["return"] == SearchCarCatalog
