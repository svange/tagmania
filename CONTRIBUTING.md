# Contributing to <project-name>

Thank you for considering contributing! We welcome pull‑requests from everyone. This guide describes our development workflow, coding standards, and review process so that your contribution can be merged smoothly.

---

## 📜 Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Coding Standards](#coding-standards)
4. [Testing & Quality Gates](#testing--quality-gates)
5. [Commit & PR Guidelines](#commit--pr-guidelines)
6. [Documentation](#documentation)
7. [Issue Reporting](#issue-reporting)
8. [Security Policy](#security-policy)
9. [Code of Conduct](#code-of-conduct)

---

## Getting Started

### 1. Fork & Clone

```bash
# 1. Fork via the GitHub UI
# 2. Clone **your fork** locally
$ git clone https://github.com/<your-gh-username>/<project-name>.git
$ cd <project-name>

# 3. Add upstream remote so you can pull future changes
$ git remote add upstream https://github.com/<upstream-org>/<project-name>.git
$ git fetch upstream
```

### 2. Set Up a Local Dev Environment

We use **Python ≥ 3.12** with [Poetry](https://python-poetry.org/) for dependency management.

```bash
# Install dependencies
$ poetry install

# Activate the virtualenv if necessary
$ poetry shell

# Install git hooks (lint + format on commit)
$ pre-commit install
```
---

## Development Workflow

1. **Sync & Branch**

   ```bash
   $ git checkout main && git pull upstream main
   $ git checkout -b feat/<short‑description>
   ```
2. **Code** – keep commits small & logically separated.
3. **Run quality gates** (pytest, pre-commit) locally.
4. **Push** your branch and open a **draft PR** early – CI will run automatically.
5. Mark the PR **“Ready for review”** when all checks pass and the PR description is complete.

> We squash‑merge into `main`; keep your branch history tidy.

---

## Coding Standards

| Topic           | Tool / Rule                      |
| --------------- | -------------------------------- |
| Formatting      | `black --line-length 88`         |
| Import ordering | `ruff --select I` (isort rules)  |
| Linting         | `ruff` (pylint‑level strictness) |
| Typing          | `mypy` (strict mode)             |
| Docstrings      | Google‑style (`pydocstyle`)      |
| Tests           | `pytest` + `pytest‑cov`          |

Use type hints everywhere. Functions without type annotations will **fail CI**.

---

## Testing & Quality Gates

```bash
# Run formatters & linters
$ pre-commit run --all-files
```

The **GitHub Actions** pipeline will replicate these steps and block merges if any check fails.

---

## Commit & PR Guidelines

### Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) spec to automate releases and changelogs.

```
<type>[optional scope]: <description>

[optional body]
[optional footer]
```

*Examples*: `feat(api): add /users endpoint`, `fix(cli): handle empty config`, `chore: bump dev deps`.

### Pull‑Request Checklist

* [ ] Title uses *Conventional Commits* style.
* [ ] Description explains **why** + **what**.
* [ ] Linked to an open issue (if applicable).
* [ ] Added/updated tests.
* [ ] `make lint` & `make test` pass locally.
* [ ] Docs and type hints updated.

---

## Documentation

All public classes, functions, and modules require docstrings. We generate documentation with **pdoc**; run locally with:

---

## Issue Reporting

Before opening a new issue, please:

1. **Search** existing issues and discussions.
2. If none match, open a new issue using the **Bug** or **Feature** template.
3. Provide a **minimal reproducible example**, expected vs. actual behaviour, and environment details.

---

## Security Policy

Please **do not** file public issues for security vulnerabilities. Instead, email the owner of this repository. We follow [Coordinated Disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure).

---

## Code of Conduct

This project adheres to the [Contributor Covenant](https://www.contributor-covenant.org/) v2.1. By participating, you agree to abide by its terms.

---

## Need Help?

Open a discussion or hop into the project chat (see README). We’re happy to help you get started!
