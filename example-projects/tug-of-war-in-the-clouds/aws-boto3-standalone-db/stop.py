import time
import boto3
from botocore.exceptions import ClientError


################################################################################################
#
# Configuration Parameters
#
################################################################################################


region = 'us-east-1'
# region = 'eu-central-1'


################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
ec2Client = boto3.client("ec2")
ec2Resource = boto3.resource('ec2')

elbv2Client = boto3.client('elbv2')

print("Deleting load balancer and deps...")
print("------------------------------------")

try:
    response = elbv2Client.describe_load_balancers(Names=['tug-of-war-loadbalancer'])
    loadbalancer_arn = response.get('LoadBalancers', [{}])[0].get('LoadBalancerArn', '')
    response = elbv2Client.delete_load_balancer(LoadBalancerArn=loadbalancer_arn)
except ClientError as e:
    print(e)

time.sleep(5)

try:
    response = elbv2Client.describe_target_groups(Names=['tug-of-war-targetgroup'])
    targetgroup_arn = response.get('TargetGroups', [{}])[0].get('TargetGroupArn', '')
    response = elbv2Client.delete_target_group(TargetGroupArn=targetgroup_arn)
except ClientError as e:
    print(e)



print("Deleting instances...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['tug-of-war']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running" or instance['State']['Name'] == "pending":
            response = ec2Client.terminate_instances(InstanceIds=[instance['InstanceId']])
            print(response)
            instanceToTerminate = ec2Resource.Instance(instance['InstanceId'])
            instanceToTerminate.wait_until_terminated()

print("Delete security group...")
print("------------------------------------")

try:
    response = ec2Client.delete_security_group(GroupName='tug-of-war')
except ClientError as e:
    print(e)
