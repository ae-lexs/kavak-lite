from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from kavak_lite.domain.errors import ValidationError


ALLOWED_TERMS = {36, 48, 60, 72}
ANNUAL_INTEREST_RATE = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class FinancingRequest:
    price: Decimal
    down_payment: Decimal
    term_months: int

    def validate(self) -> None:
        """Validate financing request parameters

        Raises:
            ValidationError: If request parameters are invalid
        """
        errors = []

        if self.price <= 0:
            errors.append(
                {
                    "field": "price",
                    "message": "Must be greater than 0",
                    "code": "INVALID_VALUE",
                }
            )
        if self.down_payment < 0:
            errors.append(
                {
                    "field": "down_payment",
                    "message": "Must be greater than 0",
                    "code": "INVALID_VALUE",
                }
            )
        if self.down_payment >= self.price:
            errors.append(
                {
                    "field": "down_payment",
                    "message": "Must be greater less than price",
                    "code": "INVALID_VALUE",
                }
            )
        if self.term_months not in ALLOWED_TERMS:
            errors.append(
                {
                    "field": "term_months",
                    "message": f"Must be one of {ALLOWED_TERMS}",
                    "code": "INVALID_VALUE",
                }
            )

        if errors:
            raise ValidationError(errors=errors)


@dataclass(frozen=True, slots=True)
class FinancingPlan:
    principal: Decimal
    annual_rate: Decimal
    term_months: int
    monthly_payment: Decimal
    total_paid: Decimal
    total_interest: Decimal
