import pytest
from tagmania.iac_tools.clusterset import ClusterSet

class TestGitHubSecretsAndVars:

    @pytest.mark.skip_ci
    def test_clusterset_stop(self):
        """
        Test the ClusterSet class stop_instances method.
        """
        cluster = ClusterSet('test', profile='test')
        cluster.stop_instances()

    @pytest.mark.skip_ci
    def test_clusterset_start(self):
        """
        Test the ClusterSet class stop_instances method.
        """
        cluster = ClusterSet('test', profile='test')
        cluster.start_instances()

    @pytest.mark.skip_ci
    def test_snapshot_backup(self):
        """
        Test the snapshot backup script.
        """
        cluster = ClusterSet('test', profile='test')

        cluster.stop_instances()
        cluster.create_snapshots('default')

    @pytest.mark.skip_ci
    def test_snapshot_restore(self):
        """
        Test the snapshot backup script.
        """
        cluster = ClusterSet('test', profile='test')

        cluster.stop_instances()
        cluster.detach_volumes()
        cluster.delete_volumes()
        # Create new volumes from snapshots and attach them
        cluster.create_volumes('default')
        cluster.attach_volumes('default')

    @pytest.mark.skip_ci
    def test_snapshot_delete(self):
        """
        Test the snapshot backup script.
        """
        cluster = ClusterSet('test', profile='test')
        cluster.delete_snapshots('default')

    def test_stub(self):
        assert True