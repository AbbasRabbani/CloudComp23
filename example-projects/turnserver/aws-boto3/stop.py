import boto3
from botocore.exceptions import ClientError


region = 'eu-central-1'

client = boto3.setup_default_session(region_name=region)
ec2Client = boto3.client("ec2")
ec2Resource = boto3.resource('ec2')

response = ec2Client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

print("Deleting old instance...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['coturn']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running" or instance['State']['Name'] == "pending":
            response = ec2Client.terminate_instances(InstanceIds=[instance['InstanceId']])
            print(response)
            instanceToTerminate = ec2Resource.Instance(instance['InstanceId'])
            instanceToTerminate.wait_until_terminated()

print("Delete old security group...")
print("------------------------------------")

try:
    response = ec2Client.delete_security_group(GroupName='coturn')
except ClientError as e:
    print(e)

print("Delete old elastic ips...")
print("------------------------------------")

try:
    response = ec2Client.describe_addresses(Filters=[{'Name': 'tag-key', 'Values': ['coturn']}])
    addresses = response['Addresses']
    for address in addresses:
        ec2Client.release_address(AllocationId=address['AllocationId'])
except ClientError as e:
    print(e)

