# ADR: REST Endpoint Design Pattern

**Date:** 2025-12-26
**Status:** Accepted
**Context:** Designing the REST layer for GET /v1/cars and establishing patterns for future endpoints

---

## Context

### Current State

We already have:

- **Domain contract:** `CatalogRepository.search(filters, paging)` with filtering responsibility in the repository
- **Use case:** `SearchCatalog.execute(request)` that validates input and delegates to the repository (no filtering in the use case)
- **Postgres adapter:** Completed and compliant with the repository contract
- **TDD workflow:** Unit tests with InMemory/Mock adapters; integration tests only when needed

This ADR defines how we wire the REST API to the existing use case, following Clean Architecture boundaries and ensuring no `float` leaks into domain/application layers.

---

## Goals

1. **Provide a REST endpoint:** `GET /v1/cars` with query params for filters + paging
2. **Keep REST layer thin and focused:**
   - Translates HTTP query params → domain request
   - Calls use case
   - Maps domain entities → response DTO
   - Returns HTTP response
3. **Use the Mapper pattern** (class-based assemblers) so the controller stays literally: **parse → execute → map → return**
4. **Enforce the Decimal boundary:** Domain/application/repository only see `Decimal`, never `float`

---

## Decision

### Design Pattern: Mapper Pattern

We will use **class-based mappers** (an evolution of the assembler pattern) to translate between REST DTOs and domain models.

**Why Mappers over simple functions:**
- ✅ Groups related conversions together (easier to discover)
- ✅ Controller stays simple and readable
- ✅ Easy to test all mappings in one test file
- ✅ Can share helper methods if needed
- ✅ Scales well as we add more endpoints

**Why Mappers over DTO methods:**
- ✅ Respects Clean Architecture dependency rule (outer layer shouldn't make inner layer aware of it)
- ✅ Domain entities stay pure, unaware of REST concerns
- ✅ Easier to test mappings independently

---

## Architecture

### Folder Structure

```
src/
  kavak_lite/
    entrypoints/
      http/
        app.py                              # FastAPI app + metadata
        dependencies.py                     # DI factory functions
        routes/
          __init__.py
          cars.py                           # GET /v1/cars route
        dtos/
          __init__.py
          car.py                            # CarResponseDTO
          catalog_search.py                 # CarsSearchQueryDTO, CarsListResponseDTO
        mappers/
          __init__.py
          catalog_search_mapper.py          # CatalogSearchMapper class
```

---

## Components

### 1. DTOs (REST Boundary)

**`CarsSearchQueryDTO`** (query params)
- Uses `price_min` / `price_max` as **string** to avoid float parsing by FastAPI/Pydantic
- Validates parseability to `Decimal`, but does not store `Decimal` itself
- Validates bounds (e.g., `limit <= 200`)
- Trims empty strings

**`CarResponseDTO`** (response)
- `price: str` (converted from domain `Decimal` at boundary)
- Other fields map directly from domain entity

**`CarsListResponseDTO`**
- `cars: list[CarResponseDTO]`
- `total: int` (total matching results)
- `offset: int` (echoed from request)
- `limit: int` (echoed from request)

---

### 2. Mapper (Translation Layer)

**`CatalogSearchMapper`** class with static methods:

```python
class CatalogSearchMapper:
    """Maps between REST DTOs and domain models for catalog search."""

    @staticmethod
    def to_domain_filters(dto: CarsSearchQueryDTO) -> CatalogFilters:
        """Converts query params to domain filters, handling Decimal conversion."""
        ...

    @staticmethod
    def to_domain_paging(dto: CarsSearchQueryDTO) -> Paging:
        """Converts pagination params to domain paging object."""
        ...

    @staticmethod
    def to_domain_request(dto: CarsSearchQueryDTO) -> SearchCatalogRequest:
        """Convenience method: builds complete domain request."""
        ...

    @staticmethod
    def to_car_response(car: Car) -> CarResponseDTO:
        """Converts domain Car entity to REST response DTO."""
        ...

    @staticmethod
    def to_response(result: SearchCatalogResult, offset: int, limit: int) -> CarsListResponseDTO:
        """Converts domain search result to REST response with pagination metadata."""
        ...
```

**Responsibilities:**
- Protocol adapter between REST types and domain types
- Handles `str → Decimal` conversion at the boundary
- Handles `Decimal → str` conversion for responses
- No business logic, just translation

---

### 3. Controller (Route)

The route **must remain an orchestration-only function:**

```python
@router.get("/v1/cars")
def search_cars(
    query: CarsSearchQueryDTO = Depends(),
    use_case: SearchCatalog = Depends(get_search_catalog_use_case),
) -> CarsListResponseDTO:
    # 1. Parse (handled by FastAPI + Pydantic)
    # 2. Map to domain
    request = CatalogSearchMapper.to_domain_request(query)

    # 3. Execute use case
    result = use_case.execute(request)

    # 4. Map to response (include pagination metadata)
    return CatalogSearchMapper.to_response(result, query.offset, query.limit)
```

**No:**
- ❌ Filtering logic
- ❌ Business logic
- ❌ Inline Decimal conversions
- ❌ Conditional transformations

**Controller is a polite little HTTP robot:** parse → execute → map → return

---

## Responsibility Boundaries

### Where Parsing/Validation Happens

1. **REST DTO layer (Pydantic):**
   - Query param parsing
   - Type constraints (e.g., `year_min: int | None`)
   - Bounds validation (e.g., `limit <= 200`)
   - String trimming

2. **Mapper:**
   - Converts DTO to domain models
   - Creates `Decimal` from `str`
   - No validation, just translation

3. **Use Case:**
   - Validates domain models (`CatalogFilters.validate()`, `Paging.validate()`)
   - Delegates to repository
   - No filtering logic

### Where Filtering Happens

**Repository only** (Postgres adapter), per previous ADR:
- AND semantics across filters
- Case-insensitive exact match (make/model)
- Inclusive year/price ranges
- Paging applied after filtering

---

## Error Handling

**Decision:** Use **custom error format** with global exception handlers.

**Rationale:**
- Domain entities already have validation rules (e.g., `CatalogFilters.validate()`)
- No need to duplicate validation in Pydantic DTOs
- DTOs handle basic type checking and bounds
- Domain layer handles business rule validation
- Global exception handlers keep routes clean

### Error Response Format

**Standard format:**
```json
{
  "detail": "Human-readable error message"
}
```

**For validation errors with multiple issues:**
```json
{
  "detail": "Validation failed",
  "errors": [
    {"field": "price_min", "message": "Must be greater than zero"},
    {"field": "year_max", "message": "Must be less than year_min"}
  ]
}
```

### Error Handling Strategy

**1. Basic Type/Constraint Errors (Pydantic)**

Handled automatically by FastAPI/Pydantic:
- Invalid types: `price_min=abc` → 422
- Bounds violations: `limit=500` → 422
- Pattern mismatches: `price_min=1.234` → 422

**2. Domain Validation Errors (Business Rules)**

Handled by **global exception handlers**:

```python
# src/kavak_lite/entrypoints/http/app.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from kavak_lite.domain.errors import ValidationError, DomainError


@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, exc: ValidationError):
    """Handle domain validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )


@app.exception_handler(ValueError)
async def handle_value_error(request: Request, exc: ValueError):
    """Handle value errors from domain logic."""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    """Handle generic domain errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    """Handle unexpected errors."""
    # Log the error for debugging
    import structlog
    logger = structlog.get_logger()
    logger.error("unexpected_error", error=str(exc), type=type(exc).__name__)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### Validation Layers

**Layer 1: DTO (Pydantic)** - Basic constraints only
```python
class CarsSearchQueryDTO(BaseModel):
    price_min: str | None = Field(
        None,
        pattern=r"^\d+(\.\d{1,2})?$"  # Format check only
    )
    limit: int = Field(20, ge=1, le=200)  # Bounds check only
```

**Layer 2: Mapper** - Translation only (no validation)
```python
class CatalogSearchMapper:
    @staticmethod
    def to_domain_filters(dto: CarsSearchQueryDTO) -> CatalogFilters:
        # Just convert, don't validate
        return CatalogFilters(
            price_min=Decimal(dto.price_min) if dto.price_min else None,
            ...
        )
```

**Layer 3: Domain** - Business rules validation
```python
class CatalogFilters:
    def validate(self) -> None:
        if self.price_min and self.price_max:
            if self.price_min > self.price_max:
                raise ValidationError("price_min cannot be greater than price_max")

        if self.year_min and self.year_max:
            if self.year_min > self.year_max:
                raise ValidationError("year_min cannot be greater than year_max")
```

### Benefits

- ✅ Single source of truth for business rules (domain layer)
- ✅ DTOs stay thin and focused on HTTP concerns
- ✅ Routes stay clean (no try/except blocks)
- ✅ Consistent error format across all endpoints
- ✅ Easy to test validation logic independently

---

## Dependency Injection Strategy

**Goal:** Wire `SearchCatalog` with `PostgresCatalogRepository` while keeping route tests fast.

**Implementation:**
```python
def get_search_catalog_use_case() -> SearchCatalog:
    """Factory function that returns configured use case."""
    repo = PostgresCatalogRepository(...)
    return SearchCatalog(repo)
```

**Testing:**
- **Unit tests:** Override `get_search_catalog_use_case()` to return a mock use case
  - No DB, no repositories
  - Fast, isolated tests
- **Integration tests (optional):** Use real FastAPI app + Postgres
  - Test full stack
  - Run in CI only

---

## Migration Strategy

### Existing `/financing/plan` Endpoint

**Current state:** The existing `/financing/plan` endpoint (app.py:31) uses `float` for monetary values:

```python
class FinancingPayload(BaseModel):
    price: float  # ⚠️ Uses float
    down_payment: float

# Response also uses float
return {
    "monthly_payment": float(plan.monthly_payment)
}
```

**Conflict:** This ADR mandates string decimals for all monetary values.

**Options:**

1. **Immediate Migration (Recommended)**
   - Update `/financing/plan` to use string decimals
   - Breaking change → Version bump to `/v2/financing/plan`
   - Keep `/v1/financing/plan` for backwards compatibility (deprecated)
   - Add deprecation warning to `/v1` response headers

2. **Gradual Migration**
   - Keep `/financing/*` endpoints with floats (legacy pattern)
   - All new `/v1/cars/*` endpoints use string decimals
   - Document the inconsistency clearly
   - Plan migration in future major version

3. **Accept Inconsistency**
   - Financial endpoints: floats (legacy)
   - Car catalog endpoints: strings (new standard)
   - Risk of confusion and errors

**Decision:** Option 1 - Immediate Migration

Since we're still in development phase with no external clients, we'll:
- Update `/financing/plan` to accept/return string decimals
- This maintains consistency across all endpoints
- No versioning needed yet (no breaking change for external users)

**Action Items:**
- Update `FinancingPayload` to use `str` for `price` and `down_payment`
- Update response to return string decimals
- Add validation in mapper to convert `str → Decimal`
- Update tests to use string decimals

---

## Consequences

### Positive

- ✅ Clear separation of concerns (REST ↔ Domain)
- ✅ Thin, readable controllers
- ✅ Proper Decimal boundary enforcement
- ✅ Easy to test each layer independently
- ✅ Pattern scales to future endpoints
- ✅ Mappers are discoverable and grouped by feature

### Negative

- ⚠️ Extra abstraction layer (mappers) adds files
- ⚠️ Developers must remember to use mappers, not inline conversions

### Mitigations

- Document the pattern clearly (this ADR)
- Code review checklist: "Does controller use mapper?"
- Keep mappers simple and focused

---

## Alternatives Considered

### 1. Simple Assembler Functions

**Approach:** Use standalone functions instead of a mapper class
```python
def to_domain_filters(dto) -> CatalogFilters: ...
def to_domain_paging(dto) -> Paging: ...
```

**Rejected because:**
- Functions become scattered across module
- Harder to discover all related mappings
- No encapsulation for shared logic

### 2. DTO Methods

**Approach:** Add mapping methods directly to DTOs
```python
class CarsSearchQueryDTO:
    def to_domain_request(self) -> SearchCatalogRequest: ...
```

**Rejected because:**
- Violates Clean Architecture dependency rule (outer layer makes inner layer aware of it)
- DTOs become coupled to domain
- Harder to keep domain entities pure

### 3. Auto-mapping Libraries (e.g., Pydantic's model_validate)

**Rejected because:**
- Loses explicit control over Decimal conversion
- Implicit magic makes boundaries unclear
- Harder to debug and test edge cases

---

## API Standards

### Response Format

**Successful responses:**
```json
{
  "cars": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "make": "Toyota",
      "model": "Camry",
      "year": 2020,
      "price": "25000.00"
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

**Error responses:**
```json
{
  "detail": "Validation error message"
}
```

or for multiple errors:

```json
{
  "detail": [
    {
      "loc": ["query", "price_min"],
      "msg": "value is not a valid decimal",
      "type": "type_error.decimal"
    }
  ]
}
```

### HTTP Status Codes

| Code | Usage | Example |
|------|-------|---------|
| `200 OK` | Successful GET request | Car list returned |
| `422 Unprocessable Entity` | Validation error | Invalid query params or domain validation failure |
| `500 Internal Server Error` | Unexpected server error | Database connection failure |

**Future endpoints may use:**
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Business rule violation

### Pagination Standards

**Current Decision:** Offset/Limit Pagination

All list endpoints return:
```json
{
  "cars": [...],        // or "items" for generic endpoints
  "total": 100,         // Total matching results
  "offset": 20,         // Current offset (echoed from request)
  "limit": 20           // Current limit (echoed from request)
}
```

**Rationale:**
- Simple to implement and understand
- Works well for small to medium datasets
- Allows jumping to arbitrary pages
- Total count helps build pagination UI

**Future Migration:** Cursor-based pagination will be evaluated in a separate ADR when:
- Dataset grows beyond 100k records
- Performance profiling shows offset queries are slow
- Deep pagination becomes a use case

Cursor-based format (future):
```json
{
  "cars": [...],
  "next_cursor": "eyJpZCI6MTIzfQ==",
  "has_more": true
}
```

### API Versioning Strategy

**Decision:** Use **URL-based versioning** starting with `/v1` prefix for all new endpoints.

**Format:** `/v{major_version}/{resource}`
- Example: `/v1/cars`, `/v1/financing/plan`

**Rationale:**
- Simple and explicit in URLs
- Easy to route different versions to different handlers
- Clear in logs and monitoring
- Supported by all HTTP clients
- No ambiguity about which version is being called

**Starting Point:**
- All new endpoints start with `/v1` prefix
- Existing `/financing/plan` will be migrated to `/v1/financing/plan`
- Old `/financing/plan` can be removed (no external clients yet)

**Future Versioning:**
- Breaking changes require new version: `/v2/cars`
- Non-breaking changes (new optional fields) stay in current version
- Support N-1 versions (e.g., maintain v1 while v2 is current)

**Alternatives Considered:**
- **Header-based versioning** (`Accept: application/vnd.kavak.v1+json`)
  - Rejected: Harder to test with curl, less visible in logs
- **Query param** (`/cars?version=1`)
  - Rejected: Pollutes query string, easy to forget
- **No versioning**
  - Rejected: Makes breaking changes impossible without client coordination

### Field Naming Conventions

- **snake_case** for all JSON keys (Python convention)
  - `price_min`, `year_max`, `created_at`
- **ISO 8601** for timestamps
  - `"created_at": "2025-12-26T10:30:00Z"`
- **String decimals** for monetary values
  - `"price": "25000.00"` (never `25000.00` as number)

---

## API Documentation Strategy

### 1. OpenAPI/Swagger (Auto-generated)

**Implementation:**
```python
from fastapi import FastAPI

app = FastAPI(
    title="Kavak Lite API",
    description="Car marketplace API",
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc
    openapi_url="/openapi.json" # OpenAPI schema
)
```

**Enhance DTOs with examples:**
```python
class CarsSearchQueryDTO(BaseModel):
    """Query parameters for searching cars in the catalog."""

    make: str | None = Field(
        None,
        description="Filter by car make (case-insensitive exact match)",
        example="Toyota"
    )
    model: str | None = Field(
        None,
        description="Filter by car model (case-insensitive exact match)",
        example="Camry"
    )
    price_min: str | None = Field(
        None,
        description="Minimum price (inclusive, decimal as string)",
        example="20000.00",
        pattern=r"^\d+(\.\d{1,2})?$"
    )
    limit: int = Field(
        20,
        ge=1,
        le=200,
        description="Maximum number of results to return"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "make": "Toyota",
                "model": "Camry",
                "year_min": 2018,
                "year_max": 2023,
                "price_min": "20000.00",
                "price_max": "35000.00",
                "offset": 0,
                "limit": 20
            }
        }
```

**Enhance routes with metadata:**
```python
@router.get(
    "/v1/cars",
    response_model=CarsListResponseDTO,
    summary="Search car catalog",
    description="""
    Search for cars in the catalog with optional filters and pagination.

    ## Filters
    - All filters use AND semantics
    - Make/model: case-insensitive exact match
    - Year/price: inclusive ranges

    ## Pagination
    - Default limit: 20
    - Max limit: 200
    - Use offset for pagination

    ## Example
    ```
    GET /v1/cars?make=Toyota&price_max=30000.00&limit=10
    ```
    """,
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "cars": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "make": "Toyota",
                                "model": "Camry",
                                "year": 2020,
                                "price": "25000.00"
                            }
                        ],
                        "total": 42
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "price_min must be a valid decimal"
                    }
                }
            }
        }
    },
    tags=["Cars"]
)
def search_cars(...):
    ...
```

### 2. Additional Documentation

**README.md with quick examples:**
```markdown
## API Quick Start

### Search Cars

GET /v1/cars?make=Toyota&price_max=30000.00

curl "http://localhost:8000/v1/cars?make=Toyota&price_max=30000.00"
```

**Postman/Thunder Client collection** (optional):
- Export OpenAPI schema
- Import into Postman
- Share collection with team

### 3. Contract Testing (Future)

Consider adding contract tests to ensure API documentation stays in sync:
```python
def test_openapi_schema_is_valid():
    """Ensure OpenAPI schema is valid and up-to-date."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    # Validate against OpenAPI 3.0 spec
    ...
```

---

## Implementation Checklist

### Phase 1: Global Infrastructure
- [ ] Add domain error classes (`ValidationError`, `DomainError`) to `domain/errors.py`
- [ ] Configure FastAPI app metadata (title, description, version) in `app.py`
- [ ] Add global exception handlers in `app.py`:
  - [ ] `ValidationError` → 422
  - [ ] `ValueError` → 422
  - [ ] `DomainError` → 400
  - [ ] `Exception` → 500 (with logging)
- [ ] Create `dependencies.py` with DI factory functions

### Phase 2: Migrate `/financing/plan` (Immediate Migration)
- [ ] Update `FinancingPayload` DTO to use `str` for `price` and `down_payment`
- [ ] Create `FinancingMapper` class to handle string → Decimal conversion
- [ ] Update route to `/v1/financing/plan`
- [ ] Update response to return string decimals
- [ ] Update tests to use string format
- [ ] Remove old `/financing/plan` endpoint

### Phase 3: Car Catalog Search Endpoint
- [ ] Create `dtos/catalog_search.py`:
  - [ ] `CarsSearchQueryDTO` with Field descriptions and examples
  - [ ] `CarResponseDTO` with Field descriptions and examples
  - [ ] `CarsListResponseDTO` (include cars, total, offset, limit)
- [ ] Create `mappers/catalog_search_mapper.py` with `CatalogSearchMapper` class:
  - [ ] `to_domain_filters()` - converts DTO to CatalogFilters
  - [ ] `to_domain_paging()` - converts to Paging
  - [ ] `to_domain_request()` - convenience method
  - [ ] `to_car_response()` - converts Car to CarResponseDTO
  - [ ] `to_response()` - converts SearchCatalogResult + pagination metadata
- [ ] Create `routes/cars.py`:
  - [ ] Router with `/v1` prefix and "Cars" tag
  - [ ] GET `/v1/cars` endpoint with OpenAPI metadata
  - [ ] Add summary, description, and response examples
- [ ] Update `app.py` to include cars router

### Phase 4: Testing
- [ ] Add unit tests for `CatalogSearchMapper`:
  - [ ] Test DTO → domain conversion
  - [ ] Test domain → DTO conversion
  - [ ] Test Decimal string conversion
- [ ] Add unit tests for `/v1/cars` route:
  - [ ] Mock use case
  - [ ] Test happy path
  - [ ] Test validation errors
  - [ ] Test pagination metadata in response
- [ ] Add unit tests for global exception handlers
- [ ] Verify OpenAPI schema generation at `/openapi.json`
- [ ] Manual test Swagger UI at `/docs`
- [ ] Manual test ReDoc at `/redoc`

### Phase 5: Documentation
- [ ] Test "Try it out" feature in Swagger UI
- [ ] Verify all examples work correctly
- [ ] Add curl examples to README (optional)
- [ ] Document pattern in team wiki (optional)

---

## References

- [API Documentation Guide](../API_DOCUMENTATION_GUIDE.md) - Comprehensive examples and best practices
- Architecture Decision Record: [Monetary Values - Decimal Arithmetic System-Wide](./12-25-25-monetary-values.md)
- Architecture Decision Record: [Database Foundation - SQLAlchemy, Alembic, and Postgres](./12-25-25-database-foundation.md)
- Martin Fowler's [Mapper Pattern](https://martinfowler.com/eaaCatalog/dataMapper.html)
- Clean Architecture by Robert C. Martin
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)