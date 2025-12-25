# Interface Definitions - Abstract Base Classes (abc.ABC)

## Status

Accepted

## Context

Clean Architecture requires defining **ports** (interfaces) that decouple domain/application layers from infrastructure implementations. In our system:

- **Ports** define contracts (e.g., `CatalogRepository`)
- **Adapters** implement those contracts (e.g., `PostgresCatalogRepository`, `InMemoryCatalogRepository`)
- **UseCases** depend on port interfaces, not concrete implementations

Python offers two primary approaches for defining interfaces:

1. **Protocol** (typing.Protocol) - Structural subtyping (duck typing)
2. **Abstract Base Classes** (abc.ABC) - Nominal subtyping (explicit inheritance)

This decision impacts:
- Code clarity and explicitness
- Error detection timing (runtime vs static analysis)
- Coupling between layers
- Developer experience (onboarding, debugging)
- Testing approach

**The question:** How should we define ports in the domain layer?

## Decision

**Use Abstract Base Classes (abc.ABC) with @abstractmethod for all port definitions.**

All repository ports, service ports, and other domain interfaces will:
- Inherit from `abc.ABC`
- Mark interface methods with `@abstractmethod`
- Require explicit inheritance from adapters

### Standard Port Pattern

```python
from abc import ABC, abstractmethod
from typing import Sequence

class CatalogRepository(ABC):
    """Port for catalog data access.

    All implementations must inherit from this class and implement
    all abstract methods.
    """

    @abstractmethod
    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        """
        Search catalog with filters and paging.

        Args:
            filters: Filter criteria (AND semantics)
            paging: Pagination parameters

        Returns:
            Sequence of cars matching all filters, paginated
        """
        ...
```

### Standard Adapter Pattern

```python
from src.domain.ports.catalog_repository import CatalogRepository

class PostgresCatalogRepository(CatalogRepository):
    """PostgreSQL implementation of CatalogRepository port."""

    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        # Implementation
        ...
```

### Enforcement Rules

1. **All ports must:**
   - Inherit from `abc.ABC`
   - Use `@abstractmethod` decorator on all interface methods
   - Include comprehensive docstrings explaining contract semantics

2. **All adapters must:**
   - Explicitly inherit from their port(s)
   - Implement all abstract methods
   - Not be instantiable if methods are missing (runtime error)

3. **No concrete implementations in ports:**
   - Ports define contracts only
   - No shared business logic in port classes
   - If shared logic needed, create separate helper/service

## Rationale

### Why abc.ABC Over Protocol

**1. Explicitness and Clarity**

With ABC, the contract is explicit in code:
```python
class PostgresCatalogRepository(CatalogRepository):  # Clear inheritance
    ...
```

Anyone reading the code immediately sees:
- Which port this adapter implements
- The architectural relationship
- Where to find the interface definition

With Protocol, this relationship is implicit (structural):
```python
class PostgresCatalogRepository:  # No visible contract
    ...
```

**2. Runtime Error Detection**

ABC catches errors at **instantiation time**:

```python
class BrokenRepo(CatalogRepository):
    pass  # Missing search() implementation

repo = BrokenRepo()  # ❌ Raises TypeError immediately
# TypeError: Can't instantiate abstract class BrokenRepo with abstract method search
```

With Protocol, errors only appear during **static type checking** (if enabled):
```python
class BrokenRepo:
    pass

repo = BrokenRepo()  # ✅ No runtime error
# Type checker: error, but code runs (until search() is called)
```

**Benefits:**
- Fail fast - errors caught during object creation, not later during execution
- Works even without type checkers (runtime safety)
- Better for production debugging

**3. Team Communication and Onboarding**

Explicit inheritance signals:
- "This is an infrastructure implementation of a domain contract"
- "Look at the parent class to understand the interface"
- "These classes are architecturally related"

For developers new to the codebase or Python:
- Familiar pattern from other languages (Java, C#, TypeScript interfaces)
- IDE "Go to Definition" navigates to port
- Clearer architectural boundaries

**4. IDE Support and Tooling**

All IDEs understand ABC inheritance:
- Autocomplete shows abstract methods to implement
- Warnings when abstract methods are missing
- "Implement abstract methods" quick-fixes
- Better refactoring support

**5. Documentation Generation**

Tools like Sphinx automatically document inheritance:
- "Subclasses: PostgresCatalogRepository, InMemoryCatalogRepository"
- Clear interface → implementation mapping
- Better API documentation

**6. Architectural Intent**

ABC makes the architectural pattern explicit:
- Port = ABC with @abstractmethod
- Adapter = concrete class inheriting port
- Clear visual distinction in codebase

## Alternatives Considered

### Use Protocol (Structural Subtyping)

Define ports using `typing.Protocol` for duck typing compatibility.

```python
from typing import Protocol

class CatalogRepository(Protocol):
    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        ...
```

**Advantages:**
- More Pythonic (duck typing philosophy)
- Lower coupling (adapters don't import ports)
- Easier mocking in tests (no inheritance required)
- Can adapt existing classes without modification

**Rejected because:**
- **Lack of runtime enforcement** - errors only caught by type checkers
- **Implicit contracts** - architectural relationships not visible in code
- **Team preference for explicitness** - clearer intent and communication
- **Fail-fast principle** - want errors at instantiation, not later
- **Better for showcasing architecture** - explicit relationships demonstrate clean architecture understanding

**When to reconsider:**
- If type checking is strictly enforced in CI and no code runs without passing
- If team becomes more comfortable with structural typing
- If need to adapt third-party classes to ports without wrappers

### Use Both (Protocol for Type Hints, ABC for Runtime)

Define ports as both Protocol and ABC, use Protocol for type hints.

```python
class CatalogRepository(Protocol):
    ...

class CatalogRepositoryABC(ABC):
    ...
```

**Rejected because:**
- Duplicates interface definitions (maintenance burden)
- Confusing - which one to use when?
- Over-engineering for current needs
- Doesn't solve the core issue (still need to choose one for adapters)

### No Interfaces (Concrete Dependencies)

Don't define ports, inject concrete implementations directly.

```python
class SearchCatalog:
    def __init__(self, repo: PostgresCatalogRepository):  # Concrete type
        ...
```

**Rejected because:**
- Violates Dependency Inversion Principle
- Couples domain to infrastructure
- Makes testing harder (must use real implementations)
- Defeats the purpose of Clean Architecture
- Not a serious consideration for this project

## Consequences

### Positive

- **Runtime safety:** Errors caught at object creation, not during execution
- **Explicitness:** Architectural relationships visible in code
- **Better IDE support:** Autocomplete, refactoring, navigation all work perfectly
- **Team clarity:** Obvious which adapters implement which ports
- **Fail-fast:** Invalid implementations rejected immediately
- **No type checker required:** Runtime enforcement works without mypy/pyright
- **Documentation:** Clear interface → implementation mapping
- **Professional showcase:** Demonstrates understanding of clean architecture patterns

### Negative

- **Coupling:** Adapters must import ports (infrastructure imports domain)
  - *Mitigation:* This is acceptable coupling - infrastructure should know about domain contracts
- **Verbosity:** Must write explicit inheritance
  - *Mitigation:* Minimal - one line: `class MyRepo(CatalogRepository):`
- **Testing:** Mocks/fakes must inherit from port
  - *Mitigation:* Still easy - test doubles inherit ABC, same as production adapters
- **Less Pythonic:** Explicit inheritance vs duck typing
  - *Mitigation:* Acceptable trade-off for clarity and safety

### Neutral

- Slightly more boilerplate (explicit inheritance)
- Standard pattern familiar to developers from other languages
- Type checkers still provide static analysis (complementary to runtime checks)

## Implementation Notes

### Port Definition Template

```python
from abc import ABC, abstractmethod

class RepositoryName(ABC):
    """Brief description of repository responsibility.

    Longer description of contract semantics, invariants,
    and expectations for implementers.
    """

    @abstractmethod
    def method_name(self, param: Type) -> ReturnType:
        """
        Method description.

        Args:
            param: Description

        Returns:
            Description

        Raises:
            ExceptionType: When and why
        """
        ...
```

### Adapter Implementation Template

```python
from src.domain.ports.repository_name import RepositoryName

class ConcreteRepositoryName(RepositoryName):
    """Implementation description and technology used."""

    def __init__(self, dependencies):
        """Initialize with required dependencies."""
        self._dependency = dependencies

    def method_name(self, param: Type) -> ReturnType:
        """Implement abstract method."""
        # Implementation
        ...
```

### Testing Pattern

Test doubles also inherit from port:

```python
class InMemoryCatalogRepository(CatalogRepository):
    """In-memory implementation for testing."""

    def __init__(self):
        self._cars: list[Car] = []

    def search(self, filters: CatalogFilters, paging: Paging) -> Sequence[Car]:
        # Simple in-memory implementation
        ...
```

### Error Handling Example

```python
# Attempting to instantiate without implementing all methods:
class IncompleteRepo(CatalogRepository):
    pass  # Forgot to implement search()

repo = IncompleteRepo()
# Raises: TypeError: Can't instantiate abstract class IncompleteRepo
#         with abstract method search
```

### Directory Structure

```
src/domain/
  ports/
    __init__.py
    catalog_repository.py      # ABC with @abstractmethod

src/infra/
  db/
    repositories/
      postgres_catalog_repository.py   # Inherits CatalogRepository
  memory/
    repositories/
      in_memory_catalog_repository.py  # Inherits CatalogRepository
```

## Acceptance Criteria

- ✅ All ports defined as ABC with @abstractmethod
- ✅ All adapters explicitly inherit from their port(s)
- ✅ Attempting to instantiate incomplete adapter raises TypeError
- ✅ IDEs show proper inheritance relationships
- ✅ Documentation clearly shows port → adapter mappings
- ✅ Ports have comprehensive docstrings explaining contract semantics
- ✅ No concrete implementation logic in port classes

## References

- Python abc module: https://docs.python.org/3/library/abc.html
- PEP 3119 - Introducing Abstract Base Classes: https://peps.python.org/pep-3119/
- Clean Architecture (Robert C. Martin): Dependency Inversion Principle
- Related: `12-25-25-database-foundation.md` - PostgresCatalogRepository implements this pattern
- Related: `12-25-25-car-catalog-search.md` - CatalogRepository port follows this decision
