import argparse
from tagmania.iac_tools.clusterset import ClusterSet
from tagmania.iac_tools import util

def main():
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

    parser.add_argument('--profile', '-p', help='the AWS profile to use', default='default')
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
