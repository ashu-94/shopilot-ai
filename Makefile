.PHONY: install migrate dev test lint build up down
install:
	uv sync --python 3.12
	cd frontend && npm ci
migrate:
	uv run alembic upgrade head
	uv run python -m backend.bootstrap
dev:
	uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
test:
	uv run pytest -q
lint:
	uv run ruff check backend mcp_servers tests
	uv run mypy backend
	cd frontend && npm run typecheck
build:
	cd frontend && npm run build
up:
	docker compose up --build -d
down:
	docker compose down
