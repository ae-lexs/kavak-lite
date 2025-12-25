from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from kavak_lite.domain.car import Car, CatalogFilters, Paging


@dataclass(frozen=True)
class SearchResult:
    """Result from catalog search including pagination metadata."""

    cars: list[Car]
    total_count: int | None = None  # Total matching cars before paging (None if not calculated)


class CarCatalogRepository(ABC):
    """
    Port for catalog data access.

    Implementations must provide search functionality with filtering and pagination.
    The total_count in SearchResult is optional - implementations can return None
    if calculating the total count is expensive or not needed.
    """

    @abstractmethod
    def search(self, filters: CatalogFilters, paging: Paging) -> SearchResult:
        """
        Search catalog with filters and paging.

        Args:
            filters: Filter criteria (AND semantics)
            paging: Pagination parameters

        Returns:
            SearchResult containing matching cars and optional total count
        """
        ...
