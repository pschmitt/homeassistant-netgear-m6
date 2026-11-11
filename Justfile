set shell := ["bash", "-euo", "pipefail", "-c"]

# Format, lint, type-check and test
default: format lint typecheck test

format:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff format --check .
    uv run ruff check .

typecheck:
    uv run pyright

test *ARGS:
    uv run pytest {{ ARGS }}
