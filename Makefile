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
SPHINX_BUILD := $(VENV_DIR)/bin/sphinx-build
PRECOMMIT := $(VENV_DIR)/bin/pre-commit

$(VENV_DIR)/bin/activate: requirements.txt
	@set -e; \
	PYBIN=python$(MY_PYTHON_VERSION); \
	command -v $$PYBIN >/dev/null 2>&1 || PYBIN=python3; \
	$$PYBIN -m venv $(VENV_DIR);
	. $(VENV_DIR)/bin/activate; pip install -r requirements.txt

venv: $(VENV_DIR)/bin/activate ## Create venv and install runtime deps

install-dev: venv ## Install QA dependencies (portable in CI)
	$(PIP) install -r requirements-qa.txt

check-deps: ## Verify all runtime deps import correctly
	@set -e; \
	. $(VENV_DIR)/bin/activate; \
	python -c "import sys, importlib.util; mods=['rmscene','numpy']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; print('Dependency check: OK' if not missing else f'Missing: {missing}', file=sys.stderr if missing else sys.stdout); sys.exit(0 if not missing else 1)"

clean: ## Remove venv and caches
	rm -rf $(VENV_DIR)
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- QA pipeline ---

upgrade: install-dev ## Modernize syntax (pyupgrade)
	find rmfiles tests -name "*.py" -exec $(PYUPGRADE) --py312-plus {} + || true

format: install-dev ## Format code (Black)
	$(BLACK) .

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

prepare-samples: venv ## Ensure sample test artifacts exist
	$(PYTHON) -c "from pathlib import Path; import sys;\
try:\
    from rmfiles.notebook import create\
except Exception:\
    sys.exit(0)\
p=Path('sample-files/triangel.rm'); p.parent.mkdir(parents=True, exist_ok=True);\
import os;\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
if not p.exists(): nb=create(); layer=nb.create_layer('Layer 1'); nb.create_triangle(layer, center_x=150, center_y=150, size=100); nb.write(str(p))"

test: install-dev check-deps ## Run tests with coverage
	# Ensure sample .rm exists (ignored by git)
	@if [ ! -f sample-files/triangel.rm ]; then \
		$(PYTHON) examples/make_triangle.py --out sample-files/triangel.rm >/dev/null 2>&1 || true; \
	fi
	$(PYTEST) -v --cov=rmfiles --cov-report=term-missing --cov-report=html

test-quick: venv check-deps ## Run tests (no coverage)
	$(PYTEST) -q

audit: ## Run all QA checks (optional dead-code excluded)
	$(MAKE) upgrade
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) pre-commit
	$(MAKE) type-check
	$(MAKE) security
	@echo "(dead-code analysis available via 'make dead-code')"

qa: test audit ## Full QA pipeline

ci: clean venv install-dev qa ## CI pipeline

docs-build: install-dev ## Build Sphinx HTML docs
	$(SPHINX_BUILD) -b html docs docs/_build/html

docs-linkcheck: install-dev ## Check docs links
	$(SPHINX_BUILD) -b linkcheck docs docs/_build/linkcheck

pre-commit: install-dev ## Run pre-commit hooks against all files (auto-fix, then verify)
	# First run may apply fixes and exit non-zero; run again to verify clean
	$(PRECOMMIT) run --all-files --show-diff-on-failure || true
	$(PRECOMMIT) run --all-files --show-diff-on-failure

.PHONY: venv install-dev clean upgrade format lint lint-fix type-check security dead-code test test-quick audit qa ci docs-build docs-linkcheck pre-commit
