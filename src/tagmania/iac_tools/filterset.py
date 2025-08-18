"""FilterSet - AWS Resource Filter Management Utilities.

This module provides the FilterSet class for managing AWS resource filters in a
consistent way. It handles the standard AWS filter format (Name/Values pairs) and
provides methods for adding, retrieving, and converting filters for use with AWS APIs.

The FilterSet class is used throughout Tagmania for building complex filter expressions
when querying AWS resources like EC2 instances, volumes, and snapshots.

Example:
    Building filters for EC2 queries:

    ```python
    # Create filter set
    filters = FilterSet()

    # Add cluster filter
    filters.add('tag:Cluster', 'production-web')

    # Add state filter
    filters.add('instance-state-name', ['running', 'stopped'])

    # Use with AWS API
    instances = ec2.instances.filter(Filters=filters.to_list())
    ```
"""


class FilterSet:
    """Wrapper class for managing AWS resource filters.

    Provides a convenient interface for working with AWS filters, which are
    typically represented as lists of Name/Values dictionaries. This class
    abstracts the details of the AWS filter format and provides simple methods
    for building complex filter expressions.

    Attributes:
        _filters: Internal list of filter dictionaries in AWS format

    Example:
        ```python
        # Create empty filter set
        filters = FilterSet()

        # Add filters
        filters.add('tag:Environment', 'production')
        filters.add('instance-state-name', ['running', 'stopped'])

        # Use with AWS EC2 API
        instances = ec2.instances.filter(Filters=filters.to_list())
        ```
    """
    def __init__(self, filters=None):
        """Initialize FilterSet with optional existing filters.

        Args:
            filters: List of filter dictionaries in AWS format (optional).
                    If None, creates empty filter set.
        """
        if filters == None:
            self._filters = []
        else:
            self._filters = filters

    def add(self, name, values):
        """Add a new filter to the filter set.

        Args:
            name: Filter name (string) - e.g., 'tag:Cluster', 'instance-state-name'
            values: Filter values (string or list of strings)

        Example:
            ```python
            filters.add('tag:Environment', 'production')
            filters.add('instance-state-name', ['running', 'stopped'])
            ```
        """
        if isinstance(values, str):
            values = [values]
        f = {'Name': name, 'Values': values}
        self._filters.append(f)

    def get(self, name):
        """Retrieve the values for a specific filter name.

        Args:
            name: Filter name to look up (string)

        Returns:
            list: Filter values if found, None if name doesn't exist

        Example:
            ```python
            cluster_values = filters.get('tag:Cluster')
            if cluster_values:
                print(f"Filtering for clusters: {cluster_values}")
            ```
        """
        for f in self._filters:
            if f['Name'] == name:
                return f['Values']
        return None

    def to_list(self):
        """Convert filter set to AWS-compatible list format.

        Returns:
            list: List of filter dictionaries in AWS format [{'Name': 'n', 'Values': ['v']}, ...]

        Example:
            ```python
            filters = FilterSet()
            filters.add('tag:Environment', 'production')
            filters.add('instance-state-name', 'running')

            # Use with AWS API
            instances = ec2.instances.filter(Filters=filters.to_list())
            ```
        """
        return self._filters
