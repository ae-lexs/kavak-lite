"""Get car by ID use case."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kavak_lite.domain.car import Car
from kavak_lite.domain.errors import NotFoundError, ValidationError
from kavak_lite.ports.car_catalog_repository import CarCatalogRepository


@dataclass(frozen=True, slots=True)
class GetCarByIdRequest:
    """Request to get a car by ID."""

    car_id: str


@dataclass(frozen=True, slots=True)
class GetCarByIdResponse:
    """Response containing the requested car."""

    car: Car


class GetCarById:
    """
    Use case for retrieving a single car by ID.

    Responsibilities:
    - Validate car_id format (must be valid UUID)
    - Delegate to repository for data access
    - Raise NotFoundError if car doesn't exist
    """

    def __init__(self, car_catalog_repository: CarCatalogRepository) -> None:
        """
        Initialize use case with dependencies.

        Args:
            car_catalog_repository: Repository for car data access
        """
        self._repository = car_catalog_repository

    def execute(self, request: GetCarByIdRequest) -> GetCarByIdResponse:
        """
        Execute the get car by ID use case.

        Args:
            request: Request containing car_id

        Returns:
            GetCarByIdResponse with the car

        Raises:
            ValidationError: If car_id is not a valid UUID format
            NotFoundError: If car with given ID doesn't exist
        """
        # Validate UUID format
        try:
            UUID(request.car_id)
        except ValueError:
            raise ValidationError(
                errors=[
                    {
                        "field": "car_id",
                        "message": "Must be a valid UUID format",
                        "code": "INVALID_UUID",
                    }
                ]
            )

        # Get car from repository
        car = self._repository.get_by_id(request.car_id)

        if car is None:
            raise NotFoundError(resource="Car", identifier=request.car_id)

        return GetCarByIdResponse(car=car)
