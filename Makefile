.PHONY: help install test test-unit test-integration test-integration-check test-coverage test-fast format security typecheck build clean deploy destroy version release-dry-run

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --all-extras

test: ## Run all tests
	uv run pytest -v

test-unit: ## Run unit tests only
	uv run pytest -m "fast or (not slow and not integration)" --cov=src --cov-report=html --cov-report=xml

test-integration: test-integration-check ## Run integration tests in parallel by cluster (requires AWS credentials)
	@echo "=== Running cluster1, cluster2, and cluster3 tests in parallel ==="
	@uv run pytest -m "cluster1 and (integration or slow)" -v --tb=short & \
	PID1=$$!; \
	uv run pytest -m "cluster2 and (integration or slow)" -v --tb=short & \
	PID2=$$!; \
	uv run pytest -m "cluster3 and (integration or slow)" -v --tb=short & \
	PID3=$$!; \
	wait $$PID1; EC1=$$?; \
	wait $$PID2; EC2=$$?; \
	wait $$PID3; EC3=$$?; \
	echo "=== Running cross-cluster tests ===" ; \
	uv run pytest -m "cluster_all and (integration or slow)" -v --tb=short; \
	EC4=$$?; \
	[ $$EC1 -eq 0 ] && [ $$EC2 -eq 0 ] && [ $$EC3 -eq 0 ] && [ $$EC4 -eq 0 ]

test-integration-check: ## Verify all integration tests have a cluster marker
	@uv run pytest --collect-only -q -m "(integration or slow) and not (cluster1 or cluster2 or cluster3 or cluster_all)" 2>/dev/null; \
	if [ $$? -ne 5 ]; then echo "ERROR: Found integration tests without a cluster marker!" && exit 1; fi

test-coverage: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=70

test-fast: ## Run fast tests (exclude slow/integration)
	uv run pytest -m "fast or (not slow and not integration)" -v

format: ## Run pre-commit hooks (lint + format)
	uv run pre-commit run --all-files

security: ## Run security scans
	uv run bandit -r src/ -ll
	uv run pip-audit --desc || true

typecheck: ## Run type checking
	uv run mypy src/

build: ## Build distribution package
	uv build

clean: ## Clean build artifacts (cross-platform)
	uv run python -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path(d) for d in ['dist', 'build', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'htmlcov']] if p.exists()]"
	uv run python -c "import pathlib; [p.unlink(missing_ok=True) for p in [pathlib.Path('.coverage'), pathlib.Path('coverage.xml'), pathlib.Path('coverage.json')]]"
	uv run python -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	uv run python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
	uv run python -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('*.egg-info')]"

docs: ## Generate documentation
	uv run pdoc --output-dir docs src/tagmania

version: ## Show current version
	@grep 'version = ' pyproject.toml | head -1

release-dry-run: ## Dry run semantic release
	uv run semantic-release version --no-commit --no-tag --no-push
