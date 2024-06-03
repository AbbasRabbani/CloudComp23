from datetime import date
import boto3
from botocore.exceptions import ClientError

################################################################################################
#
# Configuration Parameters
#
################################################################################################

endpoint_url = "http://localhost.localstack.cloud:4566"

groupNr = 22
currentYear = date.today().year
globallyUniqueS3GroupBucketName = "cloudcomp-counter-" + str(currentYear) + "-group" + str(groupNr)

# region = 'eu-central-1'
region = 'us-east-1'
functionName = 'cloudcomp-counter-lambda-demo'

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
s3Client = boto3.client('s3')
s3Resource = boto3.resource('s3', endpoint_url=endpoint_url)
lClient = boto3.client('lambda', endpoint_url=endpoint_url)
apiClient = boto3.client("apigatewayv2", endpoint_url=endpoint_url)


print("Deleting old API gateway...")
print("------------------------------------")
response = apiClient.get_apis()
for api in response["Items"]:
    if api["Name"] == functionName + '-api':
        responseDelete = apiClient.delete_api(
            ApiId=api["ApiId"]
        )

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
