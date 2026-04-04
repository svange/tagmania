---
name: ai-submit-work
description: Run all status checks locally, fix issues, commit, push, and create an automerge PR. Use when work is ready to submit.
argument-hint: "[--no-tests] [--no-security]"
---

Run all status checks, fix issues, commit, push, and create an automerge PR: $ARGUMENTS

Mirrors the CI pipeline locally to catch issues before pushing. Handles file staging, conventional commits, branch updates, and PR creation.

## Usage Examples
- `/ai-submit-work` - Full submission (all checks)
- `/ai-submit-work --no-tests` - Skip test suite (pre-commit + security still run)
- `/ai-submit-work --no-security` - Skip security + license checks
- `/ai-submit-work --no-tests --no-security` - Pre-commit only (fastest)

## 1. Safety Checks

```bash
CURRENT_BRANCH=$(git branch --show-current)
```

**Verify work branch:**
- If on `main`, `master`, `dev`, `develop`, or `staging`: **ABORT** with error "You're on $CURRENT_BRANCH. Create a work branch first with `/ai-prepare-branch`."
- Must be on a feature/fix/etc. branch.

**Verify there are changes:**
```bash
# Check for any changes (staged, unstaged, untracked)
if [ -z "$(git status --porcelain)" ]; then
    echo "No changes to submit."
    exit 0
fi
```

## 2. Handle Files

Show `git status` to the user.

**For each untracked file**, ask the user:
- **Stage** - add to this commit
- **Ignore** - leave untracked (skip for now)
- **Add to .gitignore** - add a pattern to .gitignore

**For modified/deleted tracked files**, stage them:
```bash
git add -u
```

**For any user-approved untracked files:**
```bash
git add <approved-files>
```

If no files are staged after this step, abort.

## 3. Run Status Checks

Parse `$ARGUMENTS` for skip flags:
- `--no-tests` -> skip Phase D
- `--no-security` -> skip Phase B and C

### Phase A: Pre-commit (always runs)

**Detect:** Check if `.pre-commit-config.yaml` exists.

**Run (auto-fix loop, max 2 iterations):**
```bash
# Iteration 1
uv run pre-commit run --all-files
# If uv not available, try: pre-commit run --all-files

# If exit code != 0 AND files were modified by hooks:
git diff --name-only  # Check for auto-fixed files

# Re-stage fixed files and retry
git add -u
uv run pre-commit run --all-files

# If still failing: show errors
# Distinguish fixable hooks (ruff-format, trailing-whitespace, end-of-file-fixer)
# from diagnostic hooks (mypy, uv-lock-check)
# Diagnostic failures require manual intervention - show errors and ask user to fix
```

**If pre-commit not available:** Run individual linters if detected:
```bash
# Python
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
# JavaScript
npx eslint --fix . && npx prettier --write .
```

### Phase B: Security Scan (skip with --no-security)

**Detect and run available security tools:**

```bash
# Bandit (Python security linter)
if python -c "import bandit" 2>/dev/null || uv run bandit --version 2>/dev/null; then
    uv run bandit -r src/ -ll
fi

# pip-audit (dependency vulnerabilities)
if uv run pip-audit --version 2>/dev/null; then
    uv export --no-dev --no-hashes -o /tmp/prod-requirements.txt
    uv run pip-audit -r /tmp/prod-requirements.txt --no-deps
fi

# npm audit (JavaScript)
if [ -f "package-lock.json" ]; then
    npm audit --production
fi
```

**On failure:** Show findings and ask user:
- **Fix** - attempt to fix the issue
- **Skip** - continue despite findings (will show in CI too)
- **Abort** - stop submission

### Phase C: License Compliance (skip with --no-security)

```bash
# Python
if uv run pip-licenses --version 2>/dev/null; then
    uv run pip-licenses --from=mixed --summary

    # Check for GPL/AGPL (excluding LGPL)
    python -c "
import json, subprocess
result = subprocess.run(['uv', 'run', 'pip-licenses', '--from=mixed', '--format=json'], capture_output=True, text=True)
deps = json.loads(result.stdout)
incompatible = [f\"{d['Name']}: {d['License']}\" for d in deps
                if any(g in d.get('License','').upper() for g in ['GPL','AGPL'])
                and 'LGPL' not in d.get('License','').upper()]
if incompatible:
    print('WARNING: Potentially incompatible licenses:')
    for item in incompatible:
        print(f'  - {item}')
"
fi
```

**On incompatible license found:** Warn and ask user to continue or abort.

### Phase D: Tests (skip with --no-tests)

**Detect and run the project's test suite:**

```bash
# Python with pytest
if [ -f "pyproject.toml" ] && grep -q "pytest" pyproject.toml 2>/dev/null; then
    uv run pytest --cov=src --cov-fail-under=80 -v
# Python with unittest
elif [ -d "tests" ] && [ -f "pyproject.toml" ]; then
    uv run python -m pytest -v
# JavaScript/TypeScript
elif [ -f "package.json" ] && grep -q '"test"' package.json; then
    npm test
# Makefile
elif [ -f "Makefile" ] && grep -q '^test:' Makefile; then
    make test
fi
```

**On test failure:** Show failures and tell the user which tests failed. Do not auto-fix test failures - they require understanding business logic.

## 4. Commit

### Extract issue number from branch name:
```bash
BRANCH=$(git branch --show-current)
# Try multiple patterns (in order):
# issue-42, /42-, #42, gh-42
ISSUE_NUM=$(echo "$BRANCH" | grep -oP 'issue-\K\d+' || \
            echo "$BRANCH" | grep -oP '(?<=\/)\d+(?=-)' || \
            echo "$BRANCH" | grep -oP '#\K\d+' || \
            echo "$BRANCH" | grep -oP 'gh-\K\d+' || \
            echo "")
```

### Determine conventional commit type from branch prefix:
```bash
# feat/* -> feat:, fix/* -> fix:, docs/* -> docs:, etc.
COMMIT_TYPE=$(echo "$BRANCH" | grep -oP '^[^/]+')
```

### Generate commit message:
- Type from branch prefix
- Scope from primary directory changed (e.g., `cli`, `tests`, `config`)
- Description from diff summary and branch name
- Footer: `Closes #N` (for fix/ branches) or `Refs #N` (for feat/ branches) if issue found

### Present for approval:
```
Proposed commit message:
---
feat(cli): add metrics dashboard endpoint

Refs #42
---

Accept / Edit / Abort?
```

**Always ask for approval. Never auto-commit.**

### Commit:
```bash
git commit -m "<approved message>"
```

## 5. Update Branch

### Detect target branch (same logic as ai-prepare-branch):
```bash
# Check for dev/staging branch
TARGET=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet refs/remotes/origin/$candidate; then
        TARGET=$candidate
        break
    fi
done
TARGET=${TARGET:-$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@' 2>/dev/null || echo "main")}
```

### Rebase on target:
```bash
git fetch origin $TARGET
git rebase origin/$TARGET
```

**On conflict:** Show conflicting files and ask user to resolve. Do not auto-resolve.

## 6. Push

```bash
# If rebased (branch diverged from remote):
git push --force-with-lease origin $CURRENT_BRANCH

# If no rebase needed:
git push origin $CURRENT_BRANCH
```

## 7. Create PR

```bash
# Determine PR title from commit message (first line)
PR_TITLE="<first line of commit message>"

# Create PR
gh pr create \
    --base $TARGET \
    --head $CURRENT_BRANCH \
    --title "$PR_TITLE" \
    --body "## Summary
<brief description of changes>

## Checks run locally
- [x] Pre-commit hooks
- [x] Security scan (bandit + pip-audit)
- [x] License compliance
- [x] Unit tests with coverage

## Issue
<Closes #N or Refs #N if applicable>"

# Set automerge
PR_NUMBER=$(gh pr view --json number -q .number)
gh pr merge --auto --squash $PR_NUMBER
```

## 8. Final Output

```
Submitted: feat(cli): add metrics dashboard endpoint

PR: https://github.com/owner/repo/pull/99
Target: dev
Automerge: enabled (squash)
Status checks: pending

Next step: /ai-monitor-pipeline
```

## Error Handling
- **Not on work branch**: Abort, suggest `/ai-prepare-branch`
- **No changes**: Exit cleanly
- **Pre-commit fails after 2 fix attempts**: Show errors, ask user to fix manually
- **Security findings**: Warn, let user decide to continue or fix
- **Test failures**: Show failures, do not auto-fix
- **Rebase conflicts**: Show conflicts, ask user to resolve
- **Push rejected**: Check if branch is behind, suggest `git pull --rebase`
- **PR creation fails**: Show error, the commit and push are still done
