.PHONY: help install db migrate run up down lint format typecheck test check

help:  ## Show the available commands
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

db:  ## Start only PostgreSQL (for local development and tests)
	docker compose up -d db

migrate:  ## Apply database migrations
	uv run alembic upgrade head

run:  ## Run the development server on http://localhost:5000
	uv run flask --app shop run --debug

up:  ## Build and start everything (database, migrations, API on http://localhost:8000)
	docker compose up -d --build

down:  ## Stop all containers
	docker compose down

lint:  ## Check code style and module boundaries
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports

format:  ## Fix code style
	uv run ruff check --fix .
	uv run ruff format .

typecheck:  ## Run the type checker
	uv run mypy

test:  ## Run all tests (needs PostgreSQL, see `make db`)
	uv run pytest

check: lint typecheck test  ## Run everything CI runs
