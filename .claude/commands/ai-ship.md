Ship your changes with a complete pull request workflow: $ARGUMENTS

Smart automation that handles the entire process from commit to PR creation.

## What It Does

This command handles the entire GitHub workflow:
1. Detects all changes
2. Runs pre-commit if available
3. Creates single commit with all changes
4. Pushes to remote
5. Creates pull request with proper formatting
6. Links to issues being addressed

## Usage

```bash
/ai-ship
```

The command will:
- Analyze your changes
- Run quality checks
- Create a well-formatted commit
- Push and create a PR with test plan

## The Workflow

### 1. Check Work Context

```bash
# If .current-work file exists, load issue context
if [ -f ".current-work" ]; then
    ISSUE_NUMBERS=$(grep "Issues:" .current-work | cut -d: -f2)
    echo "📋 Working on issues: $ISSUE_NUMBERS"
fi

# Verify we're on a feature branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "main" ]] || [[ "$CURRENT_BRANCH" == "master" ]]; then
    echo "❌ Cannot ship from $CURRENT_BRANCH branch"
    echo "Please use /ai-start-work to create a feature branch"
    exit 1
fi
```

### 2. Analyze All Changes

```bash
# Check what's changed
git status
git diff --cached --name-only
git diff --name-only

# Show summary of changes
echo "📊 Change Summary:"
git diff --stat
```

### 3. Run Pre-commit and Quality Checks

```bash
# Always run pre-commit first
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🔍 Running pre-commit hooks..."
    poetry run pre-commit run --all-files || true

    # Add any changes made by pre-commit
    git add -A
fi

# Run tests if available
if [ -f "Makefile" ] && grep -q "test:" Makefile; then
    echo "🧪 Running tests..."
    make test
elif [ -f "pyproject.toml" ] && grep -q "pytest" pyproject.toml; then
    echo "🧪 Running tests..."
    poetry run pytest
fi

# Run additional quality checks
if [ -f "Makefile" ] && grep -q "check:" Makefile; then
    echo "✅ Running quality checks..."
    make check
fi
```

### 4. Create Intelligent Commit

```bash
# Analyze changes to create meaningful commit message
# - Determine type (feat/fix/docs/refactor/test/chore)
# - Extract key changes
# - Link to issues

# Build commit message
COMMIT_TYPE=$(determine_commit_type_from_changes)
COMMIT_SUMMARY=$(generate_commit_summary)
COMMIT_BODY=$(generate_detailed_body)

# If working on issues, add references
if [ -n "$ISSUE_NUMBERS" ]; then
    CLOSES_CLAUSE="Closes $ISSUE_NUMBERS"
fi

# Create the commit
git commit -m "$(cat <<EOF
$COMMIT_TYPE: $COMMIT_SUMMARY

$COMMIT_BODY

$CLOSES_CLAUSE

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 5. Push to Remote

```bash
# Push the branch
echo "📤 Pushing to remote..."
git push origin $CURRENT_BRANCH
```

### 6. Create Pull Request

```bash
# Generate PR title based on commit and issues
PR_TITLE=$(generate_pr_title)

# Create comprehensive PR body
gh pr create \
  --title "$PR_TITLE" \
  --body "$(cat <<EOF
## Summary
$PR_SUMMARY_BULLETS

## Changes Made
$DETAILED_CHANGES

## Test Plan
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Pre-commit hooks pass
- [ ] Manual testing completed
$ADDITIONAL_TEST_ITEMS

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated where necessary
- [ ] No sensitive information exposed

$CLOSES_CLAUSE

## Screenshots/Output
$SCREENSHOTS_IF_APPLICABLE

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"

# Set up auto-merge if available
echo "🔄 Setting up auto-merge..."
gh pr merge --auto --squash
```

## Smart Features

### Change Detection
- Understands what kind of changes were made
- Groups related changes together
- Identifies breaking changes

### Commit Message Generation
```
Examples based on changes:

Feature Addition:
feat: add user authentication system

- Implement JWT token generation
- Add login/logout endpoints  
- Create user session management
- Add comprehensive test coverage

Closes #123, #124

Bug Fix:
fix: resolve memory leak in data processing

- Fix circular reference in cache manager
- Add proper cleanup in destructor
- Reduce memory usage by 40%

Closes #456
```

### PR Description Intelligence
- Extracts key points from changes
- Generates appropriate test plan items
- Links to related documentation
- Adds context from issue descriptions

## Error Handling

### Pre-commit Failures
```bash
if pre_commit_failed; then
    echo "⚠️  Pre-commit made changes. Reviewing..."
    git diff
    echo "Adding pre-commit changes..."
    git add -A
    # Re-run to ensure clean
    poetry run pre-commit run --all-files
fi
```

### Test Failures
```bash
if tests_failed; then
    echo "❌ Tests failed. Please fix before shipping."
    echo "Run 'make test' to see failures"
    exit 1
fi
```

### Push Conflicts
```bash
if push_failed_due_to_conflicts; then
    echo "⚠️  Remote has new changes. Updating..."
    git pull --rebase origin $CURRENT_BRANCH
    # Re-run tests after rebase
    make test
    git push origin $CURRENT_BRANCH
fi
```

## Integration with Workflow

This command completes the enterprise workflow:
1. `/ai-pick-issue` - Find work to do
2. `/ai-start-work` - Set up development branch
3. Make changes, write tests, implement features
4. `/ai-ship` - Ship completed work

## Configuration

The command respects project-specific settings:
- `.pre-commit-config.yaml` - Pre-commit hooks
- `Makefile` - Test and check targets
- `.github/pull_request_template.md` - PR template
- `pyproject.toml` / `package.json` - Project dependencies

## Notes

- Always preserves your work (no destructive operations)
- Handles both staged and unstaged changes
- Creates professional PR descriptions
- Follows conventional commit standards
- Integrates with GitHub issue tracking
- Sets up auto-merge when possible
