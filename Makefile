SHELL := /bin/sh

.PHONY: help build up down logs ps sh lock sync test test_file lint lint_fix typecheck fmt check clean

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
	@echo "  make test_file   Run specific test file (FILE=path/to/test.py)"
	@echo "  make lint        Ruff check"
	@echo "  make lint_fix    Ruff check and fix"
	@echo "  make fmt         Ruff format"
	@echo "  make typecheck   Mypy strict typecheck"
	@echo "  make check       Lint + typecheck + test"
	@echo "  make clean       Remove containers/volumes (careful)"

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

test_file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required. Usage: make test_file FILE=path/to/test.py"; \
		exit 1; \
	fi
	docker compose run --rm api uv run pytest $(FILE) -v

lint:
	docker compose run --rm api uv run ruff check .

lint_fix:
	docker compose run --rm api uv run ruff check --fix .

fmt:
	docker compose run --rm api uv run ruff format .

typecheck:
	docker compose run --rm api uv run mypy src

check: lint typecheck test

clean:
	docker compose down -v
