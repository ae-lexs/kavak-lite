from __future__ import annotations

from dataclasses import dataclass

from kavak_lite.domain.car import (
    Car,
    CatalogFilters,
    Paging,
)
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository


@dataclass(frozen=True, slots=True)
class CarSearchCatalogRequest:
    filters: CatalogFilters
    paging: Paging


@dataclass(frozen=True, slots=True)
class CarSearchCatalogResponse:
    cars: list[Car]
    total_count: int | None = None  # Total matching cars before paging (None if not calculated)


class CarSearchCatalog:
    """
    Car search catalog with filters and pagination.

    This use case validates paging parameters and delegates filtering
    to the repository adapter. No filtering logic exists in the use case.

    See: docs/adr/12-25-25-car-catalog-search.md
    """

    def __init__(self, car_catalog_repository: CarCatalogRepository) -> None:
        self._car_catalog_repository = car_catalog_repository

    def execute(self, request: CarSearchCatalogRequest) -> CarSearchCatalogResponse:
        """
        Execute catalog search.

        Validates request parameters before delegating to repository.
        This is the single source of validation (contract programming).

        Args:
            request: Search parameters (filters and paging)

        Returns:
            Response containing matching cars and optional total count

        Raises:
            PagingValidationError: If paging parameters are invalid
            FilterValidationError: If filter parameters are invalid
        """
        # Validate inputs (UseCase responsibility per contract)
        request.filters.validate()
        request.paging.validate()

        result = self._car_catalog_repository.search(
            filters=request.filters,
            paging=request.paging,
        )

        return CarSearchCatalogResponse(
            cars=result.cars,
            total_count=result.total_count,
        )
