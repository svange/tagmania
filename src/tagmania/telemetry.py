"""Anonymous usage telemetry for the tagmania CLIs.

Each run of ``cluster-start``, ``cluster-stop`` or ``cluster-snap`` sends one
small OTLP/HTTP JSON export to ``https://telemetry.augmentingintegrations.com``
when it ends. It uses no AWS credentials and never changes what a command
does: a failed or slow export is ignored after a two-second timeout. Using
``ClusterSet`` as a library sends nothing; only the CLIs record a run.

What is sent, and nothing else:

- ``tagmania.cli.invocations``: one count per run, with the command, the
  action, whether ``--target`` and ``--profile`` were given (true or false
  only), the outcome (``success``, ``noop``, ``aborted``, ``error``) and, on
  an error, its class (``error.type``, ``aws.error.code``, ``aws.operation``)
  from fixed lists.
- ``tagmania.operation.duration``: the seconds each operation took
  (``start_instances``, ``backup``, ``restore``, ...).
- ``tagmania.resources.processed``: how many instances, volumes and snapshots
  an operation acted on.
- ``tagmania.safety_limit.hit``: a query reached the 150-item safety limit.

The scrub contract: every value sent comes from a fixed list in this module,
or is a count, a duration or a true/false flag. Cluster names, profile names,
the ``--target`` pattern, snapshot names, AWS resource ids (``i-``, ``vol-``,
``snap-``, ``subnet-``, ``vpc-``), account ids and ARNs are never sent: a value
outside a list becomes ``other`` (AWS error codes and operations) or is left
out, and a value that looks like an id, an account id or an ARN is left out
before that. The server applies the same lists and drops anything else.

Turn it off with ``TAGMANIA_TELEMETRY=off`` (or ``0``, ``false``, ``no``), or
with ``DO_NOT_TRACK=1``.
"""

from __future__ import annotations

import contextvars
import http.client
import json
import os
import re
import time
import urllib.parse
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from tagmania import __version__

ENDPOINT = "https://telemetry.augmentingintegrations.com/v1/metrics"
"""The ingest's metrics route."""

OPT_OUT_VARIABLE = "TAGMANIA_TELEMETRY"
"""Set to off, 0, false or no to send nothing."""

TIMEOUT_SECONDS = 2.0
SERVICE_NAME = "tagmania"
OTHER = "other"

COMMANDS = ("cluster-start", "cluster-stop", "cluster-snap")
ACTIONS = ("start", "stop", "backup", "restore", "delete", "list")
OUTCOMES = ("success", "noop", "aborted", "error")
ERROR_TYPES = ("ClientError", "WaiterError", "NoCredentialsError", "InvalidTargetRegex")
RESOURCE_TYPES = ("instance", "volume", "snapshot")

# Closed lists; any other value is sent as "other". They are the ingest's
# allowlist (ai-agency infra/telemetry/allowlist.ts).
AWS_ERROR_CODES = (
    "AccessDenied",
    "AccessDeniedException",
    "AuthFailure",
    "DryRunOperation",
    "ExpiredToken",
    "ExpiredTokenException",
    "IncorrectInstanceState",
    "IncorrectState",
    "InsufficientInstanceCapacity",
    "InvalidClientTokenId",
    "InvalidInstanceID.NotFound",
    "InvalidParameterValue",
    "InvalidSnapshot.NotFound",
    "InvalidVolume.NotFound",
    "RequestExpired",
    "RequestLimitExceeded",
    "SnapshotLimitExceeded",
    "Throttling",
    "ThrottlingException",
    "UnauthorizedOperation",
    "VolumeInUse",
    "VolumeLimitExceeded",
    "WaiterMaxAttemptsExceeded",
)
AWS_OPERATIONS = (
    "AttachVolume",
    "CreateSnapshot",
    "CreateSnapshots",
    "CreateTags",
    "CreateVolume",
    "DeleteSnapshot",
    "DeleteVolume",
    "DescribeInstances",
    "DescribeSnapshots",
    "DescribeTags",
    "DescribeVolumes",
    "DetachVolume",
    "StartInstances",
    "StopInstances",
)
OPERATIONS = (
    "start_instances",
    "stop_instances",
    "backup",
    "restore",
    "restore_targeted",
    "create_snapshots",
    "delete_snapshots",
    "create_volumes",
    "delete_volumes",
    "detach_volumes",
    "attach_volumes",
)
# Labels the code times that report as one of the operations above.
_LABEL_TO_OPERATION = {
    "create_volumes_targeted": "create_volumes",
    "delete_volumes_targeted": "delete_volumes",
    "detach_volumes_targeted": "detach_volumes",
    "attach_volumes_targeted": "attach_volumes",
    "start_instances_targeted": "start_instances",
    "stop_instances_targeted": "stop_instances",
}

# Histogram bucket bounds, seconds.
DURATION_BOUNDS = (1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0)

_SCRUB_PATTERNS = (
    re.compile(
        r"(?:^|[^a-z0-9])(?:i|vol|snap|subnet|vpc|sg|ami|eni)-[0-9a-f]{8}(?:[0-9a-f]{9})?(?![0-9a-f])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<!\d)\d{12}(?!\d)"),
    re.compile(r"arn:aws[a-z-]*:", re.IGNORECASE),
)


def must_scrub(value: str) -> bool:
    """True when the value carries an AWS resource id, an account id or an ARN."""
    return any(pattern.search(value) for pattern in _SCRUB_PATTERNS)


def enabled(environ: Mapping[str, str] | None = None) -> bool:
    """False when the user opted out with TAGMANIA_TELEMETRY or DO_NOT_TRACK."""
    env = os.environ if environ is None else environ
    if env.get(OPT_OUT_VARIABLE, "").strip().lower() in ("off", "0", "false", "no"):
        return False
    return env.get("DO_NOT_TRACK", "").strip().lower() in ("", "0", "false")


def closed(value: str | None, allowed: tuple[str, ...], open_to_other: bool = False) -> str | None:
    """The value if it is on the list; "other" for an open key; otherwise None.

    A value that looks like an id, an account id or an ARN is None even on an
    open key: it is left out, never turned into "other".
    """
    if value is None or must_scrub(value):
        return None
    if value in allowed:
        return value
    return OTHER if open_to_other else None


def operation_name(label: str) -> str | None:
    """The operation a timing label reports as, or None if it is not one."""
    name = _LABEL_TO_OPERATION.get(label, label)
    return name if name in OPERATIONS else None


Attributes = Mapping[str, str | bool | None]


@dataclass
class Run:
    """What one CLI run reports. The CLI sets the outcome as it decides it."""

    command: str
    action: str | None = None
    targeted: bool = False
    used_profile: bool = False
    outcome: str = "success"
    error_type: str | None = None
    aws_error_code: str | None = None
    aws_operation: str | None = None
    durations: dict[tuple[str, str], list[float]] = field(default_factory=dict)
    resources: dict[tuple[str, str], int] = field(default_factory=dict)
    safety_hits: dict[str, int] = field(default_factory=dict)
    operation_stack: list[str] = field(default_factory=list)

    def fail(self, error_type: str) -> None:
        """Mark the run as an error of one of the listed classes."""
        self.outcome = "error"
        self.error_type = closed(error_type, ERROR_TYPES)

    def record_error(self, error: BaseException) -> None:
        """Classify an exception into the closed error attributes."""
        self.fail(type(error).__name__)
        code: str | None = None
        response = getattr(error, "response", None)
        if isinstance(response, dict):
            raw = (response.get("Error") or {}).get("Code")
            code = raw if isinstance(raw, str) else None
        if code is None and type(error).__name__ == "WaiterError":
            code = "WaiterMaxAttemptsExceeded"
        if code is not None:
            self.aws_error_code = closed(code, AWS_ERROR_CODES, open_to_other=True)
        operation = getattr(error, "operation_name", None)
        if isinstance(operation, str):
            self.aws_operation = closed(operation, AWS_OPERATIONS, open_to_other=True)

    def to_otlp(self, now_ns: int | None = None) -> dict[str, Any]:
        """The run as an OTLP ExportMetricsServiceRequest, JSON form."""
        now = str(time.time_ns() if now_ns is None else now_ns)
        invocation = {
            "cli.command": closed(self.command, COMMANDS),
            "cli.action": closed(self.action, ACTIONS),
            "cli.targeted": self.targeted,
            "cli.used_profile": self.used_profile,
            "outcome": closed(self.outcome, OUTCOMES),
            "error.type": self.error_type,
            "aws.error.code": self.aws_error_code,
            "aws.operation": self.aws_operation,
        }
        metrics: list[dict[str, Any]] = [
            _sum("tagmania.cli.invocations", [_point(now, 1, invocation)])
        ]
        histogram = [
            _histogram_point(now, values, {"operation.name": op, "outcome": outcome})
            for (op, outcome), values in sorted(self.durations.items())
        ]
        if histogram:
            metrics.append(
                {
                    "name": "tagmania.operation.duration",
                    "unit": "s",
                    "histogram": {"aggregationTemporality": 2, "dataPoints": histogram},
                }
            )
        processed = [
            _point(now, n, {"resource.type": resource, "operation.name": op})
            for (resource, op), n in sorted(self.resources.items())
        ]
        if processed:
            metrics.append(_sum("tagmania.resources.processed", processed))
        hits = [
            _point(now, n, {"resource.type": resource})
            for resource, n in sorted(self.safety_hits.items())
        ]
        if hits:
            metrics.append(_sum("tagmania.safety_limit.hit", hits))
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": _attributes(
                            {"service.name": SERVICE_NAME, "service.version": __version__}
                        )
                    },
                    "scopeMetrics": [{"scope": {"name": "tagmania"}, "metrics": metrics}],
                }
            ]
        }


def _attributes(values: Attributes) -> list[dict[str, Any]]:
    """OTLP key-values; a missing value, or one that must be scrubbed, is left out."""
    out: list[dict[str, Any]] = []
    for key, value in values.items():
        if isinstance(value, bool):
            out.append({"key": key, "value": {"boolValue": value}})
        elif value is not None and not must_scrub(value):
            out.append({"key": key, "value": {"stringValue": value}})
    return out


def _point(now: str, value: int, attributes: Attributes) -> dict[str, Any]:
    return {"asInt": str(value), "timeUnixNano": now, "attributes": _attributes(attributes)}


def _histogram_point(now: str, values: list[float], attributes: Attributes) -> dict[str, Any]:
    counts = [0] * (len(DURATION_BOUNDS) + 1)
    for value in values:
        counts[sum(1 for bound in DURATION_BOUNDS if value > bound)] += 1
    return {
        "timeUnixNano": now,
        "count": str(len(values)),
        "sum": sum(values),
        "min": min(values),
        "max": max(values),
        "explicitBounds": list(DURATION_BOUNDS),
        "bucketCounts": [str(c) for c in counts],
        "attributes": _attributes(attributes),
    }


def _sum(name: str, points: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "unit": "1",
        "sum": {"aggregationTemporality": 2, "isMonotonic": True, "dataPoints": points},
    }


_current: contextvars.ContextVar[Run | None] = contextvars.ContextVar(
    "tagmania_telemetry_run", default=None
)


def current_run() -> Run | None:
    """The CLI run being recorded, or None (library use records nothing)."""
    return _current.get()


@contextmanager
def measure(label: str) -> Iterator[None]:
    """Time the block as an operation, and count the resources it queries.

    Does nothing outside a CLI run, or for a label that is not an operation.
    """
    run = _current.get()
    name = operation_name(label)
    if run is None or name is None:
        yield
        return
    run.operation_stack.append(name)
    start = time.perf_counter()
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        run.operation_stack.pop()
        key = (name, "error" if failed else "success")
        run.durations.setdefault(key, []).append(time.perf_counter() - start)


def note_query(resource_type: str, count: int, max_items: int) -> None:
    """Count a query that returned the safety limit's maximum (results may be cut)."""
    run = _current.get()
    if run is None or resource_type not in RESOURCE_TYPES or count < max_items:
        return
    run.safety_hits[resource_type] = run.safety_hits.get(resource_type, 0) + 1


def note_processed(resource_type: str, count: int) -> None:
    """Add resources the innermost running operation acted on."""
    run = _current.get()
    if run is None or resource_type not in RESOURCE_TYPES or not run.operation_stack or count <= 0:
        return
    key = (resource_type, run.operation_stack[-1])
    run.resources[key] = run.resources.get(key, 0) + count


def send(payload: dict[str, Any], endpoint: str = ENDPOINT) -> bool:
    """POST the payload; True on a 2xx answer. Never raises."""
    try:
        url = urllib.parse.urlsplit(endpoint)
        if url.scheme != "https" or not url.hostname:
            return False
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        connection = http.client.HTTPSConnection(url.hostname, url.port, timeout=TIMEOUT_SECONDS)
        try:
            connection.request(
                "POST",
                url.path or "/",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"tagmania/{__version__}",
                },
            )
            response = connection.getresponse()
            response.read()
            return 200 <= response.status < 300
        finally:
            connection.close()
    except Exception:
        # Telemetry must never break a command, or slow it past the timeout.
        return False


@contextmanager
def cli_run(
    command: str,
    action: str | None = None,
    *,
    targeted: bool = False,
    used_profile: bool = False,
    environ: Mapping[str, str] | None = None,
) -> Iterator[Run]:
    """Record one CLI run and send it when it ends, unless the user opted out.

    An exception is classified and re-raised; Ctrl-C counts as aborted.
    """
    run = Run(command=command, action=action, targeted=targeted, used_profile=used_profile)
    token = _current.set(run)
    try:
        yield run
    except KeyboardInterrupt:
        run.outcome = "aborted"
        raise
    except Exception as error:
        run.record_error(error)
        raise
    finally:
        _current.reset(token)
        if enabled(environ):
            send(run.to_otlp())
