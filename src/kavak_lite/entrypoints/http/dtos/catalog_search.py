from typing import Optional
from pydantic import BaseModel, Field


class CarResponseDTO(BaseModel):
    id: str
    brand: str
    model: str
    year: int
    price: str


class CatalogSearchQueryDTO(BaseModel):
    # Query params (all optional except pagination defaults)
    brand: Optional[str] = Field(default=None, example="Toyota")
    model: Optional[str] = Field(default=None, example="Corolla")

    year_min: Optional[int] = Field(default=None, example=2015, ge=1900)
    year_max: Optional[int] = Field(default=None, example=2020, ge=1900)

    price_min: Optional[str] = Field(default=None, example="15000.0")
    price_max: Optional[str] = Field(default=None, example="25000.0")

    offset: int = Field(default=0, ge=0, example=0)
    limit: int = Field(default=20, ge=1, le=100, example=100)


class CatalogSearchResponseDTO(BaseModel):
    cars: list[CarResponseDTO]
    total: int
    offset: int
    limit: int
