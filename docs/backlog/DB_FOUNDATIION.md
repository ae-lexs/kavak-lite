# DB foundation (SQLAlchemy + Alembic + Postgres wiring)

## Goal

Lay the database foundation for `kavak-lite` so later features (Car Catalog, Pricing, etc.) can persist data without leaking infra details into domain code. This PR adds **SQLAlchemy ORM**, **Alembic migrations**, and a minimal **DB session/engine** setup. No UseCases yet.

## Business decisions

- We’re standardizing on **Postgres** as the system of record for MVP and beyond.
- Schema management is **migration-first** (Alembic), not “ORM auto-create”.

## Technical decisions

- Use **SQLAlchemy 2.0 style** (`select()`, typed mappings) to avoid legacy patterns.
- Keep DB plumbing **infra-only**: `src/infra/db/...` (domain never imports SQLAlchemy).
- Config via env vars: `DATABASE_URL` (single source of truth).

## Acceptance criteria
- ✅ alembic upgrade head runs cleanly with a valid DATABASE_URL
- ✅ Initial migration creates cars table + indexes
- ✅ SQLAlchemy engine/session wiring exists under src/infra/db
- ✅ Domain layer has zero dependency on SQLAlchemy/Alembic
- ✅ CI remains green