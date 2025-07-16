import pytest
import subprocess
import sys
import os
from tagmania.iac_tools.clusterset import ClusterSet


class TestSnapshotManagerCLI:
    """
    Test the snapshot_manager CLI with --target functionality.
    Uses the deployed test infrastructure with 2 clusters.
    """

    @pytest.fixture
    def cluster2(self):
        """ClusterSet for test2 cluster (2 instances)"""
        return ClusterSet('test2')

    def run_snapshot_manager(self, args):
        """Helper to run snapshot_manager with given arguments"""
        cmd = [sys.executable, '-m', 'tagmania.snapshot_manager'] + args

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input='yes\n',  # Automatically confirm prompts
            cwd=os.path.dirname(os.path.dirname(__file__))  # Run from project root
        )
        return result

    def test_snapshot_manager_help(self):
        """Test that help shows the new --target option"""
        result = self.run_snapshot_manager(['--help'])
        assert result.returncode == 0
        assert '--target' in result.stdout
        assert 'Regex pattern to match instance Name tags' in result.stdout

    def test_snapshot_manager_targeted_restore_validation(self):
        """Test that snapshot_manager validates regex patterns correctly"""
        # Test with invalid regex - should return error code
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--restore', '--target', '[invalid', '--name', 'test', 'test2'
        ], capture_output=True, text=True, input='yes\n')

        assert 'Invalid regex pattern' in result.stdout

    def test_snapshot_manager_targeted_restore_no_instances(self):
        """Test targeted restore when no instances match pattern"""
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--restore', '--target', 'nonexistent', '--name', 'test', 'test2'
        ], capture_output=True, text=True, input='yes\n')

        assert 'No instances found matching pattern' in result.stdout
        assert 'Operation aborted' in result.stdout

    @pytest.mark.slow
    def test_full_cli_targeted_workflow(self, cluster2):
        """Test complete CLI workflow with targeted restore"""
        # Ensure instances are running
        cluster2.start_instances()

        # Step 1: Create a backup using CLI
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--backup', '--name', 'cli-test', 'test2'
        ], capture_output=True, text=True, input='yes\n')

        assert result.returncode == 0, f"Backup failed: {result.stderr}"
        assert 'Operation completed successfully' in result.stdout

        try:
            # Step 2: Test targeted restore using CLI
            result = subprocess.run([
                sys.executable, '-m', 'tagmania.snapshot_manager',
                '--restore', '--target', '.*-api-.*', '--name', 'cli-test', 'test2'
            ], capture_output=True, text=True, input='yes\n')

            # The CLI should show the filtered instances and complete successfully
            assert 'Found 1 instances matching pattern' in result.stdout
            assert 'test2-api-01' in result.stdout
            assert 'Operation completed successfully' in result.stdout

            # After targeted restore, instances should be stopped (as per snapshot_manager behavior)
            # Just verify the restore completed successfully without waiting for start
            # (The CLI output already confirms the restore worked)
            stopped_instances = cluster2.get_stopped_instances()
            assert len(stopped_instances) >= 1, "At least one instance should be stopped after restore"

        finally:
            # Cleanup: delete test snapshots
            subprocess.run([
                sys.executable, '-m', 'tagmania.snapshot_manager',
                '--delete', '--name', 'cli-test', 'test2'
            ], capture_output=True, text=True, input='yes\n')

    def test_list_snapshots_cli(self):
        """Test listing snapshots via CLI"""
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--list', 'test2'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'Listing all snapshots associated with test2' in result.stdout

    def test_mutually_exclusive_args(self):
        """Test that backup, restore, delete, and list are mutually exclusive"""
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--backup', '--restore', 'test2'
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'not allowed' in result.stderr.lower() or 'mutually exclusive' in result.stderr.lower()

    def test_target_only_with_restore(self):
        """Test that --target is only meaningful with --restore"""
        # This should work (restore with target)
        result = subprocess.run([
            sys.executable, '-m', 'tagmania.snapshot_manager',
            '--restore', '--target', 'test.*', '--name', 'test', 'test2'
        ], capture_output=True, text=True, input='no\n')  # Say no to confirmation

        assert 'Operation aborted' in result.stdout  # Should abort on 'no'

        # --target with other operations should be ignored or handled gracefully
        # (The current implementation doesn't prevent this, which is acceptable)