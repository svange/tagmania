import boto3

# Get a handle to the lambda client
lambda_client = boto3.client('lambda')

def get_lambda_arn (function_name):
    response = lambda_client.get_function(FunctionName=function_name)
    return response['Configuration']['FunctionArn']

def tag_lambda_functions(function_arns, tags):
    # tags = {'key': 'values'}
    for function_arn in function_arns:
        lambda_client.tag_resource(
            Resource=function_arn,
            Tags=tags
        )

def untag_lambda_functions(function_arns, keys):
    # keys = ['key', 'key', ...]
    for function_arn in function_arns:
        lambda_client.untag_resource(
            Resource=function_arn,
            TagKeys=keys
        )
