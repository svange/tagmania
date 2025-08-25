#!/bin/bash
# Deep cleanup script for AWS test resources including VPCs and IGWs
# WARNING: This will delete ALL test-related resources

set -e

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
echo "Performing deep cleanup in region: $REGION"

# Clean up ALL tagmania test stacks
echo "Finding and deleting all tagmania test stacks..."
aws cloudformation describe-stacks --region $REGION --query "Stacks[?contains(StackName, 'tagmania')].StackName" --output text 2>/dev/null | while read stack; do
    if [ ! -z "$stack" ]; then
        echo "Deleting stack: $stack"
        aws cloudformation delete-stack --region $REGION --stack-name "$stack" || true
        echo "Waiting for stack deletion..."
        aws cloudformation wait stack-delete-complete --region $REGION --stack-name "$stack" 2>/dev/null || true
    fi
done

# Clean up orphaned VPCs with tagmania tags
echo "Finding orphaned VPCs with tagmania tags..."
aws ec2 describe-vpcs --region $REGION --filters "Name=tag-key,Values=aws:cloudformation:stack-name" --query "Vpcs[?Tags[?contains(Value, 'tagmania')]].VpcId" --output text 2>/dev/null | while read vpc; do
    if [ ! -z "$vpc" ]; then
        echo "Found orphaned VPC: $vpc"

        # Delete associated IGWs first
        aws ec2 describe-internet-gateways --region $REGION --filters "Name=attachment.vpc-id,Values=$vpc" --query "InternetGateways[].InternetGatewayId" --output text 2>/dev/null | while read igw; do
            if [ ! -z "$igw" ]; then
                echo "  Detaching and deleting IGW: $igw"
                aws ec2 detach-internet-gateway --region $REGION --internet-gateway-id "$igw" --vpc-id "$vpc" 2>/dev/null || true
                aws ec2 delete-internet-gateway --region $REGION --internet-gateway-id "$igw" 2>/dev/null || true
            fi
        done

        # Delete subnets
        aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$vpc" --query "Subnets[].SubnetId" --output text 2>/dev/null | while read subnet; do
            if [ ! -z "$subnet" ]; then
                echo "  Deleting subnet: $subnet"
                aws ec2 delete-subnet --region $REGION --subnet-id "$subnet" 2>/dev/null || true
            fi
        done

        # Delete route tables (except main)
        aws ec2 describe-route-tables --region $REGION --filters "Name=vpc-id,Values=$vpc" --query "RouteTables[?Associations[0].Main != \`true\`].RouteTableId" --output text 2>/dev/null | while read rt; do
            if [ ! -z "$rt" ]; then
                echo "  Deleting route table: $rt"
                aws ec2 delete-route-table --region $REGION --route-table-id "$rt" 2>/dev/null || true
            fi
        done

        # Delete security groups (except default)
        aws ec2 describe-security-groups --region $REGION --filters "Name=vpc-id,Values=$vpc" --query "SecurityGroups[?GroupName != 'default'].GroupId" --output text 2>/dev/null | while read sg; do
            if [ ! -z "$sg" ]; then
                echo "  Deleting security group: $sg"
                aws ec2 delete-security-group --region $REGION --group-id "$sg" 2>/dev/null || true
            fi
        done

        # Finally delete the VPC
        echo "  Deleting VPC: $vpc"
        aws ec2 delete-vpc --region $REGION --vpc-id "$vpc" 2>/dev/null || true
    fi
done

echo "Deep cleanup complete!"

# Show current resource counts
echo ""
echo "Current resource counts:"
vpc_count=$(aws ec2 describe-vpcs --region $REGION --query "length(Vpcs)" --output text 2>/dev/null || echo "unknown")
igw_count=$(aws ec2 describe-internet-gateways --region $REGION --query "length(InternetGateways)" --output text 2>/dev/null || echo "unknown")
stack_count=$(aws cloudformation describe-stacks --region $REGION --query "length(Stacks[?contains(StackName, 'tagmania')])" --output text 2>/dev/null || echo "0")

echo "VPCs: $vpc_count"
echo "Internet Gateways: $igw_count"
echo "Tagmania stacks: $stack_count"
