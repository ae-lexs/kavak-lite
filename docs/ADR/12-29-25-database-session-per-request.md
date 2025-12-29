# ADR: Database Session Per-Request Pattern

**Date:** 2025-12-29
**Status:** Accepted
**Context:** Managing database sessions in FastAPI with proper isolation and resource management

---

## Context

In a web application, database sessions must be carefully managed to ensure:
- **Transaction isolation** - Each request has its own transaction
- **Thread safety** - No shared state between concurrent requests
- **Resource cleanup** - Connections returned to pool after use
- **ACID guarantees** - Database operations work correctly

**The critical question:** How do we provide database sessions to our repositories and use cases?

---

## Decision

### Pattern: Database Session Per-Request

**We will create a new database session for each HTTP request** using FastAPI's dependency injection system.

```python
def get_db() -> Generator[Session, None, None]:
    """Provides a database session for a single request."""
    with get_session() as session:
        yield session
```

Each request gets:
- ✅ Fresh database session
- ✅ Isolated transaction
- ✅ Automatic commit on success
- ✅ Automatic rollback on error
- ✅ Guaranteed session cleanup

---

## The Problem with Caching Sessions

### ❌ What NOT to Do

```python
@lru_cache()  # ❌ DANGEROUS
def get_catalog_repository() -> CarCatalogRepository:
    return PostgresCarCatalogRepository(session=get_session())
    # Creates ONE session shared by ALL requests forever
```

### Why This Breaks

**1. Transaction Interference**

```
Request A                    Request B
   │                            │
   ├─ Uses shared session       ├─ Uses SAME shared session
   │                            │
   ├─ Begins transaction        │
   │                            ├─ Reads data (sees A's changes!)
   ├─ Updates car price         │
   │                            ├─ Updates SAME car
   ├─ Commits                   │
   │    └─ Commits B's changes too! ❌
   │                            │
   │                            └─ Expects to commit separately ❌
```

**Result:** Request B's transaction committed prematurely by Request A.

**2. Race Conditions**

```
Thread 1: session.query(Car).filter(...)
Thread 2: session.commit()  ← Commits Thread 1's uncommitted work!
Thread 1: session.rollback()  ← Too late, already committed!
```

**3. Connection Pool Exhaustion**

```
Connection Pool (size: 10)
   │
   ├─ Connection 1 → Cached session (NEVER RETURNED) ❌
   │
   └─ Connections 2-10 → Used by other requests
        │
        └─ New requests wait forever for Connection 1
```

**4. Stale Data**

```
Time T1: Cached session reads Car(id=1, price=20000)
Time T2: Another process updates Car(id=1, price=25000)
Time T3: Cached session STILL sees price=20000 ❌
```

Session cache prevents seeing updates from other transactions.

**5. Memory Leaks**

Cached session → Never closed → Connection never returned → Pool exhausted

---

## The Correct Pattern: Per-Request Sessions

### Implementation

```python
# src/kavak_lite/entrypoints/http/dependencies.py

from typing import Generator
from sqlalchemy.orm import Session
from kavak_lite.infra.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for a single request.

    FastAPI will:
    1. Call this function when a request starts
    2. Inject the session into route dependencies
    3. Automatically close session when request ends

    Yields:
        Session: SQLAlchemy database session (per-request)
    """
    with get_session() as session:
        yield session
```

### How It Works

**Request Lifecycle:**

```
1. HTTP Request arrives
   │
2. FastAPI calls get_db()
   │
   ├─ get_session().__enter__()
   │   └─ Creates new Session from connection pool
   │
3. Session yielded to route dependencies
   │
4. Route executes (query, insert, update, etc.)
   │
5. Route returns response
   │
6. FastAPI cleanup (even if exception)
   │
   ├─ get_session().__exit__()
   │   ├─ session.commit() if successful
   │   ├─ session.rollback() if exception
   │   └─ session.close()
   │
7. Connection returned to pool
```

**Isolation Between Requests:**

```
Request A                    Request B
   │                            │
   ├─ get_db()                  ├─ get_db()
   │   └─ Session A             │   └─ Session B
   │                            │
   ├─ Begin transaction A       ├─ Begin transaction B
   │                            │
   ├─ Query/Update              ├─ Query/Update
   │   (isolated)               │   (isolated)
   │                            │
   ├─ Commit transaction A      │
   │                            ├─ Commit transaction B
   │                            │
   └─ Close Session A           └─ Close Session B
```

**No interference.** ✅

---

## Pros and Cons

### ✅ Pros

**1. Transaction Isolation**
- Each request has its own transaction
- ACID guarantees maintained
- No interference between concurrent requests

**2. Thread Safety**
- No shared session state
- Safe for concurrent requests
- Works correctly with async/await

**3. Proper Resource Management**
- Sessions automatically closed
- Connections returned to pool
- No memory leaks

**4. Error Handling**
- Automatic rollback on exceptions
- Transaction state never corrupted
- Clean failure recovery

**5. Testability**
- Easy to override `get_db()` in tests
- Can use test database with isolated transactions
- Predictable behavior

**6. Debuggability**
- Each request's database operations are isolated
- Easier to trace request-specific queries
- No hidden shared state

### ⚠️ Cons

**1. Per-Request Overhead**
- Creating session object per request: ~0.5ms
- Checkout/return connection from pool: ~0.1ms
- **Total overhead: ~0.6ms per request**

**Mitigation:** SQLAlchemy connection pooling eliminates TCP connection overhead. We're reusing connections, just not sessions.

**2. No Cross-Request Caching**
- Can't cache session-level query results
- Each request queries database independently

**Mitigation:** Use application-level caching (Redis) for expensive queries that need cross-request caching.

**3. Connection Pool Configuration Required**
- Need to size pool correctly for concurrent requests
- Too small → requests wait for connections
- Too large → database resource exhaustion

**Mitigation:** Monitor connection usage and tune pool size accordingly. Start with `pool_size=10` and adjust based on load.

---

## Performance Considerations

### Why Per-Request Is Fast Enough

**What's cheap:**
- ✅ Session object creation: ~0.5ms
- ✅ Checkout connection from pool: ~0.1ms
- ✅ Return connection to pool: ~0.05ms

**What's expensive (avoided by pooling):**
- ❌ Creating new TCP connection: ~50-100ms
- ❌ Database authentication: ~10-20ms

**SQLAlchemy connection pooling gives us the best of both worlds:**
- Fresh session per request (correctness)
- Reused connections (performance)

### Connection Pool Configuration

```python
# src/kavak_lite/infra/db/session.py

engine = create_engine(
    database_url,
    pool_size=10,           # Keep 10 connections open
    max_overflow=20,        # Allow 20 additional connections if needed
    pool_pre_ping=True,     # Verify connection health before use
    pool_recycle=3600,      # Recycle connections every hour
)
```

**How it works:**
1. Pool maintains 10 open connections to database
2. `get_session()` checks out a connection
3. Session uses the connection
4. Session closes, connection returned to pool
5. Next request reuses the same connection

**Cost:** Connection checkout/return ≈ 0.1ms (not 50-100ms to create new connection)

---

## Usage in Routes

### Simple Route

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

@router.get("/v1/cars")
def search_cars(
    query: CarSearchQueryDTO = Depends(),
    db: Session = Depends(get_db),  # ← Fresh session injected
):
    repository = PostgresCarCatalogRepository(session=db)
    use_case = SearchCarCatalog(repository=repository)

    request = CatalogSearchMapper.to_domain_request(query)
    result = use_case.execute(request)

    return CatalogSearchMapper.to_response(result, query.offset, query.limit)
```

### Better: Use Case Factory

```python
# dependencies.py
def get_search_catalog_use_case(db: Session) -> SearchCarCatalog:
    """Factory for SearchCarCatalog use case."""
    repository = PostgresCarCatalogRepository(session=db)
    return SearchCarCatalog(car_catalog_repository=repository)

# routes/cars.py
@router.get("/v1/cars")
def search_cars(
    query: CarSearchQueryDTO = Depends(),
    use_case: SearchCarCatalog = Depends(get_search_catalog_use_case),
    # FastAPI automatically:
    # 1. Calls get_db() → yields Session
    # 2. Calls get_search_catalog_use_case(session) → returns UseCase
    # 3. Passes UseCase to this function
):
    request = CatalogSearchMapper.to_domain_request(query)
    result = use_case.execute(request)
    return CatalogSearchMapper.to_response(result, query.offset, query.limit)
```

**Benefits:**
- Routes stay thin (orchestration only)
- Dependency wiring centralized in `dependencies.py`
- Easy to test (override `get_search_catalog_use_case`)

---

## Testing Strategy

### Unit Tests (Mock Session)

```python
from unittest.mock import Mock

def test_search_cars_route():
    # Arrange
    mock_use_case = Mock(spec=SearchCarCatalog)
    mock_use_case.execute.return_value = SearchCarCatalogResponse(
        cars=[], total_count=0
    )

    # Override dependency
    app.dependency_overrides[get_search_catalog_use_case] = lambda: mock_use_case

    # Act
    client = TestClient(app)
    response = client.get("/v1/cars?make=Toyota")

    # Assert
    assert response.status_code == 200
    mock_use_case.execute.assert_called_once()
```

### Integration Tests (Real DB, Isolated Transactions)

```python
@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """Test database session with transaction rollback."""
    with get_session() as session:
        # Start transaction
        transaction = session.begin_nested()

        yield session

        # Rollback transaction (isolate tests)
        transaction.rollback()

def test_search_cars_integration(test_db: Session):
    # Override get_db to use test session
    app.dependency_overrides[get_db] = lambda: test_db

    # Seed test data
    test_db.add(Car(id="1", make="Toyota", model="Camry", year=2020, price=Decimal("25000")))
    test_db.commit()

    # Test
    client = TestClient(app)
    response = client.get("/v1/cars?make=Toyota")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["cars"]) == 1
    assert data["cars"][0]["brand"] == "Toyota"
```

---

## Dependency Injection Best Practices

### When to Use Per-Request Dependencies

**✅ Always per-request:**
- Database sessions
- Repositories (hold session reference)
- Use cases (hold repository reference)
- Request context (current user, auth token)
- Request-scoped caches

**Pattern:**
```python
def get_resource(db: Session = Depends(get_db)) -> Resource:
    return Resource(session=db)
```

### When to Use Cached Dependencies

**✅ Safe to cache with `@lru_cache()`:**
- Application settings (read-only config)
- Connection pools (thread-safe, designed for sharing)
- Stateless service clients (if thread-safe)

**Pattern:**
```python
from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    """Load settings once, reuse forever."""
    return Settings.from_env()
```

### Decision Checklist

When adding a new dependency, ask:

1. **Does it have mutable state?** → Per-request
2. **Does it manage connections/transactions?** → Per-request
3. **Is it different per request/user?** → Per-request
4. **Is it read-only configuration?** → Can cache
5. **Is it thread-safe and stateless?** → Can cache

**Golden rule:** When in doubt, use per-request. Correctness > performance.

---

## Alternatives Considered

### 1. Thread-Local Sessions

**Approach:** Use thread-local storage to manage sessions

```python
from threading import local
thread_local = local()

def get_session():
    if not hasattr(thread_local, 'session'):
        thread_local.session = Session()
    return thread_local.session
```

**Rejected because:**
- ❌ Doesn't work with async/await (request can switch threads)
- ❌ Hidden state (not explicit in function signatures)
- ❌ Hard to test
- ❌ No automatic cleanup

### 2. Manual Session Management

**Approach:** Pass sessions explicitly, no dependency injection

```python
@router.get("/v1/cars")
def search_cars(query: CarSearchQueryDTO):
    with get_session() as db:
        repository = PostgresCarCatalogRepository(session=db)
        # ... rest of logic
```

**Rejected because:**
- ❌ Duplicated session management in every route
- ❌ Hard to test (can't override dependencies)
- ❌ Violates DRY principle
- ❌ Routes know about infrastructure details

### 3. Cached Sessions with `@lru_cache()`

**Approach:** Cache session for performance

```python
@lru_cache()
def get_db() -> Session:
    return get_session()
```

**Rejected because:**
- ❌ All issues described in "The Problem with Caching Sessions"
- ❌ Transaction interference
- ❌ Race conditions
- ❌ Connection pool exhaustion
- ❌ Minimal performance gain (~0.6ms) not worth correctness risk

---

## Consequences

### Impact on System Design

**✅ Positive:**
- Clean Architecture maintained (dependencies flow inward)
- Easy to test each layer independently
- Follows FastAPI best practices
- Scales well to multiple use cases and repositories

**⚠️ Considerations:**
- Need to monitor connection pool usage
- May need to tune pool size based on load
- Developers must understand not to cache sessions

### Monitoring Recommendations

Track these metrics:
- **Connection pool size** - Current active connections
- **Connection wait time** - Time requests wait for connections
- **Session duration** - How long sessions are open
- **Connections per second** - Rate of checkout/return

**Alert on:**
- Connection pool exhaustion (all connections in use)
- Long-running sessions (> 5 seconds)
- High connection wait times (> 100ms)

---

## References

- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- Previous ADR: [Database Foundation](./12-25-25-database-foundation.md)
- Previous ADR: [REST Endpoint Design Pattern](./12-26-25-rest-endpoint-design-pattern.md)
