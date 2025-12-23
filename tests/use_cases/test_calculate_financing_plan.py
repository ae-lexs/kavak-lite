import pytest

from kavak_lite.domain.financing import FinancingRequest, InvalidFinancingInput
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


# ============================================================================
# VALIDATION TESTS
# ============================================================================


def test_rejects_zero_price():
    """Price must be greater than zero."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=0, down_payment=0, term_months=36)

    with pytest.raises(InvalidFinancingInput, match="price must be > 0"):
        uc.execute(req)


def test_rejects_negative_price():
    """Price cannot be negative."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=-100_000, down_payment=0, term_months=36)

    with pytest.raises(InvalidFinancingInput, match="price must be > 0"):
        uc.execute(req)


def test_rejects_negative_down_payment():
    """Down payment cannot be negative."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=-10_000, term_months=36)

    with pytest.raises(InvalidFinancingInput, match="down_payment must be >= 0"):
        uc.execute(req)


def test_rejects_down_payment_equal_to_price():
    """Down payment must be less than price (some amount must be financed)."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=100_000, term_months=36)

    with pytest.raises(InvalidFinancingInput, match="down_payment must be < price"):
        uc.execute(req)


def test_rejects_down_payment_exceeding_price():
    """Down payment cannot exceed price."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=150_000, term_months=36)

    with pytest.raises(InvalidFinancingInput, match="down_payment must be < price"):
        uc.execute(req)


def test_rejects_term_24_months():
    """24 months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=10_000, term_months=24)

    with pytest.raises(InvalidFinancingInput, match="term_months must be one of"):
        uc.execute(req)


def test_rejects_term_zero():
    """Zero months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=10_000, term_months=0)

    with pytest.raises(InvalidFinancingInput, match="term_months must be one of"):
        uc.execute(req)


def test_rejects_negative_term():
    """Negative months is not an allowed term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=10_000, term_months=-36)

    with pytest.raises(InvalidFinancingInput, match="term_months must be one of"):
        uc.execute(req)


# ============================================================================
# CALCULATION TESTS - VALID TERMS
# ============================================================================


def test_accepts_term_36_months():
    """36 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=20_000, term_months=36)

    plan = uc.execute(req)

    assert plan.term_months == 36
    assert plan.principal == 80_000
    assert plan.monthly_payment > 0


def test_accepts_term_48_months():
    """48 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=20_000, term_months=48)

    plan = uc.execute(req)

    assert plan.term_months == 48
    assert plan.principal == 80_000
    assert plan.monthly_payment > 0


def test_accepts_term_60_months():
    """60 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=20_000, term_months=60)

    plan = uc.execute(req)

    assert plan.term_months == 60
    assert plan.principal == 80_000
    assert plan.monthly_payment > 0


def test_accepts_term_72_months():
    """72 months is a valid term."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=20_000, term_months=72)

    plan = uc.execute(req)

    assert plan.term_months == 72
    assert plan.principal == 80_000
    assert plan.monthly_payment > 0


# ============================================================================
# CALCULATION TESTS - EDGE CASES
# ============================================================================


def test_accepts_zero_down_payment():
    """Zero down payment is valid - finance the entire price."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=0, term_months=36)

    plan = uc.execute(req)

    assert plan.principal == 100_000
    assert plan.monthly_payment > 0
    assert plan.total_paid > plan.principal


def test_small_down_payment():
    """Very small down payment should work correctly."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=100, term_months=36)

    plan = uc.execute(req)

    assert plan.principal == 99_900
    assert plan.monthly_payment > 0


def test_down_payment_just_below_price():
    """Down payment can be very close to price (minimal financing)."""
    uc = CalculateFinancingPlan()
    req = FinancingRequest(price=100_000, down_payment=99_999, term_months=36)

    plan = uc.execute(req)

    assert plan.principal == 1
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
    - r = monthly rate (0.10 / 12 = 0.008333...)
    - n = number of months (36)

    Expected monthly payment ≈ 3,226.72
    """
    uc = CalculateFinancingPlan()  # Uses default 10% annual rate
    req = FinancingRequest(price=100_000, down_payment=0, term_months=36)

    plan = uc.execute(req)

    # Verify principal is correct
    assert plan.principal == 100_000
    assert plan.annual_rate == 0.10
    assert plan.term_months == 36

    # Verify monthly payment (should be ~3,226.72)
    assert 3_226 < plan.monthly_payment < 3_227

    # Verify total paid and interest
    expected_total = plan.monthly_payment * 36
    assert abs(plan.total_paid - expected_total) < 0.01
    assert abs(plan.total_interest - (expected_total - 100_000)) < 0.01


def test_calculates_with_zero_interest_rate():
    """
    When interest rate is 0%, payment should be principal divided by term.

    Special case: The code handles r=0 separately to avoid division by zero.
    """
    uc = CalculateFinancingPlan(annual_rate=0.0)
    req = FinancingRequest(price=120_000, down_payment=20_000, term_months=48)

    plan = uc.execute(req)

    # With 0% interest, monthly payment = principal / months
    expected_payment = 100_000 / 48
    assert abs(plan.monthly_payment - expected_payment) < 0.01

    # Total paid should equal principal (no interest)
    assert abs(plan.total_paid - 100_000) < 0.01
    assert abs(plan.total_interest - 0) < 0.01


def test_calculates_with_custom_interest_rate():
    """
    The use case should accept custom annual interest rates.

    Testing with 15% annual rate (0.15).
    """
    uc = CalculateFinancingPlan(annual_rate=0.15)
    req = FinancingRequest(price=100_000, down_payment=0, term_months=36)

    plan = uc.execute(req)

    assert plan.annual_rate == 0.15
    assert plan.principal == 100_000

    # Higher interest rate means higher monthly payment than 10% rate
    # At 15%, monthly payment ≈ 3,466.91 (vs ~3,226.72 at 10%)
    assert 3_466 < plan.monthly_payment < 3_467

    # Total interest should be positive and significant
    assert plan.total_interest > 24_000  # Over $24k in interest


def test_longer_term_means_lower_monthly_payment():
    """
    For the same principal, longer terms should have lower monthly payments.
    """
    uc = CalculateFinancingPlan()
    req_36 = FinancingRequest(price=100_000, down_payment=0, term_months=36)
    req_72 = FinancingRequest(price=100_000, down_payment=0, term_months=72)

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
    req = FinancingRequest(price=250_000, down_payment=50_000, term_months=60)

    plan = uc.execute(req)

    # Verify the basics
    assert plan.principal == 200_000
    assert plan.term_months == 60
    assert plan.annual_rate == 0.10

    # Monthly payment should be around $4,249.67
    assert 4_249 < plan.monthly_payment < 4_250

    # Total paid over 5 years
    assert 254_900 < plan.total_paid < 255_000

    # Total interest over the life of the loan
    assert 54_900 < plan.total_interest < 55_000
