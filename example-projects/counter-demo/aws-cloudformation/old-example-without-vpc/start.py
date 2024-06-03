import boto3


################################################################################################
#
# Configuration Parameters
#
################################################################################################


# region = 'eu-central-1'
region = 'us-east-1'
stackName = 'cloudcomp-counter-demo-stack'
keyName = 'srieger-pub'

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!
# !!! You must change vpc, subnet and availability zone below to match your zone, or use the
# !!! start-with-vpc.py example, that creates and looks up all depedencies / necessary
# !!! resources.
# !!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
cfClient = boto3.client('cloudformation')

templateFile = open("cloudcomp-counter-demo.json", "r")
templateBody = templateFile.read()

print("Deleting old stack...")
print("------------------------------------")
response = cfClient.delete_stack(
    StackName=stackName,
)

print("creating new stack...")
print("------------------------------------")

response = cfClient.create_stack(
    StackName=stackName,
    TemplateBody=templateBody,
    Parameters=[
        {
            'ParameterKey': 'paramKeyPair',
            'ParameterValue': keyName
        },
        {
            'ParameterKey': 'paramVPC',
            'ParameterValue': 'vpc-eedd4187'
        },
        {
            'ParameterKey': 'paramAvailabilityZones',
            'ParameterValue': 'eu-central-1a, eu-central-1b, eu-central-1c',
        },
        {
            'ParameterKey': 'paramSubnetIDs',
            'ParameterValue': 'subnet-5c5f6d16, subnet-41422b28, subnet-6f2ea214',
        },
    ],
)
