from fastapi import APIRouter, Depends

from kavak_lite.entrypoints.http.dependencies import get_calculate_financing_plan_use_case
from kavak_lite.entrypoints.http.dtos.financing import (
    FinancingRequestDTO,
    FinancingResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.financing_mapper import FinancingMapper
from kavak_lite.use_cases.calculate_financing_plan import CalculateFinancingPlan


router = APIRouter(tags=["Financing"])


@router.post(
    "/financing/plan",
    response_model=FinancingResponseDTO,
    summary="Calculate financing plan",
    description="""
    Calculate a financing plan for a car purchase.

    ## Monetary Values
    - All monetary values are strings (e.g., "25000.00")
    - Must be valid decimal format with up to 2 decimal places
    - This ensures exact decimal precision (no floating-point errors)

    ## Loan Terms
    - Allowed terms: 36, 48, 60, or 72 months
    - Fixed annual interest rate: 10%

    ## Calculation
    - Principal = price - down_payment
    - Monthly payment calculated using standard amortization formula
    - Total paid = monthly_payment × term_months
    - Total interest = total_paid - principal

    ## Example
    ```
    POST /v1/financing/plan
    {
        "price": "25000.00",
        "down_payment": "5000.00",
        "term_months": 60
    }
    ```
    """,
    responses={
        200: {
            "description": "Successful calculation",
            "content": {
                "application/json": {
                    "example": {
                        "principal": "20000.00",
                        "annual_rate": "0.10",
                        "term_months": 60,
                        "monthly_payment": "424.94",
                        "total_paid": "25496.40",
                        "total_interest": "5496.40",
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_decimal": {
                            "summary": "Invalid decimal format",
                            "value": {
                                "detail": "Validation failed",
                                "code": "VALIDATION_ERROR",
                                "errors": [
                                    {
                                        "field": "price",
                                        "message": "Must be a valid decimal: abc",
                                        "code": "INVALID_DECIMAL",
                                    }
                                ],
                            },
                        },
                        "invalid_term": {
                            "summary": "Invalid term",
                            "value": {
                                "detail": "Validation failed",
                                "code": "VALIDATION_ERROR",
                                "errors": [
                                    {
                                        "field": "term_months",
                                        "message": "Must be one of {36, 48, 60, 72}",
                                        "code": "INVALID_VALUE",
                                    }
                                ],
                            },
                        },
                        "down_payment_too_high": {
                            "summary": "Down payment >= price",
                            "value": {
                                "detail": "Validation failed",
                                "code": "VALIDATION_ERROR",
                                "errors": [
                                    {
                                        "field": "down_payment",
                                        "message": "Must be greater less than price",
                                        "code": "INVALID_VALUE",
                                    }
                                ],
                            },
                        },
                    }
                }
            },
        },
    },
)
def calculate_financing_plan(
    payload: FinancingRequestDTO,
    use_case: CalculateFinancingPlan = Depends(get_calculate_financing_plan_use_case),
) -> FinancingResponseDTO:
    """
    Calculate financing plan endpoint.

    Follows the parse → execute → map → return pattern:
    1. Parse: FastAPI + Pydantic handle request parsing
    2. Map: Convert DTO to domain request
    3. Execute: Call use case (which validates domain rules)
    4. Map: Convert domain result to response DTO
    5. Return: FastAPI serializes response
    """
    # 1. Map to domain request (string → Decimal)
    request = FinancingMapper.to_domain_request(payload)

    # 2. Execute use case (validates and calculates)
    plan = use_case.execute(request)

    # 3. Map to response (Decimal → string)
    return FinancingMapper.to_response(plan)
