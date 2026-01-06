from pydantic import BaseModel, ConfigDict, Field


class CarResponseDTO(BaseModel):
    id: str
    brand: str
    model: str
    year: int
    price: str
    trim: str | None = Field(None, description="Vehicle trim level")
    mileage_km: int | None = Field(None, description="Mileage in kilometers")
    transmission: str | None = Field(
        None, description="Transmission type", examples=["Automático", "Manual", "CVT"]
    )
    fuel_type: str | None = Field(
        None, description="Fuel type", examples=["Gasolina", "Diésel", "Híbrido", "Eléctrico"]
    )
    body_type: str | None = Field(
        None, description="Body type", examples=["Sedán", "SUV", "Hatchback", "Pick-up"]
    )
    location: str | None = Field(
        None, description="Car location", examples=["CDMX", "Guadalajara", "Monterrey"]
    )
    url: str | None = Field(None, description="URL to car details page")


class CarsSearchQueryDTO(BaseModel):
    """Query parameters for searching cars in the catalog."""

    brand: str | None = Field(
        default=None,
        description="Filter by car brand (case-insensitive exact match)",
        examples=["Toyota"],
    )
    model: str | None = Field(
        default=None,
        description="Filter by car model (case-insensitive exact match)",
        examples=["Camry"],
    )
    year_min: int | None = Field(
        default=None,
        description="Minimum year (inclusive)",
        examples=[2018],
        ge=1900,
    )
    year_max: int | None = Field(
        default=None,
        description="Maximum year (inclusive)",
        examples=[2023],
        ge=1900,
    )
    price_min: str | None = Field(
        default=None,
        description="Minimum price (inclusive, decimal as string)",
        examples=["20000.00"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )
    price_max: str | None = Field(
        default=None,
        description="Maximum price (inclusive, decimal as string)",
        examples=["35000.00"],
        pattern=r"^\d+(\.\d{1,2})?$",
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip",
        examples=[0],
        ge=0,
    )
    limit: int = Field(
        default=20,
        description="Maximum number of results to return",
        examples=[20],
        ge=1,
        le=200,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "brand": "Toyota",
                "model": "Camry",
                "year_min": 2018,
                "year_max": 2023,
                "price_min": "20000.00",
                "price_max": "35000.00",
                "offset": 0,
                "limit": 20,
            }
        }
    )


class CatalogSearchResponseDTO(BaseModel):
    cars: list[CarResponseDTO]
    total: int
    offset: int
    limit: int
