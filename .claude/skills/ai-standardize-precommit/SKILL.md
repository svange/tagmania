---
name: ai-standardize-precommit
description: Audit and fix pre-commit hook configuration. Ensures consistent developer-side quality gates for formatting, linting, type checking, and secret protection.
argument-hint: "[--validate] [--generate] [--fix]"
---

Audit and fix pre-commit hook configuration for this repository: $ARGUMENTS

Validates that pre-commit hooks (Python) or equivalent tooling (Node) are configured correctly with the right scope, flags, and hook set.

## Usage Examples

- `/ai-standardize-precommit` — Full audit with recommendations
- `/ai-standardize-precommit --validate` — Report issues only
- `/ai-standardize-precommit --generate` — Generate config from template
- `/ai-standardize-precommit --fix` — Auto-fix detected issues

## 1. Detect Ecosystem

```bash
ECOSYSTEM="unknown"
[ -f "pyproject.toml" ] && ECOSYSTEM="python"
[ -f "package.json" ] && ECOSYSTEM="node"
HAS_SAM=false
[ -f "template.yaml" ] || [ -f "infrastructure/template.yaml" ] && HAS_SAM=true
```

## 2. Python Validation

Read `.pre-commit-config.yaml` and check:

### Required hooks

| Hook | Source | Purpose |
|------|--------|---------|
| `check-yaml` | pre-commit-hooks | YAML syntax validation |
| `end-of-file-fixer` | pre-commit-hooks | Files end with newline |
| `trailing-whitespace` | pre-commit-hooks | No trailing whitespace |
| `forbid-env-commit` | local | Block `.env` files from git |
| `ruff-format` | local | Code formatting |
| `ruff-check` | local | Linting with auto-fix |
| `mypy` | local | Type checking |
| `uv-lock-check` | local | Lock file matches pyproject.toml |

Flag missing hooks as **ERROR**.

### Scope correctness

Ruff format and ruff check must cover BOTH `src/` AND `tests/`:
- **Correct**: `entry: uv run --no-sync ruff format src/ tests/`
- **Wrong**: `entry: uv run ruff format src/` (missing tests/)

### Flags

All `uv run` entries should use `--no-sync` to avoid slow dependency resolution on every commit. Exception: `uv-lock-check` uses `uv lock --check` directly.

### SAM template exclusion

If `template.yaml` exists, `check-yaml` must exclude SAM templates (CloudFormation intrinsics are not valid YAML):
```yaml
exclude: '(^templates/.*\.yaml$|.*template\.yaml$)'
```

### Template

If config is missing or `--generate`, read `python-template.pre-commit-config.yaml` from `${CLAUDE_SKILL_DIR}` and adapt:
- Uncomment SAM exclusion if `HAS_SAM=true`
- Adjust source paths if project layout differs

## 3. Node Validation

Check for husky + lint-staged:
```bash
[ -d ".husky" ] && echo "husky found"
grep -q '"lint-staged"' package.json 2>/dev/null && echo "lint-staged found"
```

Verify:
- ESLint configured (`eslint.config.js` or `.eslintrc.*`)
- Prettier configured (`.prettierrc` or equivalent)
- lint-staged runs both on staged files

If no pre-commit quality gates exist: flag as **WARNING**.

## 4. Cross-checks

- **CI alignment**: verify pre-commit or equivalent runs in CI workflow
- **No auto-installed git hooks**: pre-commit should be run explicitly (`uv run pre-commit run --all-files`), not via auto-installed `.git/hooks/` (breaks across Windows/WSL)

## Error Handling

- **No ecosystem detected**: warn, cannot generate template
- **Poetry-based**: adapt commands to `poetry run` instead of `uv run --no-sync`

## Final Output

```
=== Pre-commit Standardization Report ===
Ecosystem: Python | Config: .pre-commit-config.yaml
Action: [Generated | Validated | Fixed]

Required Hooks:
  [PASS] check-yaml (with SAM exclusion)
  [FAIL] ruff-format: scope missing tests/
  [FAIL] uv-lock-check: MISSING

Flags:
  [WARN] ruff-format: missing --no-sync flag

Next steps: /ai-standardize-pipeline | /ai-standardize-repo
```
