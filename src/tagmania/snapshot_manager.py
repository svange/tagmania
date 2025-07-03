import argparse
from tagmania.iac_tools.clusterset import ClusterSet

def main():
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
    parser.add_argument('cluster',
        help='''
            the name CLUSTER of the cluster in question. This can be found by
            looking at any node in the AWS console and looking for the "Cluster"
            tag.'''
    )
    parser.add_argument('--profile', '-p', help='the AWS profile to use', default='default')
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
