from __future__ import annotations

from decimal import Decimal, InvalidOperation

from kavak_lite.domain.errors import ValidationError
from kavak_lite.domain.financing import FinancingPlan, FinancingRequest
from kavak_lite.entrypoints.http.dtos.financing import (
    FinancingRequestDTO,
    FinancingResponseDTO,
)


class FinancingMapper:
    """Maps between REST DTOs and domain models for financing."""

    @staticmethod
    def to_domain_request(dto: FinancingRequestDTO) -> FinancingRequest:
        """
        Converts request DTO to domain FinancingRequest.

        Handles string → Decimal conversion at the boundary.

        Args:
            dto: Request DTO with string monetary values

        Returns:
            FinancingRequest with Decimal monetary values

        Raises:
            ValidationError: If string values cannot be converted to valid Decimals
        """
        errors = []

        # Convert price
        try:
            price = Decimal(dto.price)
        except (InvalidOperation, ValueError):
            errors.append(
                {
                    "field": "price",
                    "message": f"Must be a valid decimal: {dto.price}",
                    "code": "INVALID_DECIMAL",
                }
            )
            price = Decimal("0")  # Placeholder to continue validation

        # Convert down_payment
        try:
            down_payment = Decimal(dto.down_payment)
        except (InvalidOperation, ValueError):
            errors.append(
                {
                    "field": "down_payment",
                    "message": f"Must be a valid decimal: {dto.down_payment}",
                    "code": "INVALID_DECIMAL",
                }
            )
            down_payment = Decimal("0")  # Placeholder to continue validation

        if errors:
            raise ValidationError(errors=errors)

        return FinancingRequest(
            price=price,
            down_payment=down_payment,
            term_months=dto.term_months,
        )

    @staticmethod
    def to_response(plan: FinancingPlan) -> FinancingResponseDTO:
        """
        Converts domain FinancingPlan to response DTO.

        Handles Decimal → string conversion at the boundary.

        Args:
            plan: Domain financing plan with Decimal values

        Returns:
            Response DTO with string monetary values
        """
        return FinancingResponseDTO(
            principal=str(plan.principal),
            annual_rate=str(plan.annual_rate),
            term_months=plan.term_months,
            monthly_payment=str(plan.monthly_payment),
            total_paid=str(plan.total_paid),
            total_interest=str(plan.total_interest),
        )
