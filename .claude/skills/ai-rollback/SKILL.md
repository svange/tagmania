---
name: ai-rollback
description: Rollback a bad release or revert a merged PR. Use when something broke after a merge or release. Also triggered by 'something broke', 'undo the last release', 'revert'.
argument-hint: "[PR-number or commit-sha or --dry-run]"
---

Rollback a bad release or revert a merged PR: $ARGUMENTS

Gathers diagnostic context, identifies the breaking change, shows a dry-run plan, and executes a revert. Handles staging/production scope and database migration awareness.

## Usage Examples
- `/ai-rollback` - Interactive rollback with diagnostic questions
- `/ai-rollback 98` - Revert PR #98
- `/ai-rollback abc1234` - Revert specific commit
- `/ai-rollback --dry-run` - Show what would be reverted without executing

## 1. Gather Diagnostic Context

Ask these questions all at once to minimize back-and-forth:

```
Something went wrong -- let's figure out where. Please answer what you can:

1. Which environment is broken? (staging/dev, production/main, or both?)
2. When was the last time you can confirm it worked as expected?
3. What change do you think broke it? (PR number, feature name, or "not sure")
4. What symptoms are you seeing? (error messages, wrong behavior, crashes, data issues?)
5. Is this causing active harm right now, or is it safe to take a few minutes to investigate?
6. Did the breaking change include any database migrations or infrastructure changes?
7. Are other people actively working on this branch right now?
```

If the user provided a PR number or commit SHA as an argument, skip questions 2-3 and use the provided reference directly. Still ask the remaining questions.

## 2. Identify the Target

### If PR number provided:
```bash
gh pr view $PR_NUMBER --json mergeCommit,title,headRefName,mergedAt,files
MERGE_COMMIT=$(gh pr view $PR_NUMBER --json mergeCommit -q .mergeCommit.oid)
```

### If commit SHA provided:
```bash
git log --oneline -1 $COMMIT_SHA
```

### If "not sure" -- help narrow it down:
```bash
# Show recent merges on the affected branch
git log --oneline --merges -20 origin/$BRANCH
# Show recent PRs
gh pr list --state merged --limit 10 --json number,title,mergedAt,headRefName
```

Use the user's "last time it worked" answer and the "symptoms" to narrow the window. Show the commits in that window and ask: "Which of these looks suspicious?"

## 3. Check for Database Migrations

```bash
# Check if the target PR/commit included migration files
git diff --name-only $MERGE_COMMIT^..$MERGE_COMMIT | grep -iE 'migration|alembic|flyway|schema'
```

If migration files are found, warn prominently:
```
WARNING: This change includes database migrations.
Code rollback alone will NOT revert schema changes. You may need to:
  - Write a reverse migration
  - Restore from a database backup
  - Fix forward instead of rolling back

Proceed with code-only rollback? [y/n]
```

## 4. Determine Environment Scope

Detect the branch detection algorithm from CLAUDE.md (Architecture > Branch Detection Algorithm).

```bash
# Which branch was affected?
DEV_BRANCH=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet refs/remotes/origin/$candidate; then
        DEV_BRANCH=$candidate
        break
    fi
done
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
```

Based on user's answer to "which environment":
- **Staging/dev only**: revert on `$DEV_BRANCH`
- **Production/main only**: revert on `$DEFAULT_BRANCH`, then ask about dev
- **Both**: revert on `$DEFAULT_BRANCH` first (stop the bleeding), then address `$DEV_BRANCH`

## 5. Dry-Run Plan (ALWAYS show before executing)

Whether `--dry-run` was passed or not, ALWAYS show this plan and get confirmation:

```
=== Rollback Plan ===
Environment: production (main)
Action: Revert merge commit abc1234 (PR #98: "feat: add auth timeout")
Effect: Creates a new commit that undoes PR #98's changes
Version impact: Semantic-release will create a new patch version (e.g., 0.21.1)
Database: No migrations detected in PR #98
Other environment: dev -- will ask after main revert

This will NOT roll back to a previous deployed artifact -- it creates a new
release with the breaking change removed. The version number moves forward,
which provides a clear audit trail of when the rollback happened.

Proceed? [y/n]
```

If `--dry-run` was passed, stop here. Otherwise, proceed after user confirmation.

## 6. Execute Revert

```bash
# Checkout the target branch
git checkout $BRANCH
git pull origin $BRANCH

# Revert the merge commit (use -m 1 for merge commits)
git revert $MERGE_COMMIT -m 1 --no-edit

# Push the revert
git push origin $BRANCH
```

For non-merge commits (direct pushes):
```bash
git revert $COMMIT_SHA --no-edit
git push origin $BRANCH
```

## 7. Handle the Other Environment

After the primary revert is pushed, ask about the other environment:

```
Revert pushed to main. Now about dev:
  - (a) Revert this PR on dev too (mirror the rollback)
  - (b) Fix forward on dev (keep the changes, fix the bug there)
  - (c) Skip -- I'll handle dev separately
```

If the user chooses (a), repeat the revert on the dev branch.

## 8. Create Hotfix Branch (Optional)

If the user wants to fix the issue (not just revert):

```bash
git checkout -b fix/revert-issue-$ISSUE_NUM $BRANCH
git push -u origin fix/revert-issue-$ISSUE_NUM
```

```
Hotfix branch created: fix/revert-issue-42
The reverted changes are available in git history if you need to reference them.

When ready: /ai-submit-work
```

## 9. Monitor the Revert Pipeline

After pushing the revert, automatically invoke `/ai-monitor-pipeline` to watch the pipeline. The revert commit will trigger CI, and for main branch, will trigger semantic-release (creating a new patch version).

## Error Handling
- **PR not found**: Suggest checking the PR number, show recent merged PRs
- **Commit not found**: Suggest checking the SHA, show recent commits
- **Branch protection prevents push**: Suggest creating a revert PR instead of direct push
- **Revert creates conflicts**: Show conflicts, ask user to resolve (the reverted code may conflict with subsequent changes)
- **User says "not sure" and can't identify the change**: Suggest a bisect approach or checking deployment logs
- **Active harm / emergency**: Fast-track the dry-run confirmation but do NOT skip safety checks
