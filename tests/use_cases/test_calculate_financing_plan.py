from decimal import Decimal

import pytest

from kavak_lite.domain.errors import ValidationError
from kavak_lite.domain.financing import FinancingRequest
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


# ============================================================================
# VALIDATION TESTS
# ============================================================================


def test_rejects_zero_price():
    """Price must be greater than zero."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("0"), down_payment=Decimal("0"), term_months=36)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_negative_price():
    """Price cannot be negative."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("-100000"), down_payment=Decimal("0"), term_months=36)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_negative_down_payment():
    """Down payment cannot be negative."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("-10000"), term_months=36)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_down_payment_equal_to_price():
    """Down payment must be less than price (some amount must be financed)."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("100000"), term_months=36)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_down_payment_exceeding_price():
    """Down payment cannot exceed price."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("150000"), term_months=36)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_term_24_months():
    """24 months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("10000"), term_months=24)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_term_zero():
    """Zero months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("10000"), term_months=0)

    with pytest.raises(ValidationError):
        uc.execute(req)


def test_rejects_negative_term():
    """Negative months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("10000"), term_months=-36)

    with pytest.raises(ValidationError):
        uc.execute(req)


# ============================================================================
# CALCULATION TESTS - VALID TERMS
# ============================================================================


def test_accepts_term_36_months():
    """36 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("20000"), term_months=36)

    plan = uc.execute(req)

    assert plan.term_months == 36
    assert plan.principal == Decimal("80000")
    assert plan.monthly_payment > 0


def test_accepts_term_48_months():
    """48 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("20000"), term_months=48)

    plan = uc.execute(req)

    assert plan.term_months == 48
    assert plan.principal == Decimal("80000")
    assert plan.monthly_payment > 0


def test_accepts_term_60_months():
    """60 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("20000"), term_months=60)

    plan = uc.execute(req)

    assert plan.term_months == 60
    assert plan.principal == Decimal("80000")
    assert plan.monthly_payment > 0


def test_accepts_term_72_months():
    """72 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("20000"), term_months=72)

    plan = uc.execute(req)

    assert plan.term_months == 72
    assert plan.principal == Decimal("80000")
    assert plan.monthly_payment > 0


# ============================================================================
# CALCULATION TESTS - EDGE CASES
# ============================================================================


def test_accepts_zero_down_payment():
    """Zero down payment is valid - finance the entire price."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("0"), term_months=36)

    plan = uc.execute(req)

    assert plan.principal == Decimal("100000")
    assert plan.monthly_payment > 0
    assert plan.total_paid > plan.principal


def test_small_down_payment():
    """Very small down payment should work correctly."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("100"), term_months=36)

    plan = uc.execute(req)

    assert plan.principal == Decimal("99900")
    assert plan.monthly_payment > 0


def test_down_payment_just_below_price():
    """Down payment can be very close to price (minimal financing)."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("99999"), term_months=36)

    plan = uc.execute(req)

    assert plan.principal == Decimal("1")
    assert plan.monthly_payment > 0
    assert plan.total_interest >= 0  # Tiny principal, minimal interest


# ============================================================================
# CALCULATION TESTS - MATHEMATICAL ACCURACY
# ============================================================================


def test_calculates_correct_monthly_payment_with_standard_rate():
    """
    Verify the amortization formula produces correct results.

    Using the standard loan formula:
    M = P * [r(1+r)^n] / [(1+r)^n - 1]

    Where:
    - P = principal (100,000)
    - r = monthly rate (0.10 / 12)
    - n = number of months (36)

    Expected monthly payment = $3,226.72 (rounded to cents)
    """
    uc = CalculateFinancingPlan()  # Uses default 10% annual rate
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("0"), term_months=36)

    plan = uc.execute(req)

    # Verify principal is correct
    assert plan.principal == Decimal("100000")
    assert plan.annual_rate == Decimal("0.10")
    assert plan.term_months == 36

    # Verify monthly payment (exact, deterministic with Decimal)
    assert plan.monthly_payment == Decimal("3226.72")

    # Verify total paid and interest (exact calculations)
    assert plan.total_paid == Decimal("3226.72") * 36
    assert plan.total_interest == plan.total_paid - Decimal("100000")


def test_calculates_with_zero_interest_rate():
    """
    When interest rate is 0%, payment should be principal divided by term.

    Special case: The code handles r=0 separately to avoid division by zero.
    """
    uc = CalculateFinancingPlan(annual_rate=Decimal("0"))
    req = FinancingRequest(price=Decimal("120000"), down_payment=Decimal("20000"), term_months=48)

    plan = uc.execute(req)

    # With 0% interest, monthly payment = principal / months (rounded to cents)
    expected_payment = Decimal("2083.33")  # 100000 / 48 = 2083.33333... rounded
    assert plan.monthly_payment == expected_payment

    # Total paid should equal monthly_payment * months (exact)
    assert plan.total_paid == expected_payment * 48
    # Small rounding difference: total_paid might be slightly different from principal
    assert plan.total_interest == plan.total_paid - Decimal("100000")


def test_calculates_with_custom_interest_rate():
    """
    The use case should accept custom annual interest rates.

    Testing with 15% annual rate (0.15).
    """
    uc = CalculateFinancingPlan(annual_rate=Decimal("0.15"))
    req = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("0"), term_months=36)

    plan = uc.execute(req)

    assert plan.annual_rate == Decimal("0.15")
    assert plan.principal == Decimal("100000")

    # Higher interest rate means higher monthly payment than 10% rate
    # At 15%, monthly payment = $3,466.53 (vs $3,226.72 at 10%)
    assert plan.monthly_payment == Decimal("3466.53")

    # Total interest should be positive and significant
    assert plan.total_interest > Decimal("24000")  # Over $24k in interest


def test_longer_term_means_lower_monthly_payment():
    """
    For the same principal, longer terms should have lower monthly payments.
    """
    uc = CalculateFinancingPlan()
    req_36 = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("0"), term_months=36)
    req_72 = FinancingRequest(price=Decimal("100000"), down_payment=Decimal("0"), term_months=72)

    plan_36 = uc.execute(req_36)
    plan_72 = uc.execute(req_72)

    # 72 months should have lower monthly payment than 36 months
    assert plan_72.monthly_payment < plan_36.monthly_payment

    # But 72 months should have higher total interest
    assert plan_72.total_interest > plan_36.total_interest


def test_calculates_realistic_car_financing_scenario():
    """
    Complete realistic example: $250,000 car, $50,000 down, 60 months at 10%.

    This serves as documentation for a typical use case.
    """
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=Decimal("250000"), down_payment=Decimal("50000"), term_months=60)

    plan = uc.execute(req)

    # Verify the basics
    assert plan.principal == Decimal("200000")
    assert plan.term_months == 60
    assert plan.annual_rate == Decimal("0.10")

    # Monthly payment (exact, deterministic)
    assert plan.monthly_payment == Decimal("4249.41")

    # Total paid over 5 years (exact)
    assert plan.total_paid == Decimal("4249.41") * 60

    # Total interest over the life of the loan
    assert plan.total_interest == plan.total_paid - Decimal("200000")
