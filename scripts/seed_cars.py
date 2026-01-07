#!/usr/bin/env python3
"""
Seed the cars table with deterministic random data.

Features:
- Deterministic: fixed seed → same dataset every run
- Idempotent: safe to run multiple times (clears before seeding)
- Realism-lite: prices correlated with year + make band

Usage:
    python scripts/seed_cars.py
    # or via Docker:
    docker compose run --rm api uv run python scripts/seed_cars.py
"""

from __future__ import annotations

import random
import sys
from decimal import Decimal
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kavak_lite.infra.db.models.car import CarRow
from kavak_lite.infra.db.session import get_session


# ==============================================================================
# Configuration
# ==============================================================================

RANDOM_SEED = 42  # Fixed seed for deterministic results
NUM_CARS = 50  # Number of cars to generate


# ==============================================================================
# Mexican Market Car Data
# ==============================================================================

# Make categories with price bands (base prices in MXN)
MAKES = {
    # Economy brands (base: 150k-250k)
    "economy": {
        "makes": ["Nissan", "Chevrolet", "Kia", "Hyundai", "SEAT"],
        "base_price_min": Decimal("150000"),
        "base_price_max": Decimal("250000"),
    },
    # Mid-range brands (base: 250k-450k)
    "mid_range": {
        "makes": ["Toyota", "Honda", "Mazda", "Volkswagen", "Ford"],
        "base_price_min": Decimal("250000"),
        "base_price_max": Decimal("450000"),
    },
    # Premium brands (base: 450k-800k)
    "premium": {
        "makes": ["BMW", "Mercedes-Benz", "Audi", "Volvo", "Jeep"],
        "base_price_min": Decimal("450000"),
        "base_price_max": Decimal("800000"),
    },
}

# Popular models by make in Mexico
MODELS_BY_MAKE = {
    # Economy
    "Nissan": ["Versa", "Sentra", "Kicks", "X-Trail", "March"],
    "Chevrolet": ["Aveo", "Onix", "Cavalier", "Tracker", "Equinox"],
    "Kia": ["Rio", "Forte", "Seltos", "Sportage", "Soul"],
    "Hyundai": ["Accent", "Elantra", "Creta", "Tucson", "Venue"],
    "SEAT": ["Ibiza", "León", "Arona", "Ateca", "Toledo"],
    # Mid-range
    "Toyota": ["Corolla", "Camry", "RAV4", "Hilux", "Yaris"],
    "Honda": ["Civic", "Accord", "CR-V", "HR-V", "Fit"],
    "Mazda": ["Mazda3", "Mazda6", "CX-3", "CX-5", "CX-30"],
    "Volkswagen": ["Jetta", "Tiguan", "Taos", "Vento", "Golf"],
    "Ford": ["Focus", "Fusion", "Escape", "Explorer", "Mustang"],
    # Premium
    "BMW": ["Serie 3", "Serie 5", "X1", "X3", "X5"],
    "Mercedes-Benz": ["Clase A", "Clase C", "GLA", "GLC", "GLB"],
    "Audi": ["A3", "A4", "Q3", "Q5", "Q7"],
    "Volvo": ["S60", "S90", "XC40", "XC60", "XC90"],
    "Jeep": ["Compass", "Renegade", "Wrangler", "Grand Cherokee", "Cherokee"],
}

# Transmissions
TRANSMISSIONS = ["Manual", "Automático", "CVT"]

# Fuel types
FUEL_TYPES = ["Gasolina", "Diésel", "Híbrido", "Eléctrico"]

# Body types
BODY_TYPES = ["Sedán", "SUV", "Hatchback", "Pick-up", "Coupé"]

# Mexican cities/locations
LOCATIONS = [
    "CDMX",
    "Guadalajara",
    "Monterrey",
    "Puebla",
    "Querétaro",
    "Cancún",
    "Mérida",
    "Tijuana",
    "León",
    "Toluca",
]


# ==============================================================================
# Price Calculation with Realism
# ==============================================================================


def calculate_price(make: str, year: int) -> Decimal:
    """
    Calculate price based on make category and year.

    Logic:
    - Newer cars are more expensive
    - Premium brands cost more than economy
    - Price depreciates ~10% per year from base price
    """
    # Find make category
    category = None
    for cat_name, cat_data in MAKES.items():
        if make in cat_data["makes"]:
            category = cat_data
            break

    if not category:
        # Fallback to mid-range if make not found
        category = MAKES["mid_range"]

    # Get base price range for this category
    base_min = category["base_price_min"]
    base_max = category["base_price_max"]

    # Random base price within category range
    base_price = Decimal(random.randint(int(base_min), int(base_max)))

    # Calculate years old (assuming current year is 2024)
    current_year = 2024
    years_old = max(0, current_year - year)

    # Depreciation: ~10% per year, capped at 70% total depreciation
    depreciation_rate = Decimal("0.10")
    max_depreciation = Decimal("0.70")

    total_depreciation = min(depreciation_rate * years_old, max_depreciation)
    depreciated_price = base_price * (Decimal("1") - total_depreciation)

    # Add some randomness (+/- 10%)
    variance = Decimal(str(random.uniform(0.90, 1.10)))
    final_price = depreciated_price * variance

    # Round to nearest 1000
    final_price = (final_price / 1000).quantize(Decimal("1")) * 1000

    # Ensure minimum price of 50k
    return max(final_price, Decimal("50000"))


# ==============================================================================
# Seed Generation
# ==============================================================================


def generate_car() -> CarRow:
    """Generate a single random car with realistic data."""
    # Pick a random category, then make, then model
    category = random.choice(list(MAKES.keys()))
    make = random.choice(MAKES[category]["makes"])
    model = random.choice(MODELS_BY_MAKE[make])

    # Year: 2015-2024 (weighted toward newer)
    year = random.choices(
        range(2015, 2025),
        weights=[1, 1, 2, 2, 3, 3, 4, 5, 6, 7],  # Favor newer years
        k=1,
    )[0]

    # Price based on make and year
    price = calculate_price(make, year)

    # Mileage: correlated with age
    # Newer cars: 0-50k km, older cars: up to 200k km
    current_year = 2024
    years_old = current_year - year
    max_mileage = min(200000, years_old * 20000 + random.randint(0, 30000))
    mileage = random.randint(0, max(1000, max_mileage))

    # Transmission: weighted toward automatic in newer/premium cars
    if year >= 2020 or category == "premium":
        transmission = random.choices(
            TRANSMISSIONS,
            weights=[1, 5, 2],  # Favor automatic
            k=1,
        )[0]
    else:
        transmission = random.choices(
            TRANSMISSIONS,
            weights=[3, 4, 1],  # More balanced
            k=1,
        )[0]

    # Fuel type: weighted toward gasoline, some electric in newer cars
    if year >= 2022:
        fuel_type = random.choices(
            FUEL_TYPES,
            weights=[5, 1, 2, 1],  # Some hybrids/electric in newer cars
            k=1,
        )[0]
    else:
        fuel_type = random.choices(
            FUEL_TYPES,
            weights=[7, 2, 1, 0],  # Mostly gas/diesel
            k=1,
        )[0]

    # Body type: depends on model name
    body_type = "Sedán"  # Default
    if any(suv in model for suv in ["X-", "CR-V", "CX-", "RAV", "Tiguan", "Q", "XC"]):
        body_type = "SUV"
    elif any(h in model for h in ["Fit", "Golf", "Ibiza"]):
        body_type = "Hatchback"
    elif "Hilux" in model:
        body_type = "Pick-up"
    elif "Mustang" in model or "Coupé" in model:
        body_type = "Coupé"

    # Location
    location = random.choice(LOCATIONS)

    # Build URL (example format)
    url = f"https://kavak-lite.com/{make.lower().replace(' ', '-')}/{model.lower().replace(' ', '-')}/{year}"

    return CarRow(
        make=make,
        model=model,
        year=year,
        price=price,
        milleage_km=mileage,
        transmission=transmission,
        fuel_type=fuel_type,
        body_type=body_type,
        location=location,
        url=url,
    )


def seed_cars(num_cars: int = NUM_CARS, seed: int = RANDOM_SEED) -> None:
    """
    Seed the database with random car data.

    Args:
        num_cars: Number of cars to generate
        seed: Random seed for deterministic results
    """
    # Set random seed for deterministic results
    random.seed(seed)

    print(f"🌱 Seeding database with {num_cars} cars (seed={seed})...")

    with get_session() as session:
        # Step 1: Clear existing data (idempotent)
        print("🗑️  Clearing existing cars...")
        deleted_count = session.query(CarRow).delete()
        print(f"   Deleted {deleted_count} existing cars")

        # Step 2: Generate and insert new cars
        print(f"🚗 Generating {num_cars} cars...")
        cars = [generate_car() for _ in range(num_cars)]

        session.add_all(cars)
        session.flush()  # Ensure all cars are inserted

        print(f"✅ Successfully seeded {len(cars)} cars!")

        # Print some sample data
        print("\n📊 Sample cars:")
        for i, car in enumerate(cars[:5], 1):
            print(
                f"   {i}. {car.year} {car.make} {car.model} - "
                f"${car.price:,.2f} ({car.transmission}, {car.fuel_type})"
            )

        if len(cars) > 5:
            print(f"   ... and {len(cars) - 5} more")


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    try:
        seed_cars()
    except Exception as e:
        print(f"❌ Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)
