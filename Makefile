.RECIPEPREFIX := >
PY=python

.PHONY: install fmt lint test

install:
> $(PY) -m pip install -U pip
> $(PY) -m pip install -e .[dev]
> pre-commit install

fmt:
> ruff format .
> black .
> isort .

lint:
> ruff check .
> ruff format --check .
> black --check .
> isort --check-only .

test:
> pytest -q tests
