---
name: ai-monitor-pipeline
description: Monitor CI pipeline after push, diagnose failures, auto-fix and re-push. Use after submitting work or to check pipeline status.
argument-hint: "[run-id or branch-name]"
---

Monitor CI pipeline, diagnose failures, and auto-fix when possible: $ARGUMENTS

Watches the pipeline run, parses failures, attempts auto-fixes for common issues, and re-pushes with user approval.

## Usage Examples
- `/ai-monitor-pipeline` - Monitor latest run on current branch
- `/ai-monitor-pipeline feat/issue-42-auth` - Monitor specific branch
- `/ai-monitor-pipeline 12345678` - Monitor specific run ID

## 1. Find the Pipeline Run

```bash
# Determine target
if [ -n "$ARGUMENTS" ]; then
    # If numeric, treat as run ID
    if echo "$ARGUMENTS" | grep -qP '^\d+$'; then
        RUN_ID=$ARGUMENTS
    else
        # Treat as branch name
        BRANCH=$ARGUMENTS
    fi
else
    BRANCH=$(git branch --show-current)
fi

# If we have a branch, find the latest run
if [ -n "$BRANCH" ]; then
    gh run list --branch "$BRANCH" --limit 5 \
        --json databaseId,status,conclusion,event,headSha,name,createdAt
    # Pick the most recent run
    RUN_ID=$(gh run list --branch "$BRANCH" --limit 1 --json databaseId -q '.[0].databaseId')
fi

if [ -z "$RUN_ID" ]; then
    echo "No pipeline runs found. Push your changes first."
    exit 1
fi
```

Show the run details:
```
Pipeline: CI/CD Pipeline
Run: #12345678
Branch: feat/issue-42-auth
Status: in_progress
Started: 2 minutes ago
```

## 2. Wait for Completion

```bash
# Watch the run in real-time
gh run watch $RUN_ID --exit-status
```

If `gh run watch` is not available, poll:
```bash
while true; do
    STATUS=$(gh run view $RUN_ID --json status,conclusion -q '.status')
    if [ "$STATUS" = "completed" ]; then
        CONCLUSION=$(gh run view $RUN_ID --json conclusion -q '.conclusion')
        break
    fi
    sleep 30
done
```

## 3. On Success

```
Pipeline PASSED

Jobs:
  - Pre-commit checks: passed
  - Security scanning: passed
  - License compliance: passed
  - Unit tests: passed

PR status: ready to merge (automerge enabled)
```

Done. No further action needed.

## 4. On Failure - Diagnose

```bash
# Get job details
gh run view $RUN_ID --json jobs

# Identify failed job(s)
FAILED_JOBS=$(gh run view $RUN_ID --json jobs -q '.jobs[] | select(.conclusion == "failure") | .name')

# Get failed logs
gh run view $RUN_ID --log-failed
```

### Categorize the Failure

**Auto-fixable failures** (skill will attempt to fix):
- **Pre-commit failures**: formatting (ruff-format), whitespace (trailing-whitespace, end-of-file-fixer), import ordering (ruff check --fix)
- **Lint errors with auto-fix**: ruff, eslint with --fix

**NOT auto-fixable** (skill reports and stops):
- **Test failures**: require understanding business logic
- **Security vulnerabilities**: bandit findings, pip-audit CVEs require judgment
- **License compliance**: dependency decisions needed
- **Build/compilation errors**: syntax errors, broken imports in non-trivial code
- **MyPy errors**: type system changes require architectural decisions
- **Release job failures**: should never be triggered from feature branches

### Failure Report

```
Pipeline FAILED

Failed jobs:
  1. Pre-commit checks (auto-fixable)
     - ruff-format: 3 files need formatting
     - trailing-whitespace: 1 file

  2. Unit tests (manual fix required)
     - test_auth.py::test_login_timeout FAILED
     - AssertionError: expected 200, got 401
```

## 5. Auto-fix Attempt

**Circuit breakers (checked before every fix attempt):**
- Maximum 2 fix attempts total
- If same failure type repeats after a fix: stop immediately
- Never modify the same file more than twice across all attempts
- Always require user approval before pushing

**Track state:**
```python
attempt_count = 0
max_attempts = 2
previous_failures = set()
modified_files = {}  # file -> modification count
```

### Fix Process

For each auto-fixable failure:

1. **Apply the fix locally:**
   ```bash
   # For pre-commit failures
   uv run pre-commit run --all-files
   # This auto-fixes formatting, whitespace, imports

   # For specific ruff issues
   uv run ruff check --fix src/ tests/
   uv run ruff format src/ tests/
   ```

2. **Verify the fix locally:**
   ```bash
   # Re-run the failing check
   uv run pre-commit run --all-files
   # Must pass now
   ```

3. **Show the diff and ask for approval:**
   ```
   Fix attempt #1:
   Files modified:
     - src/auth.py (formatting)
     - src/utils.py (trailing whitespace)

   Diff:
   [show git diff]

   Push these fixes? [y/n]
   ```

4. **If approved, commit and push:**
   ```bash
   git add -u
   git commit -m "fix: resolve pre-commit formatting issues"
   git push origin $(git branch --show-current)
   ```

5. **Watch the new run:**
   ```bash
   # Wait a moment for the new run to start
   sleep 5
   NEW_RUN_ID=$(gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId')
   gh run watch $NEW_RUN_ID --exit-status
   ```

6. **Check result:**
   - If passed: report success
   - If same failure: stop immediately ("Same failure after fix. Manual intervention needed.")
   - If different failure: attempt one more fix (if under max attempts)

### When NOT to Auto-fix

If ALL failed jobs are non-auto-fixable:
```
Pipeline FAILED - Manual fixes needed

Failed: Unit tests
  - test_auth.py::test_login_timeout FAILED
  - test_api.py::test_rate_limiting FAILED

These failures require manual intervention.
Logs: gh run view 12345678 --log-failed

Suggested actions:
  1. Fix the failing tests
  2. Run locally: uv run pytest tests/test_auth.py -v
  3. Push fixes and re-run: /ai-monitor-pipeline
```

## 6. Final Output

### After successful fix:
```
Pipeline PASSED (after 1 fix attempt)

Fix applied:
  - Commit: abc1234 "fix: resolve pre-commit formatting issues"
  - Files: src/auth.py, src/utils.py

All jobs green. PR ready to merge.
```

### After giving up:
```
Pipeline FAILED (2 fix attempts exhausted)

Attempt 1: Fixed formatting -> new failure in tests
Attempt 2: Cannot auto-fix test failures

Remaining failures:
  - Unit tests: test_auth.py::test_login_timeout

Manual fix required. Run locally:
  uv run pytest tests/test_auth.py::test_login_timeout -v
```

## Error Handling
- **No runs found**: Suggest pushing changes first
- **gh CLI not authenticated**: Remind to run `gh auth login`
- **Run cancelled**: Report cancellation, suggest re-triggering
- **Network timeout during watch**: Resume polling with last known run ID
- **Fix creates new issues**: Circuit breaker stops after 2 attempts
