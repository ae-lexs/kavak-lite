from fastapi import APIRouter, Depends

from kavak_lite.entrypoints.http.dtos.catalog_search import (
    CarsSearchQueryDTO,
    CatalogSearchResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.catalog_search_mapper import CatalogSearchMapper
from kavak_lite.entrypoints.http.dependencies import get_search_catalog_use_case
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
