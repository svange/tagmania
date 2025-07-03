import datetime
import time
import logging
import boto3
from .tagset import TagSet
from .filterset import FilterSet


class ClusterSet:
    def __init__(self, cluster_names, profile=None):
        """
        Initialize ClusterSet.

        Args:
            - cluster_names - The name of a cluster, or a list of clusters
            - profile - The AWS profile to use (optional)
        Returns:
            none
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
        self.AUTOMATION_KEY = 'SNAPSHOT_MANAGER'

        # cluster_names can be a string 'aws-dev5' or a list ['aws-dev1', 'aws-dev2', etc...]
        self.cluster_names = cluster_names

        if not isinstance(cluster_names, list):
            cluster_names = [self.cluster_names]

        # Use this as a starting point to build filters that only return
        # resources associated with this cluster. Use the 'get_cluster_filter'
        # method to get a copy of it rather than doing direct assignment.
        self._cluster_filter = [
            {'Name': 'tag:Cluster', 'Values': cluster_names},
        ]

        # Set up logging
        self._logger = logging.getLogger('tagmania')
        self._logger.setLevel(logging.INFO)
        self._logger.info("Logging initialized.")

        # Create a boto3 session using the specified profile if provided.
        if profile:
            aws_session = boto3.Session(profile_name=profile)
            self._logger.info(f"Using AWS profile: {profile}")
        else:
            aws_session = boto3.Session()

        # Create EC2 resource and client from the session.
        self._ec2 = aws_session.resource('ec2')
        self._ec2_client = aws_session.client('ec2')

    def get_cluster_filter(self):
        # Return a copy to defend against modifications
        return self._cluster_filter.copy()

    def get_instances(self):
        """
        Get list of instances associated with a cluster set provided.

        Args:
            none
        Returns:
            list of instances
        """
        self._logger.debug("method_call: get_instances")
        fs = FilterSet(self.get_cluster_filter())
        # Exclude terminated instances
        fs.add('instance-state-name', [
            'pending',
            'running',
            'shutting-down',
            'stopped',
            'stopping'
        ])
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances.limit(self._MAX_ITEMS))
        return instance_list

    def get_deployed_clusters(self):
        """
        Get a dictionary with all clusters already deployed.

        Args:
            none
        Returns:
            dictionary of clusters
        """
        self._logger.debug("method_call: get_deployed_clusters")
        fs = FilterSet(self.get_cluster_filter())
        # Exclude terminated instances
        fs.add('instance-state-name', [
            'pending',
            'running',
            'shutting-down',
            'stopped',
            'stopping'
        ])
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances)
        cluster_dict = {k: [] for k in self.cluster_names}

        for i in instance_list:
            cluster_tag = TagSet(i.tags).get('Cluster')
            cluster_dict[cluster_tag].append(i)

        return cluster_dict

    def get_deployed_cluster_names(self):
        """
        Get a set of all supported environment cluster names already deployed.

        Args:
            none
        Returns:
            set of deployed cluster_names
        """
        self._logger.debug("method_call: get_deployed_cluster_names")
        fs = FilterSet(self.get_cluster_filter())
        # Exclude terminated instances
        fs.add('instance-state-name', [
            'pending',
            'running',
            'shutting-down',
            'stopped',
            'stopping'
        ])
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances)
        instance_cluster_names = []

        for i in instance_list:
            cluster_name = TagSet(i.tags).get('Cluster')
            if cluster_name not in instance_cluster_names:
                instance_cluster_names.append(cluster_name)

        return set(instance_cluster_names)

    def get_running_instances(self):
        """
        Get list of instances that are powered on. This includes instances in
        a pending, running, or stopping state.

        Args:
            none
        Returns:
            list of instances
        """
        self._logger.debug("method_call: get_instances")
        fs = FilterSet(self.get_cluster_filter())
        # Only want instances that are pending, running, or stopping
        fs.add('instance-state-name', [
            'pending',
            'running',
            'stopping'
        ])
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances.limit(self._MAX_ITEMS))
        return instance_list

    def get_running_clusters(self):
        """
        Get a dictionary with all clusters that are powered on. This includes instances in
        a pending, running, or stopping state.

        Args:
            none
        Returns:
            dictionary of running clusters
        """
        self._logger.debug("method_call: get_running_clusters")
        fs = FilterSet(self.get_cluster_filter())
        # Only want instances that are pending, running, or stopping
        fs.add('instance-state-name', [
            'pending',
            'running',
            'stopping'
        ])
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances)
        cluster_dict = {k: [] for k in self.cluster_names}

        for i in instance_list:
            cluster_tag = TagSet(i.tags).get('Cluster')
            cluster_dict[cluster_tag].append(i)

        return cluster_dict

    def get_stopped_instances(self):
        """
        Get list of instances that are powered off.

        Args:
            none
        Returns:
            list of instances
        """
        self._logger.debug("method_call: get_instances")
        fs = FilterSet(self.get_cluster_filter())
        # Only want instances that are completely stopped
        fs.add('instance-state-name', 'stopped')
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances.limit(self._MAX_ITEMS))
        return instance_list

    def get_stopped_clusters(self):
        """
        Get a dictionary with all clusters that are powered off.

        Args:
            none
        Returns:
            dictionary of stopped clusters
        """
        self._logger.debug("method_call: get_stopped_clusters")
        fs = FilterSet(self.get_cluster_filter())
        # Only want instances that are completely stopped
        fs.add('instance-state-name', 'stopped')
        filters = fs.to_list()
        instances = self._ec2.instances.filter(Filters=filters)
        instance_list = list(instances)
        cluster_dict = {k: [] for k in self.cluster_names}

        for i in instance_list:
            cluster_tag = TagSet(i.tags).get('Cluster')
            cluster_dict[cluster_tag].append(i)

        return cluster_dict

    def start_instances(self):
        """
        Start instances associated with this cluster.

        Args:
            none
        Returns:
            none
        """
        self._logger.debug("method_call: start_instances")
        instances = self.get_stopped_instances()
        if len(instances) == 0:
            print("No instances to start.")
        else:
            # Start instances
            for i in instances:
                name = TagSet(i.tags).get('Name')
                print(f"Starting {name} ({i.id})")
                i.start()
            # Wait for instances to start. Call in separate loop because we want
            # to issue the start commands asynchronously rather than waiting for
            # each instance to start before issuing the next one.
            print(f"Waiting for {len(instances)} instances to start...")
            for i in instances:
                i.wait_until_running()

    def stop_instances(self):
        """
        Stop instances associated with this cluster.

        Args:
            none
        Returns:
            none
        """
        self._logger.debug("method_call: stop_instances")
        instances = self.get_running_instances()
        if len(instances) == 0:
            print("No instances to stop.")
        else:
            # Stop instances
            for i in instances:
                name = TagSet(i.tags).get('Name')
                print(f"Stopping {name} ({i.id})")
                i.stop()
            # Wait for instances to stop. Call in separate loop because we want
            # to issue the stop commands asynchronously rather than waiting for
            # each instance to stop before issuing the next one.
            print(f"Waiting for {len(instances)} instances to stop...")
            for i in instances:
                i.wait_until_stopped()

    def tag_instances(self, tags):
        # The resource API is somewhat less efficient than the low-level client
        # API because it does one request per tag operation. For reasonably
        # sized collections this should be ok.
        # tags = {'key': 'values'}
        instances = self.get_instances()
        for i in instances:
            print(f"Tagging instance {i.id}")
            i.create_tags(Tags=tags)

    def untag_instances(self, tags):
        # Might as well un-tag on one big batch since instance objects don't
        # have direct support for un-tagging.
        instances = self.get_instances()
        instance_ids = []
        for i in instances:
            print(f"Un-tagging instance {i.id}")
            instance_ids.append(i.id)
        self._ec2_client.delete_tags(Resources=instance_ids, Tags=tags)

    def get_volumes(self):
        """
        Get list of volumes associated with this cluster.

        Args:
            none
        Returns:
            list of volumes
        """
        self._logger.debug("method_call: get_volumes")
        fs = FilterSet(self.get_cluster_filter())
        # The tool deliberately only works with volumes that have the tag
        # 'automation_key' set. It will ignore all other volumes so that it
        # doesn't clobber volumes that it is not responsible for. It may be that
        # we only need to worry about volumes created by snapshot manager
        # because volumes created by the provisioner won't ever have a label,
        # so when looking for restored volumes, we can just look for managed
        # volumes that have a label.
        fs.add('tag:automation_key', [
            'PROVISIONER',
            self.AUTOMATION_KEY
        ])
        filters = fs.to_list()
        volumes = self._ec2.volumes.filter(Filters=filters)
        volume_list = list(volumes.limit(self._MAX_ITEMS))
        return volume_list

    def get_kubernetes_volumes(self):
        """
        Get list of kubernetes volumes associated with this cluster.

        Args:
            none
        Returns:
            list of kubernetes volumes
        """
        self._logger.debug("method_call: get_kubernetes_volumes")
        fs = FilterSet([
            {'Name': 'tag:KubernetesCluster', 'Values': [self.cluster_names]},
            {'Name': 'tag:kubernetes.io/created-for/pvc/namespace', 'Values': ['openshift-logging']}
        ])
        filters = fs.to_list()
        volumes = self._ec2.volumes.filter(Filters=filters)
        volume_list = list(volumes)
        return volume_list

    def get_restored_volumes(self, label=None):
        """
        Get list of volumes that were previously created from snapshots.

        Args:
            - label: label of volumes being sought (optional)
        Returns:
            list of snapshots
        """
        self._logger.debug("method_call: get_restored_volumes")
        fs = FilterSet(self.get_cluster_filter())
        # These volumes should be in the available state since it is expected
        # that they were just recently re-constituted from snapshots
        # | Note: The 'status' filter corresponds to the 'state' attribute in
        # | the AWS management console. Not sure about the reason behind that.
        fs.add('status', 'available')
        fs.add('tag:automation_key', self.AUTOMATION_KEY)
        # Optionally, get volumes with the given label
        # This might not really be needed because the way the snapshot manager
        # works is that it deletes all managed volumes before creating new ones
        # from snapshots. Therefore at any given time, there should only be one
        # set of available volumes.
        if label != None:
            fs.add('tag:Label', label)
        filters = fs.to_list()
        volumes = self._ec2.volumes.filter(Filters=filters)
        volume_list = list(volumes.limit(self._MAX_ITEMS))
        return volume_list

    def attach_volumes(self, label):
        """
        Attach volumes to associated instances.

        Args:
            - label: label of volume to attach
        Returns:
            none
        """
        self._logger.debug("method_call: attach_volumes")
        instances = self.get_instances()
        # We should be able to work with get_volumes, but this just protects
        # against the case when users are manually creating volumes. It filters
        # out any volumes that were not created by the snapshot manager.
        volumes = self.get_restored_volumes(label)
        # This is for debugging purposes. Sometimes the algorithm below doesn't
        # find all volumes.
        # volume_list = list(volumes)
        # print(f"Found {len(volume_list)} volumes to attach.")

        # For each instance, find all associated volumes and attach them. The
        # association is performed by matching the volume 'Instance' tag to
        # the instance 'Name' tag.
        volume_ids = []
        for i in instances:
            instance_name = TagSet(i.tags).get('Name')
            for volume in volumes:
                ts = TagSet(volume.tags)
                instance = ts.get('Instance')
                device = ts.get('Device')
                if instance == instance_name:
                    # Attach volume
                    shortname = instance_name.split('.')[0]
                    print(f"Attaching {device} ({volume.id}) to {shortname} ({i.id})")
                    volume.attach_to_instance(Device=device, InstanceId=i.id)
                    volume_ids.append(volume.id)
        if len(volume_ids) == 0:
            # This is probably an error. The expectation is that we have a set
            # of newly created volumes from snapshots.
            print("Error: No volumes to attach.")
        else:
            # Wait for the volumes to be attached
            print(f"Waiting for {len(volume_ids)} volumes to be attached...")
            self.wait_for_volumes(volume_ids, 'volume_in_use')

    def create_volumes(self, label):
        """
        Create new volumes from managed snapshots.

        Args:
            - label: label of snapshots to restore
        Returns:
            none
        """
        self._logger.debug("method_call: create_managed_volumes")
        snapshots = self.get_snapshots(label)
        # Check if snapshot list is empty (e.g. due to an invalid label)
        if len(snapshots) == 0:
            print(f"Error: No snapshots found with label '{label}'.")
        # Create volumes
        volume_ids = []
        for snapshot in snapshots:
            # Determine snapshot's associated instance and device. This is
            # needed later on so that we know where to attach it.
            ts = TagSet(snapshot.tags)
            device = ts.get('Device')
            instance = ts.get('Instance')
            if not device:
                raise Exception(f"Error: create_volume: Can't find device tag for snapshot {snapshot.id}.")
            if not instance:
                raise Exception(f"Error: create_volume: Can't find instance tag for snapshot {snapshot.id}.")
            # Determine availability zone from one of the cluster instances
            avail_zone = self.get_instances()[0].placement['AvailabilityZone']
            # Make tags
            ts = TagSet()
            ts.add('Cluster', self.cluster_names)
            ts.add('Device', device)
            ts.add('Instance', instance)
            ts.add('Label', label)
            ts.add('Name', f"{instance} - {device}")
            ts.add('automation_key', self.AUTOMATION_KEY)
            tags = ts.to_list()
            # Create volume
            print(f"Creating volume from snapshot {snapshot.id}")
            volume = self._ec2.create_volume(
                SnapshotId=snapshot.id,
                AvailabilityZone=avail_zone,
                TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags}]
            )
            volume_ids.append(volume.id)
        # Wait for the volumes to be created
        if len(volume_ids) > 0:
            print(f"Waiting for {len(volume_ids)} volumes to be created...")
            self.wait_for_volumes(volume_ids, 'volume_available')
            # When attaching newly created volumes later, not all volumes are
            # being attached for some reason. Perhaps the waiter returns before
            # the tags have actually been applied. Try giving ten more seconds
            # for the tags to be applied.
            time.sleep(10)

    def delete_volumes(self):
        """
        Delete all volumes associated with this cluster.

        Args:
            none
        Returns:
            none
        """
        self._logger.debug("method_call: delete_volumes")
        # We really only have to delete the previously detached volumes, but
        # this will delete all managed volumes in the cluster. Its probably a
        # good idea to do so as a matter of good housekeeping. Also, if there
        # are any stale volumes hanging around with the same label that we are
        # about to restore from that would cause problems because we wouldn't
        # know which volumes to attach.
        volumes = self.get_volumes()
        if len(volumes) == 0:
            print("No volumes to delete.")
        else:
            volume_ids = []
            for volume in volumes:
                print(f"Deleting volume {volume.id}")
                volume.delete()
                volume_ids.append(volume.id)
            # Wait for the volumes to be deleted
            print(f"Waiting for {len(volume_ids)} volumes to be deleted...")
            self.wait_for_volumes(volume_ids, 'volume_deleted')

    def delete_kubernetes_volumes(self):
        """
        Delete all kubernetes volumes associated with this cluster.

        Args:
            none
        Returns:
            none
        """
        self._logger.debug("method_call: delete_kubernetes_volumes")
        # We really only have to delete the previously detached volumes, but
        # this will delete all managed volumes in the cluster. Its probably a
        # good idea to do so as a matter of good housekeeping. Also, if there
        # are any stale volumes hanging around with the same label that we are
        # about to restore from that would cause problems because we wouldn't
        # know which volumes to attach.
        volumes = self.get_kubernetes_volumes()
        if len(volumes) == 0:
            print("No kubernetes volumes to delete.")
        else:
            volume_ids = []
            for volume in volumes:
                print(f"Deleting volume {volume.id}")
                volume.delete()
                volume_ids.append(volume.id)
            # Wait for the volumes to be deleted
            print(f"Waiting for {len(volume_ids)} volumes to be deleted...")
            self.wait_for_volumes(volume_ids, 'volume_deleted')

    def detach_volumes(self):
        """
        Detach all currently attached volumes.

        Args:
            none
        Returns:
            none
        """
        self._logger.debug("method_call: detach_volumes")
        # Build list of volume_ids so to pass to waiter in one big batch
        volume_ids = []
        # For each instance, detach all volumes
        instances = self.get_instances()
        for i in instances:
            volumes = i.volumes.all()
            for volume in volumes:
                device = volume.attachments[0]['Device']
                instance_name = TagSet(i.tags).get('Name')
                shortname = instance_name.split('.')[0]
                print(f"Detaching {device} ({volume.id}) from {shortname} ({i.id})")
                volume.detach_from_instance(Device=device, InstanceId=i.id)
                volume_ids.append(volume.id)
        # Wait for volumes to detach
        if len(volume_ids) > 0:
            print(f"Waiting for {len(volume_ids)} volumes to be detached...")
            self.wait_for_volumes(volume_ids, 'volume_available')

    def tag_volumes(self, tags):
        volumes = self.get_volumes()
        for volume in volumes:
            print(f"Tagging volume {volume.id}")
            volume.create_tags(Tags=tags)

    def untag_volumes(self, tags):
        volumes = self.get_volumes()
        volume_ids = []
        for volume in volumes:
            print(f"Un-tagging volume {volume.id}")
            volume_ids.append(volume.id)
        # Might as well un-tag on one big batch since volume objects don't
        # have direct support for un-tagging.
        self._ec2_client.delete_tags(Resources=volume_ids, Tags=tags)

    def wait_for_volumes(self, volume_ids, status):
        """
        Wait for an action to complete on volumes.

        Args:
            volume_ids - volume_ids: list of volume IDs
            status - status to check for completion of action
        Returns:
            none
        """
        # This is a helper method - perhaps it should be static
        self._logger.debug("method_call: wait_for_volumes")
        waiter = self._ec2_client.get_waiter(status)
        waiter.wait(
            VolumeIds=volume_ids,
            WaiterConfig={
                # 'Delay': 15  # This is the default in seconds
                'MaxAttempts': 240  # This will give AWS an hour
            }
        )

    def get_snapshots(self, label=None):
        """
        Get a list of cluster snapshots.

        Args:
            label - label of snapshots being sought (optional)
        Returns:
            list of snapshots
        """
        self._logger.debug("method_call: get_all_snapshots")
        fs = FilterSet(self.get_cluster_filter())
        # Only get snapshots in a completed state. It is expected that users
        # will only call this method after snapshots have been completed.
        fs.add('status', 'completed')
        # Only get snapshots that were created by the snapshot manager.
        fs.add('tag:automation_key', self.AUTOMATION_KEY)
        # Optionally, get snapshots with a given label
        if label != None:
            fs.add('tag:Label', label)
        filters = fs.to_list()
        snapshots = self._ec2.snapshots.filter(Filters=filters)
        snapshot_list = list(snapshots.limit(self._MAX_ITEMS))
        return snapshot_list

    def create_snapshots(self, label):
        """
        Create snapshots of volumes.

        Args:
            - label: label to apply to each snapshot
        Returns:
            none
        """
        self._logger.debug("method_call: create_snapshots")
        # Check if any snapshots with the same label already exists. If so,
        # delete them. Only one set of snapshots with a given label may
        # exist at a time.
        old_snapshots = self.get_snapshots(label)
        if len(old_snapshots) > 0:
            self.delete_snapshots(label)
        snapshot_ids = []
        # Get list of instances that need snapshots taken
        instances = self.get_instances()
        for i in instances:
            instance_name = TagSet(i.tags).get('Name')
            # Get collection of volumes for the current instance
            volumes = i.volumes.all()
            for volume in volumes:
                device = volume.attachments[0]['Device']
                # Make description
                timestamp = datetime.datetime.now()
                date = timestamp.strftime('%Y-%m-%d')
                time = timestamp.strftime('%H:%M:%S')
                description = f"Managed snapshot taken on {date} at {time}"
                # Make tags
                ts = TagSet()
                ts.add('Cluster', self.cluster_names)
                ts.add('Device', device)
                ts.add('Instance', instance_name)
                ts.add('Label', label)
                ts.add('Name', f"{instance_name} - {device}")
                ts.add('automation_key', self.AUTOMATION_KEY)
                tags = ts.to_list()
                # Create shapshot
                shortname = instance_name.split('.')[0]
                print(f"Creating snapshot of {device} ({volume.id}) on {shortname} ({i.id})")
                snapshot = volume.create_snapshot(
                    Description=description,
                    TagSpecifications=[{'ResourceType': 'snapshot', 'Tags': tags}]
                )
                snapshot_ids.append(snapshot.id)
        # Wait for snapshots to complete
        print(f"Waiting for {len(snapshot_ids)} snapshots to complete...")
        waiter = self._ec2_client.get_waiter('snapshot_completed')
        waiter.wait(
            SnapshotIds=snapshot_ids,
            WaiterConfig={
                # 'Delay': 15  # This is the default in seconds
                'MaxAttempts': 240  # This will give AWS an hour
            }
        )

    def delete_snapshots(self, label):
        """
        Delete cluster snapshots that have the given label.

        Args:
            label - label of snapshots to be deleted
        Returns:
            none
        """
        self._logger.debug("method_call: delete_snapshots")
        snapshots = self.get_snapshots(label)
        # Delete each snapshot
        print(f"Deleting {len(snapshots)} snapshots...")
        for snapshot in snapshots:
            print(f"Deleting snapshot {snapshot.id}")
            snapshot.delete()
        # There is no waiter for snapshot deletion. Add a small delay to guard
        # against any possible timing issues.
        time.sleep(2)

    def tag_snapshots(self, tags):
        snapshots = self.get_snapshots()
        for snapshot in snapshots:
            print(f"Tagging snapshot {snapshot.id}")
            snapshot.create_tags(Tags=tags)

    def untag_snapshots(self, tags):
        snapshots = self.get_snapshots()
        snapshot_ids = []
        for snapshot in snapshots:
            print(f"Un-tagging snapshot {snapshot.id}")
            snapshot_ids.append(snapshot.id)
        # Might as well un-tag on one big batch since snapshot objects don't
        # have direct support for un-tagging.
        self._ec2_client.delete_tags(Resources=snapshot_ids, Tags=tags)

    def get_subnet(self):
        """
        Get subnet belonging to this cluster.

        Args:
            none
        Returns:
            subnet
        """
        self._logger.debug("method_call: get_subnet")
        fs = FilterSet(self.get_cluster_filter())
        filters = fs.to_list()
        subnets = self._ec2.subnets.filter(Filters=filters)
        subnet_list = list(subnets.limit(self._MAX_ITEMS))
        # There should only be one subnet per cluster
        if len(subnet_list) > 1:
            raise Exception("Error (get_subnet): more than one subnet returned.")
        subnet = subnet_list[0]
        return subnet

    def tag_subnet(self, tags):
        subnet = self.get_subnet()
        print(f"Tagging subnet {subnet.id}")
        subnet.create_tags(Tags=tags)

    def untag_subnet(self, tags):
        subnet = self.get_subnet()
        print(f"Un-tagging subnet {subnet.id}")
        self._ec2_client.delete_tags(Resources=[subnet.id], Tags=tags)
