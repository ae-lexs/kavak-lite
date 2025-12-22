# kavak-lite

**kavak-lite**: Clean Architecture, SOLID principles, explicit use cases, and multiple API styles (REST, GraphQL, gRPC).

---

## Tech Stack

- **Python 3.14.2**
- **uv** (Rust-based Python package manager)
- **FastAPI** (HTTP entrypoint)
- **Docker + Docker Compose**
- **pytest / mypy / ruff**

---

## Architecture

The codebase follows a Clean Architecture layout:

```text
src/
  domain/        # Pure business rules (entities, value objects)
  use_cases/     # Application logic (orchestrates domain)
  adapters/      # Infrastructure (DB, APIs, external services)
  entrypoints/   # Delivery mechanisms (HTTP, GraphQL, gRPC)

