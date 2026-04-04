# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tagmania is a Python package for managing AWS EC2 clusters through tag-based operations. It provides CLI tools for starting, stopping, and snapshotting clusters identified by their "Cluster" tag. Published to PyPI on release.

## Development

```bash
uv sync --all-extras          # Install all dependencies
make format                   # Run all pre-commit hooks (ruff format, ruff check, mypy, etc.)
make test-unit                # Unit tests with coverage
make test-integration         # Integration tests (requires AWS credentials)
make test                     # All tests
make security                 # Bandit + pip-audit
make typecheck                # mypy
```

Run a single test:
```bash
uv run pytest tests/test_10_cluster_set.py::TestBasicClusterOperations::test_clusterset_stop -v
```

Pre-commit hooks run automatically: ruff format, ruff check (with `--fix`), mypy, uv lock check, and standard checks (trailing whitespace, merge conflicts, private key detection, .env file blocking). Run manually with `make format` or `uv run pre-commit run --all-files`.

## CRITICAL: No Rebase on Main

**NEVER use `git pull --rebase` or `git rebase` on `main`.** This repo uses CI and rewriting history on main breaks it. Always use merge commits.

## CRITICAL: Version Management

**NEVER manually edit version numbers.** Python Semantic Release owns versioning.

- Version in `pyproject.toml` and `src/tagmania/__init__.py`
- Bumped automatically via conventional commits:
  - `fix:` -> patch (2.5.1 -> 2.5.2)
  - `feat:` -> minor (2.5.1 -> 2.6.0)
  - `feat!:` -> major (2.5.1 -> 3.0.0)
- Tag format: `v{version}`

## Testing

Tests are all integration tests that hit real AWS. They are ordered by filename prefix (`test_10_`, `test_20_`, `test_30_`) and depend on a "test1" cluster existing in AWS.

Markers:
- `slow` - real AWS operations taking several minutes (snapshot create/restore)
- `integration` - requires AWS credentials
- `fast` - quick tests

```bash
uv run pytest -m "not slow and not integration"   # Fast tests only
uv run pytest -m "integration or slow"             # Integration tests
uv run pytest --cov=src --cov-fail-under=70        # With coverage threshold
```

## Architecture

### Core Layer (`src/tagmania/iac_tools/`)

**ClusterSet** (`clusterset.py`): Central class. All operations flow through here. Initialized with a cluster name and optional AWS profile. Manages EC2 instances, EBS volumes, and snapshots using tag-based filtering. Key design decisions:
- Safety limit: `_MAX_ITEMS = 150` on all lazy collection materializations
- `AUTOMATION_KEY = 'SNAPSHOT_MANAGER'` - only modifies resources tagged with this key, preventing accidental changes to unmanaged resources
- Targeted operations (`*_targeted` methods) accept regex patterns matched against instance Name tags, enabling partial cluster restores

**TagSet** (`tagset.py`) and **FilterSet** (`filterset.py`): Thin wrappers around AWS's `[{Key, Value}]` tag format and `[{Name, Values}]` filter format respectively. Used everywhere to build AWS API calls.

### CLI Layer (`src/tagmania/`)

Three entry points registered in `pyproject.toml [project.scripts]`:
- `cluster-start` -> `start_cluster:main` - starts stopped instances
- `cluster-stop` -> `stop_cluster:main` - stops running instances
- `cluster-snap` -> `snapshot_manager:main` - backup/restore/list/delete snapshots; supports `--target` regex for partial restores

All CLIs accept `--profile` for AWS credential selection.

### Snapshot Restore Flow

Full restore: stop instances -> detach volumes -> delete volumes -> create volumes from snapshots -> attach volumes. Targeted restore follows the same steps but filtered by instance name regex. Note: instances are NOT auto-started after restore (start calls are commented out).

## CI/CD Pipeline

GitHub Actions pipeline (`.github/workflows/pipeline.yaml`):
- PR: pre-commit checks + unit tests + security scan + license compliance
- Push to main/dev: adds integration tests (with AWS infra deploy) + semantic release + PyPI publish (main -> PyPI, dev -> TestPyPI) + docs to GitHub Pages
