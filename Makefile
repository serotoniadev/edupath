.DEFAULT_GOAL := help

.PHONY: help install lint test playground run

help:
	@echo "Available targets:"
	@echo "  install     Install dependencies"
	@echo "  lint        Run code quality checks"
	@echo "  test        Run unit tests"
	@echo "  playground  Launch ADK web playground (localhost:18081)"
	@echo "  run         Start local FastAPI server"

install:
	uv sync

lint:
	uv run ruff check app/ tests/

test:
	uv run pytest tests/unit/ -v

playground:
	uv run adk web app --host 127.0.0.1 --port 18081 --reload_agents

run:
	uv run uvicorn app.agent_runtime_app:agent_runtime --host 0.0.0.0 --port 8080
