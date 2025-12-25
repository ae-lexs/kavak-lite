# Monetary Values - Decimal Arithmetic System-Wide

## Status

Proposed

**Scope:** System-wide invariant applying to all domains and use cases.

## Context

This system handles financial transactions including car pricing, financing calculations, interest rates, fees, discounts, and taxes. Financial correctness is a **core business requirement** - users and regulators expect exact monetary calculations.

The challenge: computers use binary floating-point arithmetic (IEEE 754), which cannot exactly represent decimal values. For example:

```python
0.1 + 0.2 == 0.30000000000000004  # True in Python
```

This creates problems in financial systems:

- **Rounding drift:** Repeated calculations accumulate errors
- **Non-deterministic totals:** Same inputs produce different outputs depending on operation order
- **Fragile tests:** Must use `assertAlmostEqual` instead of exact comparisons
- **Silent inaccuracies:** Off-by-one-cent errors that compound over time
- **Audit failures:** Cannot reproduce exact historical calculations

In a financing system calculating monthly payments over 60 months with interest rates, these errors can result in incorrect totals, failed audits, and regulatory issues.

**This decision defines a non-negotiable system invariant.**

## Decision

All monetary values in the system **must be represented and calculated using decimal arithmetic**, never floating-point numbers.

### Canonical Rule

| Layer | Type | Rule |
|-------|------|------|
| Domain & UseCases | `Decimal` | All calculations use Python's `Decimal` type |
| Persistence (DB) | `NUMERIC(precision, scale)` | All monetary columns use PostgreSQL `NUMERIC` |
| External inputs (APIs) | `float` or `string` | May accept for ergonomics |
| Boundary conversion | Immediate | Convert to `Decimal` at system boundary |
| Rounding | Explicit | Never implicit, documented per use case |

**No monetary value is allowed to exist as a `float` inside the domain layer.**

### What Counts as a Monetary Value

This rule applies to **any value that represents or affects money**:

- Prices (car prices, fees)
- Interest rates (annual, monthly)
- Payments (monthly payment, down payment, total financed)
- Totals and subtotals
- Discounts
- Taxes
- Penalties
- Any derived financial calculation

**Rule of thumb:** If it influences money → `Decimal`.

### Layer-Specific Rules

#### Domain & UseCase Layer

Use Python's `Decimal` type exclusively:

```python
from decimal import Decimal

# Correct
price = Decimal("12999.00")
rate = Decimal("0.10")  # 10% interest rate

# Incorrect - never construct from float
price = Decimal(12999.99)  # ❌ Float precision loss
```

**Rules:**
- Never construct `Decimal` from a `float` directly
- Always use string literals or integer-based conversion
- No `float` types in domain entities, value objects, or use case parameters

#### Database Layer

All monetary columns must use PostgreSQL `NUMERIC`:

```sql
NUMERIC(precision, scale)
```

**Examples:**

```sql
-- Car pricing
price: NUMERIC(12, 2)              -- $9,999,999,999.99

-- Financing fields
interest_rate: NUMERIC(5, 4)       -- 0.0000-9.9999 (0% to 999.99%)
monthly_payment: NUMERIC(10, 2)    -- $99,999,999.99
down_payment: NUMERIC(12, 2)       -- Same as price
total_financed: NUMERIC(12, 2)     -- Same as price
```

**Guidelines:**
- `precision`: Total number of digits (choose based on maximum expected value)
- `scale`: Decimal places (typically 2 for currency, 4 for interest rates)
- Currency is intentionally not encoded at column level (application concern)

#### Boundary Layer (APIs, Controllers)

External layers may accept `float` for ergonomics, but **conversion must happen immediately** at the boundary:

```python
from decimal import Decimal

def to_decimal(value: float | int | str) -> Decimal:
    """Convert external input to Decimal at system boundary."""
    return Decimal(str(value))
```

**After boundary conversion, `float` must not cross into:**
- UseCases
- Domain entities
- Business rules
- Repository methods

#### Rounding Policy

Rounding is **never implicit** and must always be explicit and documented.

Every UseCase performing monetary calculations must define:
- **When** rounding occurs (at what step in the calculation)
- **How** rounding occurs (which rounding mode)

```python
from decimal import Decimal, ROUND_HALF_UP

# Explicit rounding
amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

**Common patterns:**
- **Monthly payments:** Round to 2 decimal places after calculation
- **Totals:** Compute precisely, round once at the end (preferred to minimize drift)
- **Intermediate values:** Keep full precision, round only at boundaries

**Warning:** If rounded values are multiplied later, this must be explicitly documented as it can compound rounding effects.

#### Integer Minor Units (Cents)

Using integers (e.g., cents) is **allowed but limited**:

**Allowed:**
- Storage optimization (store cents as `BIGINT`)
- Simple additions/subtractions

**Not allowed:**
- Interest calculations
- Division operations
- Percentage calculations

**Rule:** Convert cents → `Decimal` before any financial calculation involving multiplication, division, or interest.

```python
# Correct
cents = 1299900  # $12,999.00
price = Decimal(cents) / 100  # Convert to Decimal for calculations

# Incorrect - loses precision
price = cents / 100  # ❌ Returns float
```

Integers do **not** replace `Decimal` for financial logic.

## Alternatives Considered

### Use Floating-Point Everywhere

Use Python's native `float` type for all monetary calculations.

**Rejected:**
- Binary approximation causes precision loss
- Accumulating errors in multi-step calculations
- Non-deterministic behavior (operation order affects results)
- Fails regulatory/audit requirements for financial systems
- Tests become fragile (must use approximate equality)

### Integer Cents Only

Store and calculate everything as integer cents (e.g., 1000 cents = $10.00).

**Rejected:**
- Works for simple addition/subtraction
- Breaks down for interest calculations (e.g., 10% of 1333 cents = 133.3 cents)
- Division and multiplication require careful handling of remainders
- Interest rates would need large multipliers (10.5% = 1050 basis points)
- More complex and error-prone than `Decimal`
- Doesn't solve the fundamental problem, just shifts it

### Use Money Library (e.g., py-moneyed)

Use a third-party money library that handles currency and arithmetic.

**Deferred:**
- Adds external dependency
- Most Python money libraries use `Decimal` internally anyway
- Current needs are simple enough for direct `Decimal` usage
- Can revisit if we need multi-currency support or currency conversion
- Python's stdlib `Decimal` is battle-tested and sufficient

### Mixed Approach (Float for Display, Decimal for Calculation)

Use `float` for API responses/display, `Decimal` internally.

**Rejected:**
- Introduces unnecessary conversion points
- Risk of accidental float arithmetic
- API consumers might do float calculations on our values
- Better to be consistent: `Decimal` everywhere, serialize to string

## Consequences

### Positive

- **Correctness:** Exact decimal arithmetic, no precision loss
- **Deterministic:** Same inputs always produce same outputs
- **Auditable:** Can reproduce exact historical calculations
- **Testable:** Use exact equality assertions (`assert x == y`)
- **Regulatory compliance:** Meets financial industry standards
- **Long-term stability:** System remains correct as it scales
- **Developer confidence:** No "mystery" rounding errors

### Negative

- **Verbosity:** `Decimal("12999.00")` vs `12999.00`
- **Learning curve:** Developers must understand `Decimal` API
- **Performance:** `Decimal` arithmetic is slower than `float` (acceptable trade-off)
- **API ergonomics:** Must serialize `Decimal` to string for JSON (not auto-convertible)
- **External libraries:** Some libraries expect `float`, requiring conversion at boundaries

### Neutral

- Requires explicit rounding decisions (forces intentionality)
- Boundary conversion adds one step to input validation
- Database choice matters (PostgreSQL `NUMERIC` has excellent `Decimal` support)

## Implementation Notes

### Enforcement

This is a **system invariant** enforced through:

1. **Code review:** Any `float` in monetary contexts is rejected
2. **Type hints:** Use `Decimal` in all monetary type signatures
3. **Tests:** Verify exact decimal behavior
4. **Linting:** Consider adding custom linter rule to flag float usage in financial code

**Violations are treated as design bugs, not style issues.**

### Example: Use Case Parameter

```python
from decimal import Decimal

class CalculateFinancingPlan:
    def execute(self, request: FinancingRequest) -> FinancingResponse:
        # ✅ Correct - Decimal parameters
        car_price: Decimal = request.car_price
        down_payment: Decimal = request.down_payment

        # ❌ Would be rejected - float parameter
        # car_price: float = request.car_price
```

### Example: Database Model

```python
from decimal import Decimal
from sqlalchemy import NUMERIC

class Car(Base):
    __tablename__ = "cars"

    # ✅ Correct - NUMERIC for database, Decimal for Python
    price = Column(NUMERIC(12, 2), nullable=False)

    # When loaded from DB, SQLAlchemy returns Decimal automatically
```

### Example: API Boundary Conversion

```python
from decimal import Decimal
from pydantic import BaseModel, field_validator

class FinancingRequestDTO(BaseModel):
    car_price: float  # Accept float from API

    @field_validator("car_price")
    def convert_to_decimal(cls, v: float) -> Decimal:
        # Convert at boundary
        return Decimal(str(v))
```

### Architectural Principle

> **Money is exact. Rounding is a business decision. Floats are not allowed in the core.**

This ensures:
- Deterministic calculations
- Auditable financial behavior
- Stable and exact tests
- Long-term correctness as the system evolves

## References

- IEEE 754 Floating-Point Standard: [0.30000000000000004.com](https://0.30000000000000004.com/)
- Python `decimal` module: [Python docs](https://docs.python.org/3/library/decimal.html)
- PostgreSQL `NUMERIC` type: [PostgreSQL docs](https://www.postgresql.org/docs/current/datatype-numeric.html)
- Martin Fowler on Money pattern: *Patterns of Enterprise Application Architecture*
- Related: `12-25-25-car-catalog-search.md` - Uses this decision for price filtering
