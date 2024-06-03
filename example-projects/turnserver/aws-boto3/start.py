import boto3
from botocore.exceptions import ClientError


region = 'eu-central-1'
availabilityZone = 'eu-central-1b'
imageId = 'ami-0cc293023f983ed53'
instanceType = 't3.nano'
keyName = 'srieger-pub'
userData = ('#!/bin/bash\n'
            'COTURN_VERSION="4.5.1.1"\n'
            'LIBEVENT_VERSION="2.0.21"\n'
            '\n'
            '# extra repo for RedHat rpms\n'
            'yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm\n'
            '# essential tools\n'
            'yum install -y joe htop git\n'
            '# coturn requirements\n'
            'yum install -y gcc openssl-devel\n'
            'yum install -y sqlite-devel mysql-devel hiredis-devel mongo-c-driver-devel\n'
            '\n'
            '### libevent installation ###\n'
            'wget https://github.com/downloads/libevent/libevent/libevent-$LIBEVENT_VERSION-stable.tar.gz\n'
            '\n'
            'tar xvfz libevent-$LIBEVENT_VERSION-stable.tar.gz\n'
            'cd libevent-$LIBEVENT_VERSION-stable\n'
            './configure\n'
            'make\n'
            'make install\n'
            '\n'
            '### turnserver installation ###\n'
            'wget https://coturn.net/turnserver/v$COTURN_VERSION/turnserver-$COTURN_VERSION.tar.gz\n'
            'tar xvfz turnserver-$COTURN_VERSION.tar.gz\n'
            'cd turnserver-$COTURN_VERSION\n'
            './configure\n'
            'make\n'
            'make install\n'
            '\n'
            'openssl req -new -subj "/CN=coturn" -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out /usr/local/etc/turn_server_cert.pem -keyout /usr/local/etc/turn_server_pkey.pem\n'
            '\n'
            '/usr/local/bin/turnadmin -a -u srieger -r hs-fulda.de -p coturnserver2019\n'
            '/usr/local/bin/turnadmin -A -u srieger -p coturnserver2019\n'
            '\n'
            'MAC_ETH0=$(cat /sys/class/net/eth0/address)\n'
            'MAC_ETH1=$(cat /sys/class/net/eth1/address)\n'
            'LOCAL_IPV4S_ETH0=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/$MAC_ETH0/local-ipv4s)\n'
            'LOCAL_IPV4S_ETH1=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/$MAC_ETH1/local-ipv4s)\n'
            'PUBLIC_IPV4S_ETH0=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/$MAC_ETH0/public-ipv4s)\n'
            'PUBLIC_IPV4S_ETH1=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/$MAC_ETH1/public-ipv4s)\n'
            '\n'
            'cat <<EOF > /usr/local/etc/turnserver.conf\n'
            'verbose\n'
            'listening-ip=$LOCAL_IPV4S_ETH0\n'
            'listening-ip=$LOCAL_IPV4S_ETH1\n'
            'relay-ip=$LOCAL_IPV4S_ETH0\n'
            'relay-ip=$LOCAL_IPV4S_ETH1\n'
            'external-ip=$PUBLIC_IPV4S_ETH0/$LOCAL_IPV4S_ETH0\n'
            'external-ip=$PUBLIC_IPV4S_ETH1/$LOCAL_IPV4S_ETH1\n'
            'fingerprint\n'
            'lt-cred-mech\n'
            '#use-auth-secret\n'
            '#static-auth-secret=751c45cae60a2839711a94c8d6bf0089e78b2149ca602fdXXXXXXXXXXXXXXXXX\n'
            'realm=hs-fulda.de\n'
            'total-quota=100\n'
            'stale-nonce\n'
            'cipher-list="ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+3DES:DH+3DES:RSA+AES:RSA+3DES:!ADH:!AECDH:!MD5"\n'
            '#no-stun\n'
            '#no-loopback-peers\n'
            '#no-multicast-peers\n'
            'cli-password=coturnserver2019\n'
            'web-admin\n'
            'web-admin-ip=$LOCAL_IPV4S_ETH0\n'
            'EOF\n'
            '\n'
            '/usr/local/bin/turnserver\n'
            )

# convert with: cat install-coturn | sed "s/^/'/; s/$/\\\n'/"

client = boto3.setup_default_session(region_name=region)
ec2Client = boto3.client("ec2")
ec2Resource = boto3.resource('ec2')

response = ec2Client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
subnet_id = ec2Client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone', 'Values': [availabilityZone]
        }
    ])['Subnets'][0]['SubnetId']

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

print("Create security group...")
print("------------------------------------")

try:
    response = ec2Client.create_security_group(GroupName='coturn',
                                               Description='coturn',
                                               VpcId=vpc_id)
    security_group_id = response['GroupId']
    print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

    data = ec2Client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 3478,
             'ToPort': 3478,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'udp',
             'FromPort': 3478,
             'ToPort': 3478,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 5349,
             'ToPort': 5349,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'udp',
             'FromPort': 5349,
             'ToPort': 5349,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 8080,
             'ToPort': 8080,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'udp',
             'FromPort': 49152,
             'ToPort': 65535,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])
    print('Ingress Successfully Set %s' % data)
except ClientError as e:
    print(e)

print("Allocate additional elastic ips...")
print("------------------------------------")

response = ec2Client.allocate_address(
   Domain='vpc',
)
firstIpAddressAllocationId = response['AllocationId']
ec2Client.create_tags(Resources=[firstIpAddressAllocationId], Tags=[{'Key': 'coturn', 'Value': 'installed'}])

response = ec2Client.allocate_address(
   Domain='vpc',
)
secondIpAddressAllocationId = response['AllocationId']
ec2Client.create_tags(Resources=[secondIpAddressAllocationId], Tags=[{'Key': 'coturn', 'Value': 'installed'}])

print("Running new instance...")
print("------------------------------------")

response = ec2Client.run_instances(
    ImageId=imageId,
    InstanceType=instanceType,
    Placement={'AvailabilityZone': availabilityZone, },
    KeyName=keyName,
    MinCount=1,
    MaxCount=1,
    UserData=userData,
    NetworkInterfaces=[
        {
            'DeviceIndex': 0,
            'Groups': [
                security_group_id,
            ],
            'SubnetId': subnet_id,
        },
        {
            'DeviceIndex': 1,
            'Groups': [
                security_group_id,
            ],
            'SubnetId': subnet_id,
        },
    ],
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'coturn', 'Value': 'installed'}
            ],
        }
    ],
)

instanceId = response['Instances'][0]['InstanceId']
firstNetworkInterfaceId = response['Instances'][0]['NetworkInterfaces'][0]['NetworkInterfaceId']
secondNetworkInterfaceId = response['Instances'][0]['NetworkInterfaces'][1]['NetworkInterfaceId']

instance = ec2Resource.Instance(instanceId)
instance.wait_until_running()

response = ec2Client.associate_address(
    AllocationId=firstIpAddressAllocationId,
    NetworkInterfaceId=firstNetworkInterfaceId,
)
response = ec2Client.associate_address(
    AllocationId=secondIpAddressAllocationId,
    NetworkInterfaceId=secondNetworkInterfaceId,
)


print(instanceId)

