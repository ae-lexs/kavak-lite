from __future__ import annotations

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.ports.catalog_repository import CatalogRepository


class InMemoryCatalogRepository(CatalogRepository):
    """
    Canonical contract implementation for tests.

    - Stores cars in insertion order
    - Applies AND-semantics filtering
    - Applies paging AFTER filtering
    """

    def __init__(self, cars: list[Car]) -> None:
        self._cars = cars

    def search(self, filters: CatalogFilters, paging: Paging) -> list[Car]:
        filters.validate()
        paging.validate()

        matches = [car for car in self._cars if self._matches(car, filters)]

        start = paging.offset
        end = paging.offset + paging.limit

        return matches[start:end]

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
