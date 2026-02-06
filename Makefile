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

.PHONY: help setup-venv install install-dev test lint format precommit run-once run clean

help:
	@echo "Available targets:"
	@echo "  setup-venv   Create virtual environment in $(VENV)"
	@echo "  install      Install package"
	@echo "  install-dev  Install package with dev dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run ruff checks"
	@echo "  format       Run ruff formatter"
	@echo "  precommit    Run pre-commit hooks on all files"
	@echo "  run-once     Run one ingestion pass"
	@echo "  run          Run daemon in watch mode"
	@echo "  clean        Remove local build/cache artifacts"

setup-venv:
	python3 -m venv $(VENV)

install:
	$(PIP) install -e . --no-build-isolation

install-dev:
	$(PIP) install -e '.[dev]' --no-build-isolation

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/mpl $(PYTHON) -m pytest

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

clean:
	rm -rf build dist .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
