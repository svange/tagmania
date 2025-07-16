
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_aws_environment():
    """Set up AWS environment for tests"""
    # Ensure AWS profile is set for tests
    if 'AWS_PROFILE' not in os.environ:
        os.environ['AWS_PROFILE'] = 'test'

    # Ensure a default region is set if not already configured
    if 'AWS_DEFAULT_REGION' not in os.environ:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


class Secret:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Secret(********)"

    def __str___(self):
        return "*******"
