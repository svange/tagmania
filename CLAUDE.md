# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tagmania is a Python package that provides tools for managing AWS EC2 clusters through tag-based operations. It offers command-line utilities for starting, stopping, and creating snapshots of clusters identified by their "Cluster" tag.

## Development Commands

### Dependencies and Environment
- **Install dependencies**: `poetry install`
- **Install project in development mode**: `poetry install --no-interaction`

### Testing
- **Run tests**: `poetry run pytest tests`
- **Run tests with HTML report**: `poetry run pytest tests` (generates `test-report.html`)
- **Test configuration**: Tests are configured in `pyproject.toml` with markers for different test types (`redundant`, `end_to_end`, `no_infra`, `skip_ci`)

### Code Quality
- **Linting**: `ruff check` (via poetry: `poetry run ruff check`)
- **Code formatting**: `black .` (via poetry: `poetry run black .`)
- **Import sorting**: `isort .` (via poetry: `poetry run isort .`)
- **Pre-commit hooks**: `pre-commit run --all-files`

### Documentation
- **Generate docs**: `poetry run pdoc tagmania --output-dir docs`

### Release
- **Semantic release**: `poetry run semantic-release version`
- **Build package**: `poetry build`

## Architecture

### Core Components

**ClusterSet** (`src/tagmania/iac_tools/clusterset.py`): Central class that manages collections of EC2 instances based on cluster tags. Provides the foundation for all cluster operations with built-in safety limits (`_MAX_ITEMS = 150`) and automation tracking (`AUTOMATION_KEY = 'SNAPSHOT_MANAGER'`).

**TagSet** (`src/tagmania/iac_tools/tagset.py`): Handles tag operations on AWS resources.

**FilterSet** (`src/tagmania/iac_tools/filterset.py`): Manages AWS resource filtering based on tags.

### CLI Tools

The package provides three main command-line tools (configured in `pyproject.toml`):

- **cluster-start** → `tagmania.start_cluster:main`: Start EC2 instances in a cluster
- **cluster-stop** → `tagmania.stop_cluster:main`: Stop EC2 instances in a cluster  
- **cluster-snap** → `tagmania.snapshot_manager:main`: Create/restore/delete EBS snapshots for a cluster

### Key Patterns

- **Tag-based resource identification**: All operations rely on the "Cluster" tag to identify related resources
- **AWS profile support**: All tools accept `--profile` parameter for AWS credential management
- **Lazy collections**: Uses lazy evaluation with safety limits to prevent performance issues
- **Automation tracking**: Uses `AUTOMATION_KEY` to ensure only managed resources are modified

### Dependencies

- **Runtime**: `boto3` for AWS SDK operations
- **Development**: `pytest`, `ruff`, `black`, `isort`, `pre-commit`, `pdoc`
- **Release**: `python-semantic-release` with conventional commit parsing

### CI/CD

Uses GitHub Actions with:
- Pre-commit checks (ruff, black, etc.)
- AWS infrastructure deployment via SAM
- Python 3.12 testing with Poetry
- Semantic versioning and PyPI publishing
- Documentation generation with pdoc and GitHub Pages deployment
