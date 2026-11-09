"""ClusterSet - Core AWS EC2 Cluster Management.

This module provides the ClusterSet class, which is the central component for managing
collections of EC2 instances based on cluster tags. It provides comprehensive
functionality for cluster operations including instance management, volume operations,
and snapshot management with built-in safety features.

The ClusterSet class serves as the foundation for all cluster operations in Tagmania,
offering both simple operations (start/stop instances) and complex operations
(snapshot creation/restoration with targeted instance filtering).

Key Features:
    - Tag-based resource identification and management
    - Instance lifecycle management (start, stop, targeted operations)
    - EBS volume and snapshot management
    - Targeted operations using regex pattern matching
    - Safety limits and automation tracking
    - Comprehensive logging and error handling

Safety Features:
    - Maximum item limits to prevent performance issues
    - Automation key tracking to avoid modifying unmanaged resources
    - Built-in confirmation and validation mechanisms
    - Comprehensive error handling and logging

Example:
    Basic cluster management:

    ```python
    # Create a cluster set
    cluster = ClusterSet('production-web')

    # Start all instances
    cluster.start_instances()

    # Create snapshots
    cluster.create_snapshots('daily-backup')

    # Targeted operations
    cluster.stop_instances_targeted('.*-worker-.*')
    ```
"""

from __future__ import annotations

import datetime
import logging
import re
import time
from typing import Any

import boto3

from .filterset import FilterSet
from .tagset import TagSet
from .timing import log_duration


class ClusterSet:
    """Manages collections of EC2 instances based on cluster tags.

    The ClusterSet class provides comprehensive cluster management functionality
    including instance lifecycle management, volume operations, and snapshot
    management. It uses tag-based resource identification to ensure operations
    only affect intended resources.

    Attributes:
        cluster_names: The name(s) of the cluster(s) being managed
        _MAX_ITEMS: Safety limit for collection operations (150)
        AUTOMATION_KEY: Key used to track managed resources ('SNAPSHOT_MANAGER')

    Note:
        All operations rely on the "Cluster" tag to identify cluster membership.
        The class includes built-in safety features to prevent accidental
        modification of unmanaged resources.
    """

    _ACTIVE_INSTANCE_STATES: list[str] = [
        "pending",
        "running",
        "shutting-down",
        "stopped",
        "stopping",
    ]
    _RUNNING_INSTANCE_STATES: list[str] = ["pending", "running", "stopping"]

    def __init__(self, cluster_names: str | list[str], profile: str | None = None) -> None:
        """Initialize ClusterSet for managing one or more clusters.

        Creates a new ClusterSet instance for managing EC2 instances and related
        resources (volumes, snapshots) for the specified cluster(s). Sets up
        AWS connectivity and initializes safety limits and automation tracking.

        Args:
            cluster_names: The name of a cluster (str) or list of cluster names (list).
                         Must match the "Cluster" tag value on EC2 instances.
            profile: AWS profile name to use for authentication (optional).
                    If None, uses default AWS credentials chain.

        Example:
            ```python
            # Single cluster
            cluster = ClusterSet('production-web')

            # Multiple clusters
            clusters = ClusterSet(['prod-web', 'prod-api'])

            # With specific AWS profile
            cluster = ClusterSet('staging', profile='dev-account')
            ```

        Note:
            The cluster names must exactly match the "Cluster" tag values
            on your EC2 instances for operations to work correctly.
        """
        # Collections operate lazily. Turning a collection into a list can cause
        # performance issues if the collection is very large. Although this is
        # unlikely in our environment, we protect against this by setting an
        # upper bound on the number of items from the collection that can be
        # placed in the list. If the number of items in the collection exceed
        # this upper bound, then those items will not be processed. If this
        # happens, then it can be addressed by increasing this value.
        self._MAX_ITEMS = 150

        # Used to ensure we don't clobber anything we don't make
        self.AUTOMATION_KEY = "SNAPSHOT_MANAGER"

        # cluster_names can be a string 'aws-dev5' or a list ['aws-dev1', 'aws-dev2', etc...]
        self.cluster_names = cluster_names

        # Use this as a starting point to build filters that only return
        # resources associated with this cluster. Use the 'get_cluster_filter'
        # method to get a copy of it rather than doing direct assignment.
        self._cluster_filter: list[dict[str, Any]] = [
            {"Name": "tag:Cluster", "Values": self._cluster_list},
        ]

        # Set up logging
        self._logger = logging.getLogger("tagmania")
        self._logger.setLevel(logging.INFO)
        self._logger.info("Logging initialized.")

        # Create a boto3 session using the specified profile if provided.
        if profile:
            aws_session = boto3.Session(profile_name=profile)
            self._logger.info(f"Using AWS profile: {profile}")
        else:
            aws_session = boto3.Session()

        # Create EC2 resource and client from the session.
        self._ec2 = aws_session.resource("ec2")
        self._ec2_client = aws_session.client("ec2")

    @property
    def _cluster_name_str(self) -> str:
        """Get cluster name as a string (uses first name if multiple)."""
        if isinstance(self.cluster_names, list):
            return self.cluster_names[0]
        return self.cluster_names

    @property
    def _cluster_list(self) -> list[str]:
        """Get cluster names normalized as a list of strings."""
        if isinstance(self.cluster_names, list):
            return self.cluster_names
        return [self.cluster_names]

    def get_cluster_filter(self) -> list[dict[str, Any]]:
        """Return a shallow copy of the base cluster tag filter."""
        return self._cluster_filter.copy()

    def _query_instances(self, states: str | list[str]) -> Any:
        """Build an EC2 instance collection filtered by cluster and instance state."""
        fs = FilterSet(self.get_cluster_filter())
        fs.add("instance-state-name", states)
        return self._ec2.instances.filter(Filters=fs.to_list())

    def _group_instances_by_cluster(self, states: str | list[str]) -> dict[Any, list[Any]]:
        """Query instances in the given state(s) and group them by their Cluster tag."""
        instances = list(self._query_instances(states))
        cluster_dict: dict[str, list[Any]] = {k: [] for k in self._cluster_list}
        for instance in instances:
            cluster_tag = TagSet(instance.tags).get("Cluster")
            if cluster_tag is not None:
                cluster_dict[cluster_tag].append(instance)
        return cluster_dict

    @staticmethod
    def _compile_regex(name_pattern: str) -> re.Pattern[str]:
        """Compile a regex pattern or raise a descriptive ValueError."""
        try:
            return re.compile(name_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{name_pattern}': {e}") from e

    def _build_resource_tags(self, device: str, instance: str, label: str) -> list[Any]:
        """Build the standard tag list applied to managed volumes and snapshots."""
        ts = TagSet()
        ts.add("Cluster", self._cluster_name_str)
        ts.add("Device", device)
        ts.add("Instance", instance)
        ts.add("Label", label)
        ts.add("Name", f"{instance} - {device}")
        ts.add("automation_key", self.AUTOMATION_KEY)
        return ts.to_list()

    def _wait_instances_running(self, instance_ids: list[str]) -> None:
        """Wait for instances to reach running state using 5s polling."""
        waiter = self._ec2_client.get_waiter("instance_running")
        waiter.wait(
            InstanceIds=instance_ids,
            WaiterConfig={"Delay": 5, "MaxAttempts": 120},
        )

    def _wait_instances_stopped(self, instance_ids: list[str]) -> None:
        """Wait for instances to reach stopped state using 5s polling."""
        waiter = self._ec2_client.get_waiter("instance_stopped")
        waiter.wait(
            InstanceIds=instance_ids,
            WaiterConfig={"Delay": 5, "MaxAttempts": 120},
        )

    def _start_instance_batch(self, instances: list[Any]) -> None:
        """Start a batch of EC2 instances and wait until all are running."""
        for instance in instances:
            name = TagSet(instance.tags).get("Name")
            print(f"Starting {name} ({instance.id})")
            instance.start()
        print(f"Waiting for {len(instances)} instances to start...")
        self._wait_instances_running([i.id for i in instances])

    def _stop_instance_batch(self, instances: list[Any]) -> None:
        """Stop a batch of EC2 instances and wait until all are stopped."""
        for instance in instances:
            name = TagSet(instance.tags).get("Name")
            print(f"Stopping {name} ({instance.id})")
            instance.stop()
        print(f"Waiting for {len(instances)} instances to stop...")
        self._wait_instances_stopped([i.id for i in instances])

    def _detach_volumes_from_instances(self, instances: list[Any]) -> None:
        """Detach all volumes attached to the given instances and wait until available."""
        volume_ids: list[str] = []
        for instance in instances:
            instance_name = TagSet(instance.tags).get("Name") or ""
            shortname = instance_name.split(".")[0]
            for volume in instance.volumes.all():
                device = volume.attachments[0]["Device"]
                print(f"Detaching {device} ({volume.id}) from {shortname} ({instance.id})")
                volume.detach_from_instance(Device=device, InstanceId=instance.id)
                volume_ids.append(volume.id)
        if volume_ids:
            print(f"Waiting for {len(volume_ids)} volumes to be detached...")
            self.wait_for_volumes(volume_ids, "volume_available")

    def _delete_volume_batch(self, volumes: list[Any]) -> None:
        """Delete the given volumes and wait until deletion completes."""
        volume_ids: list[str] = []
        for volume in volumes:
            print(f"Deleting volume {volume.id}")
            volume.delete()
            volume_ids.append(volume.id)
        print(f"Waiting for {len(volume_ids)} volumes to be deleted...")
        self.wait_for_volumes(volume_ids, "volume_deleted")

    def _attach_matching_volumes(self, instances: list[Any], volumes: list[Any]) -> list[str]:
        """Attach volumes to instances whose Name tag matches the volume's Instance tag."""
        volume_ids: list[str] = []
        for instance in instances:
            instance_name = TagSet(instance.tags).get("Name") or ""
            shortname = instance_name.split(".")[0]
            for volume in volumes:
                ts = TagSet(volume.tags)
                volume_instance = ts.get("Instance")
                device = ts.get("Device")
                if volume_instance == instance_name:
                    print(f"Attaching {device} ({volume.id}) to {shortname} ({instance.id})")
                    volume.attach_to_instance(Device=device, InstanceId=instance.id)
                    volume_ids.append(volume.id)
        return volume_ids

    def _create_volumes_from_snapshots(
        self, snapshots: list[Any], label: str, include_instance_in_msg: bool = False
    ) -> None:
        """Create EBS volumes from the given snapshots and wait until available and tagged."""
        volume_ids: list[str] = []
        for snapshot in snapshots:
            ts = TagSet(snapshot.tags)
            device = ts.get("Device")
            instance = ts.get("Instance")
            if not device:
                raise Exception(
                    f"Error: create_volume: Can't find device tag for snapshot {snapshot.id}."
                )
            if not instance:
                raise Exception(
                    f"Error: create_volume: Can't find instance tag for snapshot {snapshot.id}."
                )

            avail_zone = self.get_instances()[0].placement["AvailabilityZone"]
            tags = self._build_resource_tags(device, instance, label)

            if include_instance_in_msg:
                print(f"Creating volume from snapshot {snapshot.id} for {instance}")
            else:
                print(f"Creating volume from snapshot {snapshot.id}")

            volume = self._ec2.create_volume(
                SnapshotId=snapshot.id,
                AvailabilityZone=avail_zone,
                VolumeInitializationRate=300,
                TagSpecifications=[{"ResourceType": "volume", "Tags": tags}],
            )
            volume_ids.append(volume.id)

        if volume_ids:
            print(f"Waiting for {len(volume_ids)} volumes to be created...")
            self.wait_for_volumes(volume_ids, "volume_available")
            self._wait_for_volume_tags(volume_ids)

    def get_instances(self) -> list[Any]:
        """Get all non-terminated EC2 instances belonging to this cluster set.

        Retrieves all EC2 instances that have a "Cluster" tag matching any of the
        cluster names specified during initialization. The instances are filtered
        using the cluster filter and limited by the safety maximum (_MAX_ITEMS).

        Returns:
            list: List of EC2 instance objects from boto3. Each instance object
                 contains all AWS instance metadata including ID, state, tags, etc.

        Example:
            ```python
            cluster = ClusterSet('production-web')
            instances = cluster.get_instances()
            for instance in instances:
                print(f"Instance {instance.id} is {instance.state['Name']}")
            ```

        Note:
            Returns a maximum of _MAX_ITEMS (150) instances for performance protection.
            If your cluster has more instances, increase this limit or use filtering.
        """
        self._logger.debug("method_call: get_instances")
        instances = self._query_instances(self._ACTIVE_INSTANCE_STATES)
        return list(instances.limit(self._MAX_ITEMS))

    def get_deployed_clusters(self) -> dict[Any, list[Any]]:
        """Get a dictionary mapping each cluster name to its deployed EC2 instances.

        Returns:
            dict: Mapping of cluster name to list of non-terminated instance objects.
        """
        self._logger.debug("method_call: get_deployed_clusters")
        return self._group_instances_by_cluster(self._ACTIVE_INSTANCE_STATES)

    def get_deployed_cluster_names(self) -> set[str | None]:
        """Get the set of cluster names that currently have deployed instances.

        Returns:
            set: Set of deployed cluster names found on non-terminated instances.
        """
        self._logger.debug("method_call: get_deployed_cluster_names")
        instances = list(self._query_instances(self._ACTIVE_INSTANCE_STATES))
        return {TagSet(i.tags).get("Cluster") for i in instances}

    def get_running_instances(self) -> list[Any]:
        """Get list of instances that are powered on (pending, running, or stopping).

        Returns:
            list: List of running/pending/stopping EC2 instance objects.
        """
        self._logger.debug("method_call: get_instances")
        instances = self._query_instances(self._RUNNING_INSTANCE_STATES)
        return list(instances.limit(self._MAX_ITEMS))

    def get_running_clusters(self) -> dict[Any, list[Any]]:
        """Get a dictionary with all clusters that are powered on.

        Includes instances in a pending, running, or stopping state.

        Returns:
            dict: Mapping of cluster name to list of powered-on instance objects.
        """
        self._logger.debug("method_call: get_running_clusters")
        return self._group_instances_by_cluster(self._RUNNING_INSTANCE_STATES)

    def get_stopped_instances(self) -> list[Any]:
        """Get list of instances that are completely stopped.

        Returns:
            list: List of stopped EC2 instance objects.
        """
        self._logger.debug("method_call: get_instances")
        instances = self._query_instances("stopped")
        return list(instances.limit(self._MAX_ITEMS))

    def get_stopped_clusters(self) -> dict[Any, list[Any]]:
        """Get a dictionary with all clusters that are powered off.

        Returns:
            dict: Mapping of cluster name to list of stopped instance objects.
        """
        self._logger.debug("method_call: get_stopped_clusters")
        return self._group_instances_by_cluster("stopped")

    def start_instances(self) -> None:
        """Start all stopped EC2 instances in this cluster.

        Identifies all instances in the cluster that are currently in 'stopped' state
        and starts them. Running instances are not affected. The operation processes
        instances in batches and provides feedback on progress.

        Example:
            ```python
            cluster = ClusterSet('production-web')
            cluster.start_instances()  # Starts all stopped instances
            ```

        Note:
            Only instances in 'stopped' state will be started. Instances in other
            states (running, stopping, etc.) are ignored. The operation may take
            several minutes for large clusters.
        """
        self._logger.debug("method_call: start_instances")
        instances = self.get_stopped_instances()
        if not instances:
            print("No instances to start.")
        else:
            self._start_instance_batch(instances)

    def stop_instances(self) -> None:
        """Stop all running EC2 instances associated with this cluster."""
        self._logger.debug("method_call: stop_instances")
        instances = self.get_running_instances()
        if not instances:
            print("No instances to stop.")
        else:
            self._stop_instance_batch(instances)

    def tag_instances(self, tags: list[dict[str, str]]) -> None:
        """Apply tags to all instances in this cluster.

        Args:
            tags: List of AWS tag dictionaries ``[{'Key': k, 'Value': v}, ...]``.
        """
        # The resource API is somewhat less efficient than the low-level client
        # API because it does one request per tag operation. For reasonably
        # sized collections this should be ok.
        for instance in self.get_instances():
            print(f"Tagging instance {instance.id}")
            instance.create_tags(Tags=tags)

    def untag_instances(self, tags: list[dict[str, str]]) -> None:
        """Remove tags from all instances in this cluster in a single batch call.

        Args:
            tags: List of AWS tag key dictionaries ``[{'Key': k}, ...]``.
        """
        instance_ids: list[str] = []
        for instance in self.get_instances():
            print(f"Un-tagging instance {instance.id}")
            instance_ids.append(instance.id)
        self._ec2_client.delete_tags(Resources=instance_ids, Tags=tags)  # type: ignore[arg-type]

    def get_volumes(self) -> list[Any]:
        """Get list of managed EBS volumes associated with this cluster.

        Returns:
            list: List of EBS volume objects tagged with a recognized automation_key.
        """
        self._logger.debug("method_call: get_volumes")
        fs = FilterSet(self.get_cluster_filter())
        # The tool deliberately only works with volumes that have the tag
        # 'automation_key' set. It will ignore all other volumes so that it
        # doesn't clobber volumes that it is not responsible for.
        fs.add("tag:automation_key", ["PROVISIONER", self.AUTOMATION_KEY])
        volumes = self._ec2.volumes.filter(Filters=fs.to_list())
        return list(volumes.limit(self._MAX_ITEMS))

    def get_kubernetes_volumes(self) -> list[Any]:
        """Get list of Kubernetes persistent volumes associated with this cluster.

        Returns:
            list: List of Kubernetes EBS volume objects.
        """
        self._logger.debug("method_call: get_kubernetes_volumes")
        fs = FilterSet(
            [
                {
                    "Name": "tag:KubernetesCluster",
                    "Values": self._cluster_list,
                },
                {
                    "Name": "tag:kubernetes.io/created-for/pvc/namespace",
                    "Values": ["openshift-logging"],
                },
            ]
        )
        volumes = self._ec2.volumes.filter(Filters=fs.to_list())
        return list(volumes)

    def get_restored_volumes(self, label: str | None = None) -> list[Any]:
        """Get list of volumes that were previously created from snapshots.

        Args:
            label: Optional snapshot label to filter restored volumes by.

        Returns:
            list: List of restored EBS volume objects.
        """
        self._logger.debug("method_call: get_restored_volumes")
        fs = FilterSet(self.get_cluster_filter())
        # These volumes can be in available state (if just created) or in-use state (if attached).
        # Note: The 'status' filter corresponds to the 'state' attribute in
        # the AWS management console.
        fs.add("tag:automation_key", self.AUTOMATION_KEY)
        if label is not None:
            fs.add("tag:Label", label)
        volumes = self._ec2.volumes.filter(Filters=fs.to_list())
        return list(volumes.limit(self._MAX_ITEMS))

    def attach_volumes(self, label: str) -> None:
        """Attach restored volumes with the given label to their associated instances.

        Args:
            label: Label of restored volumes to attach.
        """
        self._logger.debug("method_call: attach_volumes")
        instances = self.get_instances()
        volumes = self.get_restored_volumes(label)
        volume_ids = self._attach_matching_volumes(instances, volumes)
        if not volume_ids:
            print("Error: No volumes to attach.")
        else:
            print(f"Waiting for {len(volume_ids)} volumes to be attached...")
            self.wait_for_volumes(volume_ids, "volume_in_use")

    def create_volumes(self, label: str) -> None:
        """Create new EBS volumes from managed snapshots with the given label.

        Args:
            label: Label of snapshots to restore.
        """
        self._logger.debug("method_call: create_managed_volumes")
        with log_duration(self._logger, "create_volumes"):
            snapshots = self.get_snapshots(label)
            if not snapshots:
                print(f"Error: No snapshots found with label '{label}'.")
            self._create_volumes_from_snapshots(snapshots, label, include_instance_in_msg=False)

    def delete_volumes(self) -> None:
        """Delete all managed EBS volumes associated with this cluster."""
        self._logger.debug("method_call: delete_volumes")
        with log_duration(self._logger, "delete_volumes"):
            volumes = self.get_volumes()
            if not volumes:
                print("No volumes to delete.")
            else:
                self._delete_volume_batch(volumes)

    def delete_kubernetes_volumes(self) -> None:
        """Delete all Kubernetes persistent volumes associated with this cluster."""
        self._logger.debug("method_call: delete_kubernetes_volumes")
        volumes = self.get_kubernetes_volumes()
        if not volumes:
            print("No kubernetes volumes to delete.")
        else:
            self._delete_volume_batch(volumes)

    def detach_volumes(self) -> None:
        """Detach all volumes currently attached to instances in this cluster."""
        self._logger.debug("method_call: detach_volumes")
        self._detach_volumes_from_instances(self.get_instances())

    def tag_volumes(self, tags: list[dict[str, str]]) -> None:
        """Apply tags to all managed volumes in this cluster.

        Args:
            tags: List of AWS tag dictionaries ``[{'Key': k, 'Value': v}, ...]``.
        """
        for volume in self.get_volumes():
            print(f"Tagging volume {volume.id}")
            volume.create_tags(Tags=tags)

    def untag_volumes(self, tags: list[dict[str, str]]) -> None:
        """Remove tags from all managed volumes in this cluster in a single batch call.

        Args:
            tags: List of AWS tag key dictionaries ``[{'Key': k}, ...]``.
        """
        volume_ids: list[str] = []
        for volume in self.get_volumes():
            print(f"Un-tagging volume {volume.id}")
            volume_ids.append(volume.id)
        self._ec2_client.delete_tags(Resources=volume_ids, Tags=tags)  # type: ignore[arg-type]

    def wait_for_volumes(self, volume_ids: list[str], status: str) -> None:
        """Wait for a state transition to complete across a batch of EBS volumes.

        Args:
            volume_ids: List of EBS volume IDs to poll.
            status: Boto3 EC2 volume waiter name (e.g. ``'volume_available'``).
        """
        self._logger.debug("method_call: wait_for_volumes")
        waiter = self._ec2_client.get_waiter(status)  # type: ignore[call-overload]
        waiter.wait(
            VolumeIds=volume_ids,
            WaiterConfig={
                "Delay": 5,
                "MaxAttempts": 240,
            },
        )

    def _wait_for_volume_tags(
        self, volume_ids: list[str], expected_tag_key: str = "Cluster"
    ) -> None:
        """Poll until volumes have their tags propagated (up to 10s)."""
        for _attempt in range(5):
            response = self._ec2_client.describe_volumes(VolumeIds=volume_ids)
            all_tagged = all(
                any(t["Key"] == expected_tag_key for t in vol.get("Tags", []))
                for vol in response["Volumes"]
            )
            if all_tagged:
                return
            time.sleep(2)

    def get_snapshots(self, label: str | None = None) -> list[Any]:
        """Get a list of completed managed snapshots for this cluster.

        Args:
            label: Optional snapshot label to filter by.

        Returns:
            list: List of EC2 snapshot objects.
        """
        self._logger.debug("method_call: get_all_snapshots")
        fs = FilterSet(self.get_cluster_filter())
        fs.add("status", "completed")
        fs.add("tag:automation_key", self.AUTOMATION_KEY)
        if label is not None:
            fs.add("tag:Label", label)
        snapshots = self._ec2.snapshots.filter(Filters=fs.to_list())
        return list(snapshots.limit(self._MAX_ITEMS))

    def create_snapshots(self, label: str) -> None:
        """Create labeled EBS snapshots of all volumes attached to cluster instances.

        If snapshots with the given label already exist for this cluster, they are
        deleted first so that only one snapshot set per label exists at a time.

        Args:
            label: Label to apply to each created snapshot.
        """
        self._logger.debug("method_call: create_snapshots")
        with log_duration(self._logger, "create_snapshots"):
            if self.get_snapshots(label):
                self.delete_snapshots(label)

            snapshot_ids: list[str] = []
            for instance in self.get_instances():
                instance_name = TagSet(instance.tags).get("Name") or ""
                shortname = instance_name.split(".")[0]
                for volume in instance.volumes.all():
                    device = volume.attachments[0]["Device"]
                    timestamp = datetime.datetime.now(tz=datetime.UTC)
                    date = timestamp.strftime("%Y-%m-%d")
                    timestr = timestamp.strftime("%H:%M:%S")
                    description = f"Managed snapshot taken on {date} at {timestr}"
                    tags = self._build_resource_tags(device, instance_name, label)

                    print(
                        f"Creating snapshot of {device} ({volume.id}) on {shortname} ({instance.id})"
                    )
                    snapshot = volume.create_snapshot(
                        Description=description,
                        TagSpecifications=[{"ResourceType": "snapshot", "Tags": tags}],
                    )
                    snapshot_ids.append(snapshot.id)

            print(f"Waiting for {len(snapshot_ids)} snapshots to complete...")
            waiter = self._ec2_client.get_waiter("snapshot_completed")
            waiter.wait(
                SnapshotIds=snapshot_ids,
                WaiterConfig={
                    "Delay": 5,
                    "MaxAttempts": 720,
                },
            )

    def delete_snapshots(self, label: str) -> None:
        """Delete cluster snapshots that have the given label.

        Args:
            label: Label of snapshots to delete.
        """
        self._logger.debug("method_call: delete_snapshots")
        with log_duration(self._logger, "delete_snapshots"):
            snapshots = self.get_snapshots(label)
            print(f"Deleting {len(snapshots)} snapshots...")
            for snapshot in snapshots:
                print(f"Deleting snapshot {snapshot.id}")
                snapshot.delete()
            # There is no waiter for snapshot deletion. Add a small delay to guard
            # against any possible timing issues.
            time.sleep(2)

    def tag_snapshots(self, tags: list[dict[str, str]]) -> None:
        """Apply tags to all managed snapshots in this cluster.

        Args:
            tags: List of AWS tag dictionaries ``[{'Key': k, 'Value': v}, ...]``.
        """
        for snapshot in self.get_snapshots():
            print(f"Tagging snapshot {snapshot.id}")
            snapshot.create_tags(Tags=tags)

    def untag_snapshots(self, tags: list[dict[str, str]]) -> None:
        """Remove tags from all managed snapshots in this cluster in a single batch call.

        Args:
            tags: List of AWS tag key dictionaries ``[{'Key': k}, ...]``.
        """
        snapshot_ids: list[str] = []
        for snapshot in self.get_snapshots():
            print(f"Un-tagging snapshot {snapshot.id}")
            snapshot_ids.append(snapshot.id)
        self._ec2_client.delete_tags(Resources=snapshot_ids, Tags=tags)  # type: ignore[arg-type]

    def get_subnet(self) -> Any:
        """Get the single VPC subnet belonging to this cluster.

        Returns:
            boto3 Subnet resource for this cluster.

        Raises:
            Exception: If more than one subnet matches the cluster filter.
        """
        self._logger.debug("method_call: get_subnet")
        fs = FilterSet(self.get_cluster_filter())
        subnets = self._ec2.subnets.filter(Filters=fs.to_list())
        subnet_list = list(subnets.limit(self._MAX_ITEMS))
        if len(subnet_list) > 1:
            raise Exception("Error (get_subnet): more than one subnet returned.")
        return subnet_list[0]

    def tag_subnet(self, tags: list[dict[str, str]]) -> None:
        """Apply tags to the subnet belonging to this cluster.

        Args:
            tags: List of AWS tag dictionaries ``[{'Key': k, 'Value': v}, ...]``.
        """
        subnet = self.get_subnet()
        print(f"Tagging subnet {subnet.id}")
        subnet.create_tags(Tags=tags)

    def untag_subnet(self, tags: list[dict[str, str]]) -> None:
        """Remove tags from the subnet belonging to this cluster.

        Args:
            tags: List of AWS tag key dictionaries ``[{'Key': k}, ...]``.
        """
        subnet = self.get_subnet()
        print(f"Un-tagging subnet {subnet.id}")
        self._ec2_client.delete_tags(Resources=[subnet.id], Tags=tags)  # type: ignore[arg-type]

    def _filter_instances_by_name_regex(self, instances: list[Any], name_pattern: str) -> list[Any]:
        """Filter instances by matching their Name tag against a regex pattern.

        Args:
            instances: List of EC2 instance objects.
            name_pattern: Regex pattern to match against Name tags.

        Returns:
            list: Filtered list of matching EC2 instance objects.

        Raises:
            ValueError: If ``name_pattern`` is not a valid regular expression.
        """
        if not name_pattern:
            return instances

        pattern = self._compile_regex(name_pattern)
        filtered_instances: list[Any] = []
        for instance in instances:
            name_tag = TagSet(instance.tags).get("Name")
            if name_tag and pattern.search(name_tag):
                filtered_instances.append(instance)

        return filtered_instances

    def stop_instances_targeted(self, name_pattern: str) -> None:
        """Stop running instances whose Name tag matches the given regex pattern.

        Args:
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: stop_instances_targeted")
        instances = self._filter_instances_by_name_regex(self.get_running_instances(), name_pattern)
        if not instances:
            print(f"No running instances found matching pattern '{name_pattern}'.")
        else:
            self._stop_instance_batch(instances)

    def start_instances_targeted(self, name_pattern: str) -> None:
        """Start stopped instances whose Name tag matches the given regex pattern.

        Args:
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: start_instances_targeted")
        instances = self._filter_instances_by_name_regex(self.get_stopped_instances(), name_pattern)
        if not instances:
            print(f"No stopped instances found matching pattern '{name_pattern}'.")
        else:
            self._start_instance_batch(instances)

    def detach_volumes_targeted(self, name_pattern: str) -> None:
        """Detach volumes from instances whose Name tag matches the given regex pattern.

        Args:
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: detach_volumes_targeted")
        instances = self._filter_instances_by_name_regex(self.get_instances(), name_pattern)
        if not instances:
            print(f"No instances found matching pattern '{name_pattern}'.")
            return

        self._detach_volumes_from_instances(instances)

    def delete_volumes_targeted(self, name_pattern: str) -> None:
        """Delete volumes associated with instances matching the given Name tag regex pattern.

        Args:
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: delete_volumes_targeted")
        targeted_volumes: list[Any] = []
        for volume in self.get_volumes():
            volume_instance_tag = TagSet(volume.tags).get("Instance")
            if volume_instance_tag:
                pattern = self._compile_regex(name_pattern)
                if pattern.search(volume_instance_tag):
                    targeted_volumes.append(volume)

        if not targeted_volumes:
            print(f"No volumes found for instances matching pattern '{name_pattern}'.")
        else:
            self._delete_volume_batch(targeted_volumes)

    def create_volumes_targeted(self, label: str, name_pattern: str) -> None:
        """Create new volumes from snapshots for instances matching the Name tag regex pattern.

        Args:
            label: Label of snapshots to restore.
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: create_volumes_targeted")
        with log_duration(self._logger, "create_volumes_targeted"):
            pattern = self._compile_regex(name_pattern)
            snapshots = self.get_snapshots(label)
            if not snapshots:
                print(f"Error: No snapshots found with label '{label}'.")
                return

            targeted_snapshots = [
                snapshot
                for snapshot in snapshots
                if (instance := TagSet(snapshot.tags).get("Instance")) and pattern.search(instance)
            ]

            if not targeted_snapshots:
                print(f"No snapshots found for instances matching pattern '{name_pattern}'.")
                return

            self._create_volumes_from_snapshots(
                targeted_snapshots, label, include_instance_in_msg=True
            )

    def attach_volumes_targeted(self, label: str, name_pattern: str) -> None:
        """Attach restored volumes to instances matching the given Name tag regex pattern.

        Args:
            label: Label of volumes to attach.
            name_pattern: Regex pattern to match instance Name tags.
        """
        self._logger.debug("method_call: attach_volumes_targeted")
        instances = self._filter_instances_by_name_regex(self.get_instances(), name_pattern)
        if not instances:
            print(f"No instances found matching pattern '{name_pattern}'.")
            return

        volumes = self.get_restored_volumes(label)
        volume_ids = self._attach_matching_volumes(instances, volumes)
        if not volume_ids:
            print(f"Error: No volumes to attach for instances matching pattern '{name_pattern}'.")
        else:
            print(f"Waiting for {len(volume_ids)} volumes to be attached...")
            self.wait_for_volumes(volume_ids, "volume_in_use")
