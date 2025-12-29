from typing import Optional
from pydantic import BaseModel, Field


class CarResponseDTO(BaseModel):
    id: str
    brand: str
    model: str
    year: int
    price: str


class CarSearchQueryDTO(BaseModel):
    # Query params (all optional except pagination defaults)
    brand: Optional[str] = Field(default=None, examples=["Toyota"])
    model: Optional[str] = Field(default=None, examples=["Corolla"])

    year_min: Optional[int] = Field(default=None, examples=[2015], ge=1900)
    year_max: Optional[int] = Field(default=None, examples=[2020], ge=1900)

    price_min: Optional[str] = Field(default=None, examples=["15000.0"])
    price_max: Optional[str] = Field(default=None, examples=["25000.0"])

    offset: int = Field(default=0, ge=0, examples=[0])
    limit: int = Field(default=20, ge=1, le=100, examples=[100])


class CatalogSearchResponseDTO(BaseModel):
    cars: list[CarResponseDTO]
    total: int
    offset: int
    limit: int
