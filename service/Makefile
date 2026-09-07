.PHONY: install test lint typecheck run up down check

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy

run:
	uv run uvicorn nexus.main:app --reload --port 8000

up:
	docker compose up --build

down:
	docker compose down -v

check: lint typecheck test
