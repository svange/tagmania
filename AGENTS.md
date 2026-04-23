# Agent Guidance

This repository uses [`CLAUDE.md`](./CLAUDE.md) as the authoritative source
of agent guidance. Any AI agent (Claude Code, GitHub Copilot, Cursor, Gemini,
etc.) working in this repo should read `CLAUDE.md` first.

Key points:

- **Project**: `tagmania` is a Python library (published to PyPI) that manages
  AWS EC2 clusters through tag-based operations.
- **Default branch**: `main`.
- **Versioning**: Python Semantic Release -- never edit version numbers
  manually. Conventional-commit `fix:`/`feat:`/`feat!:` drives semver.
- **Tests hit real AWS**: integration tests require a `test1` cluster. An
  ephemeral CFN stack (`template.yaml`) provisions the fixture in CI.
- **Pipeline gates**: `Code quality`, `Security`, `Unit tests`, `Compliance`,
  `Build validation`, `Acceptance tests` are required status checks on `main`.
- **No rebase / no force push on `main`**. Merge commits only.

For the full contract (commands, workflow, critical rules, architecture,
CI/CD flow), see [`CLAUDE.md`](./CLAUDE.md).
