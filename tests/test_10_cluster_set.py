import pytest
import os
from tagmania.iac_tools.clusterset import ClusterSet

class TestBasicClusterOperations:
    """
    Basic cluster operations tests using test1 cluster (1 instance)
    These test the core functionality without getting into complex scenarios
    """

    @pytest.fixture
    def cluster(self):
        """ClusterSet for test1 cluster (1 instance)"""
        return ClusterSet('test1')

    def test_clusterset_stop(self, cluster):
        """
        Test the ClusterSet class stop_instances method.
        """
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")
        cluster.stop_instances()

    def test_clusterset_start(self, cluster):
        """
        Test the ClusterSet class start_instances method.
        """
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")
        cluster.start_instances()

    @pytest.mark.slow
    def test_snapshot_backup(self, cluster):
        """
        Test the snapshot backup script.
        """
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")

        cluster.stop_instances()
        cluster.create_snapshots('test-basic')

    @pytest.mark.slow
    def test_snapshot_restore(self, cluster):
        """
        Test the snapshot restore script.
        """
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")

        cluster.stop_instances()
        cluster.detach_volumes()
        cluster.delete_volumes()
        # Create new volumes from snapshots and attach them
        cluster.create_volumes('test-basic')
        cluster.attach_volumes('test-basic')

    def test_snapshot_delete(self, cluster):
        """
        Test the snapshot delete script.
        """
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")
        cluster.delete_snapshots('test-basic')

    def test_cleanup_after_tests(self, cluster):
        """Cleanup test resources"""
        if not os.getenv('AWS_DEFAULT_REGION'):
            pytest.skip("No AWS credentials configured")
        # Ensure instances are running for next tests
        cluster.start_instances()

        # Delete any test snapshots that might remain
        try:
            cluster.delete_snapshots('test-basic')
        except:
            pass  # Ignore if snapshots don't exist