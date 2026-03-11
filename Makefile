# ScreenScribe Makefile
# Uses uv as package manager

.PHONY: help install dev setup-hooks lint format test test-unit test-integration test-all typecheck security clean version version-patch version-minor version-major analyze

# Default target
help:
	@echo "ScreenScribe - Video Review Automation"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install CLI + git hooks"
	@echo "  dev              Install dev dependencies + git hooks"
	@echo "  setup-hooks      Install pre-commit/pre-push hooks only"
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
	@echo "  test-integration Run integration tests (uses config or LIBRAXIS_API_KEY)"
	@echo "  test-all         Run all tests including integration"
	@echo "  test-cov         Run tests with coverage report"
	@echo ""
	@echo "Commands:"
	@echo "  analyze          Start interactive video analysis server"
	@echo ""
	@echo "Versioning:"
	@echo "  version          Show current version"
	@echo "  version-patch    Bump patch version (0.1.2 -> 0.1.3)"
	@echo "  version-minor    Bump minor version (0.1.2 -> 0.2.0)"
	@echo "  version-major    Bump major version (0.1.2 -> 1.0.0)"
	@echo ""
	@echo "Other:"
	@echo "  clean            Remove cache and build artifacts"
	@echo "  run              Run ScreenScribe CLI"

# ============================================================================
# Setup
# ============================================================================

install: setup-hooks
	-uv tool uninstall screenscribe 2>/dev/null
	uv tool install . --reinstall --force

dev: setup-hooks
	uv sync --dev

setup-hooks:
	@if [ -f .pre-commit-config.yaml ]; then \
		echo "Installing pre-commit hooks..."; \
		GLOBAL_HOOKS=$$(git config --global core.hooksPath 2>/dev/null || true); \
		if [ -n "$$GLOBAL_HOOKS" ]; then \
			git config --global --unset core.hooksPath 2>/dev/null || true; \
		fi; \
		uv run pre-commit install --install-hooks || true; \
		uv run pre-commit install --hook-type pre-push || true; \
		if [ -n "$$GLOBAL_HOOKS" ]; then \
			git config --global core.hooksPath "$$GLOBAL_HOOKS"; \
		fi; \
		git config --local core.hooksPath .git/hooks; \
		echo "Hooks installed: pre-commit, pre-push"; \
	fi

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
	uv run pytest tests/ -v -m "integration" --tb=short

test-all:
	uv run pytest tests/ -v --tb=short

test-cov:
	uv run pytest tests/ -v -m "not integration" --cov=screenscribe --cov-report=term-missing --cov-report=html

# ============================================================================
# Development Helpers
# ============================================================================

run:
	uv run screenscribe --help

analyze:
	@if [ -z "$(VIDEO)" ]; then \
		echo "Usage: make analyze VIDEO=path/to/video.mov [PORT=8766]"; \
		exit 1; \
	fi
	uv run screenscribe analyze "$(VIDEO)" --port $(or $(PORT),8766)

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

# ============================================================================
# Versioning
# ============================================================================

# Get current version from pyproject.toml
CURRENT_VERSION := $(shell grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

version:
	@echo "Current version: $(CURRENT_VERSION)"

# Bump patch version (0.1.2 -> 0.1.3)
version-patch:
	@echo "Bumping patch version..."
	@NEW_VERSION=$$(echo "$(CURRENT_VERSION)" | awk -F. '{print $$1"."$$2"."$$3+1}'); \
	echo "$(CURRENT_VERSION) -> $$NEW_VERSION"; \
	sed -i '' "s/version = \"$(CURRENT_VERSION)\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	sed -i '' "s/__version__ = \"$(CURRENT_VERSION)\"/__version__ = \"$$NEW_VERSION\"/" screenscribe/__init__.py; \
	echo "Updated pyproject.toml and screenscribe/__init__.py"

# Bump minor version (0.1.2 -> 0.2.0)
version-minor:
	@echo "Bumping minor version..."
	@NEW_VERSION=$$(echo "$(CURRENT_VERSION)" | awk -F. '{print $$1"."$$2+1".0"}'); \
	echo "$(CURRENT_VERSION) -> $$NEW_VERSION"; \
	sed -i '' "s/version = \"$(CURRENT_VERSION)\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	sed -i '' "s/__version__ = \"$(CURRENT_VERSION)\"/__version__ = \"$$NEW_VERSION\"/" screenscribe/__init__.py; \
	echo "Updated pyproject.toml and screenscribe/__init__.py"

# Bump major version (0.1.2 -> 1.0.0)
version-major:
	@echo "Bumping major version..."
	@NEW_VERSION=$$(echo "$(CURRENT_VERSION)" | awk -F. '{print $$1+1".0.0"}'); \
	echo "$(CURRENT_VERSION) -> $$NEW_VERSION"; \
	sed -i '' "s/version = \"$(CURRENT_VERSION)\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	sed -i '' "s/__version__ = \"$(CURRENT_VERSION)\"/__version__ = \"$$NEW_VERSION\"/" screenscribe/__init__.py; \
	echo "Updated pyproject.toml and screenscribe/__init__.py"
