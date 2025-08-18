# Contributing to Tagmania

Thank you for considering contributing! We welcome pull requests from everyone. This guide describes our fork-based development workflow, coding standards, and review process so that your contribution can be merged smoothly.

---

## 📜 Table of Contents

1. [Fork-Based Development Model](#fork-based-development-model)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Keeping Your Fork Updated](#keeping-your-fork-updated)
5. [Coding Standards](#coding-standards)
6. [Testing & Quality Gates](#testing--quality-gates)
7. [Commit & PR Guidelines](#commit--pr-guidelines)
8. [Documentation](#documentation)
9. [Issue Reporting](#issue-reporting)
10. [Security Policy](#security-policy)
11. [Code of Conduct](#code-of-conduct)

---

## Fork-Based Development Model

Tagmania uses a **fork-based development model**. This means:
- Contributors work in their own fork of the repository
- All changes are submitted via pull requests from forks
- The main repository remains clean and stable
- Contributors maintain full control over their development branches

---

## Getting Started

### 1. Fork the Repository

1. Navigate to [https://github.com/svange/tagmania](https://github.com/svange/tagmania)
2. Click the **Fork** button in the top-right corner
3. Select your GitHub account as the destination
4. Wait for the fork to complete

### 2. Clone Your Fork Locally

```bash
# Clone YOUR fork (not the main repository)
git clone https://github.com/YOUR-USERNAME/tagmania.git
cd tagmania

# Add the original repository as "upstream" remote
git remote add upstream https://github.com/svange/tagmania.git

# Verify your remotes
git remote -v
# You should see:
# origin    https://github.com/YOUR-USERNAME/tagmania.git (fetch)
# origin    https://github.com/YOUR-USERNAME/tagmania.git (push)
# upstream  https://github.com/svange/tagmania.git (fetch)
# upstream  https://github.com/svange/tagmania.git (push)
```

### 3. Set Up Development Environment

We use **Python ≥ 3.9** with [Poetry](https://python-poetry.org/) for dependency management.

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell

# Install pre-commit hooks (automatic formatting and linting)
poetry run pre-commit install

# Verify installation
poetry run pytest tests/
```

---

## Development Workflow

### 1. Create a Feature Branch

**⚠️ IMPORTANT**: Branch naming is strictly enforced. The CI/CD pipeline only runs on PRs from branches with these prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`. PRs from incorrectly named branches will not trigger automated testing.

```bash
# Always start from an updated main branch
git checkout main
git fetch upstream
git merge upstream/main

# Create your feature branch with REQUIRED prefix
git checkout -b feat/add-instance-filtering
# Or for bug fixes:
git checkout -b fix/snapshot-timeout-issue
# Or for documentation:
git checkout -b docs/update-api-reference
```

**Required Branch Naming Conventions** (pipeline will not run without these):
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates (only triggers on branches matching this pattern)
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes
- `chore/` - Maintenance tasks

**Note**: The GitHub Actions workflow is configured to run only on branches matching these patterns. Using any other naming convention will result in your PR not being tested automatically.

### 2. Make Your Changes

- Keep commits small and focused
- Write clear, descriptive commit messages
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/test_snapshot_manager.py

# Run with coverage report
poetry run pytest tests/ --cov=tagmania

# Run linting and formatting
poetry run pre-commit run --all-files

# Run specific linters
poetry run ruff check
poetry run black .
```

### 4. Push to Your Fork

```bash
# Push your branch to your fork
git push origin feat/add-instance-filtering
```

### 5. Create a Pull Request

1. Go to your fork on GitHub
2. Click "Pull requests" → "New pull request"
3. Ensure base repository is `svange/tagmania` and base branch is `main`
4. Select your feature branch from your fork
5. Fill out the PR template with:
   - Clear description of changes
   - Link to related issue (if applicable)
   - Testing performed
   - Breaking changes (if any)
6. Submit the pull request

---

## Keeping Your Fork Updated

### Regular Updates (Recommended)

```bash
# Fetch latest changes from upstream
git fetch upstream

# Update your local main branch
git checkout main
git merge upstream/main

# Push updates to your fork
git push origin main

# Rebase your feature branch (if you have one in progress)
git checkout feat/your-feature
git rebase main
```

### Handling Conflicts

If you encounter conflicts during rebase:

```bash
# Start interactive rebase
git rebase -i main

# Resolve conflicts in each file
# After fixing conflicts, stage the changes
git add .

# Continue rebase
git rebase --continue

# If things go wrong, abort and try again
git rebase --abort
```

### Cherry-Picking Specific Commits

Sometimes you may need to selectively apply commits from upstream:

```bash
# Fetch latest from upstream
git fetch upstream

# Find the commit hash you want
git log upstream/main --oneline

# Cherry-pick the commit to your branch
git cherry-pick COMMIT_HASH

# If there are conflicts, resolve them and continue
git add .
git cherry-pick --continue
```

### Syncing a Stale Fork

If your fork is significantly behind:

```bash
# Option 1: Reset to upstream (CAUTION: destroys local changes)
git checkout main
git fetch upstream
git reset --hard upstream/main
git push origin main --force

# Option 2: Merge with history preservation
git checkout main
git fetch upstream
git merge upstream/main
# Resolve any conflicts
git push origin main
```

---

## Coding Standards

| Topic           | Tool / Rule                      | Command                           |
| --------------- | -------------------------------- | --------------------------------- |
| Formatting      | `black` (line length 88)        | `poetry run black .`              |
| Import ordering | `isort`                          | `poetry run isort .`              |
| Linting         | `ruff`                           | `poetry run ruff check`           |
| Type checking   | `mypy` (when applicable)         | `poetry run mypy tagmania`        |
| Docstrings      | Google-style                     | Required for public APIs         |
| Tests           | `pytest` + `pytest-cov`          | `poetry run pytest tests/`       |

### Code Style Guidelines

- Use descriptive variable and function names
- Keep functions focused and under 50 lines when possible
- Add type hints for function parameters and returns
- Write docstrings for all public functions and classes
- Follow PEP 8 style guidelines
- Prefer explicit over implicit

---

## Testing & Quality Gates

### Running Tests Locally

```bash
# Full test suite with HTML report
poetry run pytest tests/

# Run only fast tests (skip slow AWS operations)
poetry run pytest tests/ -m "not slow"

# Run with coverage
poetry run pytest tests/ --cov=tagmania --cov-report=html

# Run pre-commit checks
poetry run pre-commit run --all-files
```

### CI/CD Pipeline

Our GitHub Actions pipeline automatically:
1. Runs all tests on Python 3.9, 3.10, 3.11, 3.12
2. Checks code formatting with black
3. Runs linting with ruff
4. Validates commit messages
5. Builds documentation
6. Creates releases on merge to main

---

## Commit & PR Guidelines

### Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat: add regex filtering for targeted restore`
- `fix(cli): handle empty cluster names gracefully`
- `docs: update installation instructions for Poetry`
- `test: add integration tests for snapshot creation`
- `chore: update dependencies to latest versions`

### Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex logic
- [ ] Documentation updated (if applicable)
- [ ] Tests added/updated and passing
- [ ] `poetry run pre-commit run --all-files` passes
- [ ] Commit messages follow Conventional Commits format
- [ ] PR title follows Conventional Commits format
- [ ] Breaking changes are clearly documented

### PR Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. All review comments addressed
4. Final approval from maintainer
5. Squash merge into main branch

---

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def create_snapshot(cluster_name: str, label: str = "default") -> List[str]:
    """Create EBS snapshots for all volumes in a cluster.

    Args:
        cluster_name: Name of the cluster to snapshot.
        label: Label to tag snapshots with for identification.

    Returns:
        List of created snapshot IDs.

    Raises:
        ValueError: If cluster_name is empty or invalid.
        AWSError: If AWS API calls fail.
    """
```

### Updating Documentation

- API documentation is auto-generated with `pdoc`
- Update README.md for user-facing changes
- Add docstrings for all new public functions
- Include examples in docstrings when helpful

---

## Issue Reporting

Before opening an issue:

1. **Search existing issues** to avoid duplicates
2. **Check discussions** for questions and feature requests
3. **Try latest version** to see if issue is already fixed

When opening an issue, provide:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, tagmania version)
- Relevant error messages and logs

---

## Security Policy

### Reporting Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities. Instead:

1. Email the repository owner directly
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Wait for acknowledgment before public disclosure

We follow [Coordinated Disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure) practices.

---

## Code of Conduct

This project adheres to the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct v2.1.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## Need Help?

- 💬 [GitHub Discussions](https://github.com/svange/tagmania/discussions) - Ask questions and share ideas
- 📖 [Documentation](https://svange.github.io/tagmania) - Read the full documentation
- 🐛 [Issue Tracker](https://github.com/svange/tagmania/issues) - Report bugs and request features

We're happy to help you get started with contributing!
