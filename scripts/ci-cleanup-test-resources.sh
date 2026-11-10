#!/usr/bin/env bash
# Delete EBS volumes and snapshots that the acceptance tests leave behind.
#
# The testing account is shared with other work. This script deletes ONLY
# resources that can belong to nothing but the tagmania test stack:
#
#   1. Available volumes tagged TagmaniaTestStack=<stack name>.
#      template.yaml propagates this tag to each test instance's root volume.
#      A snapshot restore detaches the root volume and does not delete it,
#      because it has no automation_key tag.
#   2. Available volumes and all snapshots that tagmania made for the test
#      clusters: automation_key=SNAPSHOT_MANAGER, Cluster in the test cluster
#      names, AND Instance in the template's instance names.
#
# Volumes that are attached ("in-use") are never touched.
#
# Run it only while the job holds the testing-stack concurrency group, so no
# other run can be mid-test.
#
# Usage: ci-cleanup-test-resources.sh <stack-name> [region]
# Set DRY_RUN=1 to list the resources without deleting them.

set -euo pipefail

STACK_NAME="${1:?usage: $0 <stack-name> [region]}"
REGION="${2:-${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}}"
DRY_RUN="${DRY_RUN:-0}"

# Keep these in sync with template.yaml (parameter defaults and Name tags).
TEST_CLUSTERS="test1,test2,test3"
TEST_INSTANCES="test1-web-01,test2-api-01,test2-db-01,test3-api-01"

ec2() { aws ec2 --region "$REGION" "$@"; }

stack_volumes=$(ec2 describe-volumes \
  --filters "Name=status,Values=available" \
            "Name=tag:TagmaniaTestStack,Values=${STACK_NAME}" \
  --query 'Volumes[].VolumeId' --output text)

restore_volumes=$(ec2 describe-volumes \
  --filters "Name=status,Values=available" \
            "Name=tag:automation_key,Values=SNAPSHOT_MANAGER" \
            "Name=tag:Cluster,Values=${TEST_CLUSTERS}" \
            "Name=tag:Instance,Values=${TEST_INSTANCES}" \
  --query 'Volumes[].VolumeId' --output text)

test_snapshots=$(ec2 describe-snapshots --owner-ids self \
  --filters "Name=tag:automation_key,Values=SNAPSHOT_MANAGER" \
            "Name=tag:Cluster,Values=${TEST_CLUSTERS}" \
            "Name=tag:Instance,Values=${TEST_INSTANCES}" \
  --query 'Snapshots[].SnapshotId' --output text)

# --output text prints "None" for an empty list on some CLI versions.
volumes=$(printf '%s %s\n' "$stack_volumes" "$restore_volumes" \
  | tr -s '[:space:]' '\n' | grep -v -e '^$' -e '^None$' | sort -u || true)
snapshots=$(printf '%s\n' "$test_snapshots" \
  | tr -s '[:space:]' '\n' | grep -v -e '^$' -e '^None$' | sort -u || true)

echo "Leftover test volumes: $(printf '%s' "$volumes" | grep -c . || true)"
echo "Leftover test snapshots: $(printf '%s' "$snapshots" | grep -c . || true)"

failed=0
for id in $volumes; do
  echo "Deleting volume $id"
  if [ "$DRY_RUN" != "1" ]; then
    ec2 delete-volume --volume-id "$id" || failed=1
  fi
done
for id in $snapshots; do
  echo "Deleting snapshot $id"
  if [ "$DRY_RUN" != "1" ]; then
    ec2 delete-snapshot --snapshot-id "$id" || failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "::error::Could not delete some test resources; see the log above."
  exit 1
fi
