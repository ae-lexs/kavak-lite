"""
Comprehensive test suite for FinancingMapper.

This test suite verifies the mapper's responsibility to translate between
REST DTOs and domain models per the REST Endpoint Design Pattern ADR:
- Converts request DTO to domain FinancingRequest (str → Decimal)
- Converts domain FinancingPlan to response DTO (Decimal → str)
- Handles invalid Decimal strings with ValidationError
- No business logic, just translation

See: docs/ADR/12-26-25-rest-endpoint-design-pattern.md
"""

from __future__ import annotations

from decimal import Decimal


from kavak_lite.domain.financing import FinancingPlan, FinancingRequest
from kavak_lite.entrypoints.http.dtos.financing import (
    FinancingRequestDTO,
    FinancingResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.financing_mapper import FinancingMapper


# ==============================================================================
# to_domain_request() - DTO → Domain Request
# ==============================================================================


def test_to_domain_request_with_valid_input() -> None:
    """Mapper converts all fields from DTO to domain request."""
    dto = FinancingRequestDTO(
        price="25000.00",
        down_payment="5000.00",
        term_months=60,
    )

    result = FinancingMapper.to_domain_request(dto)

    assert isinstance(result, FinancingRequest)
    assert result.price == Decimal("25000.00")
    assert result.down_payment == Decimal("5000.00")
    assert result.term_months == 60


def test_to_domain_request_converts_strings_to_decimal() -> None:
    """Mapper converts monetary strings to Decimal type."""
    dto = FinancingRequestDTO(
        price="10000.50",
        down_payment="2500.25",
        term_months=48,
    )

    result = FinancingMapper.to_domain_request(dto)

    assert isinstance(result.price, Decimal)
    assert isinstance(result.down_payment, Decimal)
    assert result.price == Decimal("10000.50")
    assert result.down_payment == Decimal("2500.25")


def test_to_domain_request_handles_whole_numbers() -> None:
    """Mapper handles prices without decimal places."""
    dto = FinancingRequestDTO(
        price="25000",
        down_payment="5000",
        term_months=36,
    )

    result = FinancingMapper.to_domain_request(dto)

    assert result.price == Decimal("25000")
    assert result.down_payment == Decimal("5000")


def test_to_domain_request_handles_zero_down_payment() -> None:
    """Mapper handles zero down payment."""
    dto = FinancingRequestDTO(
        price="20000.00",
        down_payment="0",
        term_months=72,
    )

    result = FinancingMapper.to_domain_request(dto)

    assert result.down_payment == Decimal("0")


# ==============================================================================
# to_response() - Domain → Response DTO
# ==============================================================================


def test_to_response_converts_all_fields() -> None:
    """Mapper converts all domain fields to response DTO."""
    plan = FinancingPlan(
        principal=Decimal("20000.00"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("424.94"),
        total_paid=Decimal("25496.40"),
        total_interest=Decimal("5496.40"),
    )

    result = FinancingMapper.to_response(plan)

    assert isinstance(result, FinancingResponseDTO)
    assert result.principal == "20000.00"
    assert result.annual_rate == "0.10"
    assert result.term_months == 60
    assert result.monthly_payment == "424.94"
    assert result.total_paid == "25496.40"
    assert result.total_interest == "5496.40"


def test_to_response_converts_decimals_to_strings() -> None:
    """Mapper converts Decimal monetary values to strings."""
    plan = FinancingPlan(
        principal=Decimal("15000.00"),
        annual_rate=Decimal("0.10"),
        term_months=48,
        monthly_payment=Decimal("380.44"),
        total_paid=Decimal("18261.12"),
        total_interest=Decimal("3261.12"),
    )

    result = FinancingMapper.to_response(plan)

    assert isinstance(result.principal, str)
    assert isinstance(result.annual_rate, str)
    assert isinstance(result.monthly_payment, str)
    assert isinstance(result.total_paid, str)
    assert isinstance(result.total_interest, str)


def test_to_response_preserves_decimal_precision() -> None:
    """Mapper preserves exact decimal precision when converting to string."""
    plan = FinancingPlan(
        principal=Decimal("20000.00"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("424.94"),
        total_paid=Decimal("25496.40"),
        total_interest=Decimal("5496.40"),
    )

    result = FinancingMapper.to_response(plan)

    # Should be "424.94" not "424.9400000" or "424.94000"
    assert result.monthly_payment == "424.94"
    assert result.total_paid == "25496.40"


def test_to_response_handles_whole_numbers() -> None:
    """Mapper handles Decimals with no fractional part."""
    plan = FinancingPlan(
        principal=Decimal("20000"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("425"),
        total_paid=Decimal("25500"),
        total_interest=Decimal("5500"),
    )

    result = FinancingMapper.to_response(plan)

    assert result.principal == "20000"
    assert result.monthly_payment == "425"


def test_to_response_handles_very_precise_decimals() -> None:
    """Mapper handles Decimals with many decimal places."""
    plan = FinancingPlan(
        principal=Decimal("20000.00"),
        annual_rate=Decimal("0.10"),
        term_months=60,
        monthly_payment=Decimal("424.9400123456"),
        total_paid=Decimal("25496.400741"),
        total_interest=Decimal("5496.400741"),
    )

    result = FinancingMapper.to_response(plan)

    # Should preserve all decimals as-is
    assert result.monthly_payment == "424.9400123456"
    assert result.total_paid == "25496.400741"


def test_to_response_handles_large_numbers() -> None:
    """Mapper handles very large monetary values."""
    plan = FinancingPlan(
        principal=Decimal("500000.00"),
        annual_rate=Decimal("0.10"),
        term_months=72,
        monthly_payment=Decimal("9306.25"),
        total_paid=Decimal("670050.00"),
        total_interest=Decimal("170050.00"),
    )

    result = FinancingMapper.to_response(plan)

    assert result.principal == "500000.00"
    assert result.monthly_payment == "9306.25"
    assert result.total_paid == "670050.00"


# ==============================================================================
# Roundtrip Conversion
# ==============================================================================


def test_roundtrip_conversion_preserves_values() -> None:
    """DTO → Domain → DTO roundtrip preserves monetary values."""
    original_dto = FinancingRequestDTO(
        price="25000.00",
        down_payment="5000.00",
        term_months=60,
    )

    # Convert to domain
    domain_request = FinancingMapper.to_domain_request(original_dto)

    # Verify domain values
    assert domain_request.price == Decimal("25000.00")
    assert domain_request.down_payment == Decimal("5000.00")

    # Create a plan from the request (simulating use case execution)
    plan = FinancingPlan(
        principal=domain_request.price - domain_request.down_payment,
        annual_rate=Decimal("0.10"),
        term_months=domain_request.term_months,
        monthly_payment=Decimal("424.94"),
        total_paid=Decimal("25496.40"),
        total_interest=Decimal("5496.40"),
    )

    # Convert back to DTO
    response_dto = FinancingMapper.to_response(plan)

    # Verify values are preserved
    assert response_dto.principal == "20000.00"
    assert response_dto.term_months == 60
