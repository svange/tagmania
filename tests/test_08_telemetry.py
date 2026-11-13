import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, WaiterError

from tagmania import telemetry
from tagmania.iac_tools.clusterset import ClusterSet


def attrs(point):
    out = {}
    for a in point["attributes"]:
        value = a["value"]
        out[a["key"]] = value.get("stringValue", value.get("boolValue"))
    return out


def metrics(payload):
    scope = payload["resourceMetrics"][0]["scopeMetrics"][0]
    return {m["name"]: m for m in scope["metrics"]}


def invocation(payload):
    point = metrics(payload)["tagmania.cli.invocations"]["sum"]["dataPoints"][0]
    assert point["asInt"] == "1"
    return attrs(point)


@pytest.fixture
def sent():
    """Every payload cli_run would send, with telemetry switched on."""
    payloads = []
    with patch.object(telemetry, "send", side_effect=lambda p: payloads.append(p) or True):
        yield payloads


ON = {}


class TestOptOut:
    @pytest.mark.parametrize("value", ["off", "0", "false", "no", "OFF", " No "])
    def test_tagmania_telemetry_turns_it_off(self, value):
        assert not telemetry.enabled({"TAGMANIA_TELEMETRY": value})

    def test_do_not_track_turns_it_off(self):
        assert not telemetry.enabled({"DO_NOT_TRACK": "1"})
        assert telemetry.enabled({"DO_NOT_TRACK": "0"})

    def test_on_by_default(self):
        assert telemetry.enabled({})
        assert telemetry.enabled({"TAGMANIA_TELEMETRY": "on"})

    def test_an_opted_out_run_sends_nothing(self):
        with patch.object(telemetry, "send") as send:
            with telemetry.cli_run("cluster-start", "start", environ={"TAGMANIA_TELEMETRY": "off"}):
                pass
        send.assert_not_called()

    def test_the_test_suite_runs_opted_out(self):
        assert not telemetry.enabled()


class TestScrub:
    @pytest.mark.parametrize(
        "value",
        [
            "i-0123456789abcdef0",
            "i-01234567",
            "vol-0abc1234",
            "snap-0123456789abcdef0",
            "subnet-0a1b2c3d",
            "vpc-0a1b2c3d4e5f60718",
            "prod/i-0123456789abcdef0",
            "123456789012",
            "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc",
            "arn:aws-us-gov:iam::role/x",
        ],
    )
    def test_ids_account_ids_and_arns_are_scrubbed(self, value):
        assert telemetry.must_scrub(value)
        assert telemetry.closed(value, (value,), open_to_other=True) is None

    @pytest.mark.parametrize("value", ["cluster-snap", "ClientError", "1234567890123", "volume"])
    def test_plain_values_are_not(self, value):
        assert not telemetry.must_scrub(value)

    def test_unknown_values_become_other_only_on_an_open_key(self):
        assert telemetry.closed("Throttling", telemetry.AWS_ERROR_CODES, True) == "Throttling"
        assert telemetry.closed("SomethingNew", telemetry.AWS_ERROR_CODES, True) == "other"
        assert telemetry.closed("my-cluster", telemetry.COMMANDS) is None

    def test_an_id_in_an_attribute_is_left_out_of_the_export(self):
        run = telemetry.Run(command="cluster-start", action="start")
        run.aws_operation = "i-0123456789abcdef0"  # never set this way; the export still drops it
        payload = run.to_otlp()
        assert "aws.operation" not in invocation(payload)
        assert "i-0123456789abcdef0" not in json.dumps(payload)


class TestErrors:
    def test_client_error_is_classified_with_closed_code_and_operation(self, sent):
        error = ClientError(
            {"Error": {"Code": "UnauthorizedOperation", "Message": "acct 123456789012"}},
            "StopInstances",
        )
        with pytest.raises(ClientError):
            with telemetry.cli_run("cluster-stop", "stop", environ=ON):
                raise error
        got = invocation(sent[0])
        assert got["outcome"] == "error"
        assert got["error.type"] == "ClientError"
        assert got["aws.error.code"] == "UnauthorizedOperation"
        assert got["aws.operation"] == "StopInstances"
        assert "123456789012" not in json.dumps(sent[0])

    def test_unknown_code_and_operation_become_other(self, sent):
        error = ClientError({"Error": {"Code": "Brand.New"}}, "ModifyThing")
        with pytest.raises(ClientError):
            with telemetry.cli_run("cluster-stop", "stop", environ=ON):
                raise error
        got = invocation(sent[0])
        assert got["aws.error.code"] == "other"
        assert got["aws.operation"] == "other"

    def test_waiter_error(self, sent):
        error = WaiterError("instance_stopped", "Max attempts exceeded", {})
        with pytest.raises(WaiterError):
            with telemetry.cli_run("cluster-stop", "stop", environ=ON):
                raise error
        got = invocation(sent[0])
        assert got["error.type"] == "WaiterError"
        assert got["aws.error.code"] == "WaiterMaxAttemptsExceeded"

    def test_no_credentials(self, sent):
        with pytest.raises(NoCredentialsError):
            with telemetry.cli_run("cluster-start", "start", environ=ON):
                raise NoCredentialsError()
        got = invocation(sent[0])
        assert got["error.type"] == "NoCredentialsError"
        assert "aws.error.code" not in got

    def test_an_unlisted_exception_keeps_outcome_but_no_class(self, sent):
        with pytest.raises(RuntimeError):
            with telemetry.cli_run("cluster-start", "start", environ=ON):
                raise RuntimeError("cluster my-secret-cluster")
        got = invocation(sent[0])
        assert got["outcome"] == "error"
        assert "error.type" not in got
        assert "my-secret-cluster" not in json.dumps(sent[0])

    def test_ctrl_c_is_aborted(self, sent):
        with pytest.raises(KeyboardInterrupt):
            with telemetry.cli_run("cluster-snap", "backup", environ=ON):
                raise KeyboardInterrupt
        assert invocation(sent[0])["outcome"] == "aborted"


class TestExport:
    def test_payload_shape(self, sent):
        with telemetry.cli_run("cluster-snap", "restore", targeted=True, environ=ON) as run:
            with telemetry.measure("restore_targeted"):
                telemetry.note_processed("volume", 3)
                with telemetry.measure("create_volumes_targeted"):
                    telemetry.note_processed("volume", 2)
            telemetry.note_query("snapshot", 150, 150)
            telemetry.note_query("instance", 4, 150)
            assert telemetry.current_run() is run
        assert telemetry.current_run() is None
        payload = sent[0]
        resource = attrs(payload["resourceMetrics"][0]["resource"])
        assert resource == {"service.name": "tagmania", "service.version": telemetry.__version__}
        got = invocation(payload)
        assert got == {
            "cli.command": "cluster-snap",
            "cli.action": "restore",
            "cli.targeted": True,
            "cli.used_profile": False,
            "outcome": "success",
        }
        m = metrics(payload)
        durations = m["tagmania.operation.duration"]["histogram"]["dataPoints"]
        assert sorted(attrs(p)["operation.name"] for p in durations) == [
            "create_volumes",
            "restore_targeted",
        ]
        for p in durations:
            assert attrs(p)["outcome"] == "success"
            assert p["count"] == "1"
            assert sum(int(c) for c in p["bucketCounts"]) == 1
            assert len(p["bucketCounts"]) == len(p["explicitBounds"]) + 1
        processed = {
            (attrs(p)["resource.type"], attrs(p)["operation.name"]): p["asInt"]
            for p in m["tagmania.resources.processed"]["sum"]["dataPoints"]
        }
        assert processed == {("volume", "restore_targeted"): "3", ("volume", "create_volumes"): "2"}
        hits = m["tagmania.safety_limit.hit"]["sum"]["dataPoints"]
        assert [(attrs(p), p["asInt"]) for p in hits] == [({"resource.type": "snapshot"}, "1")]

    def test_a_failed_operation_is_timed_as_error(self, sent):
        with pytest.raises(ValueError):
            with telemetry.cli_run("cluster-start", "start", environ=ON):
                with telemetry.measure("start_instances"):
                    raise ValueError
        p = metrics(sent[0])["tagmania.operation.duration"]["histogram"]["dataPoints"][0]
        assert attrs(p) == {"operation.name": "start_instances", "outcome": "error"}

    def test_only_the_invocation_when_nothing_ran(self, sent):
        with telemetry.cli_run("cluster-snap", "list", environ=ON):
            pass
        assert list(metrics(sent[0])) == ["tagmania.cli.invocations"]

    def test_histogram_buckets(self):
        run = telemetry.Run(command="cluster-snap", action="backup")
        run.durations[("backup", "success")] = [0.5, 1.0, 7200.0]
        p = metrics(run.to_otlp(now_ns=5))["tagmania.operation.duration"]["histogram"][
            "dataPoints"
        ][0]
        assert p["timeUnixNano"] == "5"
        assert p["bucketCounts"][0] == "2"  # (-inf, 1]
        assert p["bucketCounts"][-1] == "1"  # (3600, +inf)
        assert (p["min"], p["max"]) == (0.5, 7200.0)


class TestLibraryUseRecordsNothing:
    def test_no_run_no_state(self):
        assert telemetry.current_run() is None
        with telemetry.measure("backup"):
            telemetry.note_processed("volume", 5)
            telemetry.note_query("volume", 150, 150)
        assert telemetry.current_run() is None

    def test_unknown_labels_and_types_are_ignored(self, sent):
        with telemetry.cli_run("cluster-start", "start", environ=ON) as run:
            with telemetry.measure("my_custom_step"):
                telemetry.note_processed("volume", 1)
            telemetry.note_processed("bucket", 1)
            telemetry.note_query("bucket", 500, 150)
        assert run.durations == {} and run.resources == {} and run.safety_hits == {}


class TestSend:
    def test_refuses_anything_but_https(self):
        assert telemetry.send({}, "http://telemetry.example.com/v1/metrics") is False
        assert telemetry.send({}, "not a url") is False

    def test_posts_json_and_reports_2xx(self):
        connection = MagicMock()
        connection.getresponse.return_value = SimpleNamespace(status=200, read=lambda: b"{}")
        with patch("http.client.HTTPSConnection", return_value=connection) as cls:
            assert telemetry.send({"a": 1}) is True
        cls.assert_called_once_with(
            "telemetry.augmentingintegrations.com", None, timeout=telemetry.TIMEOUT_SECONDS
        )
        method, path = connection.request.call_args.args
        assert (method, path) == ("POST", "/v1/metrics")
        kwargs = connection.request.call_args.kwargs
        assert json.loads(kwargs["body"]) == {"a": 1}
        assert kwargs["headers"]["Content-Type"] == "application/json"
        connection.close.assert_called_once()

    def test_a_non_2xx_is_false(self):
        connection = MagicMock()
        connection.getresponse.return_value = SimpleNamespace(status=429, read=lambda: b"")
        with patch("http.client.HTTPSConnection", return_value=connection):
            assert telemetry.send({}) is False

    def test_never_raises(self):
        with patch("http.client.HTTPSConnection", side_effect=OSError("offline")):
            assert telemetry.send({}) is False


class TestCliOutcomes:
    """The three CLIs report their own outcome (success, noop, aborted, error)."""

    def run_main(self, module, argv, sent, inputs="yes"):
        with (
            patch.object(telemetry, "enabled", return_value=True),
            patch("sys.argv", argv),
            patch("builtins.input", return_value=inputs),
        ):
            module.main()
        return invocation(sent[0])

    @patch("tagmania.start_cluster.ClusterSet")
    def test_cluster_start(self, mock_cs, sent):
        from tagmania import start_cluster

        got = self.run_main(
            start_cluster, ["cluster-start", "-p", "acme-admin", "web-prod-7"], sent
        )
        assert got["cli.command"] == "cluster-start"
        assert got["cli.action"] == "start"
        assert got["cli.used_profile"] is True
        assert got["outcome"] == "success"
        assert "acme-admin" not in json.dumps(sent[0])
        assert "web-prod-7" not in json.dumps(sent[0])

    @patch("tagmania.stop_cluster.ClusterSet")
    def test_cluster_stop_error(self, mock_cs, sent):
        from tagmania import stop_cluster

        mock_cs.return_value.stop_instances.side_effect = NoCredentialsError()
        with pytest.raises(NoCredentialsError):
            self.run_main(stop_cluster, ["cluster-stop", "c1"], sent)
        got = invocation(sent[0])
        assert (got["cli.action"], got["outcome"], got["error.type"]) == (
            "stop",
            "error",
            "NoCredentialsError",
        )

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_backup_declined_is_aborted(self, mock_cs, sent):
        from tagmania import snapshot_manager

        got = self.run_main(snapshot_manager, ["snap", "--backup", "c1"], sent, inputs="no")
        assert (got["cli.action"], got["outcome"]) == ("backup", "aborted")

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_backup_with_no_instances_is_noop(self, mock_cs, sent):
        from tagmania import snapshot_manager

        mock_cs.return_value.get_instances.return_value = []
        got = self.run_main(snapshot_manager, ["snap", "--backup", "c1"], sent)
        assert got["outcome"] == "noop"

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_delete_with_no_snapshots_is_noop(self, mock_cs, sent):
        from tagmania import snapshot_manager

        mock_cs.return_value.get_snapshots.return_value = []
        got = self.run_main(snapshot_manager, ["snap", "--delete", "c1"], sent)
        assert (got["cli.action"], got["outcome"]) == ("delete", "noop")

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_invalid_target_regex(self, mock_cs, sent):
        from tagmania import snapshot_manager

        got = self.run_main(snapshot_manager, ["snap", "--restore", "-t", "web-[", "c1"], sent)
        assert got["cli.targeted"] is True
        assert (got["outcome"], got["error.type"]) == ("error", "InvalidTargetRegex")
        assert "web-[" not in json.dumps(sent[0])

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_targeted_restore_with_no_match_is_noop(self, mock_cs, sent):
        from tagmania import snapshot_manager

        mock_cs.return_value._filter_instances_by_name_regex.return_value = []
        got = self.run_main(snapshot_manager, ["snap", "--restore", "-t", "web", "c1"], sent)
        assert got["outcome"] == "noop"

    @patch("tagmania.snapshot_manager.ClusterSet")
    def test_list_is_success(self, mock_cs, sent):
        from tagmania import snapshot_manager

        mock_cs.return_value.get_snapshots.return_value = []
        got = self.run_main(snapshot_manager, ["snap", "--list", "c1"], sent)
        assert (got["cli.action"], got["cli.targeted"], got["outcome"]) == (
            "list",
            False,
            "success",
        )


class TestClusterSetReports:
    """ClusterSet records what it acted on and when it hit the safety limit."""

    def make_cluster(self):
        with patch("boto3.Session"):
            return ClusterSet("test1")

    def test_start_instances_counts_and_times(self, sent):
        cluster = self.make_cluster()
        instances = [SimpleNamespace(id=f"i-{n}", tags=[], start=MagicMock()) for n in range(3)]
        with (
            patch.object(cluster, "get_stopped_instances", return_value=instances),
            patch.object(cluster, "_wait_instances_running"),
            telemetry.cli_run("cluster-start", "start", environ=ON),
        ):
            cluster.start_instances()
        m = metrics(sent[0])
        point = m["tagmania.resources.processed"]["sum"]["dataPoints"][0]
        assert attrs(point) == {"resource.type": "instance", "operation.name": "start_instances"}
        assert point["asInt"] == "3"
        duration = m["tagmania.operation.duration"]["histogram"]["dataPoints"][0]
        assert attrs(duration)["operation.name"] == "start_instances"

    def test_safety_limit_hit(self, sent):
        cluster = self.make_cluster()
        collection = MagicMock()
        collection.limit.return_value = [object()] * cluster._MAX_ITEMS
        cluster._ec2.snapshots.filter.return_value = collection
        with telemetry.cli_run("cluster-snap", "list", environ=ON):
            assert len(cluster.get_snapshots("*")) == cluster._MAX_ITEMS
        hits = metrics(sent[0])["tagmania.safety_limit.hit"]["sum"]["dataPoints"]
        assert attrs(hits[0]) == {"resource.type": "snapshot"}

    def test_log_duration_labels_are_operations(self, sent):
        cluster = self.make_cluster()
        with (
            patch.object(cluster, "get_volumes", return_value=[]),
            telemetry.cli_run("cluster-snap", "restore", environ=ON),
        ):
            cluster.delete_volumes()
        duration = metrics(sent[0])["tagmania.operation.duration"]["histogram"]["dataPoints"][0]
        assert attrs(duration)["operation.name"] == "delete_volumes"
