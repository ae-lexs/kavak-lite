from __future__ import annotations

from decimal import Decimal

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.entrypoints.http.dtos.catalog_search import (
    CarResponseDTO,
    CarSearchQueryDTO,
    CatalogSearchResponseDTO,
)
from kavak_lite.use_cases.search_car_catalog import (
    SearchCarCatalogRequest,
    SearchCarCatalogResponse,
)


class CatalogSearchMapper:
    """Maps between REST DTOs and domain models for catalog search."""

    @staticmethod
    def to_domain_filters(dto: CarSearchQueryDTO) -> CatalogFilters:
        """
        Converts query params to domain filters, handling Decimal conversion.

        Args:
            dto: The data transfer object containing search query parameters

        Returns:
            CatalogFilters: Domain filters with Decimal prices
        """
        return CatalogFilters(
            make=dto.brand,  # DTO uses 'brand', domain uses 'make'
            model=dto.model,
            year_min=dto.year_min,
            year_max=dto.year_max,
            price_min=Decimal(dto.price_min) if dto.price_min else None,
            price_max=Decimal(dto.price_max) if dto.price_max else None,
        )

    @staticmethod
    def to_domain_paging(dto: CarSearchQueryDTO) -> Paging:
        """
        Converts pagination params to domain paging object.

        Args:
            dto: The data transfer object containing search query parameters

        Returns:
            Paging: Domain paging object
        """
        return Paging(offset=dto.offset, limit=dto.limit)

    @staticmethod
    def to_domain_request(dto: CarSearchQueryDTO) -> SearchCarCatalogRequest:
        """
        Convenience method: builds complete domain request from DTO.

        Args:
            dto: The data transfer object containing search query parameters

        Returns:
            SearchCarCatalogRequest: Complete domain request with filters and paging
        """
        return SearchCarCatalogRequest(
            filters=CatalogSearchMapper.to_domain_filters(dto),
            paging=CatalogSearchMapper.to_domain_paging(dto),
        )

    @staticmethod
    def to_car_response(car: Car) -> CarResponseDTO:
        """
        Converts domain Car entity to REST response DTO.

        Handles Decimal → str conversion at the boundary.

        Args:
            car: Domain Car entity

        Returns:
            CarResponseDTO: REST response DTO with string price
        """
        return CarResponseDTO(
            id=car.id,
            brand=car.make,  # Domain uses 'make', DTO uses 'brand'
            model=car.model,
            year=car.year,
            price=str(car.price),  # Decimal → str at boundary
        )

    @staticmethod
    def to_response(
        result: SearchCarCatalogResponse,
        offset: int,
        limit: int,
    ) -> CatalogSearchResponseDTO:
        """
        Converts domain search result to REST response with pagination metadata.

        Args:
            result: Domain search result containing cars and total count
            offset: Current offset (echoed from request)
            limit: Current limit (echoed from request)

        Returns:
            CatalogSearchResponseDTO: REST response with cars and pagination metadata
        """
        return CatalogSearchResponseDTO(
            cars=[CatalogSearchMapper.to_car_response(car) for car in result.cars],
            total=result.total_count or 0,  # Handle None from repository
            offset=offset,
            limit=limit,
        )
