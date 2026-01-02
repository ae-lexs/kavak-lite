from pydantic import BaseModel, ConfigDict, Field


class FinancingRequestDTO(BaseModel):
    """Request payload for calculating financing plan."""

    price: str = Field(
        description="Car price as decimal string",
        examples=["25000.00"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )
    down_payment: str = Field(
        description="Down payment amount as decimal string",
        examples=["5000.00"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )
    term_months: int = Field(
        description="Loan term in months. Must be one of: 36, 48, 60, 72",
        examples=[60],
        ge=1,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": "25000.00",
                "down_payment": "5000.00",
                "term_months": 60,
            }
        }
    )


class FinancingResponseDTO(BaseModel):
    """Response with calculated financing plan."""

    principal: str = Field(
        description="Principal amount (price - down_payment) as decimal string",
        examples=["20000.00"],
    )
    annual_rate: str = Field(
        description="Annual interest rate as decimal string (e.g., '0.10' = 10%)",
        examples=["0.10"],
    )
    term_months: int = Field(
        description="Loan term in months",
        examples=[60],
    )
    monthly_payment: str = Field(
        description="Monthly payment amount as decimal string",
        examples=["424.94"],
    )
    total_paid: str = Field(
        description="Total amount paid over loan term as decimal string",
        examples=["25496.40"],
    )
    total_interest: str = Field(
        description="Total interest paid as decimal string",
        examples=["5496.40"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "principal": "20000.00",
                "annual_rate": "0.10",
                "term_months": 60,
                "monthly_payment": "424.94",
                "total_paid": "25496.40",
                "total_interest": "5496.40",
            }
        }
    )
