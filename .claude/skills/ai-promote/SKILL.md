---
name: ai-promote
description: Promote staging (dev) to production (main) by creating an automerge PR. Use when dev/staging is ready for release, or saying 'release to production'.
argument-hint: "[--dry-run]"
---

Promote staging to production by creating an automerge PR from dev to main: $ARGUMENTS

Verifies CI status, checks for un-reviewed commits, and creates a merge PR that preserves individual commit messages for semantic-release.

## Usage Examples
- `/ai-promote` - Promote dev to main with all safety checks
- `/ai-promote --force` - Skip the un-PR'd commit warning (still checks CI)

## 1. Verify Repo Uses Dev Branch

```bash
git fetch --all --prune

# Canonical algorithm -- see CLAUDE.md (Architecture > Branch Detection Algorithm)
DEV_BRANCH=""
for candidate in dev develop staging; do
    if git show-ref --verify --quiet refs/remotes/origin/$candidate; then
        DEV_BRANCH=$candidate
        break
    fi
done

DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

if [ -z "$DEV_BRANCH" ]; then
    echo "ERROR: This repo doesn't use a staging branch. Nothing to promote."
    echo "Branches go directly to $DEFAULT_BRANCH via /ai-submit-work."
    exit 1
fi
```

Report: "Promoting: $DEV_BRANCH -> $DEFAULT_BRANCH"

## 2. Pre-flight Checks

### Check CI passes on dev HEAD
```bash
# Get latest CI run on dev
LATEST_RUN=$(gh run list --branch $DEV_BRANCH --limit 1 --json databaseId,status,conclusion,headSha)
RUN_CONCLUSION=$(echo "$LATEST_RUN" | jq -r '.[0].conclusion')
RUN_SHA=$(echo "$LATEST_RUN" | jq -r '.[0].headSha')
DEV_SHA=$(git rev-parse origin/$DEV_BRANCH)

# Verify the run is for the current HEAD of dev
if [ "$RUN_SHA" != "$DEV_SHA" ]; then
    echo "WARNING: Latest CI run (sha: ${RUN_SHA:0:8}) does not match $DEV_BRANCH HEAD (sha: ${DEV_SHA:0:8})."
    echo "CI has not run on the latest commits. Push to $DEV_BRANCH or wait for CI to trigger."
    # Ask: wait / abort
fi

# Verify CI passed
if [ "$RUN_CONCLUSION" != "success" ]; then
    echo "ERROR: CI on $DEV_BRANCH is $RUN_CONCLUSION (not success)."
    echo "Fix CI issues first: /ai-monitor-pipeline $DEV_BRANCH"
    exit 1
fi
```

### Check dev is ahead of main (something to promote)
```bash
COMMITS=$(git log --oneline origin/$DEFAULT_BRANCH..origin/$DEV_BRANCH)
if [ -z "$COMMITS" ]; then
    echo "$DEV_BRANCH has no new commits to promote. Nothing to do."
    exit 0
fi

COMMIT_COUNT=$(echo "$COMMITS" | wc -l)
echo "$COMMIT_COUNT commit(s) to promote:"
echo "$COMMITS"
```

### Check dev is not behind main (needs sync)
```bash
if ! git merge-base --is-ancestor origin/$DEFAULT_BRANCH origin/$DEV_BRANCH; then
    echo "WARNING: $DEV_BRANCH is behind $DEFAULT_BRANCH (likely missing release bump commits)."
    echo "Sync first: /ai-prepare-branch (it will sync dev with main automatically)"
    # Ask: abort / continue anyway
fi
```

### Check for un-PR'd commits (warn, don't block)
```bash
# For each commit on dev not on main, check if it came from a merged PR
ORPHAN_COUNT=0
while IFS= read -r sha; do
    PR_COUNT=$(gh pr list --state merged --search "$sha" --json number -q 'length' 2>/dev/null || echo "0")
    if [ "$PR_COUNT" = "0" ]; then
        ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
    fi
done < <(git log --format="%H" origin/$DEFAULT_BRANCH..origin/$DEV_BRANCH)

if [ "$ORPHAN_COUNT" -gt 0 ]; then
    echo "WARNING: $ORPHAN_COUNT commit(s) on $DEV_BRANCH are not associated with a merged PR."
    echo "These commits may not have been reviewed."
    # Ask: continue / abort (unless --force flag)
fi
```

## 3. Determine PR Type

Scan the commits being promoted to suggest a conventional commit type:

```bash
COMMITS_TEXT=$(git log --format="%s" origin/$DEFAULT_BRANCH..origin/$DEV_BRANCH)

# Check for breaking changes
if echo "$COMMITS_TEXT" | grep -qP '(feat|fix|refactor)!:'; then
    SUGGESTED_TYPE="feat!"
    echo "Contains BREAKING CHANGES - this will trigger a major version bump."
# Check for features
elif echo "$COMMITS_TEXT" | grep -q '^feat'; then
    SUGGESTED_TYPE="feat"
# Check for only fixes
elif echo "$COMMITS_TEXT" | grep -q '^fix' && ! echo "$COMMITS_TEXT" | grep -qP '^(feat|refactor|perf)'; then
    SUGGESTED_TYPE="fix"
# Mixed or other
else
    SUGGESTED_TYPE="feat"
fi

echo "Suggested PR type: $SUGGESTED_TYPE"
# Ask user to confirm or change
```

## 4. Create Promotion PR

```bash
# Build commit list for PR body
COMMIT_LIST=$(git log --format="- %s (%h)" origin/$DEFAULT_BRANCH..origin/$DEV_BRANCH)

gh pr create \
    --base $DEFAULT_BRANCH \
    --head $DEV_BRANCH \
    --title "$SUGGESTED_TYPE: promote $DEV_BRANCH to $DEFAULT_BRANCH" \
    --body "## Promotion: $DEV_BRANCH -> $DEFAULT_BRANCH

### Commits being promoted
$COMMIT_LIST

### Pre-flight checks
- [x] CI passing on $DEV_BRANCH HEAD
- [x] $DEV_BRANCH is ahead of $DEFAULT_BRANCH
- [x] $DEV_BRANCH is up to date with $DEFAULT_BRANCH
- [$([ $ORPHAN_COUNT -eq 0 ] && echo 'x' || echo ' ')] All commits from reviewed PRs

### Notes
This PR uses **merge** (not squash) to preserve individual commit messages for semantic-release changelog generation."
```

## 5. Set Automerge

```bash
PR_NUMBER=$(gh pr view --json number -q .number)

# Use --merge to preserve individual commit messages for semantic-release
gh pr merge --auto --merge $PR_NUMBER
```

**Why --merge (not --squash):** Semantic-release parses individual commit messages to generate changelogs and determine version bumps. Squashing would lose this information.

## 6. Final Output

```
Promotion PR created!

PR: https://github.com/owner/repo/pull/100
From: dev -> main
Commits: 5
Type: feat (minor version bump expected)
Automerge: enabled (merge strategy)

Status checks will run on the PR. Once they pass, the PR will auto-merge.

Monitor: /ai-monitor-pipeline 100
```

## Error Handling
- **No dev branch**: Clear error explaining this is a main-only repo
- **CI not passing**: Refuse to promote, link to failing run
- **CI not run on latest**: Warn, suggest waiting or re-triggering
- **Dev behind main**: Warn about sync, suggest `/ai-prepare-branch`
- **No commits to promote**: Exit cleanly
- **PR creation fails**: Show error (common: PR already exists for this branch pair)
- **Automerge not available**: Warn that repo may need automerge enabled in settings
