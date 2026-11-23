.PHONY: help install lint format test test-cov migrate migration db-up db-down dev

help:
	@echo "Available commands:"
	@echo "  make install     - Install backend dependencies with uv"
	@echo "  make lint        - Run ruff check"
	@echo "  make format      - Run ruff format"
	@echo "  make test        - Run backend test suite"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make migrate     - Run database migrations"
	@echo "  make migration   - Create a new migration (usage: make migration MSG='create_table')"
	@echo "  make db-up       - Start PostgreSQL and pgvector via Docker Compose"
	@echo "  make db-down     - Stop PostgreSQL container"
	@echo "  make dev         - Run FastAPI backend development server"

install:
	cd backend && uv sync

lint:
	cd backend && uv run ruff check .

format:
	cd backend && uv run ruff format .

test:
	cd backend && uv run pytest

test-cov:
	cd backend && uv run pytest --cov=spindle tests/

migrate:
	cd backend && uv run alembic upgrade head

migration:
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

db-up:
	docker compose up -d

db-down:
	docker compose down

dev:
	cd backend && uv run uvicorn spindle.api.app:app --reload --host 0.0.0.0 --port 8000
