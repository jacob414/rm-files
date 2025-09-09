VENV_DIR := .venv
MY_PYTHON_VERSION := 3.12

# Tool shims (prefer venv binaries)
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
PYTEST := $(VENV_DIR)/bin/pytest
RUFF := $(VENV_DIR)/bin/ruff
MYPY := $(VENV_DIR)/bin/mypy
BANDIT := $(VENV_DIR)/bin/bandit
VULTURE := $(VENV_DIR)/bin/vulture
BLACK := $(VENV_DIR)/bin/black
PYUPGRADE := $(VENV_DIR)/bin/pyupgrade

$(VENV_DIR)/bin/activate: requirements.txt
	python$(MY_PYTHON_VERSION) -m venv $(VENV_DIR)
	. $(VENV_DIR)/bin/activate; pip install -r requirements.txt

venv: $(VENV_DIR)/bin/activate ## Create venv and install runtime deps

install-dev: venv ## Install development dependencies
	$(PIP) install -r requirements-dev.txt

clean: ## Remove venv and caches
	rm -rf $(VENV_DIR)
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- QA pipeline ---

upgrade: install-dev ## Modernize syntax (pyupgrade)
	find rmfiles tests -name "*.py" -exec $(PYUPGRADE) --py312-plus {} + || true

format: install-dev ## Format code (Black)
	$(BLACK) rmfiles tests gen.py

lint: install-dev ## Lint (Ruff)
	$(RUFF) check rmfiles tests

lint-fix: install-dev ## Lint and fix (Ruff)
	$(RUFF) check --fix rmfiles tests

type-check: install-dev ## Type-check (mypy)
	$(MYPY) rmfiles

security: install-dev ## Security scan (Bandit)
	$(BANDIT) -r rmfiles --skip B101,B404,B603,B607 -f txt

dead-code: install-dev ## Dead code scan (Vulture)
	$(VULTURE) rmfiles tests || true

test: install-dev ## Run tests with coverage
	$(PYTEST) -v --cov=rmfiles --cov-report=term-missing --cov-report=html

test-quick: venv ## Run tests (no coverage)
	$(PYTEST) -q

audit: ## Run all QA checks (optional dead-code excluded)
	$(MAKE) upgrade
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	@echo "(dead-code analysis available via 'make dead-code')"

qa: test audit ## Full QA pipeline

ci: clean venv install-dev qa ## CI pipeline

.PHONY: venv install-dev clean upgrade format lint lint-fix type-check security dead-code test test-quick audit qa ci
