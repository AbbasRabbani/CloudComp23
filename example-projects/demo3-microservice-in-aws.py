import configparser
from os.path import expanduser

from libcloud.compute.base import NodeImage
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

home = expanduser("~")

# requirements:
#   services: EC2
#   resources: 2 instances (1 keypair, 2 security groups)
#              optionally also elastic ip (comparable to floating ip) offering a persistent public
#              IP, but elastic ips are expensive - make sure to delete them after you used them

# The image to look for and use for the started instance
# aws ec2 describe-images --owner amazon | grep ubuntu | grep jammy | grep hvm | grep ssd |grep amd64 | grep -v minimal | grep -v pro | grep -v testing | grep -v k8s | grep "Name"
ubuntu_image_name = 'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20240319'

# The public key to be used for SSH connection, please make sure, that you have the corresponding private key

# use existing vockey in AWS Lab env from vocareum, enables login directly
# from the lab's terminal:
#
# ssh -i ~/.ssh/labuser.pem ubuntu@<public-ip>

keypair_name = "vockey"

# keypair_name = 'srieger-pub'
pub_key_file = home + '/.ssh/id_rsa.pub'

# id_rsa.pub should look like this (standard sshd pubkey format):
# ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAw+J...F3w2mleybgT1w== user@HOSTNAME

# flavor_name = 't2.nano'
# t2.nano only has 512 MB RAM, pip install will cause out of memory (OOM), install-aws.sh cloud-init script uses swap
# to circumvent this issue, but t2.micro is also cheap and has 1 GB RAM which is sufficient for faafo example
flavor_name = 't2.micro'

# default region
# region_name = 'eu-central-1'
# region_name = 'ap-south-1'

# AWS Academy Labs only allow us-east-1 see our AWS Academy Lab Guide, https://awsacademy.instructure.com/login/
region_name = 'us-east-1'

# starting instances in AWS Academy takes significantly longer compared to paid AWS accounts, allow ~ >2 minutes timeout
timeout = 600


def main():
    ###########################################################################
    #
    # get credentials
    #
    ###########################################################################

    # see AWS Academy Lab for Account Details
    # read credentials from file
    config = configparser.ConfigParser()
    config.read_file(open(home + '/.aws/credentials'))
    aws_access_key_id = config['default']['aws_access_key_id']
    aws_secret_access_key = config['default']['aws_secret_access_key']
    aws_session_token = config['default']['aws_session_token']

    # hard coded AWS credentials using vars
    # aws_access_key_id = "ASIAX..."
    # aws_secret_access_key = "WLxxXK+..."
    # aws_session_token = "FwoGZXIvYXdzEMb//////////wEaDE5rX.......0SleZ+L75I9iEri9LA4hovWul8HvexhCBK8.......................Ae/T+VkUbcQRtJEDwg+gYCABuk0JlSj5Wk7YA65r3BSNJXZFpkhbek6VBjvE/cEt5fKZEhENcdFxjAcAJLd6bOWi/oGXU5e3PX3mcXgm0oJpz6h3wqD1LvSDtw5GDwn0BHiF1Mu.......................cm/VukK5F"

    ###########################################################################
    #
    # create connection
    #
    ###########################################################################

    provider = get_driver(Provider.EC2)
    conn = provider(aws_access_key_id,
                    aws_secret_access_key,
                    token=aws_session_token,
                    region=region_name)

    ###########################################################################
    #
    # get image, flavor, network for instance creation
    #
    ###########################################################################

    print("Search for AMI...")
    image = conn.list_images(ex_filters={"name": ubuntu_image_name})[0]
    print("Using image: %s" % image)

    # print("Fetching images (AMI) list from AWS region. This will take a lot of seconds (AWS has a very long list of "
    #       "supported operating systems and versions)... please be patient...")
    # image = ''
    # for img in images:
    #   # if img.name == ubuntu_image_name:
    #   if img.extra['owner_alias'] == 'amazon':
    #       print(img)
    #   if img.id == ubuntu_image_name:
    #       image = img

    # fetch/select the image referenced with ubuntu_image_name above
    # image = [i for i in images if i.name == ubuntu_image_name][0]
    # print(image)

    # select image directly to save time, as retrieving the image list takes several minutes now,
    # need to change ami id here if updated or for other regions, id is working for course in
    # summer term 2022, in region: us-east-1 and pointing to ubuntu 18.04 used in the instance wizard,
    # to update AMI id use the create instance wizard and copy amd64 image id for ubuntu 18.04 in the
    # desired region
    # image = NodeImage(id="ami-0e472ba40eb589f49",
    #                   name=ubuntu_image_name,
    #                   driver="hvm")

    flavors = conn.list_sizes()
    flavor = [s for s in flavors if s.id == flavor_name][0]
    print(flavor)

    # networks = conn.ex_list_networks()
    # network = ''
    # for net in networks:
    #    if net.name == project_network:
    #        network = net

    ###########################################################################
    #
    # create keypair dependency
    #
    ###########################################################################

    print('Checking for existing SSH key pair...')
    keypair_exists = False
    for keypair in conn.list_key_pairs():
        if keypair.name == keypair_name:
            keypair_exists = True

    if keypair_exists:
        print('Keypair ' + keypair_name + ' already exists. Skipping import.')
    else:
        print('adding keypair...')
        conn.import_key_pair_from_file(keypair_name, pub_key_file)

    for keypair in conn.list_key_pairs():
        print(keypair)

    ###########################################################################
    #
    # create security group dependency
    #
    ###########################################################################

    print('Checking for existing worker security group...')
    worker_security_group_exists = False
    worker_security_group_name = 'worker'
    for security_group in conn.ex_get_security_groups():
        if security_group.name == worker_security_group_name:
            worker_security_group_id = security_group.id
            worker_security_group_exists = True

    if worker_security_group_exists:
        print('Worker Security Group ' + worker_security_group_name + ' already exists. Skipping creation.')
    else:
        worker_security_group_result = conn.ex_create_security_group('worker', 'for services that run on a worker node')
        worker_security_group_id = worker_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(worker_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')

    print('Checking for existing controller security group...')
    controller_security_group_exists = False
    controller_security_group_name = 'control'
    controller_security_group_id = ''
    for security_group in conn.ex_get_security_groups():
        if security_group.name == controller_security_group_name:
            controller_security_group_id = security_group.id
            controller_security_group_exists = True

    if controller_security_group_exists:
        print('Controller Security Group ' + controller_security_group_name + ' already exists. Skipping creation.')
    else:
        controller_security_group_result = conn.ex_create_security_group('control',
                                                                         'for services that run on a control node')
        controller_security_group_id = controller_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 80, 80, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 5672, 5672,
                                                 group_pairs=[{'group_id': worker_security_group_id}], protocol='tcp')

    # for security_group in conn.ex_list_security_groups():
    #    print(security_group)

    ###########################################################################
    #
    # create app-controller
    #
    ###########################################################################

    # https://git.openstack.org/cgit/openstack/faafo/plain/contrib/install.sh
    # is currently broken, hence the "rabbitctl" lines were added in the example
    # below, see also https://bugs.launchpad.net/faafo/+bug/1679710
    #
    # Thanks to Stefan Friedmann for finding this fix ;)

    userdata = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
        -i messaging -i faafo -r api
    rabbitmqctl add_user faafo guest
    rabbitmqctl set_user_tags faafo administrator
    rabbitmqctl set_permissions -p / faafo ".*" ".*" ".*"
    '''

    print('Starting new app-controller instance and wait until it is running (can take several minutes in free AWS'
          ' academy accounts compared to seconds when using a regular paid AWS account), timeout %i seconds...'
          % timeout)
    instance_controller_1 = conn.create_node(name='app-controller',
                                             image=image,
                                             size=flavor,
                                             ex_keyname=keypair_name,
                                             ex_userdata=userdata,
                                             ex_security_groups=[controller_security_group_name])

    wait_until_running_result = conn.wait_until_running(nodes=[instance_controller_1], timeout=timeout, ssh_interface='public_ips')
    instance_controller_1, node_addresses = wait_until_running_result[0]

    ###########################################################################
    #
    # assign app-controller elastic ip
    #
    ###########################################################################

    # AWS offers elastic ips, that have the same function as floating IPs in OpenStack. However, elastic IPs cost money,
    # and instances typically already have public IP in AWS, what a luxury ;) so I commented out elastic IP creation to
    # save your AWS academy budget

    # print('Checking for unused Elastic IP...')
    # unused_elastic_ip = None
    # for elastic_ip in conn.ex_describe_all_addresses():
    #     if not elastic_ip.instance_id:
    #         unused_elastic_ip = elastic_ip
    #         break
    #
    # if not unused_elastic_ip:
    #     print('Allocating new Elastic IP')
    #     unused_elastic_ip = conn.ex_allocate_address()
    # conn.ex_associate_address_with_node(instance_controller_1, unused_elastic_ip)
    # print('Controller Application will be deployed to http://%s' % unused_elastic_ip.ip)

    ###########################################################################
    #
    # getting id and ip address of app-controller instance
    #
    ###########################################################################

    # instance_controller_1 = conn.list_nodes(ex_node_ids=instance_controller_1.id)
    public_ip_controller = instance_controller_1.public_ips[0]
    print('Controller Application %s will be reachable after cloud-init has run at http://%s, you can also connect'
           % (instance_controller_1.id, public_ip_controller) +
          ' via ssh ubuntu@%s' % public_ip_controller)

    # get private IP of instance to use in worker/service instances to connect to the controller
    private_ip_controller = instance_controller_1.private_ips[0]

    ###########################################################################
    #
    # create app-worker-1
    #
    ###########################################################################

    userdata = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
        -i faafo -r worker -e 'http://%(ip_controller)s' -m 'amqp://faafo:guest@%(ip_controller)s:5672/'
    ''' % {'ip_controller': private_ip_controller}

    print('Starting new app-worker-1 instance and wait until it is running...')
    instance_worker_1 = conn.create_node(name='app-worker-1',
                                         image=image,
                                         size=flavor,
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata,
                                         ex_security_groups=[worker_security_group_name])

    wait_until_running_result = conn.wait_until_running(nodes=[instance_worker_1], timeout=timeout, ssh_interface='public_ips')
    instance_worker_1, node_addresses = wait_until_running_result[0]
    print('Worker instance %s has private ip: %s ' % (instance_worker_1.id, instance_worker_1.private_ips[0]))

    ###########################################################################
    #
    # assign app-worker elastic ip
    #
    ###########################################################################

    # AWS offers elastic ips, that have the same function as floating IPs in OpenStack. However, elastic IPs cost money,
    # and instances typically already have public IP in AWS, what a luxury ;) so I commented out elastic IP creation to
    # save your AWS academy budget
    # print('Checking for unused Elastic IP...')
    # unused_elastic_ip = None
    # for elastic_ip in conn.ex_describe_all_addresses():
    #     if not elastic_ip.instance_id:
    #         unused_elastic_ip = elastic_ip
    #         break
    #
    # if not unused_elastic_ip:
    #     print('Allocating new Elastic IP')
    #     unused_elastic_ip = conn.ex_allocate_address()
    # conn.ex_associate_address_with_node(instance_worker_1, unused_elastic_ip)
    # print('The worker will be available for SSH at %s' % unused_elastic_ip.ip)
    #

    print('You can use ssh to login to the controller using your private key. After login, you can list available '
          'fractals using "faafo list". To request the generation of new fractals, you can use "faafo create". '
          'You can also see other options to use the faafo example cloud service using "faafo -h".')


if __name__ == '__main__':
    main()
