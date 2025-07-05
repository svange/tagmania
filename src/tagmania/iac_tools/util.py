from functools import lru_cache
import boto3
import os

@lru_cache  # cache the client the first time we ask for it
def _lambda_client():
    # Fall back to env-var or default region so boto3 never errors
    return boto3.client("lambda", region_name=os.getenv("AWS_REGION", "us-east-1"))

def get_lambda_arn(function_name: str) -> str:
    response = _lambda_client().get_function(FunctionName=function_name)
    return response["Configuration"]["FunctionArn"]

def tag_lambda_functions(function_arns, tags):
    client = _lambda_client()
    for arn in function_arns:
        client.tag_resource(Resource=arn, Tags=tags)

def untag_lambda_functions(function_arns, keys):
    client = _lambda_client()
    for arn in function_arns:
        client.untag_resource(Resource=arn, TagKeys=keys)
