# Tagmania


[![CI Status](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml/badge.svg?branch=main)](https://github.com/svange/tagmania/actions/workflows/pipeline.yaml)

[![PyPI](https://img.shields.io/pypi/v/tagmania?style=flat-square)](https://pypi.org/project/tagmania/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=flat-square&logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-automated-blue?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?style=flat-square)](https://conventionalcommits.org)
[![semantic-release](https://img.shields.io/badge/%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg?style=flat-square)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/github/license/svange/tagmania?style=flat-square)](https://github.com/svange/tagmania/blob/main/LICENSE)
[![Sponsor](https://img.shields.io/badge/donate-github%20sponsors-blueviolet?style=flat-square&logo=github-sponsors)](https://github.com/sponsors/svange)


---

## 📚 Project Resources

| [📖 Current Documentation](https://svange.github.io/tagmania) |[🧪 Test report for last release ](https://svange.github.io/tagmania/test-report.html) |
|:----------------------------------------------------------------:|:-------------------------------------------------------------------------------------------:|

---

Tools that automate common tasks for clusters of ec2 instances ins AWS.
```yaml
Cluster: <CLUSTER_NAME>
```

## Tools in this package
Includes the following tools:
- tag-start: Start a cluster of EC2 instances.
- tag-stop: Stop a cluster of EC2 instances.
- tag-snap: Create, restore, and delete a named set of snapshots of EBS volumes across a cluster of EC2 instances.
