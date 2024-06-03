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

print("Deleting stack...")
print("------------------------------------")
response = cfClient.delete_stack(
    StackName=stackName,
)