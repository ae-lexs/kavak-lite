from __future__ import annotations

from abc import ABC, abstractmethod

from kavak_lite.domain.car import Car, CatalogFilters, Paging


class CatalogRepository(ABC):
    @abstractmethod
    def search(self, filters: CatalogFilters, paging: Paging) -> list[Car]: ...
