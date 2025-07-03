import argparse
from tagmania.iac_tools.clusterset import ClusterSet

def main():
    parser = argparse.ArgumentParser(description='AWS cluster snapshot deletion.',
                                     epilog='This tool relies on the "Cluster" and "Owner" tags on instances and '
                                            'volumes. IAC automation puts this in place.'
                                            'This tool deletes all snapshots belonging to a cluster.')
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('cluster',
                        help='the name CLUSTER of the cluster in question. This can be found by looking at any node '
                             'in the AWS console and looking for the "Cluster" tag.')

    parser.add_argument('--profile', '-p', help='the AWS profile to use', default='default')
    args = parser.parse_args()

    cluster = ClusterSet(args.cluster, profile=args.profile)
    print('Deleting snapshots for %s' % args.cluster)

    #TODO: IMPLEMENT
    print('Backup operation completed successfully!')

if __name__ == '__main__':
    main()
