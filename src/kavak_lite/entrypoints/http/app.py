from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kavak_lite.domain.financing import FinancingRequest, InvalidFinancingInput
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


app = FastAPI(title="kavak-lite")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class FinancingPayload(BaseModel):
    price: float
    down_payment: float
    term_months: int


@app.post("/financing/plan")
def financing_plan(payload: FinancingPayload) -> dict[str, int | float]:
    uc = CalculateFinancingPlan()

    try:
        plan = uc.execute(
            FinancingRequest(
                price=payload.price,
                down_payment=payload.down_payment,
                term_months=payload.term_months,
            )
        )
    except InvalidFinancingInput as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "principal": plan.principal,
        "annual_rate": plan.annual_rate,
        "term_months": plan.term_months,
        "monthly_payment": plan.monthly_payment,
        "total_paid": plan.total_paid,
        "total_interest": plan.total_interest,
    }
