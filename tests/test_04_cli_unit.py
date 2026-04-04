import subprocess
import sys
from unittest.mock import MagicMock, patch


class TestStartClusterMain:
    @patch("tagmania.start_cluster.ClusterSet")
    def test_start_cluster(self, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.cluster_names = "test1"
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["cluster-start", "test1"]):
            from tagmania.start_cluster import main

            main()
        mock_cs_class.assert_called_once_with("test1", profile=None)
        mock_cs.start_instances.assert_called_once()

    @patch("tagmania.start_cluster.ClusterSet")
    def test_start_cluster_with_profile(self, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.cluster_names = "test1"
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["cluster-start", "--profile", "myprof", "test1"]):
            from tagmania.start_cluster import main

            main()
        mock_cs_class.assert_called_once_with("test1", profile="myprof")


class TestStopClusterMain:
    @patch("tagmania.stop_cluster.ClusterSet")
    def test_stop_cluster(self, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.cluster_names = "test1"
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["cluster-stop", "test1"]):
            from tagmania.stop_cluster import main

            main()
        mock_cs_class.assert_called_once_with("test1", profile=None)
        mock_cs.stop_instances.assert_called_once()

    @patch("tagmania.stop_cluster.ClusterSet")
    def test_stop_cluster_with_profile(self, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.cluster_names = "test1"
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["cluster-stop", "-p", "devaccount", "test1"]):
            from tagmania.stop_cluster import main

            main()
        mock_cs_class.assert_called_once_with("test1", profile="devaccount")


class TestCLIHelpSubprocess:
    """Subprocess tests for help output (don't need coverage, validate UX)."""

    def test_snapshot_manager_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "tagmania.snapshot_manager", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--backup" in result.stdout
        assert "--restore" in result.stdout
        assert "--target" in result.stdout

    def test_start_cluster_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "tagmania.start_cluster", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--profile" in result.stdout

    def test_stop_cluster_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "tagmania.stop_cluster", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--profile" in result.stdout

    def test_mutually_exclusive_backup_restore(self):
        result = subprocess.run(
            [sys.executable, "-m", "tagmania.snapshot_manager", "--backup", "--restore", "test"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
