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

response = ec2Client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

elbv2Client = boto3.client('elbv2')
asClient = boto3.client('autoscaling')

print("Deleting auto scaling group...")
print("------------------------------------")

try:
    response = asClient.delete_auto_scaling_group(AutoScalingGroupName='tug-of-war-asg-autoscalinggroup', ForceDelete=True)
except ClientError as e:
    print(e)

print("Deleting launch configuration...")
print("------------------------------------")

try:
    response = asClient.delete_launch_configuration(LaunchConfigurationName='tug-of-war-asg-launchconfig')
except ClientError as e:
    print(e)



print("Deleting instances...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['tug-of-war-asg']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running":
            response = ec2Client.terminate_instances(InstanceIds=[instance['InstanceId']])
            print(response)
            instanceToTerminate = ec2Resource.Instance(instance['InstanceId'])
            instanceToTerminate.wait_until_terminated()


print("Deleting load balancer and deps...")
print("------------------------------------")

try:
    response = elbv2Client.describe_load_balancers(Names=['tug-of-war-asg-loadbalancer'])
    loadbalancer_arn = response.get('LoadBalancers', [{}])[0].get('LoadBalancerArn', '')
    response = elbv2Client.delete_load_balancer(LoadBalancerArn=loadbalancer_arn)

    waiter = elbv2Client.get_waiter('load_balancers_deleted')
    waiter.wait(LoadBalancerArns=[loadbalancer_arn])
except ClientError as e:
    print(e)

try:
    response = elbv2Client.describe_target_groups(Names=['tug-of-war-asg-targetgroup'])
    while len(response.get('TargetGroups', [{}])) > 0:
        targetgroup_arn = response.get('TargetGroups', [{}])[0].get('TargetGroupArn', '')
        try:
            response = elbv2Client.delete_target_group(TargetGroupArn=targetgroup_arn)
        except ClientError as e:
            print(e)
        response = elbv2Client.describe_target_groups(Names=['tug-of-war-asg-targetgroup'])
        time.sleep(5)
except ClientError as e:
    print(e)

print("Delete security group...")
print("------------------------------------")

try:
    response = ec2Client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['tug-of-war-asg']}])
    while len(response.get('SecurityGroups', [{}])) > 0:
        security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId', '')
        try:
            response = ec2Client.delete_security_group(GroupName='tug-of-war-asg')
        except ClientError as e:
            print(e)
        response = ec2Client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['tug-of-war-asg']}])
        time.sleep(5)
except ClientError as e:
    print(e)
