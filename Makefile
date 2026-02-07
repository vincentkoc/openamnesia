VENV ?= .venv
VENV_PY := $(VENV)/bin/python
VENV_PIP := $(VENV_PY) -m pip
VENV_PRECOMMIT := $(VENV)/bin/pre-commit

ifeq ($(wildcard $(VENV_PY)),)
PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PRECOMMIT ?= pre-commit
else
PYTHON ?= $(VENV_PY)
PIP ?= $(VENV_PIP)
PRECOMMIT ?= $(VENV_PRECOMMIT)
endif

.DEFAULT_GOAL := help

.PHONY: help setup-venv install install-dev test typecheck lint format precommit run-once run source-test e2e-all api ui sdk clean

help:
	@echo "Available targets:"
	@echo "  setup-venv   Create virtual environment in $(VENV)"
	@echo "  install      Install package"
	@echo "  install-dev  Install package with dev dependencies"
	@echo "  test         Run tests"
	@echo "  typecheck    Run mypy type checks"
	@echo "  lint         Run ruff checks"
	@echo "  format       Run ruff formatter"
	@echo "  precommit    Run pre-commit hooks on all files"
	@echo "  run-once     Run one ingestion pass"
	@echo "  run          Run daemon in watch mode"
	@echo "  source-test  Test one source (set SOURCE=imessage)"
	@echo "  e2e-all     Ingest + discovery for all sources (MODE=recent|all)"
	@echo "  api         Run API server"
	@echo "  ui          Run frontend dev server"
	@echo "  sdk         Run interactive SDK menu"
	@echo "  clean        Remove local build/cache artifacts"

setup-venv:
	python3 -m venv $(VENV)

install:
	$(PIP) install -e . --no-build-isolation

install-dev:
	$(PIP) install -e '.[dev]' --no-build-isolation

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/mpl $(PYTHON) -m pytest

typecheck:
	$(PYTHON) -m mypy --config-file pyproject.toml

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

precommit:
	$(PRECOMMIT) run --all-files

run-once:
	$(PYTHON) amnesia_daemon.py --config config.yaml --once

run:
	$(PYTHON) amnesia_daemon.py --config config.yaml

source-test:
	@if [ -z "$(SOURCE)" ]; then echo "Set SOURCE=<name>, e.g. SOURCE=imessage"; exit 1; fi
	$(PYTHON) scripts/test_source.py --config config.yaml --source $(SOURCE)

e2e-all:
	@if [ "$(MODE)" = "all" ]; then \
		$(PYTHON) scripts/run_e2e.py --mode all; \
	else \
		$(PYTHON) scripts/run_e2e.py --mode recent; \
	fi

api:
	$(PYTHON) -m amnesia.api.server

ui:
	cd frontend && npm run dev

sdk:
	amnesia

clean:
	rm -rf build dist .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
