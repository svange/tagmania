from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tagmania.iac_tools.clusterset import ClusterSet


def make_instance(name, cluster="test1", state="running", tags=None):
    """Create a mock EC2 instance."""
    if tags is None:
        tags = [
            {"Key": "Name", "Value": name},
            {"Key": "Cluster", "Value": cluster},
        ]
    return SimpleNamespace(tags=tags, id=f"i-{name}", state={"Name": state})


def make_volume(vol_id, tags=None):
    return SimpleNamespace(id=vol_id, tags=tags or [])


@pytest.fixture
def cluster():
    with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
        mock_session = MagicMock()
        mock_boto.Session.return_value = mock_session
        cs = ClusterSet("test1")
        yield cs


class TestFilterInstancesByNameRegex:
    def test_match_single_instance(self, cluster):
        instances = [make_instance("web-01"), make_instance("db-01")]
        result = cluster._filter_instances_by_name_regex(instances, "web.*")
        assert len(result) == 1
        assert result[0].id == "i-web-01"

    def test_match_multiple_instances(self, cluster):
        instances = [make_instance("web-01"), make_instance("web-02"), make_instance("db-01")]
        result = cluster._filter_instances_by_name_regex(instances, "web-.*")
        assert len(result) == 2

    def test_no_match(self, cluster):
        instances = [make_instance("web-01"), make_instance("db-01")]
        result = cluster._filter_instances_by_name_regex(instances, "nonexistent")
        assert len(result) == 0

    def test_empty_pattern_returns_all(self, cluster):
        instances = [make_instance("web-01"), make_instance("db-01")]
        result = cluster._filter_instances_by_name_regex(instances, "")
        assert len(result) == 2

    def test_invalid_regex_raises(self, cluster):
        instances = [make_instance("web-01")]
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            cluster._filter_instances_by_name_regex(instances, "[invalid")

    def test_instance_with_no_tags(self, cluster):
        inst = SimpleNamespace(tags=None, id="i-no-tags")
        result = cluster._filter_instances_by_name_regex([inst], ".*")
        assert len(result) == 0

    def test_instance_with_no_name_tag(self, cluster):
        inst = SimpleNamespace(tags=[{"Key": "Cluster", "Value": "prod"}], id="i-no-name")
        result = cluster._filter_instances_by_name_regex([inst], ".*")
        assert len(result) == 0

    def test_empty_instance_list(self, cluster):
        result = cluster._filter_instances_by_name_regex([], ".*")
        assert len(result) == 0


class TestClusterSetInit:
    def test_single_cluster_name(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            cs = ClusterSet("test1")
            assert cs.cluster_names == "test1"
            assert cs._cluster_name_str == "test1"

    def test_list_cluster_names(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            cs = ClusterSet(["cluster-a", "cluster-b"])
            assert cs.cluster_names == ["cluster-a", "cluster-b"]
            assert cs._cluster_name_str == "cluster-a"

    def test_cluster_filter_structure(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            cs = ClusterSet("prod")
            f = cs.get_cluster_filter()
            assert len(f) == 1
            assert f[0]["Name"] == "tag:Cluster"
            assert f[0]["Values"] == ["prod"]

    def test_cluster_filter_returns_copy(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            cs = ClusterSet("prod")
            f1 = cs.get_cluster_filter()
            f2 = cs.get_cluster_filter()
            assert f1 is not f2

    def test_profile_passed_to_session(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            ClusterSet("test1", profile="my-profile")
            mock_boto.Session.assert_called_once_with(profile_name="my-profile")

    def test_no_profile_uses_default(self):
        with patch("tagmania.iac_tools.clusterset.boto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            ClusterSet("test1")
            mock_boto.Session.assert_called_once_with()

    def test_max_items_set(self, cluster):
        assert cluster._MAX_ITEMS == 150

    def test_automation_key_set(self, cluster):
        assert cluster.AUTOMATION_KEY == "SNAPSHOT_MANAGER"


class TestClusterSetQueryMethods:
    def _setup_ec2_filter(self, cluster, instances):
        """Configure the mock ec2 to return instances from filter()."""
        mock_collection = MagicMock()
        mock_collection.limit.return_value = instances
        mock_collection.__iter__ = lambda self: iter(instances)
        cluster._ec2.instances.filter.return_value = mock_collection

    def test_get_instances(self, cluster):
        instances = [make_instance("web-01"), make_instance("db-01")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_instances()
        assert len(result) == 2
        cluster._ec2.instances.filter.assert_called_once()
        filters = cluster._ec2.instances.filter.call_args[1]["Filters"]
        state_filter = next(f for f in filters if f["Name"] == "instance-state-name")
        assert "running" in state_filter["Values"]
        assert "stopped" in state_filter["Values"]

    def test_get_running_instances(self, cluster):
        instances = [make_instance("web-01", state="running")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_running_instances()
        assert len(result) == 1
        filters = cluster._ec2.instances.filter.call_args[1]["Filters"]
        state_filter = next(f for f in filters if f["Name"] == "instance-state-name")
        assert "running" in state_filter["Values"]
        assert "stopped" not in state_filter["Values"]

    def test_get_stopped_instances(self, cluster):
        instances = [make_instance("web-01", state="stopped")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_stopped_instances()
        assert len(result) == 1
        filters = cluster._ec2.instances.filter.call_args[1]["Filters"]
        state_filter = next(f for f in filters if f["Name"] == "instance-state-name")
        assert state_filter["Values"] == ["stopped"]

    def test_get_deployed_clusters(self, cluster):
        instances = [make_instance("web-01", cluster="test1")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_deployed_clusters()
        assert "test1" in result
        assert len(result["test1"]) == 1

    def test_get_deployed_clusters_empty(self, cluster):
        self._setup_ec2_filter(cluster, [])
        result = cluster.get_deployed_clusters()
        assert result == {"test1": []}

    def test_get_deployed_cluster_names(self, cluster):
        instances = [make_instance("web-01", cluster="test1")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_deployed_cluster_names()
        assert result == {"test1"}

    def test_get_running_clusters(self, cluster):
        instances = [make_instance("web-01", cluster="test1")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_running_clusters()
        assert "test1" in result
        assert len(result["test1"]) == 1

    def test_get_stopped_clusters(self, cluster):
        instances = [make_instance("db-01", cluster="test1", state="stopped")]
        self._setup_ec2_filter(cluster, instances)
        result = cluster.get_stopped_clusters()
        assert "test1" in result
        assert len(result["test1"]) == 1

    def test_get_instances_empty(self, cluster):
        self._setup_ec2_filter(cluster, [])
        assert cluster.get_instances() == []

    def test_get_running_instances_empty(self, cluster):
        self._setup_ec2_filter(cluster, [])
        assert cluster.get_running_instances() == []

    def test_get_stopped_instances_empty(self, cluster):
        self._setup_ec2_filter(cluster, [])
        assert cluster.get_stopped_instances() == []
