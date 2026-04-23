# Copilot Instructions

This repository's authoritative agent contract lives in
[`CLAUDE.md`](../CLAUDE.md) at the repo root. GitHub Copilot and any other
AI assistant should defer to it. Highlights:

- **Project**: `tagmania` -- Python library for tag-based AWS EC2 cluster
  operations; publishes to PyPI via Python Semantic Release.
- **Conventional commits required**. `fix:` bumps patch, `feat:` bumps minor,
  `feat!:` or `BREAKING CHANGE` bumps major. Do NOT manually edit version
  numbers -- semantic-release owns them.
- **Branch naming**: `{type}/issue-N-description` (e.g., `feat/issue-42-snapshot-tagging`).
- **Do not**: rebase or force-push `main`; commit `.env` files; hand-edit lock
  files (`uv.lock`) -- use `uv lock`/`uv add`/`uv sync` instead.
- **Before committing**: run `uv run pre-commit run --all-files` explicitly.
  Git hooks are NOT auto-installed (they break on Windows/WSL).
- **Tests hit real AWS**. Unit-only run: `uv run pytest -m "not slow and not integration"`.
- **Pipeline gates** (required status checks on `main`): Code quality,
  Security, Unit tests, Compliance, Build validation, Acceptance tests.

See [`CLAUDE.md`](../CLAUDE.md) for the full spec including architecture,
command reference, and CI/CD flow.
