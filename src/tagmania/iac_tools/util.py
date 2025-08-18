"""AWS Utility Functions for Tagmania.

This module provides utility functions for working with various AWS services
beyond the core EC2 functionality. Currently focuses on AWS Lambda functions
but can be extended for other services as needed.

The utilities include helper functions for retrieving ARNs, managing tags,
and working with AWS clients in a consistent manner across the application.

Example:
    Lambda function utilities:

    ```python
    # Get Lambda function ARN
    arn = get_lambda_arn('my-function')

    # Tag multiple functions
    arns = [get_lambda_arn('func1'), get_lambda_arn('func2')]
    tags = {'Environment': 'production', 'Team': 'backend'}
    tag_lambda_functions(arns, tags)
    ```
"""

from functools import lru_cache
import boto3
import os


@lru_cache  # cache the client the first time we ask for it
def _lambda_client():
    """Get cached AWS Lambda client with fallback region handling.

    Returns:
        boto3.client: Configured Lambda client with region fallback

    Note:
        Uses LRU cache to avoid creating multiple clients. Falls back to
        us-east-1 if AWS_REGION environment variable is not set.
    """
    # Fall back to env-var or default region so boto3 never errors
    return boto3.client("lambda", region_name=os.getenv("AWS_REGION", "us-east-1"))


def get_lambda_arn(function_name: str) -> str:
    """Retrieve the ARN for a Lambda function.

    Args:
        function_name: Name of the Lambda function

    Returns:
        str: Full ARN of the Lambda function

    Raises:
        ClientError: If function doesn't exist or access is denied

    Example:
        ```python
        arn = get_lambda_arn('my-processing-function')
        print(f"Function ARN: {arn}")
        ```
    """
    response = _lambda_client().get_function(FunctionName=function_name)
    return response["Configuration"]["FunctionArn"]


def tag_lambda_functions(function_arns, tags):
    """Apply tags to multiple Lambda functions.

    Args:
        function_arns: List of Lambda function ARNs
        tags: Dictionary of tag key-value pairs

    Example:
        ```python
        arns = [get_lambda_arn('func1'), get_lambda_arn('func2')]
        tags = {'Environment': 'production', 'Owner': 'team-backend'}
        tag_lambda_functions(arns, tags)
        ```
    """
    client = _lambda_client()
    for arn in function_arns:
        client.tag_resource(Resource=arn, Tags=tags)


def untag_lambda_functions(function_arns, keys):
    """Remove tags from multiple Lambda functions.

    Args:
        function_arns: List of Lambda function ARNs
        keys: List of tag keys to remove

    Example:
        ```python
        arns = [get_lambda_arn('func1'), get_lambda_arn('func2')]
        keys = ['Environment', 'TempTag']
        untag_lambda_functions(arns, keys)
        ```
    """
    client = _lambda_client()
    for arn in function_arns:
        client.untag_resource(Resource=arn, TagKeys=keys)
