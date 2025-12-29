# API Documentation Guide

This guide shows how to properly document REST endpoints following our ADR standards.

## Overview

We use **FastAPI's automatic OpenAPI generation** combined with **Pydantic schemas** to create comprehensive, interactive API documentation.

**Live documentation URLs:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Documentation Layers

### Layer 1: FastAPI App Metadata

Configure the FastAPI application with project metadata:

```python
# src/kavak_lite/entrypoints/http/app.py

from fastapi import FastAPI

app = FastAPI(
    title="Kavak Lite API",
    description="""
    Car marketplace API for browsing, searching, and financing vehicles.

    ## Features
    - Search car catalog with filters
    - Calculate financing plans
    - Get car details

    ## Authentication
    Currently no authentication required (development phase).

    ## Rate Limiting
    No rate limits currently enforced.
    """,
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc alternative
    openapi_url="/openapi.json", # OpenAPI schema
    contact={
        "name": "Kavak Lite Team",
        "email": "dev@kavak-lite.com",
    },
    license_info={
        "name": "Proprietary",
    },
)
```

---

### Layer 2: DTO Schemas with Examples

Add descriptions and examples to all Pydantic models:

```python
# src/kavak_lite/entrypoints/http/dtos/catalog_search.py

from pydantic import BaseModel, Field


class CarsSearchQueryDTO(BaseModel):
    """Query parameters for searching cars in the catalog."""

    make: str | None = Field(
        None,
        description="Filter by car make (case-insensitive exact match)",
        examples=["Toyota", "Honda", "Ford"],
    )

    model: str | None = Field(
        None,
        description="Filter by car model (case-insensitive exact match)",
        examples=["Camry", "Accord", "F-150"],
    )

    year_min: int | None = Field(
        None,
        ge=1900,
        le=2100,
        description="Minimum year (inclusive)",
        examples=[2018, 2020],
    )

    year_max: int | None = Field(
        None,
        ge=1900,
        le=2100,
        description="Maximum year (inclusive)",
        examples=[2023, 2025],
    )

    price_min: str | None = Field(
        None,
        description="Minimum price in USD (inclusive, decimal as string)",
        examples=["15000.00", "20000.50"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )

    price_max: str | None = Field(
        None,
        description="Maximum price in USD (inclusive, decimal as string)",
        examples=["35000.00", "50000.99"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )

    offset: int = Field(
        0,
        ge=0,
        description="Number of results to skip (for pagination)",
        examples=[0, 20, 40],
    )

    limit: int = Field(
        20,
        ge=1,
        le=200,
        description="Maximum number of results to return",
        examples=[20, 50, 100],
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "make": "Toyota",
                    "model": "Camry",
                    "year_min": 2018,
                    "year_max": 2023,
                    "price_min": "20000.00",
                    "price_max": "35000.00",
                    "offset": 0,
                    "limit": 20,
                },
                {
                    "make": "Ford",
                    "price_max": "50000.00",
                    "limit": 10,
                },
            ]
        }


class CarResponseDTO(BaseModel):
    """A single car in the catalog."""

    id: str = Field(
        description="Unique car identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    make: str = Field(
        description="Car manufacturer",
        examples=["Toyota", "Honda", "Ford"],
    )

    model: str = Field(
        description="Car model name",
        examples=["Camry", "Accord", "F-150"],
    )

    year: int = Field(
        description="Manufacturing year",
        examples=[2020, 2021, 2022],
    )

    price: str = Field(
        description="Price in USD (decimal as string)",
        examples=["25000.00", "32500.50"],
        pattern=r"^\d+\.\d{2}$",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "make": "Toyota",
                "model": "Camry",
                "year": 2020,
                "price": "25000.00",
            }
        }


class CarsListResponseDTO(BaseModel):
    """Response containing list of cars and metadata."""

    cars: list[CarResponseDTO] = Field(
        description="List of cars matching the search criteria"
    )

    total: int = Field(
        description="Total number of cars matching filters (for pagination)",
        examples=[42, 150, 0],
    )

    offset: int = Field(
        description="Current offset (echoed from request)",
        examples=[0, 20, 40],
    )

    limit: int = Field(
        description="Current limit (echoed from request)",
        examples=[20, 50, 100],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "cars": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "make": "Toyota",
                        "model": "Camry",
                        "year": 2020,
                        "price": "25000.00",
                    },
                    {
                        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                        "make": "Honda",
                        "model": "Accord",
                        "year": 2021,
                        "price": "28500.00",
                    },
                ],
                "total": 42,
                "offset": 0,
                "limit": 20,
            }
        }
```

---

### Layer 3: Route Documentation

Add comprehensive metadata to route decorators:

```python
# src/kavak_lite/entrypoints/http/routes/cars.py

from fastapi import APIRouter, Depends
from kavak_lite.entrypoints.http.dtos.catalog_search import (
    CarsSearchQueryDTO,
    CarsListResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.catalog_search_mapper import (
    CatalogSearchMapper,
)
from kavak_lite.use_cases.search_car_catalog import SearchCatalog
from kavak_lite.entrypoints.http.dependencies import get_search_catalog_use_case


router = APIRouter(prefix="/v1", tags=["Cars"])


@router.get(
    "/cars",
    response_model=CarsListResponseDTO,
    summary="Search car catalog",
    description="""
    Search for cars in the catalog with optional filters and pagination.

    ## Filtering
    - All filters use **AND** semantics (all conditions must match)
    - **Make/Model**: Case-insensitive exact match
    - **Year/Price**: Inclusive ranges (e.g., year_min=2018 includes cars from 2018)
    - Empty filters return all cars

    ## Pagination
    - Default: 20 results per page
    - Maximum: 200 results per page
    - Use `offset` and `limit` for pagination
    - `total` field indicates total matching results (for calculating pages)

    ## Examples

    Find all Toyotas under $30,000:
    ```
    GET /v1/cars?make=Toyota&price_max=30000.00
    ```

    Find 2020-2023 Camrys, page 2 (results 20-40):
    ```
    GET /v1/cars?make=Toyota&model=Camry&year_min=2020&year_max=2023&offset=20&limit=20
    ```

    Get all cars (first 50):
    ```
    GET /v1/cars?limit=50
    ```
    """,
    responses={
        200: {
            "description": "Successful response with list of cars",
            "content": {
                "application/json": {
                    "example": {
                        "cars": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "make": "Toyota",
                                "model": "Camry",
                                "year": 2020,
                                "price": "25000.00",
                            }
                        ],
                        "total": 42,
                        "offset": 0,
                        "limit": 20,
                    }
                }
            },
        },
        422: {
            "description": "Validation error - invalid query parameters",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_decimal": {
                            "summary": "Invalid decimal format",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["query", "price_min"],
                                        "msg": "string does not match regex",
                                        "type": "value_error.str.regex",
                                    }
                                ]
                            },
                        },
                        "limit_exceeded": {
                            "summary": "Limit exceeds maximum",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["query", "limit"],
                                        "msg": "ensure this value is less than or equal to 200",
                                        "type": "value_error.number.not_le",
                                    }
                                ]
                            },
                        },
                    }
                }
            },
        },
    },
)
def search_cars(
    query: CarsSearchQueryDTO = Depends(),
    use_case: SearchCatalog = Depends(get_search_catalog_use_case),
) -> CarsListResponseDTO:
    """Search cars endpoint handler."""
    # Map to domain
    request = CatalogSearchMapper.to_domain_request(query)

    # Execute use case
    result = use_case.execute(request)

    # Map to response
    return CatalogSearchMapper.to_response(result)
```

---

## Best Practices

### 1. **Always Provide Examples**

Bad:
```python
price: str
```

Good:
```python
price: str = Field(
    description="Price in USD (decimal as string)",
    examples=["25000.00", "32500.50"],
    pattern=r"^\d+\.\d{2}$",
)
```

### 2. **Document Business Rules**

Include filtering semantics, validation rules, and edge cases:

```python
description="""
All filters use AND semantics.
Year range is inclusive: year_min=2020 includes cars from 2020.
Empty string filters are ignored.
"""
```

### 3. **Show Multiple Examples**

Provide both minimal and complex examples:

```python
class Config:
    json_schema_extra = {
        "examples": [
            {"make": "Toyota"},  # Minimal
            {  # Complex
                "make": "Toyota",
                "model": "Camry",
                "year_min": 2020,
                "price_max": "30000.00",
                "limit": 50,
            },
        ]
    }
```

### 4. **Document Error Responses**

Show realistic error examples for each status code:

```python
responses={
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "price_min must match pattern ^\\d+(\\.\\d{1,2})?$"
                }
            }
        }
    }
}
```

### 5. **Use Tags to Group Endpoints**

```python
router = APIRouter(prefix="/v1", tags=["Cars"])
```

Results in organized documentation:
- Cars
  - GET /v1/cars
  - GET /v1/cars/{id}
  - POST /v1/cars

---

## Testing Your Documentation

### 1. Visual Inspection

Start the server:
```bash
uvicorn kavak_lite.entrypoints.http.app:app --reload
```

Visit:
- http://localhost:8000/docs (Swagger UI - try the "Try it out" feature!)
- http://localhost:8000/redoc (ReDoc - better for reading)

### 2. Schema Validation

```python
# tests/test_openapi.py
from fastapi.testclient import TestClient
from kavak_lite.entrypoints.http.app import app

def test_openapi_schema_is_valid():
    """Ensure OpenAPI schema is generated correctly."""
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Check metadata
    assert schema["info"]["title"] == "Kavak Lite API"
    assert schema["info"]["version"] == "1.0.0"

    # Check endpoint exists
    assert "/v1/cars" in schema["paths"]
    assert "get" in schema["paths"]["/v1/cars"]
```

### 3. Example Validation

Ensure examples in documentation actually work:

```python
def test_documentation_examples_work():
    """Test that examples from docs actually work."""
    client = TestClient(app)

    # Example from documentation
    response = client.get(
        "/v1/cars",
        params={
            "make": "Toyota",
            "model": "Camry",
            "year_min": 2018,
            "year_max": 2023,
            "price_min": "20000.00",
            "price_max": "35000.00",
            "offset": 0,
            "limit": 20,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "cars" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data
    assert data["offset"] == 0
    assert data["limit"] == 20
```

---

## Exporting Documentation

### For Postman/Insomnia

1. Visit http://localhost:8000/openapi.json
2. Copy the JSON
3. In Postman: Import → Paste Raw Text → Import
4. All endpoints automatically configured

### For External Docs Site

Use tools like:
- **Redocly**: `npx redocly build-docs openapi.json`
- **Swagger Codegen**: Generate client libraries
- **Stoplight**: Host interactive docs

---

## Checklist for New Endpoints

When adding a new endpoint, ensure:

- [ ] DTOs have `Field()` with descriptions and examples
- [ ] Route has `summary`, `description`, and `responses`
- [ ] At least 2 examples provided (minimal + complex)
- [ ] Error responses documented with examples
- [ ] Tags assigned for grouping
- [ ] Tested in Swagger UI with "Try it out"
- [ ] OpenAPI schema validated

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/tutorial/metadata/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Pydantic Field Documentation](https://docs.pydantic.dev/latest/concepts/fields/)
