from fastapi import APIRouter, Depends

from kavak_lite.entrypoints.http.dtos.catalog_search import (
    CarResponseDTO,
    CarsSearchQueryDTO,
    CatalogSearchResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.catalog_search_mapper import CatalogSearchMapper
from kavak_lite.entrypoints.http.dependencies import (
    get_get_car_by_id_use_case,
    get_search_catalog_use_case,
)
from kavak_lite.use_cases.get_car_by_id import GetCarById, GetCarByIdRequest
from kavak_lite.use_cases.search_car_catalog import SearchCarCatalog


router = APIRouter(tags=["Cars"])


@router.get(
    "/cars",
    response_model=CatalogSearchResponseDTO,
    summary="Search car catalog",
    description="""
    Search for cars in the catalog with optional filters and pagination.

    ## Filters
    - All filters use AND semantics
    - Brand/model: case-insensitive exact match
    - Year/price: inclusive ranges

    ## Pagination
    - Default limit: 20
    - Max limit: 100
    - Use offset for pagination

    ## Example
    ```
    GET /v1/cars?brand=Toyota&price_max=30000.00&limit=10
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
                                "brand": "Toyota",
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
            "description": "Validation error",
            "content": {
                "application/json": {"example": {"detail": "price_min must be a valid decimal"}}
            },
        },
    },
)
def get_cars(
    query: CarsSearchQueryDTO = Depends(),
    use_case: SearchCarCatalog = Depends(get_search_catalog_use_case),
) -> CatalogSearchResponseDTO:
    """Search cars endpoint following parse → execute → map → return pattern."""
    # 1. Map to domain request
    request = CatalogSearchMapper.to_domain_request(query)

    # 2. Execute use case
    result = use_case.execute(request)

    # 3. Map to response
    return CatalogSearchMapper.to_response(
        result=result,
        offset=query.offset,
        limit=query.limit,
    )


@router.get(
    "/cars/{car_id}",
    response_model=CarResponseDTO,
    summary="Get car by ID",
    description="""
    Retrieve detailed information about a specific car by its ID.

    ## Parameters
    - `car_id`: Must be a valid UUID format

    ## Example
    ```
    GET /v1/cars/550e8400-e29b-41d4-a716-446655440000
    ```
    """,
    responses={
        200: {
            "description": "Car found",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "brand": "Toyota",
                        "model": "Corolla",
                        "year": 2020,
                        "price": "25000.00",
                        "trim": "XLE",
                        "mileage_km": 50000,
                        "transmission": "Automático",
                        "fuel_type": "Gasolina",
                        "body_type": "Sedán",
                        "location": "CDMX",
                        "url": "https://kavak-lite.com/toyota/corolla/2020",
                    }
                }
            },
        },
        404: {
            "description": "Car not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Car with identifier '550e8400-e29b-41d4-a716-446655440000' not found",
                        "code": "NOT_FOUND",
                    }
                }
            },
        },
        422: {
            "description": "Invalid UUID format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Validation failed",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "field": "car_id",
                                "message": "Must be a valid UUID format",
                                "code": "INVALID_UUID",
                            }
                        ],
                    }
                }
            },
        },
    },
)
def get_car_by_id(
    car_id: str,
    use_case: GetCarById = Depends(get_get_car_by_id_use_case),
) -> CarResponseDTO:
    """Get car by ID following parse → execute → map → return pattern."""
    # 1. Parse
    request = GetCarByIdRequest(car_id=car_id)

    # 2. Execute (may raise NotFoundError → 404)
    result = use_case.execute(request)

    # 3. Map to response
    return CatalogSearchMapper.to_car_response(result.car)
