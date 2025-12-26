from __future__ import annotations

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository, SearchResult


class InMemoryCarCatalogRepository(CarCatalogRepository):
    """
    Canonical contract implementation for tests.

    - Stores cars in insertion order
    - Applies AND-semantics filtering
    - Applies paging AFTER filtering
    - Returns total_count of matching cars before paging
    """

    def __init__(self, cars: list[Car]) -> None:
        self._cars = cars

    def search(self, filters: CatalogFilters, paging: Paging) -> SearchResult:
        # Trust that UseCase has validated inputs (contract programming)
        matches = [car for car in self._cars if self._matches(car, filters)]
        total_count = len(matches)  # Count BEFORE paging

        start = paging.offset
        end = paging.offset + paging.limit
        paginated_cars = matches[start:end]

        return SearchResult(cars=paginated_cars, total_count=total_count)

    def _matches(self, car: Car, filters: CatalogFilters) -> bool:
        if filters.make and car.make.lower() != filters.make.lower():
            return False
        if filters.model and car.model.lower() != filters.model.lower():
            return False
        if filters.year_min is not None and car.year < filters.year_min:
            return False
        if filters.year_max is not None and car.year > filters.year_max:
            return False
        if filters.price_min is not None and car.price < filters.price_min:
            return False
        if filters.price_max is not None and car.price > filters.price_max:
            return False
        return True
