---
name: ai-prepare-branch
description: Create a feature branch from the correct base (dev or main), sync release bumps, and set up remote tracking. Use when starting work on an issue or saying 'start working on'.
argument-hint: "[issue-number, description, or branch-name]"
---

Create a feature branch from the correct base with proper setup: $ARGUMENTS

> **Workflow automation:** This skill is part of an automated workflow. Make autonomous decisions where safe: auto-continue past pipeline warnings, auto-select obvious branch names. Only stop and ask the user when there is a genuinely ambiguous or destructive situation (uncommitted work on a different task, merge conflicts, ambiguous branch naming with no issue context).

Handles both issue-based and ad-hoc branch creation. Automatically detects whether the repo uses a dev/staging branch or only main.

## Usage Examples
- `/ai-prepare-branch 42` - Create branch for issue #42
- `/ai-prepare-branch refactor auth logic` - Create branch with description
- `/ai-prepare-branch feat/new-dashboard` - Use exact branch name
- `/ai-prepare-branch` - Interactive branch creation

## 1. Detect Repo Branching Pattern

```bash
# Fetch latest remote state
git fetch --all --prune
```

**Check for dev/staging branch (priority order):**

1. Check `ai-shell.toml` for `[workflow] dev_branch` override (wins if set)
2. Check remote branches:
   - `origin/dev` (first priority)
   - `origin/develop` (second)
   - `origin/staging` (third)
3. First match = dev branch. No match = main-only repo.

```bash
# Canonical algorithm -- see CLAUDE.md (Architecture > Branch Detection Algorithm)
DEV_BRANCH=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet refs/remotes/origin/$candidate; then
        DEV_BRANCH=$candidate
        break
    fi
done

# Determine default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
```

If both `dev` and `develop` exist, use `dev` and warn: "Both origin/dev and origin/develop exist. Using origin/dev. Set `[workflow] dev_branch = 'develop'` in ai-shell.toml to override."

**Set base branch:**
- Dev-based repos: base = `$DEV_BRANCH`
- Main-only repos: base = `$DEFAULT_BRANCH`

Report: "Repo pattern: [dev-based|main-only]. Base branch: [branch]. PR target: [branch]."

## 2. Check Current State

```bash
CURRENT_BRANCH=$(git branch --show-current)
```

**First: detect already-merged work branches.**

If on a work branch (not main/dev/staging), check whether its PR was already merged:

```bash
MERGED_PR=$(gh pr list --head $CURRENT_BRANCH --state merged --json number -q '.[0].number' 2>/dev/null)
```

If `MERGED_PR` is non-empty, this branch is stale (merged PRs + semantic-release version bumps create new commits on the target, so the old branch diverges). Handle automatically:

- **No uncommitted changes**: Report "Branch $CURRENT_BRANCH was merged via PR #$MERGED_PR. Switching to $BASE." Then `git checkout $BASE` and `git branch -D $CURRENT_BRANCH`. Proceed to step 4.
- **Uncommitted changes present**: These are new work started on a stale branch. Stash, switch, delete:
  ```bash
  git stash push -m "WIP: New work from stale branch $CURRENT_BRANCH"
  git checkout $BASE
  git branch -D $CURRENT_BRANCH
  ```
  Report: "Branch $CURRENT_BRANCH was merged via PR #$MERGED_PR. Stashed your uncommitted changes and switched to $BASE. Changes will be unstashed onto the new branch."
  After step 6 (new branch created), run `git stash pop`.

**Then: three-state check (only reached if branch was NOT already merged):**

1. **On main/dev** - proceed normally (happy path)
2. **On a work branch with no uncommitted changes and no unpushed commits** - offer to switch
3. **On a work branch with uncommitted changes OR unpushed commits** - this is dangerous:
   - Show status: X uncommitted files, Y unpushed commits
   - Check for open PR: `gh pr list --head $CURRENT_BRANCH --state open --json number,title`
   - Offer choices:
     - (a) Stash changes and switch: `git stash push -m "WIP: Before switching to new branch"`
     - (b) Submit current work first via `/ai-submit-work`, then switch
     - (c) Abort so user can finish current work

**Never silently discard work.**

## 3. Sync Release Bumps (Dev-based Repos Only)

If this is a dev-based repo, ensure dev has main's latest release bump commits:

```bash
# Check if main is already an ancestor of dev
if ! git merge-base --is-ancestor origin/$DEFAULT_BRANCH origin/$DEV_BRANCH; then
    echo "dev is behind main. Syncing release bump commits..."

    # Check if a CI/release pipeline is running on main
    MAIN_RUN_STATUS=$(gh run list --branch $DEFAULT_BRANCH --limit 1 --json status -q '.[0].status' 2>/dev/null)
    if [ "$MAIN_RUN_STATUS" = "in_progress" ] || [ "$MAIN_RUN_STATUS" = "queued" ]; then
        echo "NOTE: A CI/release pipeline is running on main. Proceeding anyway."
        echo "You may need to rebase later if new commits land."
        # Continue automatically -- do NOT ask wait/continue/abort
    fi

    # Attempt merge
    git checkout $DEV_BRANCH
    git merge origin/$DEFAULT_BRANCH
    # If merge succeeds: push
    # If conflicts: abort merge, tell user to resolve manually
fi
```

**On conflict:**
- `git merge --abort`
- Tell user: "dev has conflicts with main's release bump. Create a `chore/sync-dev-with-main` branch to resolve via PR."
- Do NOT attempt auto-resolution (version files and changelogs are fragile)

## 4. Update Base Branch

```bash
BASE=$DEV_BRANCH  # or $DEFAULT_BRANCH for main-only repos
git checkout $BASE
git pull origin $BASE
```

## 5. Create Branch

**Parse $ARGUMENTS to determine branch name:**

### From issue number (e.g., "42", "#42"):
```bash
# Fetch issue details
gh issue view $ISSUE_NUMBER --json title,labels

# Detect type from labels
# bug, bugfix -> fix/
# feature, enhancement -> feat/
# documentation -> docs/
# Default -> feat/

# Generate slug from title
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g' | cut -c1-40)
BRANCH_NAME="$PREFIX/issue-$ISSUE_NUMBER-$SLUG"
```

### From description (e.g., "refactor auth logic"):
```bash
# Auto-detect type from keywords
if echo "$ARGUMENTS" | grep -qiE 'fix|bug|issue|broken|error'; then
    PREFIX="fix"
elif echo "$ARGUMENTS" | grep -qiE 'doc|readme|comment'; then
    PREFIX="docs"
elif echo "$ARGUMENTS" | grep -qiE 'test|spec|coverage'; then
    PREFIX="test"
elif echo "$ARGUMENTS" | grep -qiE 'refactor|improve|clean|reorganize'; then
    PREFIX="refactor"
elif echo "$ARGUMENTS" | grep -qiE 'chore|update dep|maintain|ci|cd'; then
    PREFIX="chore"
elif echo "$ARGUMENTS" | grep -qiE 'perf|speed|optimize|fast'; then
    PREFIX="perf"
else
    PREFIX="feat"
fi

SLUG=$(echo "$ARGUMENTS" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g')
BRANCH_NAME="$PREFIX/$SLUG"
```

### From explicit branch name (e.g., "feat/new-dashboard"):
Use as-is if it contains a `/` and starts with a known prefix.

### Interactive (no arguments):
Ask the user:
1. What type? (feat/fix/docs/refactor/test/chore/perf)
2. Brief description?
Generate branch name from answers.

### Handle existing branch:
```bash
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
    echo "Branch $BRANCH_NAME already exists."
    # Suggest: $BRANCH_NAME-2 or ask for alternative
fi
```

## 6. Create and Push

```bash
git checkout -b $BRANCH_NAME
git push -u origin $BRANCH_NAME
```

## 7. Final Output

```
Branch created: feat/issue-42-fix-auth-timeout
Base: dev
PR target: dev
Remote tracking: origin/feat/issue-42-fix-auth-timeout
Behind target: 0 commits (up to date)

Next steps:
  - Make your changes
  - When ready: /ai-submit-work
  - To run checks manually: /ai-submit-work --no-tests

Tip: Your commit messages will automatically reference issue #42.
```

If "behind target" count is >0, add: "This is normal if the target branch has been active. It will be handled automatically when you submit."

## Error Handling
- **Rebase/merge in progress**: Warn and suggest completing or aborting first
- **Uncommitted changes**: Offer stash/submit/abort (never discard)
- **Network issues**: Warn about push failure, branch is still created locally
- **Branch exists**: Suggest alternative name
- **Release pipeline in flight**: Warn about potential stale base
