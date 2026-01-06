from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from kavak_lite.domain.errors import ValidationError


@dataclass(frozen=True)
class Car:
    id: str
    make: str
    model: str
    year: int
    price: Decimal
    trim: str | None = None
    mileage_km: int | None = None
    transmission: str | None = None
    fuel_type: str | None = None
    body_type: str | None = None
    location: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogFilters:
    make: str | None = None
    model: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None

    def validate(self) -> None:
        """Validate filter parameters.

        Raises:
            ValidationError: If filter parameters are invalid (with structured errors)
        """
        errors = []

        # Guardrails: prevent float leakage past boundary
        if self.price_min is not None and not isinstance(self.price_min, Decimal):
            errors.append(
                {
                    "field": "price_min",
                    "message": "Must be Decimal or None (no floats past the boundary)",
                    "code": "INVALID_TYPE",
                }
            )
        if self.price_max is not None and not isinstance(self.price_max, Decimal):
            errors.append(
                {
                    "field": "price_max",
                    "message": "Must be Decimal or None (no floats past the boundary)",
                    "code": "INVALID_TYPE",
                }
            )

        # Cross-field validation: year range
        if (
            self.year_min is not None
            and self.year_max is not None
            and self.year_min > self.year_max
        ):
            errors.append(
                {
                    "field": "year_min",
                    "message": "Must be less than or equal to year_max",
                    "code": "INVALID_RANGE",
                }
            )
            errors.append(
                {
                    "field": "year_max",
                    "message": "Must be greater than or equal to year_min",
                    "code": "INVALID_RANGE",
                }
            )

        # Cross-field validation: price range
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            errors.append(
                {
                    "field": "price_min",
                    "message": "Must be less than or equal to price_max",
                    "code": "INVALID_RANGE",
                }
            )
            errors.append(
                {
                    "field": "price_max",
                    "message": "Must be greater than or equal to price_min",
                    "code": "INVALID_RANGE",
                }
            )

        if errors:
            raise ValidationError(errors=errors)


@dataclass(frozen=True, slots=True)
class Paging:
    offset: int = 0
    limit: int = 20

    def validate(self) -> None:
        """Validate paging parameters.

        Raises:
            ValidationError: If paging parameters are invalid (with structured errors)
        """
        errors = []

        if self.offset < 0:
            errors.append(
                {
                    "field": "offset",
                    "message": "Must be greater than or equal to 0",
                    "code": "INVALID_VALUE",
                }
            )

        if self.limit <= 0:
            errors.append(
                {
                    "field": "limit",
                    "message": "Must be greater than 0",
                    "code": "INVALID_VALUE",
                }
            )

        if self.limit > 200:
            errors.append(
                {
                    "field": "limit",
                    "message": "Must be less than or equal to 200",
                    "code": "INVALID_VALUE",
                }
            )

        if errors:
            raise ValidationError(errors=errors)
