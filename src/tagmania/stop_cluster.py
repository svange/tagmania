import argparse
from tagmania.iac_tools.clusterset import ClusterSet


def main():
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
