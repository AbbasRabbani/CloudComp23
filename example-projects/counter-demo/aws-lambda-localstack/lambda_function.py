# import json
import base64
import os
import boto3


def lambda_handler(event, context):
    print('## ENVIRONMENT VARIABLES')
    print(os.environ)
    print('## EVENT')
    print(event)

    globally_unique_s3_group_bucket_name = os.environ.get("bucketName")
    print('Trying to access bucket: ' + globally_unique_s3_group_bucket_name)

    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=globally_unique_s3_group_bucket_name, Key='us-east-1')

    counter = int(response['Body'].read().decode('utf-8'))

    debug = ""
    incr = 0
    if 'body' in event:
        body = str(base64.b64decode(event['body']).decode("utf-8"))
        if body.startswith('input'):
            incr = int(body.rsplit('=')[1])
    elif 'input' in event:
        incr = int(event['input'])

    if incr is not 0:
        counter = counter + incr
        response = s3_client.put_object(Bucket=globally_unique_s3_group_bucket_name, Key='us-east-1', Body=str(counter))

    output = ('<html><head><title>Counter Demo</title>\n'
              # '<meta http-equiv="refresh" content="5"/></head><body>\n'
              '<h2>HS Fulda Cloud Computing - Counter Demo</h2>\n'
              '<p><b>HTML-Output:</b> ' + str(counter) + '</p></body>\n'
              '<form method=POST action="">\n'
              '<input type="hidden" name="input" value="1">\n'
              '<input type="submit" value="Increment"></form>\n'
              # '<hr><b>Lambda Event:</b><br>' + repr(event) + '\n'
              # '<hr><b>Lambda Context:</b><br>' + repr(context) + '\n'
              '</body></html>\n')

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'x-hsfd-counter': str(counter)
        },
        'body': output
    }
