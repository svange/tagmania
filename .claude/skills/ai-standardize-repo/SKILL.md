---
name: ai-standardize-repo
description: Umbrella skill that enumerates all standardization tasks, shows repo status, and runs individual or all ai-standardize-* skills.
argument-hint: "[--all] [--status] [renovate|release|pipeline|precommit|dotfiles]"
---

Run repository standardization checks and fixes: $ARGUMENTS

Entry point for standardizing repository configuration. Shows what is configured, what is missing, and can run individual or all `ai-standardize-*` skills.

## Usage Examples

```bash
/ai-standardize-repo              # Show standardization status checklist
/ai-standardize-repo --status     # Same as above (explicit)
/ai-standardize-repo --all        # Run all standardization skills sequentially
/ai-standardize-repo renovate     # Run only ai-standardize-renovate
/ai-standardize-repo release      # Run only ai-standardize-release
/ai-standardize-repo pipeline     # Run only ai-standardize-pipeline
/ai-standardize-repo precommit    # Run only ai-standardize-precommit
/ai-standardize-repo dotfiles     # Run only ai-standardize-dotfiles
```

## 1. Available Standardization Skills

| Skill | Description | Key Config Files |
|-------|-------------|-----------------|
| `ai-standardize-renovate` | Renovate dependency update configuration | `renovate.json5` |
| `ai-standardize-release` | Semantic-release versioning configuration | `pyproject.toml` / `.releaserc.json` |
| `ai-standardize-pipeline` | CI/CD security scans, coverage, type checking | `.github/workflows/*.yml` |
| `ai-standardize-precommit` | Pre-commit hooks for formatting, linting, secrets | `.pre-commit-config.yaml` |
| `ai-standardize-dotfiles` | Editor config, gitignore, tool settings | `.editorconfig`, `.gitignore`, `pyproject.toml` |

## 2. Detect Repo Context

```bash
# Repo type
git fetch --all --prune 2>/dev/null
DEV_BRANCH=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet "refs/remotes/origin/$candidate" 2>/dev/null; then
        DEV_BRANCH=$candidate
        break
    fi
done
REPO_TYPE="Library (main-only)"
[ -n "$DEV_BRANCH" ] && REPO_TYPE="IaC ($DEV_BRANCH+main)"

# Ecosystem
ECOSYSTEM=""
[ -f "pyproject.toml" ] && ECOSYSTEM="${ECOSYSTEM}Python "
[ -f "package.json" ] && ECOSYSTEM="${ECOSYSTEM}Node "
[ -z "$ECOSYSTEM" ] && ECOSYSTEM="Unknown"

# Quick config detection
RENOVATE_STATUS="missing"
for f in renovate.json5 renovate.json .renovaterc .renovaterc.json; do
    [ -f "$f" ] && RENOVATE_STATUS="found ($f)" && break
done

RELEASE_STATUS="missing"
if [ -f "pyproject.toml" ] && grep -q "semantic_release" pyproject.toml 2>/dev/null; then
    RELEASE_STATUS="configured (pyproject.toml)"
fi
for f in .releaserc.json .releaserc.yml .releaserc.js release.config.js release.config.cjs; do
    [ -f "$f" ] && RELEASE_STATUS="configured ($f)" && break
done
if [ "$RELEASE_STATUS" = "missing" ] && [ -f "package.json" ] && grep -q '"release"' package.json 2>/dev/null; then
    RELEASE_STATUS="configured (package.json)"
fi

PIPELINE_STATUS="missing"
[ -d ".github/workflows" ] && PIPELINE_STATUS="found ($(ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null | wc -l) workflow files)"

PRECOMMIT_STATUS="missing"
[ -f ".pre-commit-config.yaml" ] && PRECOMMIT_STATUS="found (.pre-commit-config.yaml)"
[ -d ".husky" ] && PRECOMMIT_STATUS="found (husky)"

EDITORCONFIG_STATUS="missing"
[ -f ".editorconfig" ] && EDITORCONFIG_STATUS="found"
```

## 3. Display Status Checklist

```
=== Repository Standardization Status ===

Repo type: {REPO_TYPE}
Ecosystem: {ECOSYSTEM}

Configuration Checklist:
  [{x or space}] Renovate config: {RENOVATE_STATUS}
  [{x or space}] Semantic-release: {RELEASE_STATUS}
  [{x or space}] CI/CD pipeline: {PIPELINE_STATUS}
  [{x or space}] Pre-commit hooks: {PRECOMMIT_STATUS}
  [{x or space}] Editor config: {EDITORCONFIG_STATUS}

Validation (run to check for issues):
  /ai-standardize-repo renovate     # Dependency update config
  /ai-standardize-repo release      # Versioning config
  /ai-standardize-repo pipeline     # Security scans, coverage, type checking
  /ai-standardize-repo precommit    # Developer quality gates
  /ai-standardize-repo dotfiles     # Editor, gitignore, tool settings

Run all: /ai-standardize-repo --all
```

Mark items with `[x]` if the config exists, `[ ]` if missing.

## 4. Run Skills

### If `$ARGUMENTS` contains `--all`:

Run each standardization skill in sequence (order matters -- later skills may reference earlier ones):

1. `/ai-standardize-dotfiles` -- foundational config files
2. `/ai-standardize-precommit` -- developer quality gates
3. `/ai-standardize-pipeline` -- CI/CD checks
4. `/ai-standardize-renovate` -- dependency management
5. `/ai-standardize-release` -- versioning (depends on renovate prefix scheme)

Report results from each, then show the combined summary.

### If `$ARGUMENTS` contains a skill name:

Map shorthand to full skill:
- `renovate` -> execute `/ai-standardize-renovate`
- `release` -> execute `/ai-standardize-release`
- `pipeline` -> execute `/ai-standardize-pipeline`
- `precommit` -> execute `/ai-standardize-precommit`
- `dotfiles` -> execute `/ai-standardize-dotfiles`

If the name does not match any known skill, show the available skills table from Step 1.

### If `$ARGUMENTS` is empty or `--status`:

Just show the status checklist from Step 3. Do not run any validation or generation.

## 5. Combined Summary (after --all)

```
=== Standardization Summary ===

Repo type: IaC (dev+main)
Ecosystem: Python

| Skill | Action | Issues | Fixed | Remaining |
|-------|--------|--------|-------|-----------|
| Dotfiles | Generated | 1 | 1 | 0 |
| Pre-commit | Fixed | 3 | 3 | 0 |
| Pipeline | Validated | 2 | 0 | 2 |
| Renovate | Validated | 1 | 1 | 0 |
| Release | Validated | 0 | 0 | 0 |

Remaining issues:
  [FAIL] Pipeline: Semgrep SAST scanning missing
  [FAIL] Pipeline: License compliance checking missing

Overall: 2 issues remaining. Add missing CI jobs manually or re-run individual skills with --fix.
```

## Error Handling

- **Not a git repo**: Abort with error
- **Unknown skill name**: Show available skills table
- **No ecosystem detected**: Warn, suggest checking if this is the correct directory
- **Skill fails mid-run during --all**: Report the failure, continue with remaining skills, include failure in summary
