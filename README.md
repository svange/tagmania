# Tagmania
![ci status](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml/badge.svg?branch=main)

![PyPI - Version](https://img.shields.io/pypi/v/tagmania)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square)](https://conventionalcommits.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Made with GH Actions](https://img.shields.io/badge/CI-GitHub_Actions-blue?logo=github-actions&logoColor=white)](https://github.com/features/actions "Go to GitHub Actions homepage")
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)

Tools that automate common tasks for clusters of ec2 instances ins AWS. 
```yaml
Cluster: <CLUSTER_NAME>
```

## Tools in this package
Includes the following tools:
- tag-start: Start a cluster of EC2 instances.
- tag-stop: Stop a cluster of EC2 instances.
- tag-snap: Create, restore, and delete a named set of snapshots of EBS volumes across a cluster of EC2 instances.