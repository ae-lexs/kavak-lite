from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Car:
    id: str
    make: str
    model: str
    year: int
    price: Decimal


@dataclass(frozen=True, slots=True)
class CatalogFilters:
    make: str | None = None
    model: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None

    def validate(self) -> None:
        # Guardrails: prevent float leakage past boundary
        if self.price_min is not None and not isinstance(self.price_min, Decimal):
            raise TypeError("price_min must be Decimal or None (no floats past the boundary)")
        if self.price_max is not None and not isinstance(self.price_max, Decimal):
            raise TypeError("price_max must be Decimal or None (no floats past the boundary)")

        if self.year_min is not None and self.year_max is not None and self.year_min > self.year_max:
            raise ValueError("year_min cannot be greater than year_max")
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min cannot be greater than price_max")


@dataclass(frozen=True, slots=True)
class Paging:
    offset: int = 0
    size: int = 20

    def validate(self) -> None:
        if self.offset < 0:
            raise ValueError("offset must be >= 0")
        if self.limit <= 0:
            raise ValueError("limit must be > 0")
        # Keep it reasonable; tweak if you already have a global constant
        if self.limit > 200:
            raise ValueError("limit must be <= 200")
