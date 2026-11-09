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


class TestClusterSetLifecycleAndResources:
    def test_start_instances_when_stopped_exist(self, cluster):
        inst = make_instance("web-01", state="stopped")
        inst.start = MagicMock()
        cluster.get_stopped_instances = MagicMock(return_value=[inst])
        waiter = MagicMock()
        cluster._ec2_client.get_waiter.return_value = waiter

        cluster.start_instances()

        inst.start.assert_called_once()
        cluster._ec2_client.get_waiter.assert_called_once_with("instance_running")
        waiter.wait.assert_called_once()

    def test_start_instances_when_none_stopped(self, cluster, capsys):
        cluster.get_stopped_instances = MagicMock(return_value=[])
        cluster.start_instances()
        assert "No instances to start." in capsys.readouterr().out

    def test_stop_instances_when_running_exist(self, cluster):
        inst = make_instance("web-01", state="running")
        inst.stop = MagicMock()
        cluster.get_running_instances = MagicMock(return_value=[inst])
        waiter = MagicMock()
        cluster._ec2_client.get_waiter.return_value = waiter

        cluster.stop_instances()

        inst.stop.assert_called_once()
        cluster._ec2_client.get_waiter.assert_called_once_with("instance_stopped")
        waiter.wait.assert_called_once()

    def test_stop_instances_when_none_running(self, cluster, capsys):
        cluster.get_running_instances = MagicMock(return_value=[])
        cluster.stop_instances()
        assert "No instances to stop." in capsys.readouterr().out

    def test_detach_and_delete_volumes_targeted(self, cluster):
        vol = make_volume("vol-1", tags=[{"Key": "Instance", "Value": "web-01"}])
        vol.attachments = [{"Device": "/dev/xvda"}]
        vol.detach_from_instance = MagicMock()
        vol.delete = MagicMock()

        inst = make_instance("web-01")
        inst.volumes = MagicMock()
        inst.volumes.all.return_value = [vol]

        cluster.get_instances = MagicMock(return_value=[inst])
        cluster.get_volumes = MagicMock(return_value=[vol])
        cluster.wait_for_volumes = MagicMock()

        cluster.detach_volumes_targeted("web-.*")
        vol.detach_from_instance.assert_called_once_with(Device="/dev/xvda", InstanceId="i-web-01")
        cluster.wait_for_volumes.assert_called_with(["vol-1"], "volume_available")

        cluster.delete_volumes_targeted("web-.*")
        vol.delete.assert_called_once()
        cluster.wait_for_volumes.assert_called_with(["vol-1"], "volume_deleted")

    def test_create_and_attach_volumes_targeted(self, cluster):
        snap = SimpleNamespace(
            id="snap-1",
            tags=[
                {"Key": "Device", "Value": "/dev/xvda"},
                {"Key": "Instance", "Value": "web-01"},
            ],
        )
        inst = make_instance("web-01")
        inst.placement = {"AvailabilityZone": "us-east-1a"}

        created_vol = make_volume(
            "vol-new",
            tags=[
                {"Key": "Device", "Value": "/dev/xvda"},
                {"Key": "Instance", "Value": "web-01"},
            ],
        )
        created_vol.attach_to_instance = MagicMock()

        cluster.get_snapshots = MagicMock(return_value=[snap])
        cluster.get_instances = MagicMock(return_value=[inst])
        cluster.get_restored_volumes = MagicMock(return_value=[created_vol])
        cluster._ec2.create_volume.return_value = created_vol
        cluster.wait_for_volumes = MagicMock()
        cluster._wait_for_volume_tags = MagicMock()

        cluster.create_volumes_targeted("daily", "web-.*")
        cluster._ec2.create_volume.assert_called_once()
        cluster.wait_for_volumes.assert_called_with(["vol-new"], "volume_available")
        cluster._wait_for_volume_tags.assert_called_once_with(["vol-new"])

        cluster.attach_volumes_targeted("daily", "web-.*")
        created_vol.attach_to_instance.assert_called_once_with(
            Device="/dev/xvda", InstanceId="i-web-01"
        )
        cluster.wait_for_volumes.assert_called_with(["vol-new"], "volume_in_use")

    def test_tag_and_untag_resources(self, cluster):
        inst = make_instance("web-01")
        inst.create_tags = MagicMock()
        vol = make_volume("vol-1")
        vol.create_tags = MagicMock()
        snap = SimpleNamespace(id="snap-1", create_tags=MagicMock())
        subnet = SimpleNamespace(id="subnet-1", create_tags=MagicMock())

        cluster.get_instances = MagicMock(return_value=[inst])
        cluster.get_volumes = MagicMock(return_value=[vol])
        cluster.get_snapshots = MagicMock(return_value=[snap])
        cluster.get_subnet = MagicMock(return_value=subnet)

        tags = [{"Key": "Env", "Value": "prod"}]
        cluster.tag_instances(tags)
        cluster.tag_volumes(tags)
        cluster.tag_snapshots(tags)
        cluster.tag_subnet(tags)

        inst.create_tags.assert_called_once_with(Tags=tags)
        vol.create_tags.assert_called_once_with(Tags=tags)
        snap.create_tags.assert_called_once_with(Tags=tags)
        subnet.create_tags.assert_called_once_with(Tags=tags)

        untag_keys = [{"Key": "Env"}]
        cluster.untag_instances(untag_keys)
        cluster.untag_volumes(untag_keys)
        cluster.untag_snapshots(untag_keys)
        cluster.untag_subnet(untag_keys)
        assert cluster._ec2_client.delete_tags.call_count == 4

    def test_volume_and_snapshot_queries(self, cluster):
        vol_collection = MagicMock()
        vol_collection.limit.return_value = [make_volume("vol-1")]
        vol_collection.__iter__ = lambda self: iter([make_volume("vol-1")])
        cluster._ec2.volumes.filter.return_value = vol_collection

        snap_collection = MagicMock()
        snap_collection.limit.return_value = [SimpleNamespace(id="snap-1")]
        cluster._ec2.snapshots.filter.return_value = snap_collection

        subnet_collection = MagicMock()
        subnet_collection.limit.return_value = [SimpleNamespace(id="subnet-1")]
        cluster._ec2.subnets.filter.return_value = subnet_collection

        assert len(cluster.get_volumes()) == 1
        assert len(cluster.get_kubernetes_volumes()) == 1
        assert len(cluster.get_restored_volumes("daily")) == 1
        assert len(cluster.get_snapshots("daily")) == 1
        assert cluster.get_subnet().id == "subnet-1"

    def test_full_volume_and_snapshot_operations(self, cluster):
        vol = make_volume(
            "vol-1",
            tags=[
                {"Key": "Device", "Value": "/dev/xvda"},
                {"Key": "Instance", "Value": "web-01"},
            ],
        )
        vol.attachments = [{"Device": "/dev/xvda"}]
        vol.detach_from_instance = MagicMock()
        vol.attach_to_instance = MagicMock()
        vol.delete = MagicMock()
        vol.create_snapshot = MagicMock(return_value=SimpleNamespace(id="snap-new"))

        inst = make_instance("web-01")
        inst.placement = {"AvailabilityZone": "us-east-1a"}
        inst.volumes = MagicMock()
        inst.volumes.all.return_value = [vol]

        snap = SimpleNamespace(
            id="snap-1",
            tags=[
                {"Key": "Device", "Value": "/dev/xvda"},
                {"Key": "Instance", "Value": "web-01"},
            ],
            delete=MagicMock(),
        )

        cluster.get_instances = MagicMock(return_value=[inst])
        cluster.get_volumes = MagicMock(return_value=[vol])
        cluster.get_kubernetes_volumes = MagicMock(return_value=[vol])
        cluster.get_restored_volumes = MagicMock(return_value=[vol])
        cluster.get_snapshots = MagicMock(return_value=[snap])
        cluster._ec2.create_volume.return_value = vol
        cluster.wait_for_volumes = MagicMock()
        cluster._wait_for_volume_tags = MagicMock()
        cluster._ec2_client.get_waiter.return_value = MagicMock()

        cluster.detach_volumes()
        vol.detach_from_instance.assert_called_once()

        cluster.delete_volumes()
        cluster.delete_kubernetes_volumes()
        assert vol.delete.call_count == 2

        cluster.create_volumes("daily")
        cluster._ec2.create_volume.assert_called_once()

        cluster.attach_volumes("daily")
        vol.attach_to_instance.assert_called_once()

        with patch("tagmania.iac_tools.clusterset.time.sleep"):
            cluster.create_snapshots("daily")
            vol.create_snapshot.assert_called_once()
            snap.delete.assert_called_once()

    def test_targeted_start_and_stop(self, cluster):
        inst_run = make_instance("web-01", state="running")
        inst_run.stop = MagicMock()
        inst_stop = make_instance("web-02", state="stopped")
        inst_stop.start = MagicMock()

        cluster.get_running_instances = MagicMock(return_value=[inst_run])
        cluster.get_stopped_instances = MagicMock(return_value=[inst_stop])
        cluster._ec2_client.get_waiter.return_value = MagicMock()

        cluster.stop_instances_targeted("web-.*")
        inst_run.stop.assert_called_once()

        cluster.start_instances_targeted("web-.*")
        inst_stop.start.assert_called_once()
