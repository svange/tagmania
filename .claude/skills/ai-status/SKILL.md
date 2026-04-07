---
name: ai-status
description: Show current workspace status, open PRs, pipeline state, and suggested next step. Also triggered by 'where am I', 'what's going on', 'status'.
argument-hint: ""
---

Show current workspace status, pipeline state, and suggest the next action.

Runs a batch of read-only commands to build a dashboard. Degrades gracefully if GitHub CLI is unavailable.

## Usage Examples
- `/ai-status` - Full dashboard
- Triggered by: "where am I", "what's going on", "status"

## 1. Gather Data

Run these commands in a single batched script to minimize tool invocations:

```bash
BRANCH=$(git branch --show-current 2>/dev/null || echo "DETACHED")
UPSTREAM=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null | sed 's|origin/||' || echo "")
STATUS=$(git status --porcelain 2>/dev/null)
MOD_COUNT=$(echo "$STATUS" | grep -c "^ M\|^M " 2>/dev/null || echo "0")
NEW_COUNT=$(echo "$STATUS" | grep -c "^??" 2>/dev/null || echo "0")
DEL_COUNT=$(echo "$STATUS" | grep -c "^ D\|^D " 2>/dev/null || echo "0")
AHEAD=$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo "?")
BEHIND=$(git rev-list --count HEAD..@{upstream} 2>/dev/null || echo "?")
echo "BRANCH=$BRANCH"
echo "UPSTREAM=$UPSTREAM"
echo "MOD=$MOD_COUNT NEW=$NEW_COUNT DEL=$DEL_COUNT"
echo "AHEAD=$AHEAD BEHIND=$BEHIND"
```

If `gh` is available and authenticated, also run:
```bash
PR_JSON=$(gh pr list --head "$BRANCH" --state open --json number,title,url --limit 1 2>/dev/null || echo "[]")
LATEST_RUN=$(gh run list --branch "$BRANCH" --limit 1 --json databaseId,status,conclusion,createdAt 2>/dev/null || echo "[]")
ASSIGNED=$(gh issue list --assignee @me --state open --limit 5 --json number,title 2>/dev/null || echo "[]")
echo "PR=$PR_JSON"
echo "RUN=$LATEST_RUN"
echo "ISSUES=$ASSIGNED"
```

If `gh` commands fail, note "GitHub data unavailable (run `gh auth login` to enable)" and show git-only info.

## 2. Format Dashboard

Present as a clean, readable dashboard:

```
=== Workspace Status ===

Branch: feat/issue-42-auth-timeout
  Changes: 3 modified, 1 new, 0 deleted
  Ahead of origin: 2 commits (unpushed)
  Behind target: 0 commits

Pipeline: passing (run #12345, completed 5 min ago)
Open PR: #98 "feat: add auth timeout handling" -- automerge enabled

Assigned issues:
  #42 auth timeout (in progress -- this branch)
  #50 metrics dashboard (open)

Suggested next step: /ai-submit-work (you have unpushed changes)
```

## 3. Suggested Next Step Logic

Based on current state, suggest ONE next action:

| State | Suggestion |
|-------|-----------|
| Uncommitted changes on work branch | `/ai-submit-work` (you have uncommitted changes) |
| Unpushed commits on work branch | `/ai-submit-work` (you have unpushed commits) |
| On main/dev, no changes | `/ai-pick-issue` (find your next task) |
| Pipeline failing on current branch | `/ai-monitor-pipeline` (pipeline needs attention) |
| Work branch, no changes, open PR, pipeline running | `/ai-monitor-pipeline` (PR awaiting CI) |
| Work branch, no changes, PR merged | Cleanup: switch to base and delete branch |
| On dev, ahead of main, CI passing | `/ai-promote` (dev is ready to release) |
| Behind target branch | Consider syncing -- will be handled automatically at submit time |

If "behind target" count is >0, add context: "This is normal if the target branch has been active. It will be handled automatically when you submit."

## Error Handling
- **Not in a git repo**: "Not in a git repository. Navigate to a project directory first."
- **No remote configured**: Show local git status only, skip GitHub data
- **gh not authenticated**: Show git data, note GitHub data is unavailable
- **Detached HEAD**: Show commit SHA instead of branch name, suggest checking out a branch
