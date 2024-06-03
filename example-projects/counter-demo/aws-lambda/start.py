from datetime import date
import zipfile
import boto3
from botocore.exceptions import ClientError

################################################################################################
#
# Configuration Parameters
#
################################################################################################

# a bucket in S3 will be created to store the counter bucket names need to be world-wide unique ;)
# Hence we create a bucket name that contains your group number and the current year.
# The counter will be stores as key (file) "us-east-1" in the bucket (same name as our default region)
# in the bucket and expects a number in it to increase
groupNr = 22
currentYear = date.today().year

globallyUniqueS3GroupBucketName = "cloudcomp-counter-" + str(currentYear) + "-group" + str(groupNr)

# region = 'eu-central-1'
region = 'us-east-1'
functionName = 'cloudcomp-counter-lambda-demo'

# The Lambda function will run using privileges of a role, that allows the function to access/create
# resources in AWS (in this case read/write to S3). In AWS Academy you need to use the role that
# use created for your student account in the lab (see lab readme).
# see ARN for AWS Academy LabRole function here:
# https://us-east-1.console.aws.amazon.com/iamv2/home?region=us-east-1#/roles/details/LabRole?section=permissions
#
# roleArn = 'arn:aws:iam::309000625112:role/service-role/cloudcomp-counter-demo-role-6rs7pah3'
# roleArn = 'arn:aws:iam::919927306708:role/cloudcomp-s3-access'
# roleArn = 'arn:aws:iam::488766701848:role/LabRole'

# standard name for role in AWS Academy lab created by vocareum is "LabRole". See README of the
# lab. The following code will lookup the AWS Resource Name (ARN) (sort of the ID for this role)
# that has the following name:
roleName = "LabRole"

################################################################################################
#
# boto3 code
#
################################################################################################


def cleanup_s3_bucket(s3_bucket):
    # Deleting objects
    for s3_object in s3_bucket.objects.all():
        s3_object.delete()
    # Deleting objects versions if S3 versioning enabled
    for s3_object_ver in s3_bucket.object_versions.all():
        s3_object_ver.delete()


client = boto3.setup_default_session(region_name=region)
iamClient = boto3.client('iam')
s3Client = boto3.client('s3')
s3Resource = boto3.resource('s3')
lClient = boto3.client('lambda')
apiClient = boto3.client("apigatewayv2")

print("Getting AWS Academy LabRole ARN...")
print("------------------------------------")
response = iamClient.list_roles()
for role in response["Roles"]:
    if role["RoleName"] == roleName:
        roleArn = role["Arn"]
        print(roleArn)

print("Deleting old function...")
print("------------------------------------")
try:
    response = lClient.delete_function(
        FunctionName=functionName,
    )
except lClient.exceptions.ResourceNotFoundException:
    print('Function not available. No need to delete it.')

print("Deleting old bucket...")
print("------------------------------------")

try:
    currentBucket = s3Resource.Bucket(globallyUniqueS3GroupBucketName)
    cleanup_s3_bucket(currentBucket)
    currentBucket.delete()
except ClientError as e:
    print(e)

print("creating S3 bucket (must be globally unique)...")
print("------------------------------------")

try:
    response = s3Client.create_bucket(Bucket=globallyUniqueS3GroupBucketName)
    response = s3Client.put_object(Bucket=globallyUniqueS3GroupBucketName, Key='us-east-1', Body=str(0))
except ClientError as e:
    print(e)

print("creating new function...")
print("------------------------------------")

zf = zipfile.ZipFile('lambda-deployment-archive.zip', 'w', zipfile.ZIP_DEFLATED)
zf.write('lambda_function.py')
zf.close()

lambdaFunctionARN = ""
with open('lambda-deployment-archive.zip', mode='rb') as file:
    zipfileContent = file.read()

    response = lClient.create_function(
        FunctionName=functionName,
        Runtime='python3.9',
        Role=roleArn,
        Code={
            'ZipFile': zipfileContent
        },
        Handler='lambda_function.lambda_handler',
        Publish=True,
        Environment={
            'Variables': {
                'bucketName': globallyUniqueS3GroupBucketName
            }
        }
    )
    lambdaFunctionARN = response['FunctionArn']

print("Lambda Function and S3 Bucket to store the counter are available. Sadly, AWS Academy labs do not allow\n"
      "creating an API gateway to be able to access the Lambda function directly via HTTP from the browser, as\n"
      "shown in https://348yxdily0.execute-api.eu-central-1.amazonaws.com/default/cloudcomp-counter-demo.\n"
      "\n"
      "However you can now run invoke-function.py to view an increment the counter. You can also use \n"
      "the test button in the Lambda AWS console. In this case you need to send the content\n"
      "\n"
      "{\n"
      "  \"input\": \"1\"\n"
      "}\n"
      "\n"
      "to increment the counter by 1.\n"
      "Try to understand how Lambda can be used to cut costs regarding cloud services and what its pros\n"
      "and cons are.\n")

# sadly, AWS Academy Labs don't allow API gateways
# API gateway would allow getting an HTTP endpoint that we could access directly in the browser,
# that would call our function, as in the provided demo:
#
# https://348yxdily0.execute-api.eu-central-1.amazonaws.com/default/cloudcomp-counter-demo
#
# print("creating API gateway...")
# print("------------------------------------")
#
# response = apiClient.create_api(
#     Name=functionName + '-api',
#     ProtocolType='HTTP',
#     Target=lambdaFunctionARN
# )
