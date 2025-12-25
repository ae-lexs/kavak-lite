# Monetary Values – System-wide Rule

This document defines a **global, non-negotiable rule** for handling money across the entire system.

It applies to **all domains and use cases**, including (but not limited to) catalog pricing, financing, fees, discounts, and taxes.

---

## Decision

All monetary values in the system **must be represented and calculated using decimal arithmetic**, never floating-point numbers.

### Canonical rule
- **Domain & UseCases:** `Decimal`
- **Persistence (DB):** `NUMERIC(precision, scale)`
- **External inputs (APIs, requests):** may accept `float` or `string`
- **Boundary rule:** convert immediately to `Decimal`
- **Rounding:** explicit and documented per use case

No monetary value is allowed to exist as a `float` inside the domain.

---

## What counts as a monetary value

This rule applies to **any value that represents or affects money**, including:

- Prices
- Interest rates
- Monthly payments
- Totals and subtotals
- Fees
- Discounts
- Taxes
- Penalties

If it influences money → **Decimal**.

---

## Rationale

Floating-point numbers (`float`) are binary approximations and **cannot exactly represent decimal values**.

Using floats for money leads to:
- Rounding drift in interest calculations
- Non-deterministic totals
- Fragile tests (`assertAlmostEqual`)
- Silent financial inaccuracies

Because pricing and financing are **core business logic**, correctness outweighs convenience.

---

## Database representation

All monetary columns must use `NUMERIC`:

```sql
NUMERIC(precision, scale)
```

Examples:
```sql
  # Car pricing
  price: NUMERIC(12, 2)              # $9,999,999,999.99

  # Financing fields (future)
  interest_rate: NUMERIC(5, 4)       # 0.0000-9.9999 (0% to 999.99%)
  monthly_payment: NUMERIC(10, 2)    # $99,999,999.99
  down_payment: NUMERIC(12, 2)       # Same as price
  total_financed: NUMERIC(12, 2)     # Same as price
```

- Precision defines maximum value
- Scale defines decimal places
- Currency is intentionally not encoded at the column level

---

## Domain & UseCase representation

Use Python’s `Decimal` type exclusively.

```python
from decimal import Decimal

price = Decimal("12999.00")
rate = Decimal("0.10")  # 10%
```

- Never construct `Decimal` from a float directly
- Always use strings or integer-based conversion

---

## Boundary conversions (mandatory)

External layers (REST, GraphQL, CLI, tests) may accept floats for ergonomics, but **conversion must happen immediately** at the boundary.

```python
from decimal import Decimal

def to_decimal(value: float | int | str) -> Decimal:
    return Decimal(str(value))
```

After conversion, floats must not cross into:
- UseCases
- Domain entities
- Business rules

---

## Rounding policy

Rounding is **never implicit**.

Every UseCase performing monetary calculations must explicitly define:
- **When** rounding occurs
- **How** rounding occurs

Example:
```python
from decimal import Decimal, ROUND_HALF_UP

amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

Common patterns:
- Monthly payments → round to 2 decimals
- Totals → compute precisely, then round once at the end (preferred)

If rounded values are multiplied later, this must be explicitly documented.

---

## Integer minor units (cents)

Using integers (e.g. cents) is allowed for:
- Storage
- Simple additions/subtractions

However:
- Interest, division, and percentage math **must use Decimal**
- Convert cents → Decimal before any financial calculation

Integers do **not** replace Decimal for financial logic.

---

## Architectural principle

> **Money is exact. Rounding is a business decision. Floats are not allowed in the core.**

This rule ensures:
- Deterministic calculations
- Auditable financial behavior
- Stable and exact tests
- Long-term correctness as the system evolves

---

## Enforcement

- UseCases must not accept `float` for monetary parameters
- Repositories must not expose `float` monetary fields
- Any violation should be treated as a **design bug**, not a style issue

This document defines a **system invariant**.
