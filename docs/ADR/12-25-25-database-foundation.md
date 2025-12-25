# Database Foundation - SQLAlchemy, Alembic, and Postgres

## Status

Accepted

## Context

As the system evolves beyond in-memory implementations, we need persistent storage for production use. Features like Car Catalog, Pricing, and Financing will require durable data storage with the following requirements:

**Functional Requirements:**
- Persist domain entities (Cars, Financing Plans, etc.)
- Support complex queries (filtering, pagination, aggregations)
- Handle concurrent access safely
- Maintain data integrity through transactions

**Architectural Requirements:**
- Keep infrastructure concerns isolated from domain code
- Follow clean architecture principles (no SQLAlchemy imports in domain layer)
- Enable testability (in-memory for tests, Postgres for production)
- Support schema evolution over time

**Operational Requirements:**
- Reproducible migrations across environments (dev, staging, prod)
- Version-controlled schema changes
- Safe rollback capabilities
- Configuration through environment variables

This decision establishes the foundational database infrastructure that all future features will build upon.

## Decision

We will use **PostgreSQL** as the primary database with **SQLAlchemy** as the ORM and **Alembic** for migrations.

### 1. PostgreSQL as System of Record

**PostgreSQL** is the standardized database for MVP and beyond.

**Rationale:**
- Production-grade ACID compliance and data integrity
- Excellent support for `NUMERIC` type (critical for our Decimal monetary values)
- Rich indexing capabilities (B-tree, GIN, GiST) for complex queries
- JSON/JSONB support for future flexibility
- Battle-tested in financial applications
- Strong Python ecosystem support

### 2. SQLAlchemy 2.0 as ORM

**SQLAlchemy 2.0** with modern patterns (`select()`, typed mappings).

**Rationale:**
- Industry-standard Python ORM with excellent PostgreSQL support
- Type-safe query construction
- Clean separation between models (infrastructure) and entities (domain)
- Automatic `NUMERIC` → `Decimal` conversion
- Connection pooling and performance optimization out-of-the-box
- Extensive documentation and community support

**Style decisions:**
- Use SQLAlchemy 2.0 style exclusively (avoid legacy 1.x patterns)
- Prefer `select()` statements over legacy query API
- Use typed attribute access for type safety

### 3. Alembic for Schema Migrations

**Alembic** handles all schema changes through migration scripts.

**Migration-first approach:**
- Schema changes are **always** done through Alembic migrations
- No ORM auto-create or manual SQL execution
- All migrations version-controlled in Git
- Reproducible across all environments

**Rationale:**
- Explicit, auditable schema changes
- Safe forward and backward migrations
- Team collaboration on schema evolution
- Production deployment safety (review migrations in PR)
- Historical record of all schema changes

### 4. Clean Architecture Boundaries

**Database code stays in infrastructure layer.**

**Directory structure:**
```
src/
  domain/              # Pure Python, zero DB dependencies
    entities/
    value_objects/
    ports/             # Repository interfaces

  application/         # UseCases, zero DB dependencies
    use_cases/

  infra/               # Infrastructure implementations
    db/
      engine.py        # SQLAlchemy engine/session setup
      models/          # SQLAlchemy models (NOT domain entities)
      repositories/    # Repository implementations
```

**Boundary rules:**
- Domain layer **never** imports SQLAlchemy, Alembic, or any DB library
- UseCases depend only on repository **ports** (interfaces)
- Infrastructure layer implements ports using SQLAlchemy

**Enforcement:**
- Import checks in tests/linting
- Code review verification
- Clear architectural documentation

### 5. Configuration Management

**Single source of truth:** `DATABASE_URL` environment variable.

```bash
# Format
DATABASE_URL=postgresql://user:password@host:port/database

# Example
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kavak_lite
```

**Configuration flow:**
1. Environment variables (production, staging)
2. `.env` file (local development)
3. No hardcoded credentials

**Managed by:**
- SQLAlchemy engine creation
- Alembic configuration (`alembic.ini` references env var)
- Test fixtures (override with in-memory or test DB)

## Alternatives Considered

### Django ORM

Use Django's ORM instead of SQLAlchemy.

**Rejected:**
- Would require adopting full Django framework (too heavyweight)
- Tighter coupling between ORM and web framework
- Less flexibility for clean architecture separation
- SQLAlchemy has better advanced query capabilities
- We're not using Django for HTTP layer

### Raw SQL with Query Builders

Use a lightweight query builder (e.g., `pypika`) or raw SQL with connection pooling.

**Rejected:**
- More manual work (writing SQL by hand)
- Lose automatic type conversions (NUMERIC → Decimal)
- More boilerplate for common CRUD operations
- Harder to maintain as schema evolves
- Less type safety
- **When reconsidered:** If performance becomes critical and ORM overhead is proven bottleneck

### NoSQL Database (MongoDB, DynamoDB)

Use a document database instead of relational.

**Rejected:**
- Financial data requires strict ACID guarantees
- Relational model fits domain well (Cars, Financing Plans have clear relationships)
- Harder to enforce data integrity constraints
- Complex queries (filtering, joins) are harder
- Exact decimal arithmetic more difficult
- **When reconsidered:** If we need flexible schemas for user-generated content or analytics

### TypeORM / Prisma (JS/TS ORMs)

Use a JavaScript/TypeScript ORM.

**Rejected:**
- Project is Python-based
- Cross-language complexity for no benefit
- Smaller Python ecosystem support

### SQLAlchemy Core Only (No ORM)

Use SQLAlchemy Core for queries but skip the ORM layer.

**Deferred:**
- Core provides more control and potentially better performance
- ORM is more productive for CRUD operations
- Can selectively use Core for complex queries if needed
- **Revisit if:** ORM overhead becomes measurable performance issue

## Consequences

### Positive

- **Production-ready:** Postgres provides ACID guarantees for financial data
- **Type safety:** SQLAlchemy 2.0 provides strong typing for queries
- **Decimal precision:** Automatic handling of NUMERIC → Decimal conversion
- **Clean architecture:** Infrastructure isolated from domain
- **Testability:** Can use in-memory repositories for unit tests, Postgres for integration tests
- **Schema evolution:** Alembic migrations provide safe, auditable schema changes
- **Developer productivity:** ORM handles boilerplate, connection pooling, etc.
- **Battle-tested:** PostgreSQL + SQLAlchemy used in countless production systems

### Negative

- **ORM overhead:** Slight performance cost vs raw SQL (acceptable for MVP)
- **Learning curve:** Team must understand SQLAlchemy 2.0 patterns
- **Migration discipline required:** Team must create migrations for all schema changes
- **Testing complexity:** Need both in-memory tests and DB integration tests
- **Initial setup cost:** More upfront work than "just use SQLite"

### Neutral

- Requires Docker/Postgres for local development (standard in modern projects)
- Migration files need code review (good practice anyway)
- Configuration via environment variables (industry standard)
- Clear separation between models (infra) and entities (domain) requires discipline

## Implementation Notes

### Directory Structure

```
src/infra/db/
  __init__.py
  engine.py              # SQLAlchemy engine/session creation
  base.py                # Declarative base
  models/
    __init__.py
    car.py               # SQLAlchemy Car model
  repositories/
    __init__.py
    car_repository.py    # PostgresCatalogRepository
```

```
alembic/
  versions/
    xxxx_initial_cars_table.py
  env.py
  script.py.mako
alembic.ini
```

### Engine & Session Setup

```python
# src/infra/db/engine.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/kavak_lite")

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL logging in dev
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
```

### Example Model

```python
# src/infra/db/models/car.py
from sqlalchemy import Column, String, Integer, NUMERIC
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CarModel(Base):
    __tablename__ = "cars"

    id = Column(String, primary_key=True)
    make = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    price_mxn = Column(NUMERIC(12, 2), nullable=False, index=True)
```

### Repository Implementation

```python
# src/infra/db/repositories/car_repository.py
from src.domain.ports.catalog_repository import CatalogRepository
from src.domain.car import Car
from src.infra.db.models.car import CarModel
from sqlalchemy.orm import Session

class PostgresCatalogRepository(CatalogRepository):
    def __init__(self, session: Session):
        self._session = session

    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        query = select(CarModel)

        # Apply filters using SQLAlchemy WHERE clauses
        if filters.make:
            query = query.where(CarModel.make.ilike(filters.make))

        # ... apply other filters

        # Apply paging
        query = query.offset(paging.offset).limit(paging.limit)

        # Execute and convert models to domain entities
        results = self._session.execute(query).scalars().all()
        return [self._to_entity(model) for model in results]

    def _to_entity(self, model: CarModel) -> Car:
        """Convert SQLAlchemy model to domain entity."""
        return Car(
            id=model.id,
            make=model.make,
            model=model.model,
            year=model.year,
            price_mxn=model.price_mxn  # Already Decimal from NUMERIC
        )
```

### Migration Example

```python
# alembic/versions/xxxx_initial_cars_table.py
def upgrade():
    op.create_table(
        'cars',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('make', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('price_mxn', sa.NUMERIC(12, 2), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_cars_make', 'cars', ['make'])
    op.create_index('ix_cars_model', 'cars', ['model'])
    op.create_index('ix_cars_year', 'cars', ['year'])
    op.create_index('ix_cars_price_mxn', 'cars', ['price_mxn'])

def downgrade():
    op.drop_table('cars')
```

### Testing Strategy

**Unit tests:** Use `InMemoryCatalogRepository` (no database)

```python
def test_search_catalog():
    repo = InMemoryCatalogRepository()
    use_case = SearchCatalog(repo)
    # Test business logic without DB
```

**Integration tests:** Use real Postgres (or test DB)

```python
def test_postgres_repository(db_session):
    repo = PostgresCatalogRepository(db_session)
    # Verify SQL queries work correctly
```

### Deployment Checklist

- ✅ `DATABASE_URL` configured in environment
- ✅ Run `alembic upgrade head` before deploying app
- ✅ Verify migrations in staging before production
- ✅ Monitor connection pool usage
- ✅ Set up database backups

## Acceptance Criteria

- ✅ `alembic upgrade head` runs cleanly with valid `DATABASE_URL`
- ✅ Initial migration creates `cars` table with proper indexes
- ✅ SQLAlchemy engine/session wiring exists under `src/infra/db/`
- ✅ Domain layer has **zero** dependency on SQLAlchemy/Alembic
- ✅ Repository implementations convert models ↔ entities cleanly
- ✅ CI remains green (lint, typecheck, tests)
- ✅ Documentation explains separation between models and entities

## References

- Related: `12-25-25-monetary-values.md` - NUMERIC column types implement Decimal requirement
- Related: `12-25-25-car-catalog-search.md` - PostgresCatalogRepository will implement this contract
- SQLAlchemy 2.0 Documentation: https://docs.sqlalchemy.org/en/20/
- Alembic Documentation: https://alembic.sqlalchemy.org/
- PostgreSQL NUMERIC type: https://www.postgresql.org/docs/current/datatype-numeric.html
- Clean Architecture (Robert C. Martin): Repository pattern, dependency inversion
