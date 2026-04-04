from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def make_instance(name):
    return SimpleNamespace(
        id=f"i-{name}",
        tags=[{"Key": "Name", "Value": name}],
    )


def make_snapshot(snap_id, label):
    return SimpleNamespace(
        id=snap_id,
        tags=[
            {"Key": "Label", "Value": label},
            {"Key": "Cluster", "Value": "test1"},
        ],
    )


class TestSnapshotManagerBackup:
    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_backup_confirmed(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = [make_instance("web-01")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--backup", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_called_once()
        mock_cs.create_snapshots.assert_called_once_with("daily")
        assert "Operation completed" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="no")
    def test_backup_aborted(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--backup", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_not_called()
        assert "Operation aborted" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_backup_no_instances(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--backup", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_not_called()
        assert "No instances found" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_backup_default_name(self, mock_input, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = [make_instance("web-01")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--backup", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.create_snapshots.assert_called_once_with("default")


class TestSnapshotManagerDelete:
    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_delete_named(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = [make_snapshot("snap-1", "daily")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--delete", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.delete_snapshots.assert_called_once_with("daily")

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_delete_all(self, mock_input, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = [make_snapshot("snap-1", "daily")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--delete", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.get_snapshots.assert_called_once_with("*")
        mock_cs.delete_snapshots.assert_called_once_with("*")

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="no")
    def test_delete_aborted(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--delete", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.delete_snapshots.assert_not_called()
        assert "Operation aborted" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_delete_no_snapshots(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--delete", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.delete_snapshots.assert_not_called()
        assert "No snapshots found" in capsys.readouterr().out


class TestSnapshotManagerRestore:
    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_full_restore(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = [make_instance("web-01")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--restore", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_called_once()
        mock_cs.detach_volumes.assert_called_once()
        mock_cs.delete_volumes.assert_called_once()
        mock_cs.create_volumes.assert_called_once_with("daily")
        mock_cs.attach_volumes.assert_called_once_with("daily")
        assert "Operation completed" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="no")
    def test_full_restore_aborted(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--restore", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_not_called()
        assert "Operation aborted" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_full_restore_no_instances(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--restore", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances.assert_not_called()
        assert "No instances found" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_targeted_restore(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        instances = [make_instance("web-01"), make_instance("db-01")]
        mock_cs.get_instances.return_value = instances
        mock_cs._filter_instances_by_name_regex.return_value = [instances[0]]
        mock_cs_class.return_value = mock_cs
        with patch(
            "sys.argv", ["snap", "--restore", "--target", "web.*", "--name", "daily", "test1"]
        ):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances_targeted.assert_called_once_with("web.*")
        mock_cs.detach_volumes_targeted.assert_called_once_with("web.*")
        mock_cs.delete_volumes_targeted.assert_called_once_with("web.*")
        mock_cs.create_volumes_targeted.assert_called_once_with("daily", "web.*")
        mock_cs.attach_volumes_targeted.assert_called_once_with("daily", "web.*")
        out = capsys.readouterr().out
        assert "Found 1 instances" in out
        assert "Operation completed" in out

    @patch("tagmania.snapshot_manager.ClusterSet")
    @patch("builtins.input", return_value="no")
    def test_targeted_restore_aborted(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = [make_instance("web-01")]
        mock_cs._filter_instances_by_name_regex.return_value = [make_instance("web-01")]
        mock_cs_class.return_value = mock_cs
        with patch(
            "sys.argv", ["snap", "--restore", "--target", "web.*", "--name", "daily", "test1"]
        ):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.stop_instances_targeted.assert_not_called()
        assert "Operation aborted" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_targeted_restore_no_match(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_instances.return_value = [make_instance("db-01")]
        mock_cs._filter_instances_by_name_regex.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch(
            "sys.argv", ["snap", "--restore", "--target", "web.*", "--name", "daily", "test1"]
        ):
            from tagmania.snapshot_manager import main

            main()
        assert "No instances found matching" in capsys.readouterr().out

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_targeted_restore_invalid_regex(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        with patch(
            "sys.argv", ["snap", "--restore", "--target", "[invalid", "--name", "daily", "test1"]
        ):
            from tagmania.snapshot_manager import main

            main()
        assert "Invalid regex pattern" in capsys.readouterr().out


class TestSnapshotManagerList:
    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_list_all(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = [
            make_snapshot("snap-1", "daily"),
            make_snapshot("snap-2", "weekly"),
        ]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--list", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.get_snapshots.assert_called_once_with("*")
        out = capsys.readouterr().out
        assert "Listing all snapshots" in out
        assert "daily" in out
        assert "weekly" in out

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_list_named(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = [make_snapshot("snap-1", "daily")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--list", "--name", "daily", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs.get_snapshots.assert_called_once_with("daily")
        out = capsys.readouterr().out
        assert "snap-1" in out

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_list_with_profile(self, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.get_snapshots.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["snap", "--list", "--profile", "myprof", "test1"]):
            from tagmania.snapshot_manager import main

            main()
        mock_cs_class.assert_called_once_with("test1", profile="myprof")
