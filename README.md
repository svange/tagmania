# Tagmania


[![CI Status](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml/badge.svg?branch=main)](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml)

[![PyPI](https://img.shields.io/pypi/v/tagmania?style=flat-square)](https://pypi.org/project/tagmania/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-automated-blue?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square)](https://conventionalcommits.org)
[![semantic-release](https://img.shields.io/badge/%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg?style=flat-square)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/github/license/svange/tagmania?style=flat-square)](https://github.com/svange/tagmania/blob/main/LICENSE)


---

## 📚 Project Resources

| [📖 Current Documentation](https://svange.github.io/tagmania) |[🧪 Test report for last release ](https://svange.github.io/tagmania/test-report.html) |
|:----------------------------------------------------------------:|:-------------------------------------------------------------------------------------------:|

---

## Overview

Tagmania provides command-line tools for managing AWS EC2 clusters through tag-based operations. It offers utilities for starting, stopping, and creating snapshots of clusters identified by their "Cluster" tag.

**Key Requirements:**
- EC2 instances must have "Cluster" tag to identify cluster membership
- Instance "Name" tags are used for targeted operations
- AWS CLI profile configuration required for authentication

## Installation

### Quick Install

```bash
pip install tagmania
```

### Version Management

For production environments, always pin to a specific version:

```bash
pip install tagmania==2.4.0
```

See [Version Management](#version-management-and-stability) for detailed guidance on version pinning and stability.

### AWS Cost Warning

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
pip install tagmania==2.4.0
```

**Poetry (recommended for projects):**
```toml
[tool.poetry.dependencies]
tagmania = "2.4.0"
```

**Requirements.txt:**
```
tagmania==2.4.0
```

### Version Selection Strategy

**Production Environments:**
- Always use exact version pinning (e.g., `==2.4.0`)
- Test new versions in development/staging before production deployment
- Document version upgrade procedures and rollback plans
- Monitor release notes for breaking changes

**Development Environments:**
- Use compatible version ranges for feature development (e.g., `~=2.4.0`)
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
pip install tagmania==2.5.0

# Test functionality
cluster-snap --list test-cluster

# If issues occur, rollback
pip install tagmania==2.4.0
```

## Contributing

We welcome contributions! Tagmania uses a fork-based development model to ensure code quality and maintain project integrity.

Please see our [Contributing Guide](CONTRIBUTING.md) for detailed instructions on:
- Setting up your development environment
- Creating and maintaining your fork
- Submitting pull requests
- Following our coding standards and commit conventions

## Troubleshooting

- **No instances found**: Verify "Cluster" tag exists and matches exactly
- **Invalid regex**: Test regex patterns before using with targeted operations
- **Permission errors**: Ensure AWS profile has EC2 and EBS permissions
- **Timeout issues**: Large volumes may take time to snapshot/restore
- **Python compatibility**: Requires Python 3.9 or higher

## Support

- 📖 [Documentation](https://svange.github.io/tagmania)
- 🐛 [Issue Tracker](https://github.com/svange/tagmania/issues)
- 💬 [Discussions](https://github.com/svange/tagmania/discussions)

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Sponsor

If you find this project useful, please consider [sponsoring](https://github.com/sponsors/svange) its development.
