"""AWS Cluster Volume Deletion CLI.

This module provides a command-line interface for listing and deleting managed
EBS volumes (including dynamically created Kubernetes volumes) associated with
an EC2 cluster identified by its "Cluster" tag.
"""

import argparse

from tagmania.iac_tools.clusterset import ClusterSet
from tagmania.iac_tools.tagset import TagSet


def main() -> None:
    """Main entry point for the cluster volume deletion CLI."""
    parser = argparse.ArgumentParser(
        description="AWS cluster volume deletion.",
        epilog='This tool relies on the "Cluster" and "Owner" tags on instances and '
        "volumes. IAC automation puts this in place. "
        "This tool deletes all volumes belonging to a cluster.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-D",
        "--delete",
        action="store_const",
        dest="delete",
        const=True,
        default=False,
        help="Delete volumes from cluster CLUSTER.",
    )
    group.add_argument(
        "-l",
        "--list",
        action="store_const",
        dest="list",
        const=True,
        default=False,
        help="List volumes belonging to cluster CLUSTER.",
    )
    parser.add_argument(
        "cluster",
        help="""
            the name CLUSTER of the cluster in question. This can be found by
            looking at any node in the AWS console and looking for the "Cluster"
            tag.""",
    )

    parser.add_argument("--profile", "-p", help="the AWS profile to use", default=None)
    args = parser.parse_args()

    cluster = ClusterSet(args.cluster, profile=args.profile)
    volumes = cluster.get_volumes()
    kubernetes_volumes = cluster.get_kubernetes_volumes()

    if args.list:
        print(f"Listing volumes for cluster {args.cluster}:")
        for volume in volumes:
            print(volume.id)

        if kubernetes_volumes:
            print(f"\nKubernetes dynamically created volumes for cluster {args.cluster}:")
            for volume in kubernetes_volumes:
                volume_name = TagSet(volume.tags).get("Name") or ""
                print(f"{volume.id} ({volume_name})")

        if not volumes and not kubernetes_volumes:
            print("No volumes found.")

    if args.delete:
        print(f"Listing all volumes for cluster {args.cluster}:")
        for volume in volumes:
            print(volume.id)

        for volume in kubernetes_volumes:
            volume_name = TagSet(volume.tags).get("Name") or ""
            print(f"{volume.id} ({volume_name})")

        if volumes or kubernetes_volumes:
            confirm = input('Do you want to delete these volumes? (only "yes" is accepted): ')
            if confirm != "yes":
                print("Command Aborted.")
            else:
                if volumes:
                    cluster.delete_volumes()
                if kubernetes_volumes:
                    cluster.delete_kubernetes_volumes()
        else:
            print("No volumes found.")


if __name__ == "__main__":
    main()
