Start working on selected issue(s) with proper branch setup: $ARGUMENTS

Intelligently creates branches and sets up your workspace after selecting issues with `/ai-pick-issue`.

## Usage Examples
- `/ai-start-work 1` - Work on first issue from pick-issue list
- `/ai-start-work the devops one` - Natural language selection
- `/ai-start-work 1 and 4` - Work on multiple issues together
- `/ai-start-work #123` - Direct issue number
- `/ai-start-work fix auth timeout` - Match by description

## 1. Parse Selection

```bash
# Understand what the user wants to work on
# This could be:
# - Number(s) from previous ai-pick-issue output
# - Issue number(s) with # prefix
# - Natural language description
# - Multiple issues joined by "and"
```

### If Previous ai-pick-issue Context Available
- Map selection numbers to actual issue numbers
- Handle natural language like "the devops one"
- Support multiple selections

### If Direct Issue Reference
- Extract issue numbers from #123 format
- Validate issues exist and are open

### If Natural Language
- Search for matching issues
- Show matches and confirm selection

## 2. Validate Current State

```bash
# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  You have uncommitted changes"
    git status -s

    echo "Options:"
    echo "1) Stash changes and continue"
    echo "2) Commit changes first"
    echo "3) Cancel"

    # If stashing:
    git stash push -m "WIP: Before starting issue #$ISSUE_NUMBER"
fi

# Ensure we're on the default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@' || echo "main")
CURRENT_BRANCH=$(git branch --show-current)

if [[ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]]; then
    echo "📍 Currently on branch: $CURRENT_BRANCH"
    echo "Switching to $DEFAULT_BRANCH first..."
    git checkout $DEFAULT_BRANCH
fi

# Pull latest changes
echo "📥 Updating $DEFAULT_BRANCH..."
git pull origin $DEFAULT_BRANCH
```

## 3. Create Branch Name

```bash
# Analyze issue(s) to determine branch type and name

# For single issue
if single_issue; then
    # Get issue details via mcp__github__get_issue
    # Extract title, labels, and type

    # Determine prefix based on labels/title
    if [[ "$LABELS" == *"bug"* ]]; then
        PREFIX="fix"
    elif [[ "$LABELS" == *"documentation"* ]] || [[ "$TITLE" == *"doc"* ]]; then
        PREFIX="docs"
    elif [[ "$LABELS" == *"enhancement"* ]] || [[ "$LABELS" == *"feature"* ]]; then
        PREFIX="feat"
    elif [[ "$LABELS" == *"refactor"* ]]; then
        PREFIX="refactor"
    elif [[ "$LABELS" == *"test"* ]]; then
        PREFIX="test"
    elif [[ "$LABELS" == *"chore"* ]]; then
        PREFIX="chore"
    else
        PREFIX="feat"  # Default
    fi

    # Create branch name
    BRANCH_NAME="$PREFIX/issue-$ISSUE_NUMBER-$(echo "$ISSUE_TITLE" |
        tr '[:upper:]' '[:lower:]' |
        tr ' ' '-' |
        sed 's/[^a-z0-9-]//g' |
        cut -c1-40)"
fi

# For multiple issues
if multiple_issues; then
    # Find common theme or use generic name
    ISSUE_NUMBERS=$(echo $ISSUES | tr ' ' '-')

    # Try to find common theme in titles
    if all_issues_contain "auth"; then
        BRANCH_NAME="feat/issues-$ISSUE_NUMBERS-auth-improvements"
    elif all_issues_contain "fix"; then
        BRANCH_NAME="fix/issues-$ISSUE_NUMBERS-multiple-fixes"
    else
        BRANCH_NAME="feat/issues-$ISSUE_NUMBERS-combined-work"
    fi
fi
```

## 4. Create and Setup Branch

```bash
# Create the branch
echo "🌿 Creating branch: $BRANCH_NAME"
git checkout -b $BRANCH_NAME

# Push and set upstream
echo "📤 Setting up remote tracking..."
git push -u origin $BRANCH_NAME

# If we stashed earlier, apply the stash
if [ "$STASHED" = true ]; then
    echo "📦 Applying stashed changes..."
    git stash pop
fi
```

## 5. Create Work Context

```bash
# Create a .current-work file to track what we're working on
cat > .current-work << EOF
# Current Work Context
Issues: $ISSUE_NUMBERS
Branch: $BRANCH_NAME
Started: $(date)

## Issue Details:
$ISSUE_SUMMARIES

## Acceptance Criteria:
$ACCEPTANCE_CRITERIA

## Notes:
- Remember to write tests first (TDD)
- Run pre-commit before committing
- Update documentation as needed
EOF

echo "📝 Created .current-work file with issue context"
```

## 6. Set Up Development Environment

```bash
# Run any project-specific setup
if [ -f "Makefile" ] && grep -q "dev-setup:" Makefile; then
    echo "🔧 Running development setup..."
    make dev-setup
fi

# Install/update dependencies if needed
if [ -f "pyproject.toml" ]; then
    echo "📦 Ensuring dependencies are up to date..."
    poetry install
elif [ -f "package.json" ]; then
    echo "📦 Ensuring dependencies are up to date..."
    npm install
fi
```

## 7. Final Output

```
✅ Ready to work on issue(s): #123, #456

📌 Branch: feat/issues-123-456-auth-improvements
🔗 Tracking: origin/feat/issues-123-456-auth-improvements

📋 Issue Summary:
- #123: Fix authentication timeout (bug, high-priority)
- #456: Add refresh token support (enhancement)

💡 Next Steps:
1. Write tests for the new functionality
2. Implement the changes
3. Run tests: make test
4. Check quality: make check
5. When ready: /ai-ship

🔧 Useful Commands:
- View issue details: gh issue view 123
- Add comment to issue: gh issue comment 123 -b "Started work"
- Check PR requirements: cat .github/pull_request_template.md

Remember: Follow TDD - write tests first! 🧪
```

## Integration with ai-pick-issue

This command is designed to work seamlessly after `/ai-pick-issue`:

1. Run `/ai-pick-issue` to see available issues
2. Select which to work on with `/ai-start-work 1` or `/ai-start-work 1 and 3`
3. Branch is created with proper naming conventions
4. Work context is established

## Error Handling

- **Invalid selection**: Show available options from last pick-issue
- **Issue not found**: Suggest running pick-issue first
- **Branch exists**: Offer to switch to it or create alternative
- **Merge conflicts on pull**: Guide through resolution
- **Network issues**: Proceed with local branch, push later
