from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def make_volume(vol_id, name=None):
    tags = [{"Key": "Name", "Value": name}] if name else []
    return SimpleNamespace(id=vol_id, tags=tags)


class TestDeleteVolumesListMode:
    @patch("tagmania.delete_volumes.ClusterSet")
    def test_list_volumes(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = [make_volume("vol-1"), make_volume("vol-2")]
        mock_cs.get_kubernetes_volumes.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--list", "test1"]):
            from tagmania.delete_volumes import main

            main()
        out = capsys.readouterr().out
        assert "vol-1" in out
        assert "vol-2" in out

    @patch("tagmania.delete_volumes.ClusterSet")
    def test_list_no_volumes(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = []
        mock_cs.get_kubernetes_volumes.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--list", "test1"]):
            from tagmania.delete_volumes import main

            main()
        assert "No volumes found" in capsys.readouterr().out

    @patch("tagmania.delete_volumes.ClusterSet")
    def test_list_with_kubernetes_volumes(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = []
        k8s_vol = make_volume("vol-k8s", name="pvc-abc123")
        mock_cs.get_kubernetes_volumes.return_value = [k8s_vol]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--list", "test1"]):
            from tagmania.delete_volumes import main

            main()
        out = capsys.readouterr().out
        assert "vol-k8s" in out
        assert "pvc-abc123" in out


class TestDeleteVolumesDeleteMode:
    @patch("tagmania.delete_volumes.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_delete_confirmed(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = [make_volume("vol-1")]
        mock_cs.get_kubernetes_volumes.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--delete", "test1"]):
            from tagmania.delete_volumes import main

            main()
        mock_cs.delete_volumes.assert_called_once()

    @patch("tagmania.delete_volumes.ClusterSet")
    @patch("builtins.input", return_value="no")
    def test_delete_aborted(self, mock_input, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = [make_volume("vol-1")]
        mock_cs.get_kubernetes_volumes.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--delete", "test1"]):
            from tagmania.delete_volumes import main

            main()
        mock_cs.delete_volumes.assert_not_called()
        assert "Command Aborted" in capsys.readouterr().out

    @patch("tagmania.delete_volumes.ClusterSet")
    def test_delete_no_volumes(self, mock_cs_class, capsys):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = []
        mock_cs.get_kubernetes_volumes.return_value = []
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--delete", "test1"]):
            from tagmania.delete_volumes import main

            main()
        assert "No volumes found" in capsys.readouterr().out

    @patch("tagmania.delete_volumes.ClusterSet")
    @patch("builtins.input", return_value="yes")
    def test_delete_kubernetes_volumes(self, mock_input, mock_cs_class):
        mock_cs = MagicMock()
        mock_cs.get_volumes.return_value = []
        mock_cs.get_kubernetes_volumes.return_value = [make_volume("vol-k8s", "pvc-abc")]
        mock_cs_class.return_value = mock_cs
        with patch("sys.argv", ["dv", "--delete", "test1"]):
            from tagmania.delete_volumes import main

            main()
        mock_cs.delete_kubernetes_volumes.assert_called_once()


class TestTagManagerTag:
    @patch("tagmania.tag_manager.util")
    @patch("tagmania.tag_manager.ClusterSet")
    def test_tag_resources(self, mock_cs_class, mock_util, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        mock_util.get_lambda_arn.return_value = "arn:aws:lambda:us-east-1:123:function:test"
        with patch("sys.argv", ["tm", "test1", "--tag", "Env:prod", "Owner:team"]):
            from tagmania.tag_manager import main

            main()
        mock_cs.tag_instances.assert_called_once()
        mock_cs.tag_volumes.assert_called_once()
        mock_cs.tag_snapshots.assert_called_once()
        tags = mock_cs.tag_instances.call_args[0][0]
        assert {"Key": "Env", "Value": "prod"} in tags
        assert {"Key": "Owner", "Value": "team"} in tags


class TestTagManagerUntag:
    @patch("tagmania.tag_manager.util")
    @patch("tagmania.tag_manager.ClusterSet")
    def test_untag_resources(self, mock_cs_class, mock_util, capsys):
        mock_cs = MagicMock()
        mock_cs_class.return_value = mock_cs
        mock_util.get_lambda_arn.return_value = "arn:aws:lambda:us-east-1:123:function:test"
        with patch("sys.argv", ["tm", "test1", "--untag", "TempTag", "BuildNum"]):
            from tagmania.tag_manager import main

            main()
        mock_cs.untag_instances.assert_called_once()
        mock_cs.untag_volumes.assert_called_once()
        mock_cs.untag_snapshots.assert_called_once()
        tags = mock_cs.untag_instances.call_args[0][0]
        assert {"Key": "TempTag"} in tags
        assert {"Key": "BuildNum"} in tags
