from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kavak_lite.domain.financing import FinancingRequest, InvalidFinancingInput
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


app = FastAPI(title="kavak-lite")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class FinancingPayload(BaseModel):
    """
    External API payload - accepts floats for ergonomics.

    Boundary rule: convert to Decimal immediately upon entering the system.
    """

    price: float
    down_payment: float
    term_months: int


@app.post("/financing/plan")
def financing_plan(payload: FinancingPayload) -> dict[str, int | float]:
    """
    Calculate a financing plan for a car purchase.

    Accepts float inputs (standard for JSON APIs) but converts to Decimal
    at the boundary per MONETARY_VALUES ADR.
    """
    uc = CalculateFinancingPlan()

    try:
        # Boundary conversion: float → Decimal
        plan = uc.execute(
            FinancingRequest(
                price=Decimal(str(payload.price)),
                down_payment=Decimal(str(payload.down_payment)),
                term_months=payload.term_months,
            )
        )
    except InvalidFinancingInput as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Boundary conversion: Decimal → float for JSON serialization
    return {
        "principal": float(plan.principal),
        "annual_rate": float(plan.annual_rate),
        "term_months": plan.term_months,
        "monthly_payment": float(plan.monthly_payment),
        "total_paid": float(plan.total_paid),
        "total_interest": float(plan.total_interest),
    }
