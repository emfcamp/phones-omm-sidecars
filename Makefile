.PHONY: test lint lint-fix check-format format check

test:
	uv run pytest

lint:
	uv run basedpyright
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

check-format:
	uv run ruff format --check .

format:
	uv run ruff format .

check: test lint check-format
