import argparse
from tagmania.iac_tools.tagset import TagSet
from tagmania.iac_tools.clusterset import ClusterSet

def main():
    parser = argparse.ArgumentParser(description='AWS cluster volume deletion.',
                                     epilog='This tool relies on the "Cluster" and "Owner" tags on instances and '
                                            'volumes. IAC automation puts this in place'
                                            'This tool deletes all volumes belonging to a cluster.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-D', '--delete',
        action='store_const',
        dest='delete',
        const=True,
        default=False,
        help='Delete snapshots from cluster CLUSTER.'
    )
    group.add_argument('-l', '--list',
        action='store_const',
        dest='list',
        const=True,
        default=False,
        help='List snapshots with a given label or all if none specified.'
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
    volumes = cluster.get_volumes()
    kubernetes_volumes = cluster.get_kubernetes_volumes()

    if args.list:
        print('Listing volumes for cluster %s:' % args.cluster)
        for volume in volumes:
            print(volume.id)

        if len(kubernetes_volumes) != 0:
            print('\nKubernetes dynamically created volumes for cluster %s:' % args.cluster)
            for volume in kubernetes_volumes:
                ts = TagSet(volume.tags)
                volume_name = ts.get('Name')
                print(volume.id + " (" + volume_name + ")")

        if len(volumes) == 0 and len(kubernetes_volumes) == 0:
            print("No volumes found.")

    if args.delete:
        print('Listing all volumes for cluster %s:' % args.cluster)
        for volume in volumes:
            print(volume.id)

        for volume in kubernetes_volumes:
            ts = TagSet(volume.tags)
            volume_name = ts.get('Name')
            print(volume.id + " (" + volume_name + ")")

        if len(volumes) != 0 or len(kubernetes_volumes) != 0:
            confirm = input("Do you want to delete these volumes? (only \"yes\" is accepted): ")
            if confirm != "yes":
                print("Command Aborted.")
            else:
                if len(volumes) != 0:
                    cluster.delete_volumes()
                if len(kubernetes_volumes) != 0:
                    cluster.delete_kubernetes_volumes()
        else:
            print("No volumes found.")
if __name__ == '__main__':
    main()
