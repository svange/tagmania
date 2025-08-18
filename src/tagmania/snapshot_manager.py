"""AWS Cluster Snapshot Management CLI.

This module provides the main CLI interface for creating, restoring, deleting,
and listing EBS snapshots for EC2 clusters. It supports both full cluster
operations and targeted operations using regex patterns to match specific instances.

The tool relies on EC2 instances having "Cluster" tags to identify cluster membership
and "Name" tags for targeted operations. All operations include safety features
with confirmation prompts to prevent accidental data loss.

Features:
    - Create named snapshots of entire clusters
    - Restore clusters from snapshots with volume replacement
    - Targeted restore using regex patterns on instance names
    - List and delete existing snapshots
    - Safety confirmations for all destructive operations

Usage:
    The module is typically invoked via the cluster-snap CLI command:

    ```bash
    # Create a backup
    cluster-snap --backup --name daily-backup production

    # Restore entire cluster
    cluster-snap --restore --name daily-backup production

    # Targeted restore (only web servers)
    cluster-snap --restore --target ".*-web-.*" production

    # List snapshots
    cluster-snap --list production

    # Delete snapshots
    cluster-snap --delete --name daily-backup production
    ```

Warning:
    Restore operations permanently delete existing EBS volumes and replace them
    with volumes created from snapshots. This operation cannot be undone.
    Always confirm you have the correct backup before proceeding.
"""

import argparse
import re
from tagmania.iac_tools.clusterset import ClusterSet


def main():
    """Main entry point for the cluster snapshot management CLI.

    Parses command line arguments and executes the appropriate snapshot operation
    (backup, restore, list, or delete) on the specified cluster.

    The function handles all user interactions including confirmation prompts
    for destructive operations and provides detailed feedback on operation progress.

    Raises:
        SystemExit: On invalid command line arguments or user cancellation.
        ValueError: On invalid regex patterns for targeted operations.
        AWSError: On AWS API failures during snapshot operations.
    """
    parser = argparse.ArgumentParser(
        description='AWS cluster snapshot backup and restore tool.',
        epilog='''
            This tool relies on the "Cluster" and "Owner" tags on instances and
            volumes. IAC automation puts this in place. This tool
            creates multiple sets of labeled snapshots and creates volumes from
            them when a restore operation is performed.'''
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-b', '--backup',
        action='store_const',
        dest='backup',
        const=True,
        default=False,
        help='Create snapshots for cluster CLUSTER.'
    )
    group.add_argument('-D', '--delete',
        action='store_const',
        dest='delete',
        const=True,
        default=False,
        help='Delete snapshots from cluster CLUSTER.'
    )
    group.add_argument('-r', '--restore',
        action='store_const',
        dest='restore',
        const=True,
        default=False,
        help='Restore cluster CLUSTER from snapshots.'
    )
    group.add_argument('-l', '--list',
        action='store_const',
        dest='list',
        const=True,
        default=False,
        help='List snapshots with a given label or all if none specified.'
    )
    parser.add_argument('-n', '--name',
        default=None,
        help='Name to use for the snapshots.'
    )
    parser.add_argument('-t', '--target',
        type=str,
        default=None,
        help='Regex pattern to match instance Name tags for targeted restore.'
    )
    parser.add_argument('cluster',
        help='''
            the name CLUSTER of the cluster in question. This can be found by
            looking at any node in the AWS console and looking for the "Cluster"
            tag.'''
    )
    parser.add_argument('--profile', '-p', help='the AWS profile to use', default=None)
    args = parser.parse_args()

    cluster = ClusterSet(args.cluster, profile=args.profile)

    if args.backup:
        if args.name is None:
            snapshot_name = "default"
        else:
            snapshot_name = args.name
        confirm = input(f"Create backup of {args.cluster} named '{snapshot_name}'? [no] ")
        if confirm == "yes":
            print(f"Making backup.")
            instances = cluster.get_instances()
            if len(instances) == 0:
                print("No instances found. Operation aborted.")
            else:
                # Stop the cluster (not clean)
                cluster.stop_instances()
                cluster.create_snapshots(snapshot_name)
                # Start cluster
                #cluster.start_instances()
                print("Operation completed successfully!")
        else:
            print("Operation aborted.")

    if args.delete:
        if args.name is None:
            snapshot_name = "*"
            confirm_string = f"Delete all backups for {args.cluster}"
        else:
            snapshot_name = args.name
            confirm_string = f"Delete backup of {args.cluster} named '{snapshot_name}'"
        confirm = input(f"{confirm_string}? [no] ")
        if confirm == "yes":
            print(f"Deleting snapshots.")
            snapshots = cluster.get_snapshots(snapshot_name)
            if len(snapshots) == 0:
                print(f"No snapshots found. Operation aborted.")
            else:
                cluster.delete_snapshots(snapshot_name)
        else:
            print("Operation aborted.")

    if args.restore:
        if args.name is None:
            snapshot_name = "default"
        else:
            snapshot_name = args.name

        # Handle targeted restore
        if args.target:
            try:
                # Validate regex pattern
                re.compile(args.target)

                # Check if any instances match the pattern
                instances = cluster.get_instances()
                filtered_instances = cluster._filter_instances_by_name_regex(instances, args.target)

                if len(filtered_instances) == 0:
                    print(f"No instances found matching pattern '{args.target}'. Operation aborted.")
                else:
                    print(f"Found {len(filtered_instances)} instances matching pattern '{args.target}':")
                    for instance in filtered_instances:
                        name_tag = "Unknown"
                        if instance.tags:
                            for tag in instance.tags:
                                if tag['Key'] == 'Name':
                                    name_tag = tag['Value']
                                    break
                        print(f"  - {instance.id} ({name_tag})")

                    confirm = input(f"Restore backup '{snapshot_name}' for these {len(filtered_instances)} instances? [no] ")
                    if confirm == "yes":
                        print(f"Restoring targeted instances.")
                        # Stop targeted instances
                        cluster.stop_instances_targeted(args.target)
                        # Detach and delete volumes from targeted instances
                        cluster.detach_volumes_targeted(args.target)
                        cluster.delete_volumes_targeted(args.target)
                        # Create new volumes from snapshots and attach them
                        cluster.create_volumes_targeted(snapshot_name, args.target)
                        cluster.attach_volumes_targeted(snapshot_name, args.target)
                        # Start targeted instances
                        # cluster.start_instances_targeted(args.target)
                        print("Operation completed successfully!")
                    else:
                        print("Operation aborted.")
            except re.error as e:
                print(f"Invalid regex pattern '{args.target}': {e}")
                print("Operation aborted.")
        else:
            # Full cluster restore
            confirm = input(f"Restore backup of {args.cluster} named '{snapshot_name}'? [no] ")
            if confirm == "yes":
                print(f"Restoring cluster.")
                instances = cluster.get_instances()
                if len(instances) == 0:
                    print("No instances found. Operation aborted.")
                else:
                    # Stop cluster (not clean)
                    cluster.stop_instances()
                    # Detach and delete current volumes
                    cluster.detach_volumes()
                    cluster.delete_volumes()
                    # Create new volumes from snapshots and attach them
                    cluster.create_volumes(snapshot_name)
                    cluster.attach_volumes(snapshot_name)
                    # Start cluster
                    #cluster.start_instances()
                    print("Operation completed successfully!")
            else:
                print("Operation aborted.")

    if args.list:
        if args.name is None:
            print(f"Listing all snapshots associated with {args.cluster}.")
            snapshots = cluster.get_snapshots("*")

            # Getting a dictionary of all snapshots associated with the cluster provided grouped by label
            label_list = []
            snapshot_dict = {}
            for snapshot in snapshots:
                for tag in snapshot.tags:
                    if 'Label' in tag['Key'] and tag['Value'] not in label_list:
                        label_list.append(tag['Value'])
                        snapshot_dict[tag['Value']] = []
                        snapshot_dict[tag['Value']].append(snapshot.id)
                    elif 'Label' in tag['Key']:
                        snapshot_dict[tag['Value']].append(snapshot.id)

            # Printing snapshots sorted by Label name
            label_list.sort()
            for label in label_list:
                print("\nLabel: " + label)
                for snapshot_id in snapshot_dict[label]:
                    print(snapshot_id)
        else:
            print(f"Listing snapshots labeled '{args.name}' for {args.cluster}.")
            snapshots = cluster.get_snapshots(args.name)
            for snapshot in snapshots:
                print(snapshot.id)

if __name__ == '__main__':
    main()
