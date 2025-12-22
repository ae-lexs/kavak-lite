import pytest

from kavak_lite.domain.financing import FinancingRequest, InvalidFinancingInput
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


def test_rejects_invalid_term():
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=10_000, term_months=24)

    with pytest.raises(InvalidFinancingInput):
        uc.execute(req)


def test_rejects_down_payment_ge_price():
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=100_000, term_months=36)

    with pytest.raises(InvalidFinancingInput):
        uc.execute(req)


def test_calculates_plan_happy_path():
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=200_000, down_payment=50_000, term_months=60)

    plan = uc.execute(req)

    assert plan.principal == 150_000
    assert plan.term_months == 60
    assert plan.monthly_payment > 0
    assert plan.total_paid > plan.principal
    assert plan.total_interest > 0
