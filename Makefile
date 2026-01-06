SHELL := /bin/sh

.PHONY: help build up down logs ps sh lock sync test test-file test-coverage lint lint-fix typecheck fmt check clean db-status db-history db-up db-down db-base db-new db-sql db-shell db-seed

help:
	@echo "kavak-lite commands:"
	@echo "  make build       Build images"
	@echo "  make up          Start API (foreground)"
	@echo "  make down        Stop services"
	@echo "  make logs        Tail logs"
	@echo "  make ps          Show running containers"
	@echo "  make sh          Shell inside api container"
	@echo "  make lock        Generate/update uv.lock"
	@echo "  make sync        Install deps from lock (frozen)"
	@echo "  make test        Run all tests"
	@echo "  make test-file   Run specific test file (FILE=path/to/test.py)"
	@echo "  make test-coverage  Run tests with coverage report"
	@echo "  make lint        Ruff check"
	@echo "  make lint-fix    Ruff check and fix"
	@echo "  make fmt         Ruff format"
	@echo "  make typecheck   Mypy strict typecheck"
	@echo "  make check       Lint + typecheck + test"
	@echo "  make clean       Remove containers/volumes (careful)"
	@echo ""
	@echo "Database commands:"
	@echo "  make db-status   Show current revision and heads"
	@echo "  make db-history  Show migration history (verbose)"
	@echo "  make db-up       Upgrade to latest migration"
	@echo "  make db-down     Downgrade one migration"
	@echo "  make db-base     Downgrade to base (empty DB)"
	@echo "  make db-new      Create new migration (autogenerate)"
	@echo "  make db-sql      Show SQL for upgrade (dry-run)"
	@echo "  make db-shell    Open psql shell in postgres container"
	@echo "  make db-seed     Seed database with 50 sample cars (idempotent)"

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

sh:
	docker compose run --rm api sh

lock:
	docker compose run --rm api uv lock

sync:
	docker compose run --rm api uv sync --frozen

test:
	docker compose run --rm api uv run pytest

test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required. Usage: make test-file FILE=path/to/test.py"; \
		exit 1; \
	fi
	docker compose run --rm api uv run pytest $(FILE) -v

test-coverage:
	docker compose run --rm api uv run pytest --cov=src/kavak_lite --cov-report=term-missing

lint:
	docker compose run --rm api uv run ruff check .

lint-fix:
	docker compose run --rm api uv run ruff check --fix .

fmt:
	docker compose run --rm api uv run ruff format .

typecheck:
	docker compose run --rm api uv run mypy src

check: lint typecheck test

clean:
	docker compose down -v

db-status:
	@docker compose run --rm api uv run alembic current
	@echo ""
	@docker compose run --rm api uv run alembic heads

db-history:
	docker compose run --rm api uv run alembic history --verbose

db-up:
	docker compose run --rm api uv run alembic upgrade head

db-down:
	docker compose run --rm api uv run alembic downgrade -1

db-base:
	docker compose run --rm api uv run alembic downgrade base

db-new:
	@read -p "Migration message: " msg; \
	docker compose run --rm api uv run alembic revision --autogenerate -m "$$msg"

db-sql:
	docker compose run --rm api uv run alembic upgrade head --sql

db-shell:
	docker compose exec postgres psql -U kavak -d kavak_lite

db-seed:
	docker compose run --rm api uv run python scripts/seed_cars.py
