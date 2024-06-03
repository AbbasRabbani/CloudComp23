from datetime import date
import json
import boto3

################################################################################################
#
# Configuration Parameters
#
################################################################################################

endpoint_url = "http://localhost.localstack.cloud:4566"

# region = 'eu-central-1'
region = 'us-east-1'
functionName = 'cloudcomp-counter-lambda-demo'


################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
lClient = boto3.client('lambda', endpoint_url=endpoint_url)


print("Invoking function...")
print("------------------------------------")
try:
    response = lClient.invoke(
        FunctionName=functionName,
        Payload='{ "input": "1" }'
    )
except lClient.exceptions.ResourceNotFoundException:
    print('Function not available.')

streamingBody = response['Payload']
result = streamingBody.read()
jsonResult = json.loads(result)

print(json.dumps(response, indent=4, sort_keys=True, default=str))

print('Payload:\n' + str(result) + "\n")

print("Counter is now at: " + jsonResult['headers']['x-hsfd-counter'])
