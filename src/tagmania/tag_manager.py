"""AWS Cluster Tag Management CLI.

This module provides a command-line interface for managing tags on AWS resources
within a cluster. It supports adding and removing tags from EC2 instances,
volumes, snapshots, and Lambda functions belonging to a cluster.

The tool processes tag operations in the order specified on the command line,
allowing for complex tag management scenarios including tag overrides and
conditional operations.

Features:
    - Add tags to all resources in a cluster
    - Remove tags from all resources in a cluster
    - Support for multiple resource types (instances, volumes, snapshots, Lambda)
    - Batch operations for efficiency
    - Tag override capability

Usage:
    The module is typically invoked via a CLI command for tag management:

    ```bash
    # Add tags to cluster
    tag-manager --tag Environment production --tag Owner backend-team cluster-name

    # Remove tags from cluster
    tag-manager --untag TempTag --untag BuildNumber cluster-name

    # Override existing tag
    tag-manager --tag Environment staging cluster-name
    ```

Note:
    Operations are performed in command-line argument order. If a tag is both
    added and removed in the same command, it will be added first then removed.
"""

import argparse
from tagmania.iac_tools.clusterset import ClusterSet
from tagmania.iac_tools import util


def main():
    """Main entry point for the cluster tag management CLI.

    Parses command line arguments and executes tag operations (add/remove)
    on all resources within the specified cluster. Supports both EC2 resources
    (instances, volumes, snapshots) and Lambda functions.

    The function processes tag operations in the order they appear on the
    command line, allowing for complex tag management scenarios.

    Raises:
        SystemExit: On invalid command line arguments.
        AWSError: On AWS API failures during tag operations.
    """
    parser = argparse.ArgumentParser(
        description='AWS cluster tag manager.',
        epilog='''
            This tool relies on the "Cluster" and "Owner" tags on instances and
            volumes. IAC automation puts this in place. Tags are
            dealt with in the order of the parameter arguments:
            i.e. if a tag is listed as both a tag and an untag, it will be added
            and then removed from the resources.
            To override a tag's value, simply add it as a tag and the value will
            be overwritten.'''
    )
    parser.add_argument('-t', '--tag',
        nargs='*',
        dest='tag',
        help='''
            Add tags to cluster CLUSTER. Tags must take the form of key:value
            Can add as many tags as desired (AWS has a 50 tag limit), seperated
            by spaces.'''
    )
    parser.add_argument('-u', '--untag',
        nargs='*',
        dest='untag',
        help='''
            Remove tags from cluster CLUSTER. Accepts only the key of the tag.
            Can remove as many tags as desired, seperated by spaces. If the key
            doesn't exist, ignores.'''
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

    # Perform tagging operations
    if args.tag:
        tags = []
        for tag in args.tag:
            pair = tag.split(':')
            tags.append({'Key': pair[0], 'Value': pair[1]})

        # Tag EC2 resources
        cluster.tag_instances(tags)
        cluster.tag_volumes(tags)
        cluster.tag_snapshots(tags)
        # cluster.tag_subnet(tags)

        # Tag lambda functions
        print("Tagging lambda function(s)")
        lambda_arn = util.get_lambda_arn("TAGMANIA-AUTO-" + args.cluster)
        # Lambda tagging uses an plain dictionary of keys and values
        lambda_tags = {}
        for tag in tags:
            key = tag['Key']
            value = tag['Value']
            lambda_tags[key] = value
        util.tag_lambda_functions([lambda_arn], lambda_tags)

    # Perform un-tagging operations
    if args.untag:
        tags = []
        for tag in args.untag:
            tags.append({'Key': tag})

        # Un-tag EC2 resources
        cluster.untag_instances(tags)
        cluster.untag_volumes(tags)
        cluster.untag_snapshots(tags)
        # cluster.untag_subnet(tags)

        # Un-tag lambda functions
        print("Un-tagging lambda function(s)")
        lambda_arn = util.get_lambda_arn("TAGMANIA-AUTO-" + args.cluster)
        # Lambda un-tagging uses a plain list of keys
        lambda_keys = []
        for tag in tags:
            key = tag['Key']
            lambda_keys.append(key)
        util.untag_lambda_functions([lambda_arn], lambda_keys)


if __name__ == '__main__':
    main()
