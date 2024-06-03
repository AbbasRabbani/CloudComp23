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
availabilityZone = 'us-east-1a'
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

# if you only have one VPC, vpc_id can be retrieved using:
response = ec2Client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
# if you have more than one VPC, vpc_id should be specified, and code
# top retrieve VPC id below needs to be commented out
# vpc_id = 'vpc-eedd4187'

subnet_id = ec2Client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone', 'Values': [availabilityZone]
        }
    ])['Subnets'][0]['SubnetId']

print("Deleting old instance...")
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

print("Delete old security group...")
print("------------------------------------")

try:
    response = ec2Client.delete_security_group(GroupName='tug-of-war')
except ClientError as e:
    print(e)

print("Create security group...")
print("------------------------------------")

try:
    response = ec2Client.create_security_group(GroupName='tug-of-war',
                                               Description='tug-of-war',
                                               VpcId=vpc_id)
    security_group_id = response['GroupId']
    print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

    data = ec2Client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 3306,
             'ToPort': 3306,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 443,
             'ToPort': 443,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])
    print('Ingress Successfully Set %s' % data)
except ClientError as e:
    print(e)


userDataDB = ('#!/bin/bash\n'
              '# extra repo for RedHat rpms\n'
              'yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm\n'
              '# essential tools\n'
              'yum install -y joe htop git\n'
              '# mysql\n'
              'yum install -y mariadb mariadb-server\n'
              '\n'
              'service mariadb start\n'
              '\n'
              'echo "create database cloud_tug_of_war" | mysql -u root\n'
              '\n'
              'echo "create table clouds ( cloud_id INT AUTO_INCREMENT, name VARCHAR(255) NOT NULL, value INT, max_value INT, PRIMARY KEY (cloud_id))" | mysql -u root cloud_tug_of_war\n'
              '\n'
              'echo "CREATE USER \'cloud_tug_of_war\'@\'%\' IDENTIFIED BY \'cloudpass\';" | mysql -u root\n'
              'echo "GRANT ALL PRIVILEGES ON cloud_tug_of_war.* TO \'cloud_tug_of_war\'@\'%\';" | mysql -u root\n'
              'echo "FLUSH PRIVILEGES" | mysql -u root\n'
              )
# convert user-data from script with: cat install-mysql | sed "s/^/'/; s/$/\\\n'/"

print("Running new DB instance...")
print("------------------------------------")

response = ec2Client.run_instances(
    ImageId=imageId,
    InstanceType=instanceType,
    Placement={'AvailabilityZone': availabilityZone, },
    KeyName=keyName,
    MinCount=1,
    MaxCount=1,
    UserData=userDataDB,
    SecurityGroupIds=[
        security_group_id,
    ],
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': 'tug-of-war-db1'},
                {'Key': 'tug-of-war', 'Value': 'db'}
            ],
        }
    ],
)

instanceIdDB = response['Instances'][0]['InstanceId']
privateIpDB = response['Instances'][0]['PrivateIpAddress']
# privateIpDB = response['Instances'][0]['NetworkInterfaces'][0]['NetworkInterfaceId']

print("Using private IP to connect to the db: " + privateIpDB);

instance = ec2Resource.Instance(instanceIdDB)
instance.wait_until_running()

print(instanceIdDB)

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

for i in range(1, 3):
    print("Running new Web Server instance...")
    print("------------------------------------")

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
        print("Using AWS Academy Lab you should be able to login as shown in the lab README using:")
        print("ssh -i ~/.ssh/labsuser.pem ec2-user@" + instance.public_ip_address)
    else:
        print("Could not get public IP using boto3, this is likely an AWS Educate problem. You can however lookup the "
              "public ip from the AWS management console.")
