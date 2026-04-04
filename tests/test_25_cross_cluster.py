import pytest

from tagmania.iac_tools.clusterset import ClusterSet


@pytest.mark.integration
@pytest.mark.cluster_all
class TestCrossCluster:
    """
    Tests that require multiple clusters simultaneously.
    Runs after cluster-isolated tests complete.
    """

    @pytest.fixture
    def cluster1(self):
        """ClusterSet for test1 cluster (1 instance)"""
        return ClusterSet("test1")

    @pytest.fixture
    def cluster2(self):
        """ClusterSet for test2 cluster (2 instances)"""
        return ClusterSet("test2")

    @pytest.fixture
    def cluster3(self):
        """ClusterSet for test3 cluster (2 instances)"""
        return ClusterSet("test3")

    @pytest.mark.slow
    def test_cross_cluster_isolation(self, cluster1, cluster2):
        """Test that targeted operations don't affect other clusters"""
        # Ensure both clusters are running
        cluster1.start_instances()
        cluster2.start_instances()

        # Stop instances in cluster2 only
        cluster2.stop_instances_targeted("test2-.*")

        # Verify cluster1 instances are still running
        cluster1_running = cluster1.get_running_instances()
        cluster1_stopped = cluster1.get_stopped_instances()

        assert len(cluster1_running) == 1, "Cluster1 instance should still be running"
        assert len(cluster1_stopped) == 0, "Cluster1 should have no stopped instances"

        # Verify cluster2 instances are stopped
        cluster2_running = cluster2.get_running_instances()
        cluster2_stopped = cluster2.get_stopped_instances()

        assert len(cluster2_running) == 0, "Cluster2 should have no running instances"
        assert len(cluster2_stopped) == 2, "Cluster2 should have 2 stopped instances"

    def test_cleanup_after_tests(self, cluster1, cluster2, cluster3):
        """Final cleanup - ensure all clusters are running and snapshots deleted"""
        cluster1.start_instances()
        cluster2.start_instances()
        cluster3.start_instances()

        for cluster in [cluster1, cluster2, cluster3]:
            for label in ["test-basic", "test-targeted", "cli-test"]:
                try:
                    cluster.delete_snapshots(label)
                except Exception:
                    pass
