import pytest
import time
import logging
from tagmania.iac_tools.clusterset import ClusterSet

logger = logging.getLogger(__name__)

class TestBasicClusterOperations:
    """
    Basic cluster operations tests using test1 cluster (1 instance)
    These test the core functionality without getting into complex scenarios
    """

    @pytest.fixture
    def cluster(self):
        """ClusterSet for test1 cluster (1 instance)"""
        return ClusterSet('test1')

    def test_clusterset_stop(self, cluster, retry_helper):
        """
        Test the ClusterSet class stop_instances method.
        """
        retry_helper.retry_operation(cluster.stop_instances)
        time.sleep(2)  # Give AWS time to process

    def test_clusterset_start(self, cluster, retry_helper):
        """
        Test the ClusterSet class start_instances method.
        """
        retry_helper.retry_operation(cluster.start_instances)
        time.sleep(2)  # Give AWS time to process

    @pytest.mark.slow
    @pytest.mark.aws_intensive
    def test_snapshot_backup(self, cluster, retry_helper):
        """
        Test the snapshot backup script.
        """
        retry_helper.retry_operation(cluster.stop_instances)
        time.sleep(10)  # Wait for instances to fully stop

        # Add delay to avoid snapshot rate limit
        time.sleep(5)
        retry_helper.retry_operation(cluster.create_snapshots, snapshot_name='test-basic')

    @pytest.mark.slow
    @pytest.mark.aws_intensive
    def test_snapshot_restore(self, cluster, retry_helper):
        """
        Test the snapshot restore script.
        """
        retry_helper.retry_operation(cluster.stop_instances)
        time.sleep(10)  # Wait for instances to fully stop

        retry_helper.retry_operation(cluster.detach_volumes)
        time.sleep(5)  # Wait for volumes to detach

        retry_helper.retry_operation(cluster.delete_volumes)
        time.sleep(5)  # Wait for volumes to delete

        # Create new volumes from snapshots and attach them
        retry_helper.retry_operation(cluster.create_volumes, snapshot_name='test-basic')
        time.sleep(5)  # Wait for volumes to be created

        retry_helper.retry_operation(cluster.attach_volumes, snapshot_name='test-basic')

    def test_snapshot_delete(self, cluster, retry_helper):
        """
        Test the snapshot delete script.
        """
        retry_helper.retry_operation(cluster.delete_snapshots, snapshot_name='test-basic')

    def test_cleanup_after_tests(self, cluster, retry_helper):
        """Cleanup test resources"""
        # Ensure instances are running for next tests
        retry_helper.retry_operation(cluster.start_instances)
        time.sleep(5)  # Give AWS time to stabilize

        # Delete any test snapshots that might remain
        try:
            cluster.delete_snapshots('test-basic')
        except:
            pass  # Ignore if snapshots don't exist