import boto3


################################################################################################
#
# Configuration Parameters
#
################################################################################################

# place your credentials in ~/.aws/credentials, as mentioned in AWS Educate Classroom,
# Account Details, AWC CLI -> Show (Copy and paste the following into ~/.aws/credentials)

# !!! you also need to specify an IAM role for this example to able to access S3 !!!


# region = 'eu-central-1'
region = 'us-east-1'
stackName = 'cloudcomp-counter-demo-stack'
# keyName = 'srieger-pub'
keyName = 'vockey'
roleName = 'LabInstanceProfile'

################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
cfClient = boto3.client('cloudformation')

templateFile = open("cloudcomp-counter-demo-with-vpc.json", "r")
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
            'ParameterKey': 'paramIamInstanceRole',
            'ParameterValue': roleName
        },
    ],
)

print("You can observe the state of the stack using status.py, cli commands 'aws cloudformation ...' or the web "
      "console.")
