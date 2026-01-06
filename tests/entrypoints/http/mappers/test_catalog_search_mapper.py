"""
Comprehensive test suite for CatalogSearchMapper.

This test suite verifies the mapper's responsibility to translate between
REST DTOs and domain models per the REST Endpoint Design Pattern ADR:
- Converts query params to domain filters (handles Decimal conversion)
- Converts pagination params to domain paging
- Converts domain entities to REST response DTOs
- Handles Decimal ↔ str conversion at the boundary
- No business logic, just translation

See: docs/ADR/12-26-25-rest-endpoint-design-pattern.md
"""

from __future__ import annotations

from decimal import Decimal

from kavak_lite.domain.car import Car, CatalogFilters, Paging
from kavak_lite.entrypoints.http.dtos.catalog_search import (
    CarResponseDTO,
    CarsSearchQueryDTO,
    CatalogSearchResponseDTO,
)
from kavak_lite.entrypoints.http.mappers.catalog_search_mapper import CatalogSearchMapper
from kavak_lite.use_cases.search_car_catalog import (
    SearchCarCatalogRequest,
    SearchCarCatalogResponse,
)


# ==============================================================================
# to_domain_filters() - DTO → Domain Filters
# ==============================================================================


def test_to_domain_filters_with_all_fields() -> None:
    """Mapper converts all filter fields from DTO to domain."""
    dto = CarsSearchQueryDTO(
        brand="Toyota",
        model="Camry",
        year_min=2018,
        year_max=2023,
        price_min="20000.00",
        price_max="35000.00",
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert isinstance(result, CatalogFilters)
    assert result.make == "Toyota"  # DTO 'brand' → domain 'make'
    assert result.model == "Camry"
    assert result.year_min == 2018
    assert result.year_max == 2023
    assert result.price_min == Decimal("20000.00")  # str → Decimal
    assert result.price_max == Decimal("35000.00")  # str → Decimal


def test_to_domain_filters_with_no_filters() -> None:
    """Mapper handles empty filters (all None)."""
    dto = CarsSearchQueryDTO(
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert isinstance(result, CatalogFilters)
    assert result.make is None
    assert result.model is None
    assert result.year_min is None
    assert result.year_max is None
    assert result.price_min is None
    assert result.price_max is None


def test_to_domain_filters_converts_brand_to_make() -> None:
    """Mapper translates DTO 'brand' to domain 'make'."""
    dto = CarsSearchQueryDTO(
        brand="Honda",
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert result.make == "Honda"


def test_to_domain_filters_converts_price_strings_to_decimal() -> None:
    """Mapper converts price strings to Decimal at the boundary."""
    dto = CarsSearchQueryDTO(
        price_min="15000.50",
        price_max="45000.99",
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    # Verify Decimal conversion
    assert isinstance(result.price_min, Decimal)
    assert isinstance(result.price_max, Decimal)
    assert result.price_min == Decimal("15000.50")
    assert result.price_max == Decimal("45000.99")


def test_to_domain_filters_handles_none_prices() -> None:
    """Mapper handles None prices without conversion."""
    dto = CarsSearchQueryDTO(
        price_min=None,
        price_max=None,
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert result.price_min is None
    assert result.price_max is None


def test_to_domain_filters_preserves_year_values() -> None:
    """Mapper passes year values through unchanged."""
    dto = CarsSearchQueryDTO(
        year_min=2015,
        year_max=2020,
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert result.year_min == 2015
    assert result.year_max == 2020


def test_to_domain_filters_handles_partial_filters() -> None:
    """Mapper works with only some filters populated."""
    dto = CarsSearchQueryDTO(
        brand="Ford",
        year_min=2019,
        # model, year_max, prices not set
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_filters(dto)

    assert result.make == "Ford"
    assert result.year_min == 2019
    assert result.model is None
    assert result.year_max is None
    assert result.price_min is None
    assert result.price_max is None


# ==============================================================================
# to_domain_paging() - DTO → Domain Paging
# ==============================================================================


def test_to_domain_paging_with_default_values() -> None:
    """Mapper converts default pagination values."""
    dto = CarsSearchQueryDTO(
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_paging(dto)

    assert isinstance(result, Paging)
    assert result.offset == 0
    assert result.limit == 20


def test_to_domain_paging_with_custom_values() -> None:
    """Mapper converts custom pagination values."""
    dto = CarsSearchQueryDTO(
        offset=100,
        limit=50,
    )

    result = CatalogSearchMapper.to_domain_paging(dto)

    assert result.offset == 100
    assert result.limit == 50


def test_to_domain_paging_with_max_limit() -> None:
    """Mapper handles maximum allowed limit."""
    dto = CarsSearchQueryDTO(
        offset=0,
        limit=200,
    )

    result = CatalogSearchMapper.to_domain_paging(dto)

    assert result.limit == 200


def test_to_domain_paging_with_min_limit() -> None:
    """Mapper handles minimum allowed limit."""
    dto = CarsSearchQueryDTO(
        offset=0,
        limit=1,
    )

    result = CatalogSearchMapper.to_domain_paging(dto)

    assert result.limit == 1


# ==============================================================================
# to_domain_request() - DTO → Complete Domain Request
# ==============================================================================


def test_to_domain_request_builds_complete_request() -> None:
    """Mapper convenience method builds complete domain request."""
    dto = CarsSearchQueryDTO(
        brand="Toyota",
        model="Corolla",
        year_min=2018,
        year_max=2023,
        price_min="20000.00",
        price_max="35000.00",
        offset=10,
        limit=50,
    )

    result = CatalogSearchMapper.to_domain_request(dto)

    # Verify request structure
    assert isinstance(result, SearchCarCatalogRequest)
    assert isinstance(result.filters, CatalogFilters)
    assert isinstance(result.paging, Paging)

    # Verify filters
    assert result.filters.make == "Toyota"
    assert result.filters.model == "Corolla"
    assert result.filters.year_min == 2018
    assert result.filters.year_max == 2023
    assert result.filters.price_min == Decimal("20000.00")
    assert result.filters.price_max == Decimal("35000.00")

    # Verify paging
    assert result.paging.offset == 10
    assert result.paging.limit == 50


def test_to_domain_request_with_minimal_data() -> None:
    """Mapper handles minimal request (only pagination)."""
    dto = CarsSearchQueryDTO(
        offset=0,
        limit=20,
    )

    result = CatalogSearchMapper.to_domain_request(dto)

    assert isinstance(result, SearchCarCatalogRequest)
    assert result.filters.make is None
    assert result.filters.model is None
    assert result.paging.offset == 0
    assert result.paging.limit == 20


# ==============================================================================
# to_car_response() - Domain Car → Response DTO
# ==============================================================================


def test_to_car_response_converts_all_fields() -> None:
    """Mapper converts domain Car to response DTO."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Camry",
        year=2020,
        price=Decimal("25000.00"),
    )

    result = CatalogSearchMapper.to_car_response(car)

    assert isinstance(result, CarResponseDTO)
    assert result.id == "550e8400-e29b-41d4-a716-446655440000"
    assert result.brand == "Toyota"  # Domain 'make' → DTO 'brand'
    assert result.model == "Camry"
    assert result.year == 2020
    assert result.price == "25000.00"  # Decimal → str


def test_to_car_response_converts_make_to_brand() -> None:
    """Mapper translates domain 'make' to DTO 'brand'."""
    car = Car(
        id="1",
        make="Honda",
        model="Civic",
        year=2021,
        price=Decimal("30000.00"),
    )

    result = CatalogSearchMapper.to_car_response(car)

    assert result.brand == "Honda"


def test_to_car_response_converts_decimal_to_string() -> None:
    """Mapper converts Decimal price to string at the boundary."""
    car = Car(
        id="1",
        make="Ford",
        model="F-150",
        year=2022,
        price=Decimal("45000.99"),
    )

    result = CatalogSearchMapper.to_car_response(car)

    # Verify string conversion
    assert isinstance(result.price, str)
    assert result.price == "45000.99"


def test_to_car_response_preserves_decimal_precision() -> None:
    """Mapper preserves decimal precision when converting to string."""
    car = Car(
        id="1",
        make="Tesla",
        model="Model 3",
        year=2023,
        price=Decimal("49999.50"),
    )

    result = CatalogSearchMapper.to_car_response(car)

    assert result.price == "49999.50"  # Two decimal places preserved


def test_to_car_response_handles_whole_numbers() -> None:
    """Mapper handles whole number prices correctly."""
    car = Car(
        id="1",
        make="Chevrolet",
        model="Silverado",
        year=2021,
        price=Decimal("40000.00"),
    )

    result = CatalogSearchMapper.to_car_response(car)

    # String representation may vary, but should be parseable back to Decimal
    assert result.price in ["40000.00", "40000"]
    assert Decimal(result.price) == Decimal("40000.00")


def test_to_car_response_maps_all_fields_with_extended_car() -> None:
    """Mapper converts all fields from extended Car entity."""
    car = Car(
        id="550e8400-e29b-41d4-a716-446655440000",
        make="Toyota",
        model="Corolla",
        year=2020,
        price=Decimal("25000.00"),
        trim="XLE",
        mileage_km=50000,
        transmission="Automático",
        fuel_type="Gasolina",
        body_type="Sedán",
        location="CDMX",
        url="https://kavak.com/mx/toyota/corolla/2020",
    )

    result = CatalogSearchMapper.to_car_response(car)

    assert isinstance(result, CarResponseDTO)
    assert result.id == "550e8400-e29b-41d4-a716-446655440000"
    assert result.brand == "Toyota"
    assert result.model == "Corolla"
    assert result.year == 2020
    assert result.price == "25000.00"
    assert result.trim == "XLE"
    assert result.mileage_km == 50000
    assert result.transmission == "Automático"
    assert result.fuel_type == "Gasolina"
    assert result.body_type == "Sedán"
    assert result.location == "CDMX"
    assert result.url == "https://kavak.com/mx/toyota/corolla/2020"


def test_to_car_response_handles_optional_fields_none() -> None:
    """Mapper handles None values for optional fields."""
    car = Car(
        id="1",
        make="Honda",
        model="Civic",
        year=2021,
        price=Decimal("30000.00"),
        # All optional fields as None (default)
    )

    result = CatalogSearchMapper.to_car_response(car)

    assert isinstance(result, CarResponseDTO)
    assert result.id == "1"
    assert result.brand == "Honda"
    assert result.model == "Civic"
    assert result.year == 2021
    assert result.price == "30000.00"
    assert result.trim is None
    assert result.mileage_km is None
    assert result.transmission is None
    assert result.fuel_type is None
    assert result.body_type is None
    assert result.location is None
    assert result.url is None


# ==============================================================================
# to_response() - Domain Result → Response DTO with Pagination
# ==============================================================================


def test_to_response_converts_complete_result() -> None:
    """Mapper converts domain result to response DTO with pagination metadata."""
    cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.00")),
        Car(id="2", make="Honda", model="Civic", year=2021, price=Decimal("30000.00")),
    ]
    domain_result = SearchCarCatalogResponse(
        cars=cars,
        total_count=42,
    )

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    assert isinstance(result, CatalogSearchResponseDTO)
    assert len(result.cars) == 2
    assert result.total == 42
    assert result.offset == 0
    assert result.limit == 20


def test_to_response_converts_cars_to_dtos() -> None:
    """Mapper converts each car entity to CarResponseDTO."""
    cars = [
        Car(id="1", make="Toyota", model="Camry", year=2020, price=Decimal("25000.00")),
    ]
    domain_result = SearchCarCatalogResponse(cars=cars, total_count=1)

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    # Verify car conversion
    assert len(result.cars) == 1
    assert isinstance(result.cars[0], CarResponseDTO)
    assert result.cars[0].id == "1"
    assert result.cars[0].brand == "Toyota"
    assert result.cars[0].model == "Camry"
    assert result.cars[0].year == 2020
    assert result.cars[0].price == "25000.00"


def test_to_response_handles_empty_results() -> None:
    """Mapper handles empty result list."""
    domain_result = SearchCarCatalogResponse(
        cars=[],
        total_count=0,
    )

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    assert result.cars == []
    assert result.total == 0
    assert result.offset == 0
    assert result.limit == 20


def test_to_response_handles_none_total_count() -> None:
    """Mapper handles None total_count (repository may not calculate it)."""
    cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.00")),
    ]
    domain_result = SearchCarCatalogResponse(
        cars=cars,
        total_count=None,
    )

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    assert result.total == 0  # Mapper handles None by converting to 0
    assert len(result.cars) == 1


def test_to_response_echoes_pagination_metadata() -> None:
    """Mapper includes pagination metadata in response (echoed from request)."""
    cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.00")),
    ]
    domain_result = SearchCarCatalogResponse(cars=cars, total_count=100)

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=50,
        limit=10,
    )

    # Pagination metadata should be echoed
    assert result.offset == 50
    assert result.limit == 10


def test_to_response_with_multiple_cars() -> None:
    """Mapper converts multiple cars correctly."""
    cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.00")),
        Car(id="2", make="Honda", model="Civic", year=2021, price=Decimal("30000.00")),
        Car(id="3", make="Ford", model="F-150", year=2022, price=Decimal("45000.00")),
    ]
    domain_result = SearchCarCatalogResponse(cars=cars, total_count=3)

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    assert len(result.cars) == 3
    assert result.cars[0].brand == "Toyota"
    assert result.cars[1].brand == "Honda"
    assert result.cars[2].brand == "Ford"
    assert all(isinstance(car, CarResponseDTO) for car in result.cars)


def test_to_response_preserves_decimal_precision_in_all_cars() -> None:
    """Mapper preserves decimal precision for all cars in the response."""
    cars = [
        Car(id="1", make="Toyota", model="Corolla", year=2020, price=Decimal("25000.50")),
        Car(id="2", make="Honda", model="Civic", year=2021, price=Decimal("30000.99")),
    ]
    domain_result = SearchCarCatalogResponse(cars=cars, total_count=2)

    result = CatalogSearchMapper.to_response(
        result=domain_result,
        offset=0,
        limit=20,
    )

    # Verify decimal precision preserved in string conversion
    assert result.cars[0].price == "25000.50"
    assert result.cars[1].price == "30000.99"


# ==============================================================================
# Edge Cases and Data Integrity
# ==============================================================================


def test_mapper_does_not_modify_input_dto() -> None:
    """Mapper does not mutate input DTO (pure function)."""
    dto = CarsSearchQueryDTO(
        brand="Toyota",
        price_min="20000.00",
        offset=0,
        limit=20,
    )

    # Store original values
    original_brand = dto.brand
    original_price_min = dto.price_min

    # Call mapper
    CatalogSearchMapper.to_domain_filters(dto)

    # Verify DTO unchanged
    assert dto.brand == original_brand
    assert dto.price_min == original_price_min


def test_mapper_does_not_modify_domain_car() -> None:
    """Mapper does not mutate domain Car entity (pure function)."""
    car = Car(
        id="1",
        make="Toyota",
        model="Camry",
        year=2020,
        price=Decimal("25000.00"),
    )

    # Store original values
    original_make = car.make
    original_price = car.price

    # Call mapper
    CatalogSearchMapper.to_car_response(car)

    # Verify Car unchanged
    assert car.make == original_make
    assert car.price == original_price


def test_decimal_roundtrip_conversion() -> None:
    """Mapper preserves exact decimal values through DTO → Domain → DTO."""
    # Start with DTO
    dto = CarsSearchQueryDTO(
        price_min="12345.67",
        price_max="98765.43",
        offset=0,
        limit=20,
    )

    # Convert to domain
    filters = CatalogSearchMapper.to_domain_filters(dto)

    # Create a car with same prices
    car = Car(
        id="1",
        make="Test",
        model="Car",
        year=2020,
        price=filters.price_min,  # type: ignore - we know it's not None
    )

    # Convert back to DTO
    response_dto = CatalogSearchMapper.to_car_response(car)

    # Verify roundtrip preservation
    assert response_dto.price == "12345.67"
    assert Decimal(response_dto.price) == Decimal("12345.67")
