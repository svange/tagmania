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

Direct commands (without make):
```bash
uv run ruff check src/                       # Lint
uv run mypy src/                             # Type check
uv run pre-commit run --all-files            # Run all pre-commit hooks
```

## Critical Rules

- **No rebase on main**: NEVER use `git pull --rebase` or `git rebase` on the default branch. This repo uses CI and rewriting history on main breaks it. Always use merge commits.
- **No manual versioning**: NEVER manually edit version numbers. Python Semantic Release owns versioning.
- **No lock file edits**: NEVER directly write text into lock files (uv.lock, package-lock.json, poetry.lock, yarn.lock). Always use package manager commands (`uv lock`, `uv add`, `npm install`) to regenerate them. When a package manager command updates a lock file, ALWAYS stage and include it in the commit -- lock file changes must never be left uncommitted.
- **No .env commits**: NEVER commit .env files. Use .env.example for templates.
- **No force push to main**: NEVER use `git push --force` on main or the default branch.

Version in `pyproject.toml` and `src/tagmania/__init__.py`:
- Bumped automatically via conventional commits:
  - `fix:` -> patch (2.5.1 -> 2.5.2)
  - `feat:` -> minor (2.5.1 -> 2.6.0)
  - `feat!:` -> major (2.5.1 -> 3.0.0)
- Tag format: `v{version}`

## Conventions

- **Commits**: Conventional commits required. `fix:` = patch, `feat:` = minor, `feat!:` / `BREAKING CHANGE` = major.
- **Branches**: `{type}/issue-N-description` where type is one of: feat, fix, docs, refactor, test, chore, ci, build, style, revert, perf.
- **PRs**: Target the default development branch. Enable automerge.
- **Pre-commit**: Run `uv run pre-commit run --all-files` explicitly before committing (no automatic git hooks -- they break across Windows/WSL). If checks fail, fix the issue and create a NEW commit (do not amend).
- **Tests**: Write tests for all new functionality. Bug fixes require regression tests.

## Development Workflow

**IMPORTANT**: Always follow this sequence. Do NOT skip to step 3 without completing step 2 first.

1. **Pick an issue**: `/ai-pick-issue` -- find or get assigned work
2. **Prepare branch**: `/ai-prepare-branch` -- REQUIRED before any code changes. Creates a fresh branch from the latest base (main or dev), syncs upstream, sets up remote tracking. Never start coding on an existing branch from a previous task.
3. **Develop**: Write code with tests, following project conventions
4. **Submit**: `/ai-submit-work` -- runs all checks locally, commits, pushes, creates automerge PR
5. **Monitor**: `/ai-monitor-pipeline` -- watches CI, diagnoses failures, auto-fixes and re-pushes

## Testing

Tests are all integration tests that hit real AWS. They are ordered by filename prefix (`test_10_`, `test_20_`, `test_30_`) and depend on a "test1" cluster existing in AWS.

Markers:
- `slow` - real AWS operations taking several minutes (snapshot create/restore)
- `integration` - requires AWS credentials
- `fast` - quick tests

```bash
uv run pytest -m "not slow and not integration"   # Fast tests only (no coverage)
uv run pytest -m "integration or slow"             # Integration tests (requires AWS)
uv run pytest --cov=src                            # Full suite with coverage (threshold from pyproject.toml)
```

Coverage threshold lives in `pyproject.toml` under `[tool.coverage.report] fail_under`. `coverage.py` enforces it automatically whenever `--cov` is passed to pytest. Never pass `--cov-fail-under` on the CLI or in CI -- pyproject.toml is the single source of truth.

## Key Commands

```bash
# Git
git status                    # Check working tree
git log --oneline -10         # Recent commits

# GitHub CLI
gh issue list --state open    # View open issues
gh pr create                  # Create pull request
gh pr merge --auto --merge    # Enable automerge
gh run list                   # List workflow runs
gh run view <id>              # View run details
gh run watch <id>             # Watch run in real-time
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

GitHub Actions pipeline (`.github/workflows/pipeline.yaml`) gates by canonical stage names:

### Pre-deploy gates (run on both PR and push, no AWS required)

- `Code quality` -- pre-commit hooks, ruff, mypy
- `Security` -- bandit, pip-audit, semgrep
- `Compliance` -- license scans
- `Build validation` -- sdist/wheel build
- `Unit tests` -- fast regression check (`pytest -m "fast or (not slow and not integration)"`); no coverage enforcement at this stage

### Post-deploy gates (AWS-dependent; gated on `approval-required` environment for PRs)

- `Deploy test infrastructure` -- transient CFN stack providing the `test1` cluster fixture
- `Acceptance tests` -- full suite with `pytest --cov=src`; `[tool.coverage.report] fail_under = 80` in pyproject.toml enforces the threshold
- `Cleanup test infrastructure` -- deletes the CFN stack (always runs, including on test failure)

"Deploy" here means **ephemeral test fixture**, not production artifact. The real deploy is the PyPI publish at the end of the pipeline.

### Flow by trigger

- **Draft PR**: pre-deploy gates only. AWS jobs skipped (`if: !github.event.pull_request.draft`).
- **Ready-for-review PR**: pre-deploy gates run automatically. AWS jobs queue on the `approval-required` environment -- a maintainer clicks "Approve and deploy" to run the acceptance flow. Required status check `Acceptance tests` must pass for merge.
- **Push to main/dev** (post-merge): all gates run unattended. Release and publish gated on acceptance.

### Concurrency

AWS-touching jobs share `concurrency.group: testing-stack-${{ github.repository }}` to prevent parallel PRs from colliding on the shared test stack. Runs serialize through that group.

### Required status checks (ruleset)

`Code quality`, `Security`, `Unit tests`, `Compliance`, `Build validation`, `Acceptance tests`.
