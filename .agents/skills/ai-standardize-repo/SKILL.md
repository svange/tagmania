---
name: ai-standardize-repo
description: Audit and fix repository standards (pipeline, rulesets, pre-commit, renovate, release, dotfiles) against universal quality gates.
argument-hint: "[--validate|--fix] [github|pipeline|quality|security|tests|licenses|renovate|release|dotfiles]"
---

Audit and fix repository standards: $ARGUMENTS

Unified standardization skill. Detects project type, audits against the universal standard, and fixes drift. Uses `ai-gh` for GitHub-side config and directly patches local files.

## Usage Examples

```bash
/ai-standardize-repo                 # Full audit, present findings, ask before fixing
/ai-standardize-repo --validate      # Audit only, no changes
/ai-standardize-repo --fix           # Audit and fix everything
/ai-standardize-repo renovate        # Audit+fix just renovate config
/ai-standardize-repo github          # Audit+fix GitHub settings via ai-gh
```

---

## The Standard

### Pipeline Architecture

- **Qualification layer** (pre-merge, universal): 4 protected checks enforced by branch rulesets
- **Delivery layer** (post-merge, varies by type): release/publish/deploy, test stages named by type
- **Adapter layer** (per language/framework): tool choices inside each gate

### 4 Universal Quality Gates

All repos, all languages. These are the branch ruleset status check names.

| # | Gate (status check name) | Python adapter | TypeScript/React adapter |
|---|---|---|---|
| 1 | **Code quality** | ruff format+check, mypy, yaml/whitespace/eof, forbid .env, uv.lock check, `uv build` | biome (lint+format), tsc --noEmit, yaml/whitespace/eof, forbid .env, lockfile check, `npm run build` / `cdk synth` / `sam build` |
| 2 | **Security scanning** | semgrep (p/python, p/owasp-top-ten, p/secrets), pip-audit | semgrep (p/typescript, p/react, p/nodejs, p/owasp-top-ten, p/secrets), npm audit |
| 3 | **Unit tests** | pytest --cov-fail-under=80 | vitest --coverage (threshold >=80%) |
| 4 | **License compliance** | liccheck (enforce block on GPL/AGPL, allow LGPL) + pip-licenses (reporting artifacts) | licensee (enforce block on GPL/AGPL, allow LGPL) |

Build validation is inside Code quality -- "can this code produce its artifact?" is a quality concern.

### 2 Project Types

| Type | Branch strategy | Rulesets | Post-merge delivery |
|---|---|---|---|
| **library** | main-only | 4 checks on main | release -> publish (PyPI/npm) -> docs |
| **service** | dev + main | 4 checks on dev AND main | dev: deploy staging -> integration tests -> e2e tests; main: deploy prod -> smoke tests -> release |

"Service" covers IaC (SAM, CDK, Terraform), frontends (React/Vite/Next.js), APIs, and anything that deploys.

### Language Adapters

- **Python**: uv, ruff, mypy, pytest, semgrep, pip-audit, liccheck + pip-licenses, pre-commit
- **TypeScript**: pnpm, biome, tsc, vitest, semgrep, npm audit, licensee

Framework (SAM/CDK/Terraform/Vite/Next.js) affects only the build step inside Code quality and the deploy step in delivery.

---

## 1. Context Detection

Detect project shape before auditing.

### Repo type
1. Check `ai-shell.toml` for `[project] repo_type` override
2. Check remote branches: if `origin/dev`, `origin/develop`, or `origin/staging` exists -> **service**
3. Otherwise -> **library**

### Language
- `pyproject.toml` exists -> **python**
- `package.json` exists -> **typescript**
- Both exist -> **both** (audit each language's requirements)

### Framework (service repos only)
- `template.yaml` or `template.yml` or `samconfig.toml` -> **SAM**
- `cdk.json` -> **CDK**
- `main.tf` -> **Terraform**
- `vite.config.*` -> **Vite**
- `next.config.*` -> **Next.js**
- None detected -> **plain**

Display detected configuration:
```
Detected: type=service, language=python, framework=sam
Branch strategy: dev+main (dev branch: dev)
```

---

## 2. Audit

Check each concern against the standard. Report as PASS / DRIFT / MISSING with error (E) and warning (W) counts.

### 2a. GitHub settings (`github` section)

**Prerequisite**: `ai-gh` CLI must be available and `.env` must have `GH_REPO`, `GH_ACCOUNT`, `GH_TOKEN`. If missing, report and skip this section.

Run: `ai-gh status --type <library|service> --verbose`

Check:
- Auto-merge enabled
- Merge strategy: merge commits only (no squash, no rebase)
- Delete branch on merge: enabled (unless dev branch exists)
- Rulesets exist and match expected template
- Required status checks match the 4 universal gates: "Code quality", "Security scanning", "Unit tests", "License compliance"

**Note**: ai-gh may still use older gate names (e.g., "Pre-commit checks" instead of "Code quality"). If so, flag this as DRIFT and note that ai-gh templates need updating per augint-github issues.

### 2b. Pipeline (`pipeline` section)

Check `.github/workflows/pipeline.yaml` exists.

Verify it has 4 jobs with these exact `name:` values (these are the status check contract):
1. "Code quality"
2. "Security scanning"
3. "Unit tests"
4. "License compliance"

For each job, check language-appropriate contents:

**Code quality job** must include:
- Python: ruff format check, ruff lint check, mypy, yaml validation, .env blocking, uv.lock check, `uv build` (or framework build command)
- TypeScript: biome check, tsc --noEmit, lockfile check, `npm run build` (or framework build command)

**Security scanning job** must include:
- Python: semgrep with p/python + p/owasp-top-ten + p/secrets rulesets, pip-audit
- TypeScript: semgrep with p/typescript + p/react + p/nodejs rulesets, npm audit
- Must NOT contain bandit (superseded by semgrep)

**Unit tests job** must include:
- Python: pytest with --cov-fail-under=80 (or configured threshold)
- TypeScript: vitest or jest with coverage threshold >=80%

**License compliance job** must include:
- Python: liccheck or pip-licenses with enforcement (must have pass/fail exit code for GPL/AGPL)
- TypeScript: licensee with allowlist enforcement

**Delivery jobs** (post-merge, not in rulesets):
- Library: release, publish, docs jobs
- Service: integration tests, e2e/smoke tests, deploy jobs (named by test type)

### 2c. Pre-commit / hooks (`quality` section)

**Python repos**: Check `.pre-commit-config.yaml` exists and contains:
- `ruff-format` hook covering src/ and tests/
- `ruff-check` hook with --fix covering src/ and tests/
- `mypy` hook covering src/
- `check-yaml` (with SAM template exclusion if framework is SAM)
- `end-of-file-fixer`, `trailing-whitespace`
- `forbid-env-commit` (blocks .env files)
- `uv-lock-check` (validates uv.lock freshness)
- All `uv run` entries use `--no-sync` flag

**TypeScript repos**: Check for biome config (`biome.json` or `biome.jsonc`) and hook integration.

Use `python-template.pre-commit-config.yaml` in this skill's directory as reference template.

### 2d. Renovate (`renovate` section)

Check `renovate.json5` exists.

Validate:
- Correct template for type: library targets main, service targets dev (`baseBranchPatterns`)
- Commit prefix scheme aligns with release config:
  - Library: `chore(deps):` for prod deps (no release trigger), `fix(deps):` for vulnerabilities
  - Service: `fix(deps):` for prod deps (triggers patch release on promotion)
  - Both: `ci(deps):` for GitHub Actions, `chore(deps-dev):` for dev deps
- `vulnerabilityAlerts` enabled with `automerge: true`
- Major prod deps require `dependencyDashboardApproval: true`
- `semantic-release` / `python-semantic-release` packages have `automerge: false`
- No deprecated options: `baseBranches` (use `baseBranchPatterns`), `matchDepGroups` (use `matchCategories`)
- No invalid managers: `uv` (use `pep621`), `pip_requirements` (use `pep621`)

Use `library-template.json5` or `service-template.json5` in this skill's directory as reference.

### 2e. Semantic release (`release` section)

**Python repos**: Check `[tool.semantic_release]` in `pyproject.toml`:
- `exclude_commit_patterns` must exclude `chore`, `ci`, `style`, `test`, `build` (except `build(deps):`)
- `commit_message` includes `[skip ci]`
- `tag_format` uses project-name prefix: `{project-name}-v{version}`
- `build_command`: library=`"uv lock && uv build"`, service=`""`
- `version_variables` points to valid `__init__.py` with `__version__`

**TypeScript repos**: Check `.releaserc.json` or `release.config.js`:
- `releaseRules`: `chore`/`ci` map to false, `fix` scope `deps` to patch
- Git plugin message includes `[skip ci]`

Verify renovate prefix alignment: `fix(deps):` must NOT be excluded (triggers releases). `chore(deps):`, `ci(deps):` must be excluded.

Use `python-template.toml` or `node-template.releaserc.json` in this skill's directory as reference.

### 2f. Dotfiles (`dotfiles` section)

Check `.editorconfig`:
- `root = true`, `end_of_line = lf`, `insert_final_newline = true`
- Python: 4 spaces indent. JS/TS/YAML/JSON: 2 spaces indent.

Check `.gitignore`:
- **Safety (ERROR if missing)**: `.env`, `.env.*`, `*.pem`, `.claude/settings.local.json`
- **Build artifacts (WARNING)**: `__pycache__`, `node_modules/`, `*.pyc`, `.coverage`, `dist/`, `build/`
- **Anti-patterns (flag)**: `*.lock` files should NOT be in .gitignore (lock files must be committed)

Check tool config:
- Python `pyproject.toml`: ruff `line-length = 100`, mypy strict or `disallow_untyped_defs`, coverage source and omit
- TypeScript `package.json`: required scripts (dev, build, test, lint, format), biome config present

Use `editorconfig-template` in this skill's directory as reference.

---

## 3. Present Findings

Display a summary table:

```
Section          Status    Errors  Warnings  Notes
----------------------------------------------------------------------
GitHub settings  DRIFT     1E      0W        Rulesets use old gate names
Pipeline         PASS      0E      0W
Pre-commit       DRIFT     0E      2W        Missing uv-lock-check hook
Renovate         MISSING   1E      0W        No renovate.json5
Release          PASS      0E      0W
Dotfiles         DRIFT     0E      1W        Missing .editorconfig
----------------------------------------------------------------------
Total                      2E      3W
```

If `--validate` was specified, stop here.

If no args (default), ask the user: "Found 2 errors and 3 warnings. Fix all? [Y/n]"

If `--fix` was specified or user confirms, proceed to step 4.

---

## 4. Fix (dependency order)

Apply fixes in this order (later steps may depend on earlier ones):

1. **Dotfiles**: Generate `.editorconfig` from template if missing. Add safety entries to `.gitignore`.
2. **Pre-commit / quality config**: Generate `.pre-commit-config.yaml` from template if missing. Patch existing config to add missing hooks.
3. **GitHub settings**: Run `ai-gh config --standardize`. Run `ai-gh rulesets --apply <library|service>`.
4. **Pipeline**: If missing, generate via `ai-gh workflow --type <library|service>`. If exists but drifted, show diff and patch specific issues. Customize build step for detected framework.
5. **Renovate**: Generate `renovate.json5` from template if missing. If exists, validate and patch prefix scheme.
6. **Release**: Generate or append semantic-release config. Verify renovate prefix alignment.

For each fix, show what changed. If a fix would overwrite user customizations in an existing file, show the diff and ask for confirmation.

---

## 5. Verify

After fixes:
1. If `ai-gh` is available: run `ai-gh status --type <library|service> --verbose` to verify GitHub-side alignment
2. Re-run the audit from step 2 to confirm all issues are resolved
3. Report final state

```
Verification: 0 errors, 0 warnings. Repository is standard-compliant.
```

If issues remain, list them with guidance on manual resolution.

---

## Error Handling

- `ai-gh` not installed or `.env` missing GH variables: skip GitHub sections, audit local config only, note what was skipped
- Unknown repo type: ask the user (library or service?)
- Unknown language: ask the user (python or typescript?)
- Template file not found in skill directory: report error, skip that section
- `ai-gh` commands fail: show error output, continue with remaining sections
- Existing file has user customizations that conflict with standard: show diff, ask before overwriting
