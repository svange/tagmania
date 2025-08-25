Intelligently find or select GitHub issues: $ARGUMENTS

Smart issue finder that understands numbers, keywords, and natural language.

## Usage Examples
- `/ai-pick-issue 24` - Get issue #24
- `/ai-pick-issue devops` - Find open issues about devops
- `/ai-pick-issue the one about pre-commit` - Natural language search
- `/ai-pick-issue` - Recommend best issues to work on

## 1. Parse Input Type

```bash
# Get repository context from current directory
REPO_URL=$(git remote get-url origin 2>/dev/null)
if [ -z "$REPO_URL" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Extract owner/repo from URL
REPO_CONTEXT="repo:$(echo $REPO_URL | sed -E 's|.*[:/]([^/]+/[^/]+)\.git|\1|')"
```

Analyze $ARGUMENTS:
- **Numeric only** (e.g., "24", "123") → Direct issue lookup
- **Keywords** (e.g., "auth", "devops", "bug") → Keyword search
- **Natural language** (e.g., "the one about...") → Smart search
- **Empty** → Issue recommendation mode

## 2. Direct Issue Lookup (Numeric)

If $ARGUMENTS is numeric, use `mcp__github__get_issue`:
```
- Fetch issue details
- Show title, state, labels, assignee
- Display description and recent comments
- Highlight if issue is CLOSED (warn user)
```

## 3. Search Mode (Keywords/Natural Language)

Use `mcp__github__search_issues` with:
```
Query: "$ARGUMENTS state:open $REPO_CONTEXT"
```

For natural language queries:
- Extract key terms
- Remove filler words ("the", "about", "that")
- Search in title, body, and comments

Display results:
```
=== Open Issues Matching "$ARGUMENTS" ===

1. #123 [bug] Pre-commit hooks not working on Windows
   Last updated: 2 days ago
   Labels: bug, windows, tooling

2. #456 [enhancement] Add pre-commit configuration
   Last updated: 1 week ago
   Labels: enhancement, developer-experience
```

## 4. Recommendation Mode (Empty Arguments)

When no arguments provided, intelligently recommend issues:

### Fetch Candidates
```
Queries to run:
1. High priority: "state:open label:P0,P1,critical,bug $REPO_CONTEXT"
2. Good first: "state:open label:good-first-issue $REPO_CONTEXT"  
3. Recent activity: "state:open $REPO_CONTEXT sort:updated-desc"
```

### Scoring Algorithm
```python
score = 0
# Priority labels
if "P0" in labels: score += 10
if "P1" in labels: score += 7
if "bug" in labels: score += 5

# Freshness
days_old = (now - created_at).days
if days_old > 30: score += 3  # Older issues need attention

# Community interest
score += min(reactions_count, 5)  # Cap at 5

# Complexity (fewer comments = simpler)
if comment_count < 3: score += 2

# Unassigned
if not assignee: score += 3
```

### Present Recommendations
```
=== Recommended Issues ===

1. #123 [Score: 18] 🐛 Fix authentication timeout
   - High priority bug affecting multiple users
   - Clear reproduction steps provided
   - Estimated: 2-4 hours

2. #456 [Score: 15] ✨ Add metrics dashboard  
   - High impact feature request
   - Good first issue for monitoring
   - Estimated: 1-2 days

3. #789 [Score: 12] 📚 Update API documentation
   - Quick win, improves developer experience
   - Estimated: 1 hour
```

## 5. Final Output

**IMPORTANT**: This command only presents issues. To start working on an issue, use:
```
/ai-start-work <issue-number-or-description>
```

Examples:
- `/ai-start-work 1` - Start work on the first recommended issue
- `/ai-start-work the auth bug` - Start work on the authentication issue
- `/ai-start-work 1 and 3` - Work on multiple issues together

## Error Handling

- **Issue not found**: Suggest similar issue numbers or search
- **No matches**: Broaden search or check closed issues
- **API errors**: Provide helpful context and retry options
