from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from kavak_lite.domain.errors import DomainError


class InvalidFinancingInput(DomainError):
    pass


ALLOWED_TERMS = {36, 48, 60, 72}
ANNUAL_INTEREST_RATE = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class FinancingRequest:
    price: Decimal
    down_payment: Decimal
    term_months: int

    def validate(self) -> None:
        if self.price <= 0:
            raise InvalidFinancingInput("price must be > 0")
        if self.down_payment < 0:
            raise InvalidFinancingInput("down_payment must be >= 0")
        if self.down_payment >= self.price:
            raise InvalidFinancingInput("down_payment must be < price")
        if self.term_months not in ALLOWED_TERMS:
            raise InvalidFinancingInput(f"term_months must be one of {sorted(ALLOWED_TERMS)}")


@dataclass(frozen=True, slots=True)
class FinancingPlan:
    principal: Decimal
    annual_rate: Decimal
    term_months: int
    monthly_payment: Decimal
    total_paid: Decimal
    total_interest: Decimal
