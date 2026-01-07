# Cars Table Database Indexes for Query Optimization

## Status

Accepted

## Context

The car catalog search feature enables users to filter cars by make, model, price range, and year range. As the system scales beyond the initial 50-car seed dataset, query performance will become critical for user experience.

**Current State:**
- `cars` table has only a primary key index on `id` (UUID)
- No indexes on filterable columns (make, model, year, price)
- Repository queries use case-insensitive matching via `LOWER()` functions
- Pagination uses OFFSET/LIMIT with COUNT(*) for total results

**Query Patterns (from `postgres_car_catalog_repository.py`):**
```python
# Case-insensitive exact match (lines 104-109)
query.where(func.lower(CarRow.make) == func.lower(filters.make))
query.where(func.lower(CarRow.model) == func.lower(filters.model))

# Range queries (lines 112-121)
query.where(CarRow.year >= filters.year_min)
query.where(CarRow.year <= filters.year_max)
query.where(CarRow.price >= filters.price_min)
query.where(CarRow.price <= filters.price_max)
```

**Performance Requirements:**
- Target query: `/v1/cars?brand=Toyota&price_max=30000.00&limit=10`
- Must scale from 50 cars (MVP) to 10,000+ cars (production)
- Read-heavy workload (catalog browsing >> car updates)
- Zero-downtime deployments required

**Problem:**
Without indexes on filterable columns, PostgreSQL performs sequential scans (full table scans) for every search query. This is acceptable with 50 cars but will degrade to unacceptable latency (50-100ms+) as the dataset grows.

**Functional indexes required:**
The repository uses `LOWER(make)` and `LOWER(model)` for case-insensitive matching. PostgreSQL cannot use a standard index on `make` to optimize `LOWER(make)` queries - functional indexes on the expressions are required.

## Decision

We will add **5 database indexes** to the `cars` table via an Alembic migration, optimized for the specific query patterns in `PostgresCarCatalogRepository`.

### 1. Functional Index on LOWER(make)

```sql
CREATE INDEX CONCURRENTLY idx_cars_make_lower ON cars (LOWER(make));
```

**Purpose:** Optimize case-insensitive brand filtering
**Query pattern:** `WHERE LOWER(make) = LOWER('Toyota')`
**Cardinality:** Medium (~15 distinct makes in seed data, 50-100 in production)
**Selectivity:** High (brand is primary filter criterion)

### 2. Functional Index on LOWER(model)

```sql
CREATE INDEX CONCURRENTLY idx_cars_model_lower ON cars (LOWER(model));
```

**Purpose:** Optimize case-insensitive model filtering
**Query pattern:** `WHERE LOWER(model) = LOWER('Corolla')`
**Cardinality:** High (~30-40 distinct models in seed data, 200+ in production)
**Selectivity:** Very high (model is highly selective)

### 3. B-tree Index on year

```sql
CREATE INDEX CONCURRENTLY idx_cars_year ON cars (year);
```

**Purpose:** Optimize year range queries
**Query pattern:** `WHERE year >= 2020 AND year <= 2024`
**Cardinality:** Low (~10 distinct years: 2015-2024)
**Selectivity:** Low-Medium (year ranges typically filter 20-40% of cars)

**Why B-tree:** Excellent for range scans and inequality operators (>=, <=).

### 4. B-tree Index on price

```sql
CREATE INDEX CONCURRENTLY idx_cars_price ON cars (price);
```

**Purpose:** Optimize price range queries
**Query pattern:** `WHERE price <= 300000.00`
**Cardinality:** Very high (prices are continuous values)
**Selectivity:** High (price is a strong filter, especially `price_max`)

**Why B-tree:** Optimal for range queries and ordered data.

### 5. Composite Index on (LOWER(make), price)

```sql
CREATE INDEX CONCURRENTLY idx_cars_make_lower_price ON cars (LOWER(make), price);
```

**Purpose:** Optimize the common "brand + price" filter combination
**Query pattern:** `WHERE LOWER(make) = 'toyota' AND price <= 300000.00`
**Use cases:**
- "Show me Toyotas under $30,000" (exact use case from requirements)
- "Show me all Toyotas" (uses leftmost prefix rule)

**Column ordering rationale:**
- `LOWER(make)` first - equality condition (more selective in composite)
- `price` second - range condition
- PostgreSQL can use this index for make-only queries via leftmost prefix optimization

### Implementation Strategy

**CONCURRENTLY for zero-downtime:**
- All indexes created with `CREATE INDEX CONCURRENTLY`
- Prevents `ACCESS EXCLUSIVE` locks that would block queries
- Safe for production deployment without downtime
- Trade-off: Slower index creation (requires two table scans vs one)

**Alembic migration approach:**
- Separate migration file (not modifying original table creation)
- Explicit index naming convention: `idx_{table}_{columns}_{function}`
- Reversible: `downgrade()` drops indexes using `CONCURRENTLY`
- Links to existing migration: `down_revision = 'd049065b730f'`

## Alternatives Considered

### Use citext Extension for Case-Insensitive Columns

**Approach:** Change `make` and `model` columns to `citext` type for automatic case-insensitivity.

```sql
CREATE EXTENSION IF NOT EXISTS citext;
ALTER TABLE cars ALTER COLUMN make TYPE citext;
ALTER TABLE cars ALTER COLUMN model TYPE citext;
CREATE INDEX idx_cars_make ON cars (make);  -- Standard index works with citext
```

**Pros:**
- Eliminates need for `LOWER()` in queries
- Simpler query syntax
- Standard indexes work automatically

**Cons:**
- Requires schema migration (column type changes)
- More invasive change to existing table
- Less explicit (citext behavior not obvious in schema)
- Functional indexes achieve same performance without schema changes

**Decision:** **Rejected** - Functional indexes are less invasive and achieve identical performance. Changing column types is unnecessary complexity.

### GIN/GiST Indexes for Pattern Matching

**Approach:** Use GIN indexes with `pg_trgm` extension for fuzzy/partial matching.

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_cars_make_gin ON cars USING GIN (make gin_trgm_ops);
```

**Pros:**
- Supports `LIKE '%toyota%'` pattern matching
- Enables fuzzy search and autocomplete
- Useful for partial matches

**Cons:**
- Current queries use exact match (`=`), not `LIKE`
- GIN indexes are larger (2-3x size of B-tree)
- Slower for exact equality comparisons
- More complex query planning

**Decision:** **Deferred** - Not needed for current query patterns. Revisit if full-text search or autocomplete features are added.

### Covering Indexes with INCLUDE Clause

**Approach:** Add frequently-selected columns to index leaf nodes to avoid heap fetches.

```sql
CREATE INDEX idx_cars_make_lower_price_covering
ON cars (LOWER(make), price)
INCLUDE (id, model, year, trim, transmission, fuel_type, body_type, location);
```

**Pros:**
- Enables index-only scans (no heap access)
- Significantly faster queries (no random I/O for heap fetches)
- Beneficial for high-read workloads

**Cons:**
- Index size increases 2-3x (storage cost)
- Slower writes (must update larger indexes)
- Premature optimization for current 50-car dataset

**Decision:** **Deferred** - Monitor with `EXPLAIN ANALYZE` after deployment. Add covering indexes only if:
1. Profiling shows heap fetches are a bottleneck
2. Dataset grows to 10,000+ cars
3. Read:write ratio remains heavily read-biased (>10:1)

### Adding Indexes to Original Table Migration

**Approach:** Modify `d049065b730f_create_cars_table.py` to include indexes.

**Pros:**
- Single migration file
- Simpler migration history

**Cons:**
- Violates single-responsibility principle (one migration = one logical change)
- Original migration already deployed (can't modify history)
- Harder to rollback just indexes
- Separate migration is cleaner for code review

**Decision:** **Rejected** - Separate migration is more maintainable and follows best practices.

### Partial Indexes for Recent Cars

**Approach:** Index only recent cars (e.g., `WHERE year >= 2020`).

```sql
CREATE INDEX idx_cars_recent
ON cars (LOWER(make), price)
WHERE year >= 2020;
```

**Pros:**
- Smaller index (fewer rows)
- Faster queries on recent cars
- Lower maintenance cost

**Cons:**
- Only useful if >70% of queries filter by recent years
- Current filters don't show this pattern
- Adds query planning complexity

**Decision:** **Deferred** - Insufficient evidence that queries primarily target recent cars. Monitor query patterns first.

## Consequences

### Positive

**Query Performance:**
- **Projected 25-60x faster** filtered queries at 10,000+ cars
- Make filter: 50ms → 2ms (sequential scan → index scan)
- Price range: 40ms → 3ms (range scan optimization)
- Make + Price: 60ms → 1-2ms (composite index optimization)

**Scalability:**
- Database can efficiently handle millions of cars
- Leverages PostgreSQL query planner and optimizer
- Index scans scale logarithmically (O(log n)) vs linear (O(n))

**Production Readiness:**
- `CONCURRENTLY` enables zero-downtime deployments
- No table locks during index creation
- Safe for production databases under load

**Developer Productivity:**
- Repository queries work efficiently without code changes
- No need to redesign filtering architecture
- Transparent performance improvement

**Future-Proofing:**
- Indexes support current queries and reasonable extensions
- Can add sorting (ORDER BY) without major rework
- Foundation for advanced features (faceted search, aggregations)

### Negative

**Write Performance:**
- **10-20% slower** inserts/updates (must maintain 5 indexes + PK)
- Each INSERT updates 6 index structures
- Trade-off acceptable for read-heavy catalog workload

**Storage Overhead:**
- **~1 MB index storage** for 10,000 cars (~20% of table size)
- Functional indexes store computed values
- Composite index duplicates make + price data
- Total overhead: ~5-6 indexes × ~200KB each

**Maintenance Burden:**
- Indexes can become bloated over time (deleted rows)
- May need periodic `REINDEX CONCURRENTLY` on high-churn tables
- Must monitor `pg_stat_user_indexes` for usage/bloat

**Index Selection Complexity:**
- Query planner must choose between 5+ indexes
- Suboptimal index selection possible (rare with good statistics)
- May need `ANALYZE` runs to update statistics

**Migration Complexity:**
- `CONCURRENTLY` cannot run in transaction (Alembic handles this)
- If index creation fails midway, must retry manually
- Index builds can be slow on large tables (minutes for millions of rows)

### Neutral

**Requires Monitoring:**
- Must verify index usage with `EXPLAIN ANALYZE`
- Monitor `pg_stat_user_indexes` for index effectiveness
- Track query performance over time with `pg_stat_statements`

**Testing Strategy:**
- Integration tests needed to verify index usage
- Can't fully test performance benefits with 50-car dataset
- Must validate on staging with production-like data volume

**Configuration:**
- No application code changes required
- Database-only change (infrastructure layer)
- Repository queries automatically benefit from indexes

## Implementation Notes

### Migration File Structure

**File:** `alembic/versions/XXXX_add_cars_indexes.py`

```python
"""Add indexes for cars table query optimization"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '<generated>'
down_revision: Union[str, Sequence[str], None] = 'd049065b730f'

def upgrade() -> None:
    """Create indexes for cars table."""

    # Functional indexes for case-insensitive text search
    op.create_index(
        'idx_cars_make_lower',
        'cars',
        [sa.text('LOWER(make)')],
        unique=False,
        postgresql_concurrently=True,
    )

    op.create_index(
        'idx_cars_model_lower',
        'cars',
        [sa.text('LOWER(model)')],
        unique=False,
        postgresql_concurrently=True,
    )

    # B-tree indexes for range queries
    op.create_index(
        'idx_cars_year',
        'cars',
        ['year'],
        unique=False,
        postgresql_concurrently=True,
    )

    op.create_index(
        'idx_cars_price',
        'cars',
        ['price'],
        unique=False,
        postgresql_concurrently=True,
    )

    # Composite index for common filter combination
    op.create_index(
        'idx_cars_make_lower_price',
        'cars',
        [sa.text('LOWER(make)'), 'price'],
        unique=False,
        postgresql_concurrently=True,
    )

def downgrade() -> None:
    """Drop indexes in reverse order."""
    op.drop_index('idx_cars_make_lower_price', table_name='cars', postgresql_concurrently=True)
    op.drop_index('idx_cars_price', table_name='cars', postgresql_concurrently=True)
    op.drop_index('idx_cars_year', table_name='cars', postgresql_concurrently=True)
    op.drop_index('idx_cars_model_lower', table_name='cars', postgresql_concurrently=True)
    op.drop_index('idx_cars_make_lower', table_name='cars', postgresql_concurrently=True)
```

**Key implementation details:**

1. **`sa.text('LOWER(make)')`** - Required for functional indexes. SQLAlchemy's `create_index()` expects column names; expressions must be wrapped in `sa.text()`.

2. **`postgresql_concurrently=True`** - Critical for production safety:
   - Builds index without blocking reads/writes
   - Requires two table scans (slower) but zero downtime
   - Cannot run in transaction (Alembic handles this automatically)

3. **Drop order** - Downgrade drops composite index first, then individual indexes. Prevents dangling references.

### Deployment Process

**Local development:**
```bash
# Generate migration (or create manually)
make db-new

# Review SQL without executing
make db-sql

# Apply migration
make db-up

# Verify indexes
make db-shell
\d cars
```

**Production deployment:**
```bash
# On production server/CI
alembic upgrade head

# Verify indexes created
psql $DATABASE_URL -c "SELECT indexname FROM pg_indexes WHERE tablename = 'cars';"
```

### Verification Strategy

**Create verification script:** `scripts/verify_indexes.sql`

```sql
-- Verify indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'cars'
ORDER BY indexname;

-- Verify index usage with EXPLAIN
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM cars WHERE LOWER(make) = LOWER('Toyota');

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM cars WHERE price <= 300000.00;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM cars
WHERE LOWER(make) = LOWER('Toyota') AND price <= 300000.00;
```

**Success criteria:**
- See "Index Scan using idx_cars_*" or "Bitmap Index Scan" in plans
- Should NOT see "Seq Scan on cars" for filtered queries
- Execution time significantly reduced on 10,000+ row dataset

### Monitoring Queries

**Index usage statistics:**
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'cars'
ORDER BY idx_scan DESC;
```

**Index bloat detection:**
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename = 'cars'
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Query performance:**
```sql
-- Requires pg_stat_statements extension
SELECT
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%cars%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

## Acceptance Criteria

- ✅ ADR created and reviewed documenting decision rationale
- ✅ Alembic migration created with correct revision chain
- ✅ Migration SQL reviewed (`make db-sql`) shows correct DDL
- ✅ Migration applies cleanly (`make db-up`)
- ✅ All 6 indexes exist in `pg_indexes`:
  - `cars_pkey` (existing)
  - `idx_cars_make_lower`
  - `idx_cars_model_lower`
  - `idx_cars_year`
  - `idx_cars_price`
  - `idx_cars_make_lower_price`
- ✅ `EXPLAIN` shows index usage for make filter queries
- ✅ `EXPLAIN` shows index usage for price range queries
- ✅ `EXPLAIN` shows composite index usage for make+price queries
- ✅ Existing tests pass (`make test`) - no regressions
- ✅ Verification script created and executes successfully
- ✅ Production deployment tested on staging environment

## References

**Related ADRs:**
- `12-25-25-database-foundation.md` - Established PostgreSQL, SQLAlchemy, Alembic foundation
- `12-25-25-car-catalog-search.md` - Defined repository contract and query patterns that these indexes optimize

**Implementation files:**
- `alembic/versions/d049065b730f_create_cars_table.py` - Original cars table schema
- `src/kavak_lite/adapters/postgres_car_catalog_repository.py` - Query patterns (lines 101-123)
- `src/kavak_lite/infra/db/models/car.py` - CarRow ORM model

**PostgreSQL documentation:**
- Indexes: https://www.postgresql.org/docs/current/indexes.html
- Functional Indexes: https://www.postgresql.org/docs/current/indexes-expressional.html
- CREATE INDEX CONCURRENTLY: https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY
- B-tree Indexes: https://www.postgresql.org/docs/current/indexes-types.html

**Performance resources:**
- Use The Index, Luke: https://use-the-index-luke.com/
- PostgreSQL Index Advisor: https://www.postgresql.org/docs/current/pgstatstatements.html
