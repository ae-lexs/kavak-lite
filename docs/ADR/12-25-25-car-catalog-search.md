# Car Catalog Search Design

## Status

Proposed

## Context

We need a car catalog search feature that enables users to discover vehicles matching their preferences. The system must:

- Handle filtering by multiple criteria (make, model, price range, year range)
- Support pagination for large result sets
- Work with multiple data sources (in-memory for tests, Postgres for production)
- Follow clean architecture principles with clear separation between domain and infrastructure
- Scale efficiently from dozens to millions of cars

This feature is foundational for the car sales flow - users must be able to find cars before proceeding to financing.

## Decision

### 1. Repository-Based Filtering

**Filtering logic lives in the Repository/Adapter layer, not the UseCase.**

The `CatalogRepository` contract defines filter semantics (what filtering means), while each adapter implements the filtering optimally for its technology.

**Rationale:**

**Performance & Scalability:**
- Leverage database query optimization (indexes, WHERE clauses, query planners)
- Filter millions of records at DB level, not in-memory
- Postgres can efficiently handle complex queries that would be expensive in application code
- Avoid loading entire dataset into memory just to filter it

**Contract vs Implementation:**
- `CatalogFilters` defines **semantics** (domain layer) - what filtering means
- Adapters define **implementation** (infrastructure layer) - how to execute it
- Same contract, different optimizations per technology

**Clean Separation of Concerns:**
- **UseCase responsibility:** Validate business rules (offset >= 0, limit >= 1)
- **Repository responsibility:** Execute data access (filtering, retrieval, pagination)
- Filtering is a **data access concern**, not business logic
- Business logic would be: "Users only see cars they're approved for" or "Apply dynamic pricing"
- Simple field filtering (make, model, price range) belongs in infrastructure

**Reference Implementation:**
- `InMemoryCatalogRepository` serves as canonical behavior for tests
- Defines the "truth" of filter semantics (case-insensitive, inclusive ranges, AND logic)
- Future adapters (Postgres, Elasticsearch) must honor the same semantics

**Future-proof:**
- Postgres adapter can use SQL WHERE clauses
- Elasticsearch adapter can use query DSL
- Each adapter optimizes for its strengths while honoring the contract

### 2. Contract Definition

#### Models

**Car** (or `CarDTO` if we prefer boundary-only):

```python
id: str
make: str
model: str
year: int
price_mxn: int
```

#### Filters (AND Semantics)

**CatalogFilters** (all fields optional):

| Field | Type | Behavior |
|-------|------|----------|
| `make` | `str` | Case-insensitive exact match |
| `model` | `str` | Case-insensitive exact match |
| `year_min` | `int` | Inclusive minimum year |
| `year_max` | `int` | Inclusive maximum year |
| `price_min_mxn` | `int` | Inclusive minimum price |
| `price_max_mxn` | `int` | Inclusive maximum price |

**Semantics:**
- All filters use **AND logic** (car must match all provided filters)
- Missing/None filter fields are ignored (no constraint applied)
- String matching is case-insensitive
- Range filters are inclusive on both ends

#### Paging

**Paging parameters:**

```python
limit: int | None  # None = no limit
offset: int = 0    # Default: 0
```

**Rules:**
- Paging applied **after** filtering
- `offset` must be >= 0
- `limit` must be `None` or >= 1
- Out-of-bounds offset returns empty results (not an error)

#### Ordering

- `InMemoryCatalogRepository` returns cars in **insertion order**
- This is the reference behavior; DB adapter may define explicit sort if needed
- Future: Consider adding explicit ordering to contract if needed

### 3. Architecture Design

#### Port (Domain Layer)

```python
class CatalogRepository(Protocol):
    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        """
        Search catalog with filters and paging.

        Returns cars matching ALL provided filters (AND semantics),
        paginated according to paging parameters.
        """
        ...
```

#### UseCase (Application Layer)

```python
class SearchCatalog:
    def execute(self, request: SearchCatalogRequest) -> SearchCatalogResponse:
        """Execute catalog search."""
        ...
```

**Responsibilities:**
- Validate paging parameters (`offset` >= 0, `limit` >= 1 or None)
- Delegate to repository
- Return response DTO
- **No filtering logic** - completely delegated to repository

#### InMemory Adapter (Infrastructure Layer)

`InMemoryCatalogRepository` stores `list[Car]` and implements:

- Filtering function `_matches(car, filters)` - applies all filter rules
- Paging slice after filtering - `results[offset:offset+limit]`
- Serves as reference implementation for tests

## Alternatives Considered

### UseCase-Level Filtering

Pull all records from repository, filter in application code within the UseCase.

**Rejected:**
- Doesn't scale beyond small datasets
- Defeats database optimization (indexes, query planning)
- Would load millions of records into memory unnecessarily
- Makes in-memory adapter behavior different from production (misleading tests)

### Specification Pattern

Create composable filter specifications that can be combined and evaluated.

**Deferred:**
- Over-engineering for current needs
- Adds complexity without clear benefit
- Current filter contract is simple and sufficient
- Revisit if filters become significantly more complex (e.g., OR logic, nested conditions)

### Raw SQL in UseCase

Accept SQL WHERE clauses directly in UseCase.

**Rejected:**
- Violates clean architecture (infrastructure leaks into domain)
- Couples UseCase to specific database
- Makes testing difficult
- Loses type safety

## Consequences

### Positive

- **Performance:** Leverage database capabilities for efficient filtering
- **Scalability:** Can handle millions of cars without memory issues
- **Clean Architecture:** Clear separation between domain contract and infrastructure implementation
- **Testability:** InMemory adapter makes tests fast and deterministic
- **Flexibility:** Easy to add new adapters (Elasticsearch, etc.) while honoring contract
- **Type Safety:** Strongly-typed filter contract prevents errors

### Negative

- **Semantic Consistency:** Must ensure all adapters honor filter semantics identically
  - Mitigation: InMemory adapter serves as reference, comprehensive contract tests
- **Sync Risk:** In-memory reference implementation must stay in sync with contract
  - Mitigation: Contract tests exercise all adapters against same test cases
- **Limited Query Complexity:** Simple AND-only filters may need evolution for complex queries
  - Mitigation: Acceptable for MVP, can extend contract later if needed

### Neutral

- Requires clear contract documentation (this ADR provides it)
- Each new adapter must implement full contract
- Testing strategy requires both unit tests (InMemory) and integration tests (Postgres)

## Implementation Notes

### Testing Strategy

- **Always** unit test with InMemory/Mock adapters (no real DB)
- InMemory adapter exercises full contract including edge cases
- Postgres adapter has integration tests verifying semantic equivalence
- Contract tests can be shared across adapters

### Future Extensions

Potential evolution paths (not implemented now):

- **OR Logic:** `filters: list[CatalogFilters]` for OR semantics
- **Sorting:** Add `OrderBy` parameter to contract
- **Full-Text Search:** Add `search_text` field for fuzzy matching
- **Facets:** Return aggregations (count by make, price histogram, etc.)

These should be added to the contract (port), not implemented ad-hoc in adapters.

## Acceptance Criteria

- ✅ `CatalogRepository` port exists with `search()` method
- ✅ `SearchCatalog` UseCase exists with request/response DTOs
- ✅ `InMemoryCatalogRepository` implements filtering + paging
- ✅ Unit tests cover UseCase validation/delegation + repository contract
- ✅ Filter semantics clearly documented and tested
- ✅ CI green (lint + typecheck + tests)

## References

- Related: `12-25-25-monetary-values.md` - Price fields follow Decimal rules (though stored as int for MXN cents)
- Clean Architecture: Repository pattern from Robert C. Martin's "Clean Architecture"
