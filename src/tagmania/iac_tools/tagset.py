"""TagSet - AWS Resource Tag Management Utilities.

This module provides the TagSet class for managing AWS resource tags in a consistent
and convenient way. It handles the standard AWS tag format (Key/Value pairs) and
provides methods for adding, retrieving, and manipulating tags.

The TagSet class is used throughout Tagmania for working with EC2 instance tags,
volume tags, and snapshot tags in a unified manner.

Example:
    Basic tag operations:

    ```python
    # Create from existing tags
    tags = TagSet(instance.tags)

    # Get cluster name
    cluster = tags.get('Cluster')

    # Add new tag
    tags.add('Environment', 'production')

    # Convert to AWS format
    tag_list = tags.to_list()
    ```
"""


class TagSet:
    """Wrapper class for managing AWS resource tags.

    Provides a convenient interface for working with AWS tags, which are
    typically represented as lists of Key/Value dictionaries. This class
    abstracts the details of the AWS tag format and provides simple methods
    for common tag operations.

    Attributes:
        _tags: Internal list of tag dictionaries in AWS format

    Example:
        ```python
        # Create empty tagset
        tags = TagSet()

        # Create from existing tags
        tags = TagSet(instance.tags)

        # Add tags
        tags.add('Name', 'web-server-01')
        tags.add('Environment', 'production')

        # Retrieve values
        name = tags.get('Name')
        ```
    """
    def __init__(self, tags=None):
        """Initialize TagSet with optional existing tags.

        Args:
            tags: List of tag dictionaries in AWS format (optional).
                 If None, creates empty tag set.
        """
        if tags == None:
            self._tags = []
        else:
            self._tags = tags

    def add(self, key, value):
        """Add a new tag to the tag set.

        Args:
            key: Tag key (string)
            value: Tag value (string)

        Example:
            ```python
            tags.add('Environment', 'production')
            tags.add('Owner', 'team-backend')
            ```
        """
        tag = {'Key': key, 'Value': value}
        self._tags.append(tag)

    def get(self, key):
        """Retrieve the value for a specific tag key.

        Args:
            key: Tag key to look up (string)

        Returns:
            str: Tag value if found, None if key doesn't exist

        Example:
            ```python
            cluster_name = tags.get('Cluster')
            if cluster_name:
                print(f"Instance belongs to cluster: {cluster_name}")
            ```
        """
        for tag in self._tags:
            if tag['Key'] == key:
                return tag['Value']
        return None

    def to_list(self):
        """Convert tag set to AWS-compatible list format.

        Returns:
            list: List of tag dictionaries in AWS format [{'Key': 'k', 'Value': 'v'}, ...]

        Example:
            ```python
            tags = TagSet()
            tags.add('Name', 'web-server')
            tags.add('Environment', 'prod')

            # Use with AWS API
            ec2.create_tags(Resources=[instance_id], Tags=tags.to_list())
            ```
        """
        return self._tags
