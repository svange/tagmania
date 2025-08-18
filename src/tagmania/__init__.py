"""Tagmania - AWS EC2 Cluster Management Tools.

Tagmania provides command-line tools for managing AWS EC2 clusters through tag-based operations.
It offers utilities for starting, stopping, and creating snapshots of clusters identified by their "Cluster" tag.

Key Features:
    - Start and stop EC2 instances in clusters
    - Create, restore, and manage EBS snapshots
    - Targeted restore operations using regex patterns
    - Tag-based resource identification and filtering
    - Safety features with confirmation prompts

Main CLI Commands:
    - cluster-start: Start all instances in a cluster
    - cluster-stop: Stop all instances in a cluster
    - cluster-snap: Create, restore, delete, and list snapshots

Example:
    Basic usage examples:

    ```bash
    # Start a cluster
    cluster-start production-web

    # Create a snapshot backup
    cluster-snap --backup --name daily-backup production-web

    # Restore from snapshot
    cluster-snap --restore --name daily-backup production-web

    # Targeted restore (only web servers)
    cluster-snap --restore --target ".*-web-.*" production-web
    ```

Note:
    All operations require EC2 instances to have a "Cluster" tag for identification.
    AWS CLI profile configuration is required for authentication.
"""

__version__ = "2.4.0"
__author__ = "Samuel Vange"
__email__ = "7166607+svange@users.noreply.github.com"
