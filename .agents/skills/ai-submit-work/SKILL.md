---
name: ai-submit-work
description: Run all status checks locally, fix issues, commit, push, and create an automerge PR. Use when work is ready to submit, or saying 'submit my work' or 'I'm done'.
argument-hint: "[--no-tests] [--no-security]"
---

Run all status checks, fix issues, commit, push, and create an automerge PR: $ARGUMENTS

> **Workflow automation:** This skill is part of an automated workflow. Auto-commit with generated messages (do NOT ask Accept/Edit/Abort). Auto-rebase when behind target. Auto-resolve mechanical rebase conflicts (version files, changelogs, lock files -- target branch wins). Auto-fix formatting AND diagnostic pre-commit failures (mypy, uv-lock-check). Auto-fix patch-level security bumps. Auto-stage known project files. Auto-transition to pipeline monitoring after PR creation. Only stop and ask the user for: non-patch security bumps, license compliance issues, test failures, code-level rebase conflicts, and unrecognized untracked files.

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

**Verify branch is current with target:**
```bash
# Detect target branch -- canonical algorithm from CLAUDE.md
DEV_BRANCH=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet refs/remotes/origin/$candidate; then
        DEV_BRANCH=$candidate
        break
    fi
done
TARGET=${DEV_BRANCH:-$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")}

git fetch origin $TARGET
BEHIND=$(git rev-list --count HEAD..origin/$TARGET)
if [ "$BEHIND" -gt 0 ]; then
    echo "WARNING: Your branch is $BEHIND commits behind $TARGET."
    echo "This usually means /ai-prepare-branch was not run before starting work."
fi
```

If the branch is behind, automatically rebase:
```bash
git rebase origin/$TARGET
```
Report: "Rebased on $TARGET (was $BEHIND commits behind)." Do NOT ask the user to choose -- just rebase. If the rebase has conflicts, see the conflict resolution rules in Section 5.

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

**For modified/deleted tracked files**, stage them:
```bash
git add -u
```

**For untracked files**, use smart staging:

**Auto-stage without asking** (known project files):
- Files in `.claude/`, `.agents/`, `.github/` directories
- `CLAUDE.md`, `AGENTS.md`, `NOTES.md`
- Files under `src/`, `tests/` (matches project structure)
- Files matching existing tracked file patterns

**Rely on `.gitignore` for blocking.** Do not duplicate exclusion logic in the skill. If `.env` or other secret files appear as untracked, `.gitignore` is misconfigured -- suggest fixing it.

**Batch-prompt remaining unknowns** (if any) in a single table:
```
New files detected:
  Auto-staged: .claude/skills/ai-status/SKILL.md, src/new_module.py, tests/test_new.py

  Needs your decision:
    1. notes.txt         [Ignore?]
    2. scratch/debug.py  [Ignore?]

  Accept defaults, or specify (e.g., "stage 1")?
```

If >20 untracked files need decisions, warn: "You have N untracked files. This usually means a directory is missing from .gitignore. Fix .gitignore first."

**Zero prompts** if all untracked files are auto-staged. **One prompt** if there are unknowns.

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
```

**Auto-fix ALL hook failures (formatting AND diagnostic):**

- **Formatting hooks** (ruff-format, trailing-whitespace, end-of-file-fixer): Auto-fixed by hooks themselves. Re-stage and retry.
- **mypy / type checker failures**: Analyze the errors and fix the actual types. **Hard rule: NEVER use `# type: ignore` or `Any` as escape hatches.** Fix the real types (missing return annotation, wrong parameter type, missing import, etc.). If the ONLY available fix requires `# type: ignore` or `Any`, then stop and ask the user.
- **uv-lock-check failures**: Run `uv lock` to regenerate the lock file. If `uv lock` fails (conflicting constraints, yanked package), stop and show the error.

**Circuit breaker:** Max 2 iterations total. If the same failure repeats after a fix attempt, stop and show errors.

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

**On failure -- auto-fix patch bumps, ask for larger changes:**

1. Check if fixes are available and what version delta they require
2. **Patch bumps** (e.g., 2.28.0 -> 2.28.1): Auto-fix using `uv add package==new_version` then `uv lock`. Continue without asking.
3. **Minor/major bumps** (e.g., 2.28.0 -> 2.31.0 or 3.0.0): Show findings and ask user: Fix / Skip / Abort. These can change API behavior.
4. **No fix available**: Show findings and ask user: Skip / Abort.
5. After any auto-fix, re-run the audit once to catch transitive vulnerabilities. **Circuit breaker: max 1 auto-fix round for security.** If new findings appear after the fix, show them and ask.

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

### Commit automatically:

Generate the commit message and commit immediately. Show the message in the output so the user can see what was committed, but do NOT ask for approval. Do NOT present Accept/Edit/Abort options.

```
Committed:
---
feat(cli): add metrics dashboard endpoint

Refs #42
---
```

```bash
git commit -m "<generated message>"
```

**Do NOT ask for approval. Auto-commit with the generated message.** The user trusts the conventional commit format derived from the branch prefix and diff analysis.

## 5. Update Branch

### Detect target branch:
Use the branch detection algorithm from CLAUDE.md (Architecture > Branch Detection Algorithm). Use `$TARGET` from Section 1 if already detected.

### Rebase on target:
```bash
git fetch origin $TARGET
git rebase origin/$TARGET
```

### Conflict resolution (auto-resolve mechanical, ask for code):

**Mechanical files** (target branch wins -- main/dev owns versions and changelogs, semantic-release regenerates them):
- `CHANGELOG.md` -- accept target version
- `pyproject.toml` (version field) -- accept target version
- `__init__.py` (version string) -- accept target version
- Lock files (`uv.lock`, `package-lock.json`) -- accept target, then regenerate with `uv lock` or `npm install`

**For each conflicting file during rebase:**
1. If ALL hunks are in mechanical files listed above: auto-resolve with `git checkout --theirs <file>` then `git add <file>`, continue rebase
2. If a file has MIXED mechanical + code conflicts: auto-resolve the mechanical hunks, leave code hunks for the user
3. If ANY file is purely code: show the conflict diff and ask the user to resolve

```
Rebase conflicts:
  - pyproject.toml (version) -- auto-resolved (target branch owns versions)
  - CHANGELOG.md -- auto-resolved (target branch owns changelog)
  - src/auth.py lines 42-58 -- NEEDS YOUR INPUT

[show conflict diff for auth.py]
```

After resolving all conflicts: `git rebase --continue`

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

# Set automerge -- use --merge (not --squash) to preserve commit ancestry
# for clean promotion and release sync across long-lived branches
PR_NUMBER=$(gh pr view --json number -q .number)
gh pr merge --auto --merge $PR_NUMBER
```

## 8. Final Output and Automatic Transition

```
Submitted: feat(cli): add metrics dashboard endpoint

PR: https://github.com/owner/repo/pull/99
Target: dev
Automerge: enabled (merge)
Status checks: monitoring...
```

**Automatic next step:** After the PR is created and automerge is enabled, immediately invoke `/ai-monitor-pipeline` to watch the pipeline. Do NOT just print "Next step: /ai-monitor-pipeline" -- actually run it. The user expects the workflow to continue automatically.

## Error Handling
- **Not on work branch**: Abort, suggest `/ai-prepare-branch`
- **No changes**: Exit cleanly
- **Pre-commit fails after 2 fix attempts**: Show errors, ask user to fix manually
- **mypy fix requires type:ignore or Any**: Stop, show errors, ask user (never use escape hatches)
- **uv lock fails**: Stop, show error (conflicting constraints or yanked package)
- **Patch security bump**: Auto-fix, re-audit once, then continue
- **Non-patch security bump**: Warn, let user decide (Fix / Skip / Abort)
- **Test failures**: Show failures, do not auto-fix
- **Mechanical rebase conflicts** (version, changelog, lock files): Auto-resolve, target branch wins
- **Code rebase conflicts**: Show conflicts, ask user to resolve
- **Push rejected**: Check if branch is behind, suggest rebase
- **PR creation fails**: Show error, the commit and push are still done
