import json

import boto3


################################################################################################
#
# Configuration Parameters
#
################################################################################################


# region = 'eu-central-1'
region = 'us-east-1'
stackName = 'cloudcomp-counter-demo-stack'


################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
cfClient = boto3.client('cloudformation')

print("Showing stack...")
print("------------------------------------")
response = cfClient.describe_stacks(
    StackName=stackName,
)
print(json.dumps(response, indent=4, sort_keys=True, default=str))
