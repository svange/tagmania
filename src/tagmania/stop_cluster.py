"""AWS Cluster Stop CLI.

This module provides a command-line interface for stopping all EC2 instances
in a cluster identified by their "Cluster" tag. It's a simple utility that
stops all running instances in the specified cluster.

The tool relies on EC2 instances having "Cluster" tags to identify which
instances belong to the cluster that should be stopped.

Features:
    - Stop all instances in a cluster simultaneously
    - Support for AWS profile selection
    - Simple command-line interface
    - Confirmation message on completion

Usage:
    The module is typically invoked via the cluster-stop CLI command:

    ```bash
    # Stop a cluster using default AWS profile
    cluster-stop production-web

    # Stop a cluster using specific AWS profile
    cluster-stop --profile myprofile production-web
    ```

Note:
    This operation stops all instances in the cluster regardless of their
    current state. Stopped instances are not affected.

Warning:
    Stopping instances will interrupt any running processes and may result
    in data loss if applications don't handle graceful shutdown properly.
"""

import argparse
from tagmania.iac_tools.clusterset import ClusterSet


def main():
    """Main entry point for the cluster stop CLI.

    Parses command line arguments to identify the cluster name and optional
    AWS profile, then stops all EC2 instances in the specified cluster.

    Args:
        Command line arguments are parsed internally:
        - cluster: Name of the cluster to stop (required)
        - --profile: AWS profile to use (optional)

    Raises:
        SystemExit: On invalid command line arguments.
        AWSError: On AWS API failures during instance stop operations.
    """
    parser = argparse.ArgumentParser(description='AWS cluster stop tool.',
                                     epilog='This tool relies on the "Cluster" and "Owner" tags on instances and '
                                            'volumes. IAC automation puts this in place.'
                                            'Stops the cluster CLUSTER.')
    parser.add_argument('cluster',
                        help='the name CLUSTER of the cluster in question. This can be found by looking at any node '
                             'in the AWS console and looking for the "Cluster" tag.')

    parser.add_argument('--profile', '-p', help='the AWS profile to use', default=None)
    args = parser.parse_args()

    cluster = ClusterSet(args.cluster, profile=args.profile)
    cluster.stop_instances()
    print('Cluster %s stopped!' % cluster.cluster_names)

if __name__ == '__main__':
    main()
