.PHONY: install test lint typecheck run up down check migrate migrate-down revision current history

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

revision:
	@test -n "$(m)" || (echo 'usage: make revision m="what changed"'; exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

current:
	uv run alembic current

history:
	uv run alembic history --verbose

# Schema is applied by `make migrate`, never by the service on boot (NX-030).
run: migrate
	uv run uvicorn nexus.main:app --reload --port 8000

up:
	docker compose up --build

down:
	docker compose down -v

check: lint typecheck test
