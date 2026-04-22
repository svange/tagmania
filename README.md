# Tagmania

[![CI Status](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml/badge.svg?branch=main)](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml)
[![PyPI](https://img.shields.io/pypi/v/tagmania?style=flat-square)](https://pypi.org/project/tagmania/)
[![semantic-release](https://img.shields.io/badge/%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg?style=flat-square)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/github/license/svange/tagmania?style=flat-square)](https://github.com/svange/tagmania/blob/main/LICENSE)

Manic tools for manipulating sets of tagged resources in AWS.

---

## Pipeline Artifacts

> Reports are published to GitHub Pages on every release to `main`.

| Report | Link |
|--------|------|
| API Documentation | [svange.github.io/tagmania](https://svange.github.io/tagmania/) |
| Test Report | [tests/test-report.html](https://svange.github.io/tagmania/tests/test-report.html) |
| Coverage Report | [coverage/](https://svange.github.io/tagmania/coverage/) |
| Security Scan | [security/security-reports.html](https://svange.github.io/tagmania/security/security-reports.html) |
| License Compliance | [compliance/license-report.html](https://svange.github.io/tagmania/compliance/license-report.html) |
| PyPI | [pypi.org/project/tagmania](https://pypi.org/project/tagmania/) |

Per-run downloadable artifacts (`bandit-report.json`, `pip-audit-report.json`, `coverage.xml`, `test-report.html`, `license-report.json`, built `dist/` on release) are available under the [Actions tab](https://github.com/svange/tagmania/actions) > select a run > scroll to "Artifacts".

---

## What This Does

Tagmania is a command-line toolkit for managing groups of AWS EC2 instances that share a `Cluster` tag. You point it at a cluster name and it can start, stop, snapshot, or restore every instance in that cluster as a single unit. It's useful if you run dev/test environments on EC2 and want a simple way to pause them overnight, back them up before risky changes, or roll an entire cluster back to a known-good state.

It operates only on resources it's been told to manage (via a `SNAPSHOT_MANAGER` automation tag), so it won't accidentally touch unrelated resources in your account.

---

## Getting Started

> This project uses AI-assisted development. You do not need to memorize
> git commands or CI configuration -- your AI agent handles that.

### Prerequisites

- Python 3.12 or higher
- An AWS account with EC2 access
- An AWS CLI profile configured (e.g. via `aws configure`)
- EC2 instances tagged with a `Cluster` tag identifying their membership
- IAM permissions for the `ec2:*` actions listed in the [template IAM policy](template.yaml) (read + start/stop + snapshot/volume lifecycle)

### First-time setup

```bash
pip install tagmania
# or, with uv
uv tool install tagmania
```

For production, pin to an exact version:

```bash
pip install tagmania==2.6.1
```

### Running locally

```bash
cluster-start  my-cluster                 # boot all instances in my-cluster
cluster-stop   my-cluster                 # stop all instances in my-cluster
cluster-snap --backup  my-cluster         # snapshot every attached EBS volume
cluster-snap --restore my-cluster         # restore volumes from most recent snapshot
cluster-snap --list    my-cluster         # list snapshots for the cluster
```

All commands accept `--profile <aws-profile>` for credential selection. See [Available Commands](#available-commands) and [Advanced Features](#advanced-features) below for more.

---

## How to Contribute

> Contributions are made through AI agents (Claude Code, Copilot, etc.).
> You describe what you want changed in plain language; the agent handles
> branching, coding, testing, and submitting a pull request.

1. **Open Claude Code** (or your AI agent) in this repo.
2. **Describe the change** you want -- a bug fix, a new feature, a doc update.
3. The agent will:
   - Create a feature branch
   - Make the changes
   - Run pre-commit checks and tests
   - Open a pull request
4. **Review the PR** when the agent is done. CI runs automatically.
5. **Merge** once CI is green.

If you need to work manually, see the full [contributor guide](CONTRIBUTING.md).

---

<!-- Custom sections preserved from previous README -->

## AWS Cost Warning

**⚠️ Important**: This tool operates on AWS infrastructure and can incur costs:
- EBS snapshot storage charges apply for all created snapshots
- Data transfer costs may apply when creating/restoring snapshots
- Test infrastructure in `template.yaml` will create billable EC2 instances
- Always clean up test resources after use to avoid ongoing charges

For testing, consider using AWS Free Tier eligible instance types and remember to delete snapshots when no longer needed.

## Available Commands

- `cluster-start` - Start all instances in a cluster
- `cluster-stop` - Stop all instances in a cluster
- `cluster-snap` - Create, restore, delete, and list snapshots

## Quick Start

### Starting and Stopping Clusters

```bash
# Start all instances in a cluster
cluster-start production-cluster

# Stop all instances in a cluster
cluster-stop production-cluster

# Use specific AWS profile
cluster-start --profile myprofile production-cluster
```

### Creating Snapshots

```bash
# Create a snapshot backup of entire cluster
cluster-snap --backup production-cluster

# Create a named snapshot
cluster-snap --backup --name daily-backup production-cluster
```

### Restoring from Snapshots

```bash
# Restore entire cluster from default snapshot
cluster-snap --restore production-cluster

# Restore from named snapshot
cluster-snap --restore --name daily-backup production-cluster
```

## Advanced Features

### Targeted Restore

Restore specific instances within a cluster using regex pattern matching against instance "Name" tags:

```bash
# Restore only web servers
cluster-snap --restore --target ".*-web-.*" production-cluster

# Restore specific instance
cluster-snap --restore --target "server-01" --name daily-backup production-cluster
```

**Common Targeting Patterns:**
- `".*-web-.*"` - All instances with "web" in the name
- `"server-[0-9]+"` - Instances named server-1, server-2, etc.
- `"prod-api-.*"` - All production API servers
- `"backup-db"` - Specific instance named "backup-db"

### Snapshot Management

```bash
# List all snapshots for a cluster
cluster-snap --list production-cluster

# List specific labeled snapshots
cluster-snap --list --name daily-backup production-cluster

# Delete specific snapshot set
cluster-snap --delete --name daily-backup production-cluster

# Delete all snapshots for cluster
cluster-snap --delete production-cluster
```

## How It Works

### Backup Process
1. Stops all cluster instances
2. Creates EBS snapshots of all attached volumes
3. Tags snapshots with cluster and label information
4. Instances remain stopped after backup (use `cluster-start` to restart)

### Restore Process
1. Stops all cluster instances (or targeted instances)
2. Detaches and deletes current EBS volumes
3. Creates new volumes from snapshots
4. Attaches new volumes to instances
5. Instances remain stopped after restore (use `cluster-start` to restart)

### Targeted Restore Process
1. Validates regex pattern
2. Filters instances by Name tag matching pattern
3. Displays matched instances for confirmation
4. Performs restore only on matched instances
5. Other instances in cluster remain unchanged

## Safety Features

- **Confirmation Required**: All destructive operations require "yes" confirmation
- **Cluster Isolation**: Operations only affect instances with matching "Cluster" tag
- **Automation Tracking**: Uses "SNAPSHOT_MANAGER" key to track managed resources
- **Regex Validation**: Targeted operations validate regex patterns before execution
- **Item Limits**: Maximum 150 items processed per operation for performance protection

## Version Management and Stability

To ensure consistent and stable deployments, it is critical to pin Tagmania to specific versions rather than using floating version numbers.

### Recommended Installation Methods

**pip with version pinning:**
```bash
pip install tagmania==2.6.1
```

**Poetry (recommended for projects):**
```toml
[tool.poetry.dependencies]
tagmania = "2.6.1"
```

**Requirements.txt:**
```
tagmania==2.6.1
```

### Version Selection Strategy

**Production Environments:**
- Always use exact version pinning (e.g., `==2.6.1`)
- Test new versions in development/staging before production deployment
- Document version upgrade procedures and rollback plans
- Monitor release notes for breaking changes

**Development Environments:**
- Use compatible version ranges for feature development (e.g., `~=2.6.1`)
- Pin to exact versions when reproducing production issues
- Update regularly to stay current with security patches

### Checking Installed Version

```bash
pip show tagmania
```

Or within Python:
```python
import tagmania
print(tagmania.__version__)
```

### Upgrade Planning

```bash
# Create backup of current environment
pip freeze > requirements-backup.txt

# Upgrade to specific version
pip install tagmania==2.6.1

# Test functionality
cluster-snap --list test-cluster

# If issues occur, rollback
pip install tagmania==2.5.0
```

## Troubleshooting

- **No instances found**: Verify "Cluster" tag exists and matches exactly
- **Invalid regex**: Test regex patterns before using with targeted operations
- **Permission errors**: Ensure AWS profile has EC2 and EBS permissions
- **Timeout issues**: Large volumes may take time to snapshot/restore
- **Python compatibility**: Requires Python 3.12 or higher

## Support

- [Documentation](https://svange.github.io/tagmania)
- [Issue Tracker](https://github.com/svange/tagmania/issues)
- [Discussions](https://github.com/svange/tagmania/discussions)

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Sponsor

If you find this project useful, please consider [sponsoring](https://github.com/sponsors/svange) its development.
