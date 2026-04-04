---
name: ai-setup-oidc
description: Check and configure AWS OIDC trust policies for GitHub Actions deployment. Detects repo type and adds the correct branch conditions.
argument-hint: "[--profile PROFILE] [--check-only]"
---

Check and configure AWS OIDC trust policy for GitHub Actions in this repository: $ARGUMENTS

Detects the current repo, finds the AWS OIDC identity provider and associated IAM roles, checks whether this repo is authorized, and updates the trust policy if needed. The OIDC provider and role are expected to already exist (e.g. via Organization StackSet).

## Usage Examples

```bash
/ai-setup-oidc                          # Interactive: ask for profile, detect and fix
/ai-setup-oidc --profile my-profile     # Use specific AWS profile
/ai-setup-oidc --check-only             # Report current state without changes
```

## 1. Determine Context

```bash
# Get repo owner and name from git remote
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -z "$REMOTE_URL" ]; then
    echo "ERROR: No origin remote configured."
    exit 1
fi

# Parse owner/repo from SSH or HTTPS URL
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's#.*github\.com[:/]##' | sed 's/\.git$//')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Repository: $OWNER/$REPO"

# Detect repo type based on dev branch existence
git fetch --all --prune 2>/dev/null
REPO_TYPE="library"
if git show-ref --verify --quiet refs/remotes/origin/dev 2>/dev/null; then
    REPO_TYPE="iac"
fi
echo "Repo type: $REPO_TYPE"
```

### Determine AWS profile

Parse `$ARGUMENTS` for `--profile PROFILE`. If not provided, ask the user which AWS profile to use.

### Verify AWS credentials

```bash
aws sts get-caller-identity --profile $PROFILE --output json
```

If this fails, report the error and abort. Common issues:
- Profile does not exist in `~/.aws/config`
- Credentials expired -- suggest `aws sso login --profile $PROFILE`
- No default region configured

Report: account ID, ARN, and user/role name from the response.

## 2. Find OIDC Identity Provider

```bash
PROVIDERS=$(aws iam list-open-id-connect-providers --profile $PROFILE --output json)
OIDC_ARN=$(echo "$PROVIDERS" | jq -r '.OpenIDConnectProviderList[].Arn' | grep 'token.actions.githubusercontent.com')
```

**If no OIDC provider found**: Abort. The GitHub Actions OIDC identity provider does not exist in this AWS account. It should be provisioned via the Organization StackSet.

**If found**: Show the ARN and fetch details.

```bash
aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "$OIDC_ARN" \
    --profile $PROFILE --output json
```

Verify the provider has `sts.amazonaws.com` in its `ClientIDList`. If not, warn that the audience may be misconfigured.

## 3. Find Roles Trusting the OIDC Provider

```bash
ROLES=$(aws iam list-roles --profile $PROFILE --output json)

# Extract roles whose trust policy references the GitHub OIDC provider
echo "$ROLES" | jq -r --arg arn "$OIDC_ARN" '
  .Roles[] |
  select(.AssumeRolePolicyDocument.Statement[]? |
    .Principal.Federated? == $arn
  ) |
  .RoleName
'
```

Note: `list-roles` may paginate. If the result includes a `Marker` or `IsTruncated: true`, repeat with `--starting-token` until all roles are fetched.

**If no roles found**: Abort. No IAM roles trust the GitHub OIDC provider in this account. The role should be provisioned via the Organization StackSet.

**If multiple roles found**: List them and ask the user which role to inspect/update.

```
Found roles trusting GitHub OIDC:
  1. GitHubActionsRole
  2. DeployRole

Which role should be updated?
```

If only one role matches, proceed with it automatically.

## 4. Check Current Repo Access

```bash
TRUST_POLICY=$(aws iam get-role --role-name "$ROLE_NAME" --profile $PROFILE --output json \
    | jq '.Role.AssumeRolePolicyDocument')
echo "$TRUST_POLICY" | jq .
```

Parse the trust policy conditions on `token.actions.githubusercontent.com:sub`. Check both `StringEquals` and `StringLike`:

```bash
echo "$TRUST_POLICY" | jq -r '
  .Statement[] |
  select(.Principal.Federated? | test("token.actions.githubusercontent.com")) |
  (.Condition.StringEquals["token.actions.githubusercontent.com:sub"] //
   .Condition.StringLike["token.actions.githubusercontent.com:sub"] //
   empty) |
  if type == "array" then .[] else . end
'
```

### Determine required subjects

Based on repo type detected in Step 1:

- **Library** (no dev branch): `repo:OWNER/REPO:ref:refs/heads/main`
- **IaC** (dev branch exists): both `repo:OWNER/REPO:ref:refs/heads/main` and `repo:OWNER/REPO:ref:refs/heads/dev`

### Report coverage

```
=== OIDC Access Check for OWNER/REPO ===
Role: ROLE_NAME
Repo type: REPO_TYPE

  [PASS] repo:svange/my-lib:ref:refs/heads/main
  [MISSING] repo:svange/my-lib:ref:refs/heads/dev
```

If a wildcard pattern (e.g. `repo:OWNER/*`) already covers this repo, note that and skip the update.

If all required subjects are already present, report success and stop.

## 5. Update Trust Policy

**If `--check-only` is set**: Report the current state and stop.

**If changes are needed**: Show what will change and wait for explicit user confirmation.

```
The following subjects will be ADDED to the trust policy for role ROLE_NAME:
  + repo:svange/my-lib:ref:refs/heads/dev

The following existing subjects will be PRESERVED:
  = repo:svange/other-repo:ref:refs/heads/main
  = repo:svange/my-lib:ref:refs/heads/main

Confirm this update? [yes/no]
```

### Build and apply the updated trust policy

```bash
# Read current trust policy
CURRENT_POLICY=$(aws iam get-role --role-name "$ROLE_NAME" --profile $PROFILE --output json \
    | jq '.Role.AssumeRolePolicyDocument')

# Add new subject(s) to the condition array
# Handle both single-string and array formats
UPDATED_POLICY=$(echo "$CURRENT_POLICY" | jq --arg new_sub "$NEW_SUBJECT" '
  .Statement |= map(
    if (.Principal.Federated? | test("token.actions.githubusercontent.com")) then
      if .Condition.StringEquals["token.actions.githubusercontent.com:sub"] then
        .Condition.StringEquals["token.actions.githubusercontent.com:sub"] |=
          (if type == "array" then . + [$new_sub] else [., $new_sub] end)
      elif .Condition.StringLike["token.actions.githubusercontent.com:sub"] then
        .Condition.StringLike["token.actions.githubusercontent.com:sub"] |=
          (if type == "array" then . + [$new_sub] else [., $new_sub] end)
      else . end
    else . end
  )
')

# Apply -- this will trigger a permission prompt since it is not auto-allowed
echo "$UPDATED_POLICY" > /tmp/trust-policy.json
aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document file:///tmp/trust-policy.json \
    --profile $PROFILE
rm -f /tmp/trust-policy.json
```

If multiple subjects need to be added (IaC repo needing both main and dev), apply all new subjects in a single policy update.

### Verify the update

```bash
aws iam get-role --role-name "$ROLE_NAME" --profile $PROFILE --output json | \
    jq '.Role.AssumeRolePolicyDocument.Statement[] |
    select(.Principal.Federated? | test("token.actions.githubusercontent.com")) |
    .Condition'
```

Confirm the new subjects appear in the output.

## Error Handling

- **Not a git repo / no origin remote**: Abort with clear message
- **AWS profile invalid**: Report error, suggest checking `~/.aws/config`
- **AWS credentials expired**: Suggest `aws sso login --profile $PROFILE`
- **No OIDC provider**: Abort -- should be provisioned via Organization StackSet
- **No roles trust OIDC provider**: Abort -- role should be provisioned via Organization StackSet
- **Wildcard already covers repo**: Report that a wildcard pattern matches, no update needed
- **Trust policy has unexpected structure**: Show the raw JSON and ask user to review manually
- **update-assume-role-policy fails**: Show error. Common causes: insufficient IAM permissions, policy size limit (10240 chars)
- **Paginated role listing**: Handle pagination if `IsTruncated` is true

## Final Output

```
=== OIDC Setup Complete ===

Repository: svange/my-lib
Repo type: IaC (dev + main)
AWS Account: 123456789012
Profile: my-profile
Role: GitHubActionsRole

Subjects configured:
  [PASS] repo:svange/my-lib:ref:refs/heads/main
  [PASS] repo:svange/my-lib:ref:refs/heads/dev

GitHub Actions in this repo can now assume GitHubActionsRole.

Workflow snippet for .github/workflows/:

    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1
```
