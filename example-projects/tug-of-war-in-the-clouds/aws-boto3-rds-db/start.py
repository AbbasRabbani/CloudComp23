import boto3
from botocore.exceptions import ClientError

################################################################################################
#
# Configuration Parameters
#
################################################################################################

# print("!!!!!!!! You cannot use RDS in AWS Educate Account !!!!!!!!")
# exit(-1)

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
# boto3 clients and resources (dependencies)
#
################################################################################################

client = boto3.setup_default_session(region_name=region)
ec2Client = boto3.client("ec2")
ec2Resource = boto3.resource('ec2')

rdsClient = boto3.client("rds")

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

################################################################################################
#
# boto3 code to deploy the application
#
################################################################################################

print("Deleting old instance...")
print("------------------------------------")

response = ec2Client.describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['tug-of-war-rds']}])
print(response)
reservations = response['Reservations']
for reservation in reservations:
    for instance in reservation['Instances']:
        if instance['State']['Name'] == "running" or instance['State']['Name'] == "pending":
            response = ec2Client.terminate_instances(InstanceIds=[instance['InstanceId']])
            print(response)
            instanceToTerminate = ec2Resource.Instance(instance['InstanceId'])
            instanceToTerminate.wait_until_terminated()

print("Deleting old DB instance...")
print("------------------------------------")

try:
   response = rdsClient.delete_db_instance(
       DBInstanceIdentifier='tug-of-war-rds-db1',
       SkipFinalSnapshot=True,
       DeleteAutomatedBackups=True
   )
except ClientError as e:
   print(e)

waiter = rdsClient.get_waiter('db_instance_deleted')
waiter.wait(DBInstanceIdentifier='tug-of-war-rds-db1')

#time.sleep(5)

print("Delete old security group...")
print("------------------------------------")

try:
   response = ec2Client.delete_security_group(GroupName='tug-of-war-rds')
except ClientError as e:
   print(e)

print("Create security group...")
print("------------------------------------")

try:
   response = ec2Client.create_security_group(GroupName='tug-of-war-rds',
                                              Description='tug-of-war-rds',
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

print("Running new DB instance...")
print("------------------------------------")
print("...can take 10s of minutes using free AWS accounts and also takes substantially more time compared to"
      " creating an EC2 instance also for payed accounts.")

# TODO potentially upgrade to recent RDS instance types (t4g.small or t3.small), possibly switch to mariadb or aurora
response = rdsClient.create_db_instance(DBInstanceIdentifier="tug-of-war-rds-db1",
    AllocatedStorage=20,
    DBName='cloud_tug_of_war',
    # Engine='mariadb',
    Engine='mysql',
    # General purpose SSD
    StorageType='gp2',
    #StorageEncrypted=True,
    AutoMinorVersionUpgrade=True,
    # Set this to true later?
    MultiAZ=False,
    MasterUsername='cloud_tug_of_war',
    MasterUserPassword='cloudpass',
    VpcSecurityGroupIds=[security_group_id],
    # DBInstanceClass='db.m3.2xlarge',
    # DBInstanceClass='db.t3.micro',
    DBInstanceClass='db.t2.small',
    Tags=[
        {'Key': 'Name', 'Value': 'tug-of-war-rds-db1'},
        {'Key': 'tug-of-war-rds', 'Value': 'db'}
    ],
)

waiter = rdsClient.get_waiter('db_instance_available')
waiter.wait(DBInstanceIdentifier='tug-of-war-rds-db1')

response = ec2Client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': ['tug-of-war-rds']}])
security_group_id = response.get('SecurityGroups', [{}])[0].get('GroupId', '')

response = rdsClient.describe_db_instances(DBInstanceIdentifier='tug-of-war-rds-db1')
print(response)
dbEndpointAddress = response['DBInstances'][0]['Endpoint']['Address']
dbEndpointPort = response['DBInstances'][0]['Endpoint']['Port']

print(str(dbEndpointAddress) + ":" + str(dbEndpointPort))

userDataWebServer = ('#!/bin/bash\n'
                     '# extra repo for RedHat rpms\n'
                     'yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm\n'
                     '# essential tools\n'
                     'yum install -y joe htop git\n'
                     '# httpd and mysql client\n'
                     'yum install -y httpd mariadb\n'
                     '# fix php5.x PDO prob PDO::__construct(): Server sent charset (255) unknown to the client.\n'
                     '# by using Amazons Linux 2 PHP extras\n'
                     'amazon-linux-extras install -y php7.4\n'
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
                     'sed -i s/localhost/' + dbEndpointAddress + '/g /var/www/html/config.php\n'
                     '\n'
                     '# create default table\n'
                     'echo "create table clouds ( cloud_id INT AUTO_INCREMENT, name VARCHAR(255) NOT NULL, value INT, max_value INT, PRIMARY KEY (cloud_id))" | mysql -h ' + dbEndpointAddress + ' -u cloud_tug_of_war -pcloudpass cloud_tug_of_war\n'
                     )

for i in range(1, 2):
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
                    {'Key': 'Name', 'Value': 'tug-of-war-rds-webserver' + str(i)},
                    {'Key': 'tug-of-war-rds', 'Value': 'webserver'}
                ],
            }
        ],
    )

    instanceIdWeb = response['Instances'][0]['InstanceId']

    instance = ec2Resource.Instance(instanceIdWeb)
    instance.wait_until_running()
    instance.load()

    print("tug-of-war-in-the-clouds can be accessed at: http://" + instance.public_ip_address)

    print("This example uses an RDS instance (managed MySQL offered by AWS) instead of installing the db on our own in"
          "an EC2 instance. You can see different options esp. for replication etc. in RDS. The larger the instance,"
          "the more fault tolerance options (esp. for Aurora) and performance, but obviously at higher costs. Compare"
          " the trade-off between flexibility, maintenance effort and related costs.")

    print("You can watch the creation of the DB in the cli using 'aws rds ...' or the web console.")
