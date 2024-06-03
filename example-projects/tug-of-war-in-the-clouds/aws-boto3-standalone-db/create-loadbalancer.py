import boto3

################################################################################################
#
# Configuration Parameters
#
################################################################################################


# place your credentials in ~/.aws/credentials, as mentioned in AWS Educate Classroom,
# Account Details, AWC CLI -> Show (Copy and paste the following into ~/.aws/credentials)

# changed to use us-east, to be able to use AWS Educate Classroom
region = 'us-east-1'
availabilityZone1 = 'us-east-1a'
availabilityZone2 = 'us-east-1b'
availabilityZone3 = 'us-east-1c'
# region = 'eu-central-1'
# availabilityZone = 'eu-central-1b'

# AMI ID of Amazon Linux 2 image 64-bit x86 in us-east-1 (can be retrieved, e.g., at
# https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#LaunchInstanceWizard:)
imageId = 'ami-0d5eff06f840b45e9'
# for eu-central-1, AMI ID of Amazon Linux 2 would be:
# imageId = 'ami-0cc293023f983ed53'

# potentially change instanceType to t2.micro for "free tier" if using a regular account
# for production, t3.nano seams better
# as of SoSe 2022 t2.nano seams to be a bit too low on memory, mariadb first start can fail
# due to innodb cache out of memory, therefore t2.micro or swap in t2.nano currently recommended
# instanceType = 't2.nano'
instanceType = 't2.micro'

# keyName = 'srieger-pub'
keyName = 'vockey'


################################################################################################
#
# boto3 code
#
################################################################################################


client = boto3.setup_default_session(region_name=region)
ec2Client = boto3.client("ec2")
ec2Resource = boto3.resource('ec2')

# if you only have one VPC, vpc_id can be retrieved using:
response = ec2Client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
# if you have more than one VPC, vpc_id should be specified, and code
# top retrieve VPC id below needs to be commented out
# vpc_id = 'vpc-eedd4187'

subnet_id1 = ec2Client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone', 'Values': [availabilityZone1]
        }
    ])['Subnets'][0]['SubnetId']

subnet_id2 = ec2Client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone', 'Values': [availabilityZone2]
        }
    ])['Subnets'][0]['SubnetId']

subnet_id3 = ec2Client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone', 'Values': [availabilityZone3]
        }
    ])['Subnets'][0]['SubnetId']


response = ec2Client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['tug-of-war']}])
security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId', '')

elbv2Client = boto3.client('elbv2')

response = elbv2Client.create_load_balancer(
    Name='tug-of-war-loadbalancer',
    Subnets=[
        subnet_id1,
        subnet_id2,
        subnet_id3
    ],
    SecurityGroups=[
        security_group_id
    ]
)

loadbalancer_arn = response.get('LoadBalancers', [{}])[0].get('LoadBalancerArn', '')
loadbalancer_dns = response.get('LoadBalancers', [{}])[0].get('DNSName', '')

response = elbv2Client.create_target_group(
    Name='tug-of-war-targetgroup',
    Port=80,
    Protocol='HTTP',
    VpcId=vpc_id,
)

targetgroup_arn = response.get('TargetGroups', [{}])[0].get('TargetGroupArn', '')

response = elbv2Client.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': targetgroup_arn,
            'Type': 'forward',
        },
    ],
    LoadBalancerArn=loadbalancer_arn,
    Port=80,
    Protocol='HTTP',
)

response = elbv2Client.modify_target_group_attributes(
    TargetGroupArn=targetgroup_arn,
    Attributes=[
        {
            'Key': 'stickiness.enabled',
            'Value': 'true'
        },
    ]
)

print("Registering instances...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag:tug-of-war', 'Values': ['webserver']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running" or instance['State']['Name'] == "pending":
            response = elbv2Client.register_targets(
                TargetGroupArn=targetgroup_arn,
                Targets=[
                    {
                        'Id': instance['InstanceId'],
                    },
                ],
            )

print('Waiting for Load Balancer to become available...')

waiter = elbv2Client.get_waiter('load_balancer_available')
waiter.wait(LoadBalancerArns=[loadbalancer_arn])
print('Load Balancer should be reachable at: http://' + loadbalancer_dns)
