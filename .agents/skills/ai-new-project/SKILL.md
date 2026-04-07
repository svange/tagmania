---
name: ai-new-project
description: Stand up a new repository with standard quality gates, CI/CD pipeline, and configuration files.
argument-hint: "[repo-name]"
---

Create a new standardized repository: $ARGUMENTS

Interactive project standup. Determines project shape, creates the repo, configures GitHub settings, scaffolds the pipeline and local config files, and verifies everything is aligned.

## Usage Examples

```bash
/ai-new-project my-new-lib          # Create repo named my-new-lib, will ask type/language
/ai-new-project                     # Interactive, will ask for all details
```

---

## 1. Gather Requirements

Ask the user for each of these. Use $ARGUMENTS as repo name if provided.

### Repo name
- Must be lowercase, hyphens allowed, no special characters
- Will be used as GitHub repo name and package name

### Type
- **library**: Publishes artifacts (PyPI, npm). Main-only branch strategy.
- **service**: Deploys to environments (AWS staging/prod). Dev + main branch strategy.

Ask: "Is this a library (publishes to a registry) or a service (deploys to environments)?"

### Language
- **python**: Uses uv, ruff, mypy, pytest
- **typescript**: Uses pnpm, biome, tsc, vitest

Ask: "Python or TypeScript?"

### Framework (service repos only)
- **SAM**: AWS Serverless Application Model
- **CDK**: AWS Cloud Development Kit
- **Terraform**: HashiCorp Terraform
- **Vite**: React + Vite frontend
- **Next.js**: Next.js frontend
- **plain**: No specific framework

Ask: "Which framework? (SAM/CDK/Terraform/Vite/Next.js/plain)"

### Visibility
- **private** (default for most projects)
- **public** (open source libraries)

Ask: "Public or private? (default: private)"

---

## 2. Create Repository

```bash
# Create the repo on GitHub
gh repo create <owner>/<repo-name> --<visibility> --clone
cd <repo-name>

# Initialize git if needed
git init
git remote add origin https://github.com/<owner>/<repo-name>.git
```

For **service** type, create the dev branch:
```bash
# Create initial commit so branches work
git commit --allow-empty -m "chore: initialize repository"
git push -u origin main
git checkout -b dev
git push -u origin dev
git checkout main
```

Ensure `origin/HEAD` points to main:
```bash
git remote set-head origin main
```

---

## 3. GitHub Configuration via ai-gh

**Prerequisite**: `.env` file must exist with `GH_REPO`, `GH_ACCOUNT`, `GH_TOKEN`. If missing, help the user create it.

```bash
# Standardize repo settings (automerge, merge strategy, branch deletion)
ai-gh config --standardize

# Apply branch rulesets with 4 universal quality gate checks
ai-gh rulesets --apply <library|service>
```

**Note**: ai-gh may not yet support the new gate names ("Code quality" instead of "Pre-commit checks") or the `service` type. If so:
- Use `--apply iac` as a temporary substitute for `--apply service`
- Note that rulesets will need updating once ai-gh is updated (see augint-github issues)

Generate pipeline:
```bash
ai-gh workflow --type <library|service>
```

If ai-gh does not yet support `--lang`, the generated pipeline will be Python-focused. For TypeScript projects, the skill should manually adjust the pipeline after generation.

---

## 4. Generate Local Configuration Files

### Python projects

**pyproject.toml** - Create with:
- `[project]` section: name, version = "0.0.0", python requires >= 3.12
- `[build-system]` with `uv_build`
- `[tool.ruff]`: line-length = 100, select = ["E", "F", "I", "W", "B", "C4", "UP", "DTZ"]
- `[tool.ruff.lint.isort]`: known-first-party
- `[tool.mypy]`: python_version = "3.12", disallow_untyped_defs = true, warn_return_any = true
- `[tool.pytest.ini_options]`: testpaths = ["tests"], addopts = "-ra -q --strict-markers"
- `[tool.coverage.run]`: source = ["src"], omit = ["*/tests/*"]
- Dependencies: include dev deps for ruff, mypy, pytest, pytest-cov, pre-commit, semgrep, pip-audit, liccheck, pip-licenses, python-semantic-release

Create `src/<package_name>/__init__.py` with `__version__ = "0.0.0"`.
Create `tests/__init__.py` and `tests/unit/__init__.py`.

**.pre-commit-config.yaml** - Copy from `python-template.pre-commit-config.yaml` in the ai-standardize-repo skill directory. Adjust paths if framework uses SAM (exclude template.yaml from check-yaml).

**renovate.json5** - Copy from `library-template.json5` or `service-template.json5` based on type.

**Semantic release config** - Append from `python-template.toml`. Customize:
- `tag_format`: `{repo-name}-v{version}`
- `version_variables`: `["src/{package_name}/__init__.py:__version__"]`
- `build_command`: `"uv lock && uv build"` for library, `""` for service

### TypeScript projects

**package.json** - Create with:
- name, version = "0.0.0"
- scripts: dev, build, test, lint, format, type-check
- devDependencies: biome, typescript, vitest, semgrep (or as CI-only)

**tsconfig.json** - Strict mode, ESNext target, appropriate module resolution.

**biome.json** - Standard configuration matching ruff's philosophy (opinionated defaults).

**renovate.json5** - Same templates as Python, adapted for npm ecosystem.

**.releaserc.json** - Copy from `node-template.releaserc.json`. Customize tag format.

### Common files (all languages)

**.editorconfig** - Copy from `editorconfig-template` in ai-standardize-repo skill directory.

**.gitignore** - Generate with:
- Safety: `.env`, `.env.*`, `*.pem`, `.claude/settings.local.json`
- Python (if applicable): `__pycache__/`, `*.pyc`, `.coverage`, `htmlcov/`, `dist/`, `build/`, `*.egg-info/`, `.mypy_cache/`, `.ruff_cache/`
- TypeScript (if applicable): `node_modules/`, `dist/`, `build/`, `.next/`, `coverage/`
- IDE: `.vscode/`, `.idea/`
- OS: `.DS_Store`, `Thumbs.db`

---

## 5. Customize Build Step

The pipeline's "Code quality" job must include the build validation step for the detected framework:

| Framework | Build command |
|---|---|
| Plain Python library | `uv build` |
| SAM | `sam build` |
| CDK (Python) | `cdk synth` |
| CDK (TypeScript) | `cdk synth` |
| Terraform | `terraform init && terraform validate && terraform plan` |
| Vite / React | `npm run build` |
| Next.js | `npm run build` |
| Plain TS library | `npm run build` |

Edit the pipeline's code-quality job to include the appropriate build command. If the pipeline was generated by ai-gh, look for a placeholder comment like `# Customize build step` and replace it.

---

## 6. AI Tool Scaffolding

Run augint-shell scaffolding to deploy AI tool configurations:

```bash
ai-shell init --project <repo-name>
```

This deploys `.claude/skills/`, `.agents/skills/`, `ai-shell.toml`, and `NOTES.md` with the correct repo type and skill set.

If `ai-shell` is not available, manually note that the user should run it later.

---

## 7. README

Create `README.md` with:

```markdown
# {repo-name}

{Description placeholder - update this}

## Pipeline

![Pipeline](https://github.com/{owner}/{repo-name}/actions/workflows/pipeline.yaml/badge.svg)

## Development

{Language-specific development instructions}

## Reports

- [Coverage Report](https://{owner}.github.io/{repo-name}/coverage/)
- [Security Scan](https://{owner}.github.io/{repo-name}/security/)
- [License Compliance](https://{owner}.github.io/{repo-name}/compliance/)
```

For libraries, add:
```markdown
## Installation

pip install {repo-name}
```

---

## 8. Initial Commit and Push

```bash
git add .
git commit -m "feat: initial project scaffold"
git push -u origin main
```

For service repos:
```bash
git checkout dev
git merge main
git push -u origin dev
git checkout main
```

---

## 9. Verify

Run verification:
```bash
ai-gh status --type <library|service> --verbose
```

Check:
- All 4 quality gate status checks are configured in rulesets
- Auto-merge is enabled
- Pipeline file exists with correct job names
- Local config files are present

Report final status. If any issues remain, list them with guidance.

---

## Error Handling

- `gh` CLI not authenticated: ask user to run `gh auth login`
- `ai-gh` not installed: skip GitHub config steps, note manual setup needed
- `.env` missing GH variables: help user create it from `.env.example` or prompt for values
- Repo already exists: ask if user wants to standardize existing repo instead (suggest `/ai-standardize-repo`)
- Network errors: retry once, then report and continue with local-only setup
- Framework detection failed for service: ask the user which framework
