.RECIPEPREFIX := >
PY=python
PKG=land_scout tests

.PHONY: install fmt lint test verify

install:
> $(PY) -m pip install -U pip
> $(PY) -m pip install -e .[dev]
> pre-commit install

fmt:
> ruff format $(PKG)
> black $(PKG)
> isort $(PKG)

lint:
> ruff check $(PKG)
> ruff format --check $(PKG)
> black --check $(PKG)
> isort --check-only $(PKG)

test:
> pytest -q

verify:
> python -c "import land_scout, pathlib; print('OK:', land_scout.__file__)"
