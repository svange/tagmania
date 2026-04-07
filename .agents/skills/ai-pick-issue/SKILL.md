---
name: ai-pick-issue
description: Find, analyze, and recommend GitHub issues to work on. Use when looking for issues, or asking 'what should I work on next'.
argument-hint: "[issue-number or search-terms]"
---

Intelligently find or select GitHub issues: $ARGUMENTS

> **Workflow automation:** This skill is part of an automated workflow. When an issue is selected and the design conversation concludes, proceed directly to branch preparation by invoking `/ai-prepare-branch`. Do NOT prompt "shall I continue?" or "would you like me to run /ai-prepare-branch?" -- just do it.

Smart issue finder that understands numbers, keywords, and natural language.

## Usage Examples
- `/ai-pick-issue 24` - Get issue #24
- `/ai-pick-issue devops` - Find open issues about devops
- `/ai-pick-issue the one about pre-commit` - Natural language search
- `/ai-pick-issue` - Recommend best issues to work on

## 1. Parse Input Type

```bash
# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Get repository owner/name from remote
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
if [ -z "$REPO" ]; then
    echo "Error: Could not determine repository. Make sure 'gh' is authenticated."
    exit 1
fi
```

Analyze $ARGUMENTS:
- **Numeric only** (e.g., "24", "123") -> Direct issue lookup
- **Keywords** (e.g., "auth", "devops", "bug") -> Keyword search
- **Natural language** (e.g., "the one about...") -> Smart search
- **Empty** -> Issue recommendation mode

## 2. Direct Issue Lookup (Numeric)

If $ARGUMENTS is numeric, use `gh issue view`:
```bash
gh issue view $ISSUE_NUMBER --json number,title,state,labels,assignees,body,comments
```

- Show title, state, labels, assignee
- Display description and recent comments
- **IMPORTANT**: If state is "CLOSED", warn user prominently

## 3. Search Mode (Keywords/Natural Language)

Use `gh issue list` with search:
```bash
# For keyword search
gh issue list --state open --search "$ARGUMENTS" --limit 30 --json number,title,labels,updatedAt,comments

# For label-based search
gh issue list --state open --label "$LABEL" --limit 30
```

For natural language queries:
- Extract key terms
- Remove filler words ("the", "about", "that")
- Search in title and body

## 4. Recommendation Mode (Empty Arguments)

When no arguments provided, intelligently recommend OPEN issues only:

### Fetch Candidates
```bash
# Get all open issues with detailed information
gh issue list --state open --limit 100 --json number,title,labels,createdAt,updatedAt,comments,assignees,body

# Separate queries for specific categories:
# High priority bugs
gh issue list --state open --label bug --limit 20

# Good first issues
gh issue list --state open --label good-first-issue --limit 20

# Recently updated
gh issue list --state open --sort updated --limit 20
```

### Scoring Algorithm
```python
score = 0
# Priority labels
if "P0" or "critical" in labels: score += 10
if "P1" or "high-priority" in labels: score += 7
if "bug" in labels: score += 5
if "security" in labels: score += 8

# Freshness (older issues need attention)
days_old = (now - created_at).days
if days_old > 30: score += 3
if days_old > 60: score += 2

# Activity level
if comment_count == 0: score += 1  # Needs initial response
if comment_count > 10: score -= 2  # Might be complex/stuck

# Assignment status
if not assignee: score += 3  # Available to work on

# Implementation readiness
if "good-first-issue" in labels: score += 4
if "help-wanted" in labels: score += 3
if body_length > 500: score += 2  # Well-documented

# CRITICAL: Never recommend closed issues
if state == "CLOSED": score = -1000

# Renovate Dependency Dashboard filtering (see subsection below)
if is_renovate_dashboard(issue):
    if not has_actionable_items(issue):
        score = -1000  # Skip -- schedule handles it
    else:
        score = 6  # Override with moderate score for actionable dashboards
```

### Renovate Dependency Dashboard Filtering

Renovate creates a "Dependency Dashboard" issue that tracks all pending updates. Most of the time this issue requires no human intervention -- the Renovate schedule handles everything automatically. Only surface it when there are genuinely stuck or failed items.

**Detection**: An issue is a Renovate dashboard if:
- Title contains "Dependency Dashboard" (case-insensitive), OR
- Author/creator is `renovate[bot]`

**Triage the dashboard body** for actionable items. Fetch the full issue body:
```bash
gh issue view $NUMBER --json number,title,body,author
```

**Actionable** (include in recommendations):
- Any item with a warning or error icon (`:warning:`, `:x:`, unicode warning/error symbols)
- A "Rate-Limited" section with items stuck for >7 days
- PRs listed under "Open" that are older than 14 days (stale/stuck)
- Items explicitly marked as "Failing" or "Error"
- Checkboxes the user has manually ticked (indicating manual intervention requested)

**Not actionable** (exclude from recommendations):
- Dashboard body says "all updates are up-to-date" or equivalent
- Only contains "Detected Dependencies" section (informational)
- All pending items are within their scheduled window
- Open PRs are recent (<7 days) and progressing normally (awaiting CI or automerge)

When a Renovate dashboard IS actionable, present it with a brief summary of what needs attention (e.g., "2 stuck PRs, 1 failed update") rather than showing the full dashboard body.

### Present Recommendations

Display results as a ranked table:

```
=== Recommended Open Issues ===

| Rank | Issue | Score | Title                      | Labels            | Age     |
|------|-------|-------|----------------------------|-------------------|---------|
| 1    | #123  | 18    | Fix authentication timeout | bug, high-priority| 5 days  |
| 2    | #456  | 15    | Add metrics dashboard      | enhancement       | 2 weeks |
| 3    | #789  | 12    | Update API documentation   | docs, good-first  | 1 month |

Recommendation: Start with #123 - high priority bug with clear reproduction steps.
```

## 5. Implementation Details

### Use gh CLI for All Operations
```bash
# List issues (never includes closed by default)
gh issue list --state open [options]

# View specific issue
gh issue view NUMBER [options]

# Search issues
gh issue list --state open --search "query"

# Get issue with all details
gh issue view NUMBER --json number,title,state,labels,body,comments,assignees,createdAt,updatedAt
```

### JSON Processing
Use `--json` flag with `jq` for structured data:
```bash
gh issue list --state open --label high-priority --json number,title,labels | jq '.[] | select(.labels[].name == "bug")'
```

### Error Handling
- **Issue not found**: Suggest checking issue number or searching
- **No matches**: Broaden search or check if any open issues exist
- **Authentication errors**: Remind user to run `gh auth login`
- **Closed issue accessed**: Prominently warn that issue is closed

## 6. Collaborative Design Conversation

After presenting the issue details, do NOT immediately suggest `/ai-prepare-branch`. Instead, engage the user in a design dialogue scaled to the issue's complexity.

### Gauge Complexity

Before starting, assess issue complexity from labels, body, and title:

**Simple** (clear bug with repro steps, small config change, docs fix):
- 0-1 questions max. Present approach briefly and proceed.
- Signals: "bug" label, clear reproduction steps, single file mentioned, short body with clear intent.
- **Exception**: if combined title+body is <100 characters AND lacks clear reproduction steps, ask at least 1 question (prevent proceeding on insufficient info).

**Medium** (feature with mostly clear spec, refactor with known scope):
- 2-3 targeted questions. Present approach and proceed.
- Signals: "enhancement" label, moderate body, clear acceptance criteria.

**Complex** (architectural change, unclear requirements, multiple approaches):
- 3-5 questions. Full design dialogue with approach summary checkpoint.
- Signals: "RFC" or "discussion" labels, multiple components mentioned, no clear acceptance criteria, security-sensitive.

**Conflict resolution**: If signals conflict (e.g., "good-first-issue" + "security"), highest complexity wins.

### Initiate the Conversation

1. **Summarize your understanding** of the issue in 2-3 sentences
2. **Propose an implementation approach** - identify the key files, components, or architecture involved
3. **Surface trade-offs and open questions** - flag ambiguities, alternative approaches, or constraints you see
4. **Ask clarifying questions** (number based on complexity assessment above), such as:
   - Requirements: "The issue mentions X -- should that also handle Y?"
   - Scope: "Should this include Z, or is that a separate issue?"
   - Architecture: "I see two approaches here: A vs B. Which fits your codebase better?"
   - Constraints: "Are there performance/compatibility concerns I should know about?"

### Continue the Dialogue (Medium/Complex only)

- Listen to the user's answers and refine your understanding
- Propose a more detailed plan when you have enough context
- Ask follow-up questions if answers reveal new ambiguities
- Challenge assumptions respectfully -- raise risks the user may not have considered

### Confirm Alignment

When you believe alignment is reached, present a concise implementation summary:

```
=== Proposed Approach ===
Goal: [one sentence]
Approach: [2-3 key decisions]
Files likely affected: [list]
Out of scope: [what we're NOT doing]
```

Present this summary naturally as part of the conversation. If the user engages with questions or corrections, refine the approach. If the user signals agreement (or does not object), proceed to prepare the branch.

Do NOT ask "Ready to proceed?" or wait for explicit confirmation. Treat the design summary as a natural checkpoint -- pause briefly for the user to react, then move forward.

## 7. Final Output and Automatic Transition

**IMPORTANT**:
- Only recommend or list OPEN issues
- If user specifies a closed issue number, show it but warn prominently
- Never include closed issues in recommendation scoring

**Automatic next step:** After the design conversation concludes (user agrees or does not object to the proposed approach), immediately invoke `/ai-prepare-branch <issue-number>` to create the branch. Do NOT just suggest it -- actually run it. The user expects the workflow to continue automatically.

If no specific issue was selected (e.g., user was just browsing recommendations), present the recommendations and stop.
