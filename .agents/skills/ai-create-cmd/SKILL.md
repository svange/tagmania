---
name: ai-create-cmd
description: Create a new Claude skill for augint-shell repositories. Use when building new automation commands or skills.
argument-hint: "[skill-name and description]"
---

Create a new Claude skill for trinity repositories: $ARGUMENTS

Follow these steps to create a well-structured skill:

1. **Parse the skill request**:
   ```
   Extract from user input:
   - Skill name (kebab-case)
   - Skill purpose
   - Key functionality needed
   - Target repos (default: all trinity)
   ```

2. **Determine skill scope**:
   - **Trinity skill**: For augint-library, augint-api, augint-web
   - **Meta skill**: Only if it makes sense for augint-project management

   Ask: "Should this skill also have a meta version for the augint-project repo?"
   (Only if the skill relates to project management, vision docs, or cross-repo operations)

3. **Create the skill directory and file**:
   ```bash
   # Create in templates first
   mkdir -p src/ai_shell/templates/claude/skills/{skill-name}
   touch src/ai_shell/templates/claude/skills/{skill-name}/SKILL.md
   ```

4. **Generate SKILL.md** with this structure:
   ```markdown
   ---
   name: {skill-name}
   description: {One-line description of what it does and when to use it. Max 250 chars.}
   argument-hint: "[expected arguments]"
   ---

   {Command description in active voice}: $ARGUMENTS

   {Brief overview of what this skill does.}

   ## Usage Examples
   - `/{skill-name}` - Default behavior
   - `/{skill-name} specific args` - With arguments

   ## 1. {First Major Step}
   - {Specific action}
   - {Validation check}
   ```bash
   # Example command
   ```

   ## 2. {Second Major Step}
   - {Specific action}
   - {Error handling}

   ## 3. {Output/Report}
   ```
   === {Skill Name} Results ===

   {Structured output format}

   Status: {success/warnings/failures}
   ```

   ## Error Handling
   - {Error condition}: {Recovery action}
   ```

5. **Choose appropriate frontmatter options**:
   - `argument-hint` to show expected arguments in the skill menu
   - Keep description under 250 characters, front-load key use case

6. **Validate the skill**:
   ```bash
   # Check SKILL.md exists and has frontmatter
   head -10 src/ai_shell/templates/claude/skills/{skill-name}/SKILL.md

   # Verify frontmatter has required fields
   grep -E "^(name|description):" src/ai_shell/templates/claude/skills/{skill-name}/SKILL.md
   ```

7. **Register in scaffold.py**:
   Add the skill name to `CLAUDE_SKILL_DIRS` in `src/ai_shell/scaffold.py`:
   ```python
   CLAUDE_SKILL_DIRS = [
       # ... existing skills ...
       "{skill-name}",
   ]
   ```

8. **Best practices**:
   - Keep skills focused on one primary task
   - Use active voice ("Create PR" not "PR should be created")
   - Include usage examples
   - Make steps explicit and numbered
   - Include error handling section
   - Reference related skills (e.g., "Next: `/ai-submit-work`")
   - Keep SKILL.md under 500 lines
   - Be directive, not conversational

9. **Copy to trinity repositories**:
   ```bash
   # Deploy via scaffold
   for repo in augint-library augint-api augint-web; do
     python -c "
   from ai_shell.scaffold import scaffold_claude
   from pathlib import Path
   scaffold_claude(Path('../$repo'), overwrite=True)
   "
   done
   ```

10. **Verify deployment**:
    ```bash
    # Check all trinity repos have the skill
    ls -la ../augint-*/.claude/skills/{skill-name}/SKILL.md
    ```

## Skill Patterns

### For Git Workflow Skills:
```markdown
{Action} for {purpose}: $ARGUMENTS

## 1. Check current state
## 2. Perform action
## 3. Verify success
## 4. Report results with next step
```

### For Analysis Skills:
```markdown
Analyze {target} for {criteria}: $ARGUMENTS

## 1. Gather data
## 2. Process and categorize
## 3. Generate insights
## 4. Provide recommendations
```

### For Automation Skills:
```markdown
Automate {task} across {scope}: $ARGUMENTS

## 1. Validate prerequisites
## 2. Execute automation
## 3. Handle errors
## 4. Confirm completion
```

## Why This Matters
Consistent skill creation ensures all repositories have access to the same automation capabilities with predictable behavior and quality.
