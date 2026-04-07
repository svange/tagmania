---
name: ai-repo-health
description: Comprehensive repository health check with remote-first git hygiene, branch cleanup, and code quality analysis. Use for repo maintenance, or saying 'clean up the repo'.
argument-hint: "[--remote-only] [--local-only] [--dry-run]"
---

Comprehensive repository health check with remote-first git hygiene: $ARGUMENTS

Deep repository analysis and cleanup that prioritizes remote repository hygiene, prevents lost work, and maintains code quality. Remote branches are cleaned first to ensure a truly clean repository state.

## Usage Options

```bash
# Full health check with remote cleanup
/ai-repo-health

# Focus modes
/ai-repo-health --remote-only    # Just remote cleanup
/ai-repo-health --local-only     # Just local cleanup
/ai-repo-health --issues-only    # Just GitHub issues
/ai-repo-health --code-only      # Just code quality

# Safety options
/ai-repo-health --dry-run        # Preview only
/ai-repo-health --backup-first   # Force backup before any changes

# Automation
/ai-repo-health --auto --max-age=90  # Auto-delete branches older than 90 days
```

## Phase 1: Remote Repository Hygiene (Priority)

1. **Sync and analyze remote state**:
   ```bash
   # Full remote sync
   git fetch --all --prune --tags
   git remote show origin

   # Get default branch
   DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

   # List ALL remote branches with details
   git for-each-ref --format='%(refname:short)|%(committerdate:relative)|%(authorname)|%(committername)' refs/remotes/origin/ | grep -v HEAD | sort -t'|' -k2 -r
   ```

2. **Identify remote branches for cleanup**:
   ```bash
   # Fully merged to default branch
   git branch -r --merged origin/$DEFAULT_BRANCH | grep -v -E "(HEAD|$DEFAULT_BRANCH|master|main|develop|release|hotfix)"

   # Stale branches (no commits in 60+ days)
   for branch in $(git branch -r | grep -v HEAD); do
     last_commit=$(git log -1 --format="%cr" $branch)
     days_ago=$(git log -1 --format="%ct" $branch | xargs -I{} date -d @{} +%s | xargs -I{} echo $(( ($(date +%s) - {}) / 86400 )))
     if [ $days_ago -gt 60 ]; then
       echo "$branch|$last_commit|$days_ago days"
     fi
   done
   ```

3. **Check GitHub PR status for each branch**:
   ```bash
   # For each remote branch, check:
   # - Is there an open PR?
   # - Was the PR merged?
   # - Is the branch protected?
   # - Who is the last committer?
   gh pr list --state all --head <branch-name> --json number,state,mergedAt
   ```

4. **Interactive remote cleanup**:
   For each deletable remote branch:
   ```
   Branch: origin/feature-xyz
   Last commit: 3 months ago by John Doe
   Status: PR #123 merged 3 months ago
   Protected: No

   Delete this remote branch? [y/n/skip-all/delete-all]
   ```

   If confirmed:
   ```bash
   git push origin --delete feature-xyz
   ```

5. **Verify remote cleanup**:
   ```bash
   git fetch --prune
   git branch -r | wc -l  # Should show reduced count
   ```

## Phase 2: Lost Work Recovery

6. **Scan for orphaned commits**:
   ```bash
   # Find dangling commits not on any branch
   git fsck --lost-found --no-reflogs | grep commit | cut -d' ' -f3 > /tmp/orphaned-commits.txt

   # Analyze each orphan
   while read commit; do
     echo "=== Orphaned commit: $commit ==="
     git show --stat --format="%h %ae %ad %s" --date=relative $commit

     if git branch -r --contains $commit | grep -q .; then
       echo "Exists on remote branch"
     else
       echo "WARNING: Not on any remote branch - AT RISK"
     fi
   done < /tmp/orphaned-commits.txt
   ```

7. **Interactive recovery**:
   For each at-risk commit:
   - Show full details and diff
   - Options: Create recovery branch / Skip / Create stash
   - If recovering: `git branch recovery/orphan-$SHORT_HASH $COMMIT`

8. **Stash management**:
   ```bash
   git stash list --format="%gd: %gs - %ar" | while read stash; do
     age=$(echo $stash | grep -oE "[0-9]+ (weeks?|months?|years?) ago")
     if [[ $age =~ (month|year) ]]; then
       echo "Old stash: $stash"
       # Show contents and ask to keep/apply/drop
     fi
   done
   ```

## Phase 3: Local Branch Hygiene

9. **Analyze local branches**:
   ```bash
   # Find locals with deleted remotes
   git branch -vv | grep ': gone]' | awk '{print $1}'

   # Find locals that are fully merged
   git branch --merged $DEFAULT_BRANCH | grep -v -E "^\*|$DEFAULT_BRANCH"

   # Find locals with no upstream
   git branch -vv | grep -v '\[' | awk '{print $1}'
   ```

10. **Interactive local cleanup**:
    For each category:
    - **Deleted remote**: "Remote branch was deleted. Delete local?"
    - **Fully merged**: "Branch is merged. Delete local?"
    - **No upstream**: "No remote tracking. Push to remote or delete?"

## Phase 4: Repository Optimization

11. **Git maintenance**:
    ```bash
    # Before size
    du -sh .git

    # Aggressive cleanup
    git reflog expire --expire=30.days --expire-unreachable=now --all
    git gc --aggressive --prune=now
    git repack -a -d -f --depth=250 --window=250

    # After size
    du -sh .git
    ```

12. **Config cleanup**:
    ```bash
    for branch in $(git config --get-regexp '^branch\.' | cut -d. -f2 | sort -u); do
      if ! git show-ref --verify --quiet refs/heads/$branch; then
        echo "Removing config for deleted branch: $branch"
        git config --remove-section branch.$branch 2>/dev/null
      fi
    done
    ```

## Phase 5: Code & Project Health

13. **GitHub issue management**:
    ```bash
    # Find stale issues (>90 days inactive)
    gh issue list --state open --json number,title,updatedAt --limit 100

    # Issues referencing deleted branches
    # Issues already implemented
    # Duplicate issues
    ```

14. **Code quality scan**:
    ```bash
    # TODOs and FIXMEs
    rg -i "TODO|FIXME|HACK|XXX|BUG" --stats

    # Large files
    find . -size +10M -type f | grep -v -E "\.git|node_modules|\.venv"

    # Generated files in repo
    find . -name "*.pyc" -o -name "__pycache__" -o -name ".DS_Store" -o -name "*.log"
    ```

15. **Dependency health**:
    ```bash
    # Python
    if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
      pip-audit 2>/dev/null || uv run pip-audit 2>/dev/null
    fi

    # JavaScript
    if [ -f "package.json" ]; then
      npm audit
      npm outdated
    fi
    ```

16. **Documentation check**:
    ```bash
    # Find broken internal links in markdown
    rg '\[([^\]]+)\]\(([^)]+)\)' -o -r '$2' *.md | while read link; do
      if [[ $link =~ ^[^:]+$ ]] && [ ! -e "$link" ]; then
        echo "Broken link: $link"
      fi
    done
    ```

## Phase 6: Comprehensive Report

17. **Generate detailed report**:
    ```markdown
    # Repository Health Report - [DATE]

    ## Executive Summary
    - Remote branches deleted: X
    - Local branches deleted: Y
    - Orphaned commits recovered: Z
    - Repository size: X MB -> Y MB (Z% reduction)

    ## Remote Cleanup
    ### Deleted Remote Branches
    - origin/feature-old (PR #123 merged 3 months ago)

    ### Kept Remote Branches
    - origin/feature-active (recent activity)

    ## Local Cleanup
    ### Deleted Local Branches
    - feature-old (tracking deleted remote)

    ### Branches Needing Attention
    - feature-local-only (uncommitted changes)

    ## Recovered Work
    ### Created Recovery Branches
    - recovery/orphan-abc123 (Fix critical bug)

    ## Code Health Issues
    ### High Priority
    - 3 security vulnerabilities in dependencies

    ### Medium Priority
    - 8 stale issues can be closed

    ## Recommendations
    1. Review recovery branches within 7 days
    2. Update dependencies to fix vulnerabilities
    3. Enable branch protection rules
    ```

## Safety Features

- **Pre-cleanup backup**: `git bundle create repo-backup-$(date +%Y%m%d).bundle --all`
- **Confirmation required** for ALL remote deletions
- **Never delete** protected branches or branches with open PRs
- **Recovery period**: All deleted branches recoverable via reflog for 30 days
- **Dry run mode**: `--dry-run` flag to preview without changes
