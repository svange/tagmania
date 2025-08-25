#!/bin/bash
# Cleanup script for test resources left behind in AWS

set -e

echo "Cleaning up test CloudFormation stacks..."

# Find and delete all test stacks
aws cloudformation describe-stacks --query "Stacks[?contains(StackName, 'tagmania-testing')].StackName" --output text | while read stack; do
    if [ ! -z "$stack" ]; then
        echo "Deleting stack: $stack"
        aws cloudformation delete-stack --stack-name "$stack" || true
        echo "Waiting for stack deletion..."
        aws cloudformation wait stack-delete-complete --stack-name "$stack" || true
    fi
done

echo "Cleanup complete!"
