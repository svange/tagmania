---
name: ai-standardize-pipeline
description: Audit and fix CI/CD GitHub Actions workflows. Checks security scanning, coverage enforcement, type checking, CVE ignores, and concurrency settings.
argument-hint: "[--validate-only] [--fix]"
---

Audit and fix CI/CD pipeline configuration for this repository: $ARGUMENTS

Reads GitHub Actions workflow files and validates they meet the standard security/quality gate structure. Detects missing scans, inconsistent settings, and provides fixes.

## Usage Examples

```bash
/ai-standardize-pipeline              # Full audit with recommendations
/ai-standardize-pipeline --validate   # Report issues only, no fixes
/ai-standardize-pipeline --fix        # Auto-fix detected issues
```

## 1. Detect Ecosystem and Workflow Files

```bash
# Find all workflow files
WORKFLOWS=$(find .github/workflows -name '*.yml' -o -name '*.yaml' 2>/dev/null)
if [ -z "$WORKFLOWS" ]; then
    echo "ERROR: No GitHub Actions workflows found in .github/workflows/"
    exit 1
fi

# Detect ecosystem
ECOSYSTEM="unknown"
[ -f "pyproject.toml" ] && ECOSYSTEM="python"
[ -f "package.json" ] && ECOSYSTEM="node"

# Detect if repo has infrastructure (SAM/CloudFormation)
HAS_INFRA=false
[ -f "template.yaml" ] && HAS_INFRA=true
[ -f "infrastructure/template.yaml" ] && HAS_INFRA=true

# Detect repo type (library vs IaC)
DEV_BRANCH=""
for candidate in dev develop staging; do
    git show-ref --verify --quiet "refs/remotes/origin/$candidate" 2>/dev/null && DEV_BRANCH=$candidate && break
done
```

Report: ecosystem, workflow files found, infrastructure presence, repo type.

## 2. Security Scanning Completeness

Read each workflow file and check for the presence of required security tools.

### Python repos must have ALL of:

1. **Bandit** (static security analysis)
   ```bash
   grep -l "bandit" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
   ```
   - Expected: `uv run bandit -r src/ -ll` (medium+high severity)
   - Should output both JSON report and console summary
   - Report should be uploaded as artifact

2. **pip-audit** (dependency vulnerability scanning)
   ```bash
   grep -l "pip-audit" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
   ```
   - Expected: `uv run pip-audit --desc --format json --output pip-audit-report.json`
   - Should scan production dependencies (`--no-dev` or default)
   - CVE ignores should use **GHSA format** (e.g., `--ignore-vuln GHSA-xxxx-xxxx-xxxx`), not CVE IDs
   - Report should be uploaded as artifact

3. **Semgrep** (SAST pattern matching)
   ```bash
   grep -l "semgrep" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
   ```
   - Expected: Semgrep with relevant rulesets (`p/python`, `p/security-audit`, `p/secrets`, `p/owasp-top-ten`)
   - Can use `semgrep/semgrep-action@v1` or manual install
   - Should output SARIF for GitHub integration

4. **License compliance** (GPL/AGPL detection)
   ```bash
   grep -l "pip-licenses" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
   ```
   - Expected: `uv run pip-licenses --from=mixed --format=json`
   - Must check for incompatible licenses (GPL, AGPL -- LGPL is OK)
   - Should fail the build if incompatible licenses found

### Node repos must have ALL of:

1. **npm audit** (dependency vulnerability scanning)
   - Expected: `npm audit --audit-level=critical --omit=dev`
   - Should fail on critical vulnerabilities

2. **Semgrep** (SAST pattern matching)
   - Expected: rulesets `p/javascript`, `p/typescript`, `p/security-audit`, `p/secrets`

Flag any missing tools with severity **ERROR** and provide the job/step YAML to add.

## 3. Coverage Enforcement

### Python repos

Search for coverage enforcement in test jobs:
```bash
grep -n "cov-fail-under\|coverage.*fail" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

- Expected: `--cov-fail-under=80` in pytest commands
- If missing: flag as **ERROR** and show the fix:
  ```yaml
  - name: Run tests with coverage
    run: uv run pytest --cov=src --cov-fail-under=80 -v
  ```

### Node repos

Search for coverage thresholds in test configuration:
- Check `vitest.config.js` or `jest.config.js` for `coverageThreshold`
- Check workflow for `--coverage` flag
- If no enforcement: flag as **WARNING**

## 4. Type Checking in CI

### Python repos

```bash
grep -n "mypy" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

- MyPy should run either in the pre-commit job or as a dedicated step
- Expected: `uv run mypy src/`
- If missing: flag as **ERROR**

### Node repos

```bash
grep -n "tsc\|type-check\|vue-tsc" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

- TypeScript type checking should run in quality checks
- If missing: flag as **WARNING**

## 5. CVE Ignore Standardization

Extract all vulnerability ignore directives:
```bash
grep -n "ignore-vuln\|--ignore\|GHSA-\|CVE-" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

Validate:
- **Format**: All ignores should use GHSA identifiers (e.g., `GHSA-5239-wwwm-4pmq`), not CVE IDs
  - CVE IDs can change; GHSA is the GitHub-canonical identifier
  - If CVE format found, look up the GHSA equivalent and suggest the fix
- **Documentation**: Each ignore should have a comment explaining why and when it was added
- **Review process**: Check if a quarterly CVE review workflow exists:
  ```bash
  grep -l "cve-review\|cve_review\|vulnerability.*review" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
  ```
  - If missing: flag as **WARNING** and provide the template (cron quarterly, auto-creates review issue)

## 6. Concurrency Settings

Read concurrency config from each workflow:
```bash
grep -A3 "concurrency:" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

Rules:
- **Repos with infrastructure deployment jobs** (SAM deploy, CloudFormation, Terraform): `cancel-in-progress: false`
  - Canceling an in-progress infrastructure deployment can leave resources in inconsistent state
- **Pure CI repos** (no infra, just tests/lint/publish): `cancel-in-progress: true` is acceptable
  - Saves CI minutes by canceling superseded runs

If a repo has infrastructure jobs but uses `cancel-in-progress: true`, flag as **ERROR**.

## 7. Pipeline Structure Validation

Check the standard job dependency chain:

### Python library pattern:
```
pre-commit -> [security-scan, compliance, unit-tests] (parallel) -> release -> [publish, docs] (parallel)
```

### Python IaC pattern:
```
pre-commit -> [security-scan, compliance, unit-tests, infra-validation] (parallel) -> deploy -> [integration-tests, smoke-tests] -> release
```

### Node IaC pattern:
```
[quality-checks, sast-scan, unit-tests] (parallel) -> build-deploy -> deploy-verify -> [e2e suites] (parallel)
```

Flag if:
- Security scans don't gate the deploy job
- Tests run after deploy without depending on deploy success
- Release runs without all quality gates passing first

## 8. Artifact and Reporting

Check that security reports are preserved:
```bash
grep -n "upload-artifact\|actions/upload" .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

Verify:
- Bandit report (JSON) uploaded as artifact
- pip-audit report (JSON) uploaded as artifact
- Semgrep SARIF uploaded (either as artifact or via GitHub code scanning)
- Coverage reports uploaded
- Retention days set (recommend 1-7 days for CI artifacts)

## Error Handling

- **No workflows found**: Abort -- repo may not use GitHub Actions
- **Mixed ecosystems**: Handle repos with both Python and Node (check both sets of requirements)
- **Custom CI systems**: If no `.github/workflows/` but has `.gitlab-ci.yml`, Jenkinsfile, etc., warn that this skill only supports GitHub Actions
- **Workflow syntax errors**: Don't attempt to fix YAML syntax -- flag and skip

## Final Output

```
=== CI/CD Pipeline Standardization Report ===

Ecosystem: Python
Repo type: IaC (dev+main)
Infrastructure: SAM (template.yaml detected)
Workflows analyzed: 3

Security Scanning:
  [PASS] Bandit: present in pipeline.yaml
  [PASS] pip-audit: present in pipeline.yaml
  [FAIL] Semgrep: MISSING -- add SAST scanning
  [FAIL] License compliance: MISSING -- add GPL/AGPL detection

Quality Gates:
  [PASS] Coverage enforcement: 80% floor in unit-tests job
  [FAIL] MyPy type checking: not found in any workflow
  [PASS] Pre-commit: runs as first job

Pipeline Safety:
  [PASS] Concurrency: cancel-in-progress: false (correct for infra)
  [WARN] CVE ignores use CVE format -- recommend GHSA identifiers
  [WARN] No quarterly CVE review workflow found

Artifacts:
  [PASS] Bandit report uploaded
  [PASS] pip-audit report uploaded
  [WARN] Semgrep SARIF not uploaded (Semgrep not configured)

Next steps:
  /ai-standardize-precommit    # Validate pre-commit hooks
  /ai-standardize-dotfiles     # Validate project config files
  /ai-standardize-repo         # Full standardization checklist
```
