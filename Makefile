.PHONY: up down logs test test-local lint format typecheck check

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

test:
	docker compose run --rm --build tests

test-local:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

check: lint typecheck test-local
