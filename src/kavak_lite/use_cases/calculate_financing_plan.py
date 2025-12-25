from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from kavak_lite.domain.financing import (
    ANNUAL_INTEREST_RATE,
    FinancingPlan,
    FinancingRequest,
)


@dataclass(frozen=True, slots=True)
class CalculateFinancingPlan:
    """
    Calculate a financing plan using exact decimal arithmetic.

    Rounding policy:
    - All intermediate calculations use full precision Decimal
    - Monthly payment is rounded to 2 decimal places (cents) using ROUND_HALF_UP
    - Total amounts are computed from the rounded monthly payment (not re-rounded)
    - This ensures: total_paid = monthly_payment * term_months (exactly)
    """

    annual_rate: Decimal = ANNUAL_INTEREST_RATE

    def execute(self, req: FinancingRequest) -> FinancingPlan:
        req.validate()

        principal = req.price - req.down_payment
        monthly_rate = self.annual_rate / Decimal("12")
        term_months = Decimal(req.term_months)

        # Standard amortized loan payment:
        # monthly_payment = P * (r*(1+r)^n) / ((1+r)^n - 1)
        if monthly_rate == 0:
            monthly_payment_precise = principal / term_months
        else:
            one = Decimal("1")
            factor = (one + monthly_rate) ** term_months
            monthly_payment_precise = principal * (monthly_rate * factor) / (factor - one)

        # Explicit rounding: monthly payment to 2 decimal places (cents)
        monthly_payment = monthly_payment_precise.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if monthly_payment <= 0:
            raise ValueError("Computed monthly payment is invalid")

        # Compute totals from rounded monthly payment
        total_paid = monthly_payment * term_months
        total_interest = total_paid - principal

        return FinancingPlan(
            principal=principal,
            annual_rate=self.annual_rate,
            term_months=int(term_months),
            monthly_payment=monthly_payment,
            total_paid=total_paid,
            total_interest=total_interest,
        )
