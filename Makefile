# ScreenScribe Makefile
# Uses uv as package manager

.PHONY: help install dev lint format test test-unit test-integration test-all typecheck security clean

# Default target
help:
	@echo "ScreenScribe - Video Review Automation"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install production dependencies"
	@echo "  dev              Install dev dependencies"
	@echo ""
	@echo "Quality:"
	@echo "  lint             Run linter (ruff check)"
	@echo "  format           Format code (ruff format)"
	@echo "  typecheck        Run type checker (mypy)"
	@echo "  security         Run security checks (bandit)"
	@echo "  check            Run all quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run unit tests (default)"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests (requires LIBRAXIS_API_KEY)"
	@echo "  test-all         Run all tests including integration"
	@echo "  test-cov         Run tests with coverage report"
	@echo ""
	@echo "Other:"
	@echo "  clean            Remove cache and build artifacts"
	@echo "  run              Run ScreenScribe CLI"

# ============================================================================
# Setup
# ============================================================================

install:
	uv pip install -e .

dev:
	uv pip install -e ".[dev]" || uv pip install -e . && uv pip install pytest ruff mypy bandit

# ============================================================================
# Code Quality
# ============================================================================

lint:
	uv run ruff check screenscribe tests

format:
	uv run ruff format screenscribe tests
	uv run ruff check --fix screenscribe tests

typecheck:
	uv run mypy screenscribe

security:
	uv run bandit -r screenscribe -c pyproject.toml

check: lint typecheck security
	@echo "All quality checks passed!"

# ============================================================================
# Testing
# ============================================================================

# Default test target - unit tests only (fast, no API required)
test: test-unit

test-unit:
	uv run pytest tests/ -v -m "not integration" --tb=short

test-integration:
	@if [ -z "$$LIBRAXIS_API_KEY" ]; then \
		echo "Error: LIBRAXIS_API_KEY environment variable is required"; \
		echo "Usage: LIBRAXIS_API_KEY=xxx make test-integration"; \
		exit 1; \
	fi
	uv run pytest tests/ -v -m "integration" --tb=short

test-all:
	@if [ -z "$$LIBRAXIS_API_KEY" ]; then \
		echo "Warning: LIBRAXIS_API_KEY not set, skipping integration tests"; \
		uv run pytest tests/ -v -m "not integration" --tb=short; \
	else \
		uv run pytest tests/ -v --tb=short; \
	fi

test-cov:
	uv run pytest tests/ -v -m "not integration" --cov=screenscribe --cov-report=term-missing --cov-report=html

# ============================================================================
# Development Helpers
# ============================================================================

run:
	uv run screenscribe --help

clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf screenscribe/__pycache__
	rm -rf tests/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# CI targets
ci-lint: lint typecheck security

ci-test:
	uv run pytest tests/ -v -m "not integration" --tb=short --junitxml=test-results.xml

ci-test-integration:
	uv run pytest tests/ -v -m "integration" --tb=short --junitxml=integration-results.xml
