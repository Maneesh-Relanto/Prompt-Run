.DEFAULT_GOAL := help

# ── Variables ──────────────────────────────────────────────────────────────────
PYTHON  ?= python
PIP     ?= pip
PKG      = prompt_run
TESTS    = tests
EXAMPLES = examples

# ── Help ───────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  prompt-run — development commands"
	@echo ""
	@echo "  Setup"
	@echo "    make install        Install package in editable mode with dev deps"
	@echo "    make install-all    Install with all provider SDKs (anthropic + openai)"
	@echo ""
	@echo "  Quality"
	@echo "    make test           Run the full test suite"
	@echo "    make test-v         Run tests with verbose output"
	@echo "    make lint           Ruff check + format check + mypy"
	@echo "    make format         Auto-fix formatting with ruff"
	@echo "    make typecheck      Run mypy only"
	@echo "    make check          lint + test (run before pushing)"
	@echo ""
	@echo "  Prompts"
	@echo "    make validate       Validate all example .prompt files"
	@echo ""
	@echo "  Build & Release"
	@echo "    make build          Build sdist + wheel"
	@echo "    make publish        Upload to PyPI (requires twine)"
	@echo "    make publish-test   Upload to TestPyPI"
	@echo ""
	@echo "  Housekeeping"
	@echo "    make clean          Remove build artifacts and __pycache__"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────────
.PHONY: install
install:
	$(PIP) install -e ".[dev]"

.PHONY: install-all
install-all:
	$(PIP) install -e ".[all,dev]"

# ── Test ───────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	$(PYTHON) -m pytest $(TESTS) --tb=short -q

.PHONY: test-v
test-v:
	$(PYTHON) -m pytest $(TESTS) -v

.PHONY: test-cov
test-cov:
	$(PYTHON) -m pytest $(TESTS) --cov=$(PKG) --cov-report=term-missing --cov-report=html

# ── Lint & Format ──────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	ruff check .
	ruff format --check .
	$(MAKE) typecheck

.PHONY: format
format:
	ruff format .
	ruff check --fix .

.PHONY: typecheck
typecheck:
	mypy $(PKG) --ignore-missing-imports

# ── Combined check (run before pushing) ───────────────────────────────────────
.PHONY: check
check: lint test

# ── Prompts ────────────────────────────────────────────────────────────────────
.PHONY: validate
validate:
	prompt validate $(EXAMPLES)/*.prompt

# ── Build ──────────────────────────────────────────────────────────────────────
.PHONY: build
build: clean
	$(PYTHON) -m build

.PHONY: publish
publish: build
	twine upload dist/*

.PHONY: publish-test
publish-test: build
	twine upload --repository testpypi dist/*

# ── Clean ──────────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/
