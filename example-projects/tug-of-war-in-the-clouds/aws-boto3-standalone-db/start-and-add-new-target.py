import time

import boto3
from botocore.exceptions import ClientError


################################################################################################
#
# Configuration Parameters
#
################################################################################################


# place your credentials in ~/.aws/credentials, as mentioned in AWS Educate Classroom,
# Account Details, AWC CLI -> Show (Copy and paste the following into ~/.aws/credentials)

# changed to use us-east, to be able to use AWS Educate Classroom
region = 'us-east-1'
availabilityZone = 'us-east-1b'
# region = 'eu-central-1'
# availabilityZone = 'eu-central-1b'

# AMI ID of Amazon Linux 2 image 64-bit x86 in us-east-1 (can be retrieved, e.g., at
# https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#LaunchInstanceWizard:)
# TODO update to recent version of Amazon Linux 2 AMI?
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

elbv2Client = boto3.client('elbv2')

response = ec2Client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['tug-of-war']}])
security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId', '')

print("Getting DB IP...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag:tug-of-war', 'Values': ['db']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running" or instance['State']['Name'] == "pending":
            instanceDB = ec2Resource.Instance(instance['InstanceId'])
            privateIpDB = instanceDB.private_ip_address

userDataWebServer = ('#!/bin/bash\n'
                     '# extra repo for RedHat rpms\n'
                     'yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm\n'
                     '# essential tools\n'
                     'yum install -y joe htop git\n'
                     '# mysql\n'
                     'yum install -y httpd php php-mysql\n'
                     '\n'
                     'service httpd start\n'
                     '\n'
                     # 'wget http://mmnet.informatik.hs-fulda.de/cloudcomp/tug-of-war-in-the-clouds.tar.gz\n'
                     # 'cp tug-of-war-in-the-clouds.tar.gz /var/www/html/\n'
                     # 'tar zxvf tug-of-war-in-the-clouds.tar.gz\n'
                     'cd /var/www/html\n'
                     'wget https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/example-projects/tug-of-war-in-the-clouds/web-content/index.php\n'
                     'wget https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/example-projects/tug-of-war-in-the-clouds/web-content/cloud.php\n'
                     'wget https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/example-projects/tug-of-war-in-the-clouds/web-content/config.php\n'
                     '\n'
                     '# change hostname of db connection\n'
                     'sed -i s/localhost/' + privateIpDB + '/g /var/www/html/config.php\n'
                     )


for i in range(3, 4):
    print("Running new Web Server instance (in additional availability zone)...")
    print("-----------------------------------------------------------------------------------------")

    response = ec2Client.run_instances(
        ImageId=imageId,
        InstanceType=instanceType,
        Placement={'AvailabilityZone': availabilityZone, },
        KeyName=keyName,
        MinCount=1,
        MaxCount=1,
        UserData=userDataWebServer,
        SecurityGroupIds=[
            security_group_id,
        ],

        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': 'tug-of-war-webserver' + str(i)},
                    {'Key': 'tug-of-war', 'Value': 'webserver'}
                ],
            }
        ],
    )

    instanceIdWeb = response['Instances'][0]['InstanceId']

    instance = ec2Resource.Instance(instanceIdWeb)
    instance.wait_until_running()
    instance.load()
    # sometimes even after reloading instance details, public IP cannot be retrieved using current boto3 version and
    # AWS Educate accounts, try for 10 secs, and ask user to get it from AWS console otherwise
    timeout = 10
    while instance.public_ip_address is None and timeout > 0:
        print("Waiting for public IP to become available...")
        instance.load()
        time.sleep(1)
        timeout -= 1
    if instance.public_ip_address is not None:
        print("tug-of-war-in-the-clouds can be accessed at: http://" + instance.public_ip_address)
    else:
        print("Could not get public IP using boto3, this is likely an AWS Educate problem. You can however lookup the "
              "public ip from the AWS management console.")

print("Registering instance in load balancer, load balancer has to be already created...")
print("-----------------------------------------------------------------------------------------")

try:
    response = elbv2Client.describe_target_groups(Names=['tug-of-war-targetgroup'])
    targetgroup_arn = response.get('TargetGroups', [{}])[0].get('TargetGroupArn', '')
except ClientError as e:
    print(e)

response = elbv2Client.register_targets(
    TargetGroupArn=targetgroup_arn,
    Targets=[
        {
            'Id': instanceIdWeb,
        },
    ],
)
