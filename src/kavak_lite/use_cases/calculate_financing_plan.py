from __future__ import annotations
from dataclasses import dataclass
from math import isfinite

from kavak_lite.domain.financing import (
    ANNUAL_INTEREST_RATE,
    FinancingPlan,
    FinancingRequest,
)


@dataclass(frozen=True, slots=True)
class CalculateFinancingPlan:
    annual_rate: float = ANNUAL_INTEREST_RATE

    def execute(self, req: FinancingRequest) -> FinancingPlan:
        req.validate()

        principal = req.price - req.down_payment
        monthly_rate = self.annual_rate / 12.0
        term_months = req.term_months

        # Standard amortized loan payment:
        # monthly_payment = P * (r*(1+r)^n) / ((1+r)^n - 1)
        if monthly_rate == 0:
            monthly_payment = principal / term_months
        else:
            factor = (1 + monthly_rate) ** term_months
            monthly_payment = principal * (monthly_rate * factor) / (factor - 1)

        if not isfinite(monthly_payment) or monthly_payment <= 0:
            raise ValueError("Computed monthly payment is invalid")

        total_paid = monthly_payment * term_months
        total_interest = total_paid - principal

        return FinancingPlan(
            principal=principal,
            annual_rate=self.annual_rate,
            term_months=term_months,
            monthly_payment=monthly_payment,
            total_paid=total_paid,
            total_interest=total_interest,
        )
