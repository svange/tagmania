from pathlib import Path
import pytest
import time
import logging
from tagmania.iac_tools.clusterset import ClusterSet

logger = logging.getLogger(__name__)


class Secret:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Secret(********)"

    def __str___(self):
        return "*******"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup and teardown for entire test session"""
    # Setup
    logger.info("Setting up test environment")

    # Ensure test clusters are in clean state before tests
    for cluster_name in ['test1', 'test2']:
        try:
            cluster = ClusterSet(cluster_name)
            # Try to start instances to ensure they're in a known state
            logger.info(f"Ensuring {cluster_name} cluster is in clean state")
            cluster.start_instances()
            time.sleep(5)  # Give AWS time to stabilize
        except Exception as e:
            logger.warning(f"Could not initialize {cluster_name}: {e}")

    yield

    # Teardown
    logger.info("Cleaning up test environment")
    for cluster_name in ['test1', 'test2']:
        try:
            cluster = ClusterSet(cluster_name)
            # Ensure instances are started for next test run
            cluster.start_instances()
            # Clean up any test snapshots
            for snapshot_name in ['test-basic', 'test-targeted']:
                try:
                    cluster.delete_snapshots(snapshot_name)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Could not cleanup {cluster_name}: {e}")


class RetryHelper:
    """Helper class for retrying AWS operations"""

    @staticmethod
    def retry_operation(func, max_attempts=3, delay=5, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(delay * (2 ** attempt))  # Exponential backoff


@pytest.fixture
def retry_helper():
    """Provide retry helper to tests"""
    return RetryHelper()


def pytest_configure(config):
    # compute the CSS file's absolute path from this file's location
    project_root = Path(__file__).parent.parent
    css_file = project_root / "resources" / "pytest-html.css"
    # override whatever was in addopts
    config.option.css = [str(css_file)]

    # ensure we're still inlining it into the HTML
    if not config.option.self_contained_html:
        config.option.self_contained_html = True

    # Add custom markers
    config.addinivalue_line(
        "markers", "aws_intensive: marks tests that make many AWS API calls"
    )
