# Project Notes

<!-- Project-specific notes for AI coding agents. This file is created
     once by ai-shell and NEVER overwritten or deleted by scaffold
     operations (--update, --clean). Each agent's /init reads this file
     and integrates it into the appropriate config (CLAUDE.md, AGENTS.md,
     CONVENTIONS.md). -->

## Project Overview

<!-- Describe your project here. This file is read automatically by Codex and opencode. -->

## Critical Rules

- **No rebase on main**: NEVER use `git pull --rebase` or `git rebase` on the default branch. Use merge commits only.
- **No manual versioning**: NEVER manually edit version numbers. Semantic Release manages versions via conventional commits.
- **No lock file edits**: NEVER manually edit lock files (uv.lock, package-lock.json, poetry.lock, yarn.lock). They are auto-generated.
- **No .env commits**: NEVER commit .env files. Use .env.example for templates.
- **No force push to main**: NEVER use `git push --force` on main or the default branch.

## Development Commands

```bash
uv sync --all-extras                         # Install dependencies
uv run pytest                                # Run tests
uv run pytest --cov=src --cov-fail-under=80  # Tests with coverage
uv run ruff check src/                       # Lint
uv run mypy src/                             # Type check
uv run pre-commit run --all-files            # Run all pre-commit hooks
```

## Conventions

- **Commits**: Conventional commits required. `fix:` = patch, `feat:` = minor, `feat!:` / `BREAKING CHANGE` = major.
- **Branches**: `{type}/issue-N-description` where type is one of: feat, fix, docs, refactor, test, chore, ci, build, style, revert, perf.
- **PRs**: Target the default development branch. Enable automerge.
- **Pre-commit**: Run `uv run pre-commit run --all-files` explicitly before committing (no automatic git hooks -- they break across Windows/WSL). If checks fail, fix the issue and create a NEW commit (do not amend).
- **Tests**: Write tests for all new functionality. Bug fixes require regression tests.

## Development Workflow

1. **Pick an issue**: Find or get assigned an issue to work on
2. **Create a branch**: `git checkout -b feat/issue-N-description`
3. **Develop**: Write code with tests, following project conventions
4. **Check**: Run `uv run pre-commit run --all-files` and `uv run pytest`
5. **Submit**: Commit with conventional messages, create PR
6. **Monitor**: Watch CI pipeline, fix any failures

## Key Commands

```bash
# Git
git status                    # Check working tree
git log --oneline -10         # Recent commits

# GitHub CLI
gh issue list --state open    # View open issues
gh pr create                  # Create pull request
gh pr merge --auto --squash   # Enable automerge
gh run list                   # List workflow runs
gh run view <id>              # View run details
gh run watch <id>             # Watch run in real-time
```

## Architecture

<!-- Key architectural decisions, dependency flow, module structure -->

## Domain Concepts

<!-- Important domain terms, business rules, or constraints -->

## Project-Specific Commands

<!-- Any project-specific commands beyond the defaults above -->

## Notes

<!-- Anything else an AI agent should know about this project -->
