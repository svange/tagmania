# Tagmania Examples

Real-world usage patterns. Each example assumes:

- You have the [Minimum IAM Policy](README.md#minimum-iam-policy) attached to whatever AWS identity you're using.
- Your EC2 instances carry a `Cluster` tag that matches the name you pass.
- Your instance `Name` tags are set -- targeted restores and log output both depend on them.

---

## 1. Back up and restore a whole cluster

Back up every attached EBS volume on every instance in a cluster, then restore from the same snapshot set later.

```bash
# Take a named snapshot of the whole cluster.
# This stops instances first, snapshots all attached volumes, then leaves
# instances stopped. Start them again with cluster-start.
cluster-snap --backup --name pre-upgrade my-cluster

# ... do risky work ...

# Roll every volume back to the snapshot set. Again, leaves instances stopped.
cluster-snap --restore --name pre-upgrade my-cluster
cluster-start my-cluster
```

What happens during restore:

1. Stop every instance in `my-cluster`.
2. Detach every managed volume.
3. Delete the detached volumes.
4. Create fresh volumes from the snapshots tagged `Label=pre-upgrade`.
5. Attach the new volumes back to their original instance + device.

Instances stay stopped at the end -- you run `cluster-start` when you're ready to bring the cluster back up. This gives you a chance to verify volumes are attached correctly before boot.

---

## 2. Targeted restore with a regex

Restore only a subset of the cluster -- handy when one service is misbehaving but you don't want to roll everything back.

```bash
# Roll back only the web tier. The regex matches against the Name tag.
cluster-snap --restore --target ".*-web-.*" --name pre-upgrade my-cluster

# Roll back a specific instance by exact name.
cluster-snap --restore --target "my-cluster-db-01" --name pre-upgrade my-cluster
```

Common patterns:

| Pattern | Matches |
|---------|---------|
| `".*-web-.*"` | any instance whose Name contains `-web-` |
| `"worker-[0-9]+"` | `worker-1`, `worker-2`, ... |
| `"prod-api-.*"` | every prod API box |
| `"db-01"` | exactly the one DB box named `db-01` |

The CLI prints the list of matched instances and asks for `yes` before touching anything.

---

## 3. Scheduled overnight snapshots via cron

Back up a dev cluster every night, keeping only the last snapshot per label. Tagmania's `--backup --name X` overwrites any prior snapshot set that shares the same label, so you get one rolling snapshot per label without any extra bookkeeping.

```bash
# ~/.aws/credentials or an instance role must provide the AWS identity.
# Example crontab entry -- nightly at 2am UTC:
0 2 * * * /usr/local/bin/cluster-snap --backup --name nightly dev-cluster
```

Notes:

- This replaces the `nightly` snapshot set every night -- you keep one-deep history.
- To keep a week of rolling history, schedule seven jobs with day-of-week labels:

  ```cron
  0 2 * * 0 /usr/local/bin/cluster-snap --backup --name sun dev-cluster
  0 2 * * 1 /usr/local/bin/cluster-snap --backup --name mon dev-cluster
  # ... through Saturday
  ```

- `cluster-snap --backup` stops instances before snapshotting. For a dev cluster that's usually fine. For a production cluster, plan maintenance windows around this.

---

## 4. Cross-region snapshots -- what doesn't work

Tagmania operates within whatever region the AWS CLI profile points to. **EBS snapshots are region-scoped**, and Tagmania does not copy snapshots across regions.

If you need cross-region disaster-recovery copies, do the copy yourself with the AWS CLI after Tagmania runs:

```bash
# Take snapshots in the primary region.
cluster-snap --backup --name dr-primary my-cluster --profile us-east-1

# Use aws ec2 copy-snapshot to replicate each snapshot to the DR region.
# Tagmania's snapshots carry automation_key=SNAPSHOT_MANAGER and
# Label=dr-primary, so you can filter to just the ones you care about:
aws --profile us-east-1 ec2 describe-snapshots \
  --filters "Name=tag:automation_key,Values=SNAPSHOT_MANAGER" \
            "Name=tag:Label,Values=dr-primary" \
  --query 'Snapshots[].SnapshotId' --output text \
  | xargs -n1 -I{} aws --profile us-east-1 ec2 copy-snapshot \
      --source-region us-east-1 \
      --destination-region us-west-2 \
      --source-snapshot-id {}
```

Restoring in the DR region would require creating a matching cluster there (same `Cluster` tag), then manually attaching volumes created from the copied snapshots -- Tagmania's restore assumes the source snapshots live in the same region as the target cluster.
