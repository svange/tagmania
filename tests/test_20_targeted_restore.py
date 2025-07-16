import pytest
import re
from tagmania.iac_tools.clusterset import ClusterSet


class TestTargetedRestore:
    """
    Test targeted restore functionality with regex filtering.
    Uses the deployed test infrastructure with 2 clusters:
    - test1: 1 instance (test1-web-01)
    - test2: 2 instances (test2-api-01, test2-db-01)
    """

    @pytest.fixture
    def cluster1(self):
        """ClusterSet for test1 cluster (1 instance)"""
        return ClusterSet('test1')

    @pytest.fixture
    def cluster2(self):
        """ClusterSet for test2 cluster (2 instances)"""
        return ClusterSet('test2')

    def test_filter_instances_by_name_regex_single_match(self, cluster2):
        """Test filtering instances with regex that matches single instance"""
        instances = cluster2.get_instances()
        assert len(instances) == 2, "Should have 2 instances in test2 cluster"

        # Filter for only API instances
        filtered = cluster2._filter_instances_by_name_regex(instances, ".*-api-.*")
        assert len(filtered) == 1, "Should match exactly 1 api instance"

        # Verify the matched instance has correct name
        instance_name = None
        for tag in filtered[0].tags:
            if tag['Key'] == 'Name':
                instance_name = tag['Value']
                break
        assert instance_name == 'test2-api-01', f"Expected test2-api-01, got {instance_name}"

    def test_filter_instances_by_name_regex_multiple_match(self, cluster2):
        """Test filtering instances with regex that matches multiple instances"""
        instances = cluster2.get_instances()

        # Filter for all test2 instances
        filtered = cluster2._filter_instances_by_name_regex(instances, "test2-.*")
        assert len(filtered) == 2, "Should match both test2 instances"

    def test_filter_instances_by_name_regex_no_match(self, cluster2):
        """Test filtering instances with regex that matches nothing"""
        instances = cluster2.get_instances()

        # Filter for non-existent pattern
        filtered = cluster2._filter_instances_by_name_regex(instances, "nonexistent")
        assert len(filtered) == 0, "Should match no instances"

    def test_filter_instances_invalid_regex(self, cluster2):
        """Test filtering with invalid regex raises appropriate error"""
        instances = cluster2.get_instances()

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            cluster2._filter_instances_by_name_regex(instances, "[invalid")

    @pytest.mark.slow
    def test_stop_instances_targeted_single(self, cluster2):
        """Test stopping single instance with targeted method"""
        # Ensure instances are running first
        cluster2.start_instances()

        # Stop only the API instance
        cluster2.stop_instances_targeted(".*-api-.*")

        # Verify only the API instance is stopped
        running_instances = cluster2.get_running_instances()
        stopped_instances = cluster2.get_stopped_instances()

        # Should have 1 running (db) and 1 stopped (api)
        assert len(running_instances) == 1, "Should have 1 running instance"
        assert len(stopped_instances) == 1, "Should have 1 stopped instance"

        # Verify the stopped instance is the API instance
        stopped_name = None
        for tag in stopped_instances[0].tags:
            if tag['Key'] == 'Name':
                stopped_name = tag['Value']
                break
        assert stopped_name == 'test2-api-01', f"Expected api instance stopped, got {stopped_name}"

    @pytest.mark.slow
    def test_start_instances_targeted_single(self, cluster2):
        """Test starting single instance with targeted method"""
        # Ensure instances are stopped first
        cluster2.stop_instances()

        # Start only the DB instance
        cluster2.start_instances_targeted(".*-db-.*")

        # Verify only the DB instance is running
        running_instances = cluster2.get_running_instances()
        stopped_instances = cluster2.get_stopped_instances()

        # Should have 1 running (db) and 1 stopped (api)
        assert len(running_instances) == 1, "Should have 1 running instance"
        assert len(stopped_instances) == 1, "Should have 1 stopped instance"

        # Verify the running instance is the DB instance
        running_name = None
        for tag in running_instances[0].tags:
            if tag['Key'] == 'Name':
                running_name = tag['Value']
                break
        assert running_name == 'test2-db-01', f"Expected db instance running, got {running_name}"

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

    def test_targeted_no_instances_found(self, cluster2):
        """Test targeted operations when no instances match pattern"""
        # This should not raise an error, just print a message
        cluster2.stop_instances_targeted("nonexistent-pattern")
        cluster2.start_instances_targeted("nonexistent-pattern")

    @pytest.mark.slow
    def test_full_targeted_restore_workflow(self, cluster2):
        """Test complete targeted restore workflow"""
        # This test is marked as slow - it does real backup/restore operations

        # Create a backup first
        cluster2.stop_instances()
        cluster2.create_snapshots('test-targeted')

        # Now test targeted restore for just the API instance
        try:
            # Stop only API instance (they're already stopped from backup)
            # cluster2.stop_instances_targeted(".*-api-.*")

            # Detach and delete volumes for API instance only
            cluster2.detach_volumes_targeted(".*-api-.*")
            cluster2.delete_volumes_targeted(".*-api-.*")

            # Restore volumes for API instance only
            cluster2.create_volumes_targeted('test-targeted', ".*-api-.*")
            cluster2.attach_volumes_targeted('test-targeted', ".*-api-.*")

            # Don't start instances - just verify the targeted operations completed
            # This saves significant time waiting for instance start

            # If we got here without exceptions, the targeted restore workflow worked
            # Let's just verify we have some restored volumes with the correct label
            restored_volumes = cluster2.get_restored_volumes('test-targeted')
            assert len(restored_volumes) > 0, "Should have some restored volumes"

            # Verify the volumes have the correct label
            labeled_volumes = []
            for volume in restored_volumes:
                if volume.tags:
                    for tag in volume.tags:
                        if tag['Key'] == 'Label' and tag['Value'] == 'test-targeted':
                            labeled_volumes.append(volume)
                            break

            assert len(labeled_volumes) > 0, "Should have volumes with correct label"

        finally:
            # Cleanup: delete test snapshots
            cluster2.delete_snapshots('test-targeted')

    def test_targeted_restore_invalid_regex(self, cluster2):
        """Test that invalid regex in targeted operations raises appropriate errors"""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            cluster2.stop_instances_targeted("[invalid")

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            cluster2.create_volumes_targeted('test', "[invalid")

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            cluster2.attach_volumes_targeted('test', "[invalid")

    def test_cleanup_after_tests(self, cluster1, cluster2):
        """Cleanup test resources"""
        # Ensure all instances are running for next tests
        cluster1.start_instances()
        cluster2.start_instances()

        # Delete any test snapshots that might remain
        try:
            cluster1.delete_snapshots('test-targeted')
        except:
            pass  # Ignore if snapshots don't exist

        try:
            cluster2.delete_snapshots('test-targeted')
        except:
            pass  # Ignore if snapshots don't exist