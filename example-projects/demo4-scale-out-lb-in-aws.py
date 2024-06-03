import configparser
from os.path import expanduser

# import libcloud.security
import time

from libcloud.compute.base import NodeImage
from libcloud.compute.base import NodeState
from libcloud.compute.providers import get_driver as compute_get_driver
from libcloud.compute.types import Provider as compute_Provider

from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import Provider as loadbalancer_Provider
from libcloud.loadbalancer.providers import get_driver as loadbalancer_get_driver

home = expanduser("~")

# requirements:
#   services: EC2, ELB
#   resources: 2 instances, (1 keypair, 2 security groups),
#              1 (Classic) Elastic Load Balancer, expensive! delete it after you used it!

# The image to look for and use for the started instance
# aws ec2 describe-images --owner amazon | grep ubuntu | grep jammy | grep hvm | grep ssd |grep amd64 | grep -v minimal | grep -v pro | grep -v testing | grep -v k8s | grep "Name"
ubuntu_image_name = 'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20240319'
# ubuntu_image_name = 'ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-20210128'

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

# AWS Academy Labs only allow us-east-1 and us-west-1 see our AWS Academy Lab Guide, https://awsacademy.instructure.com/login/
region_name = 'us-east-1'
# region_name = 'us-west-1'

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

    provider = compute_get_driver(compute_Provider.EC2)
    conn = provider(key=aws_access_key_id,
                    secret=aws_secret_access_key,
                    token=aws_session_token,
                    region=region_name)

    ###########################################################################
    #
    # get image, flavor, network for instance creation
    #
    ###########################################################################

    # print("Search for AMI...")
    # image = conn.list_images(ex_filters={"name": ubuntu_image_name})[0]
    # print("Using image: %s" % image)

    # print("Fetching images (AMI) list from AWS region. This will take a lot of seconds (AWS has a very long list of "
    #       "supported operating systems and versions)... please be patient...")
    # image = ''
    # for img in images:
    #   # if img.name == ubuntu_image_name:
    #   if img.extra['owner_alias'] == 'amazon':
    #       print(img)
    #   if img.id == ubuntu_image_name:
    #       image = img

    # select image directly to save time, as retrieving the image list takes several minutes now,
    # need to change ami id here if updated or for other regions, id is working for course in
    # summer term 2022, in region: us-east-1 and pointing to ubuntu 18.04 used in the instance wizard,
    # to update AMI id use the create instance wizard and copy amd64 image id for ubuntu 18.04 in the
    # desired region
    #

    print("Selecting AMI...")
    # us-east-1 examples as of 23.05.2024:
    # 
    # https://cloud-images.ubuntu.com/locator/ec2/
    #
    # Canonical, Ubuntu, 22.04 LTS, amd64 jammy image build on 2022-04-20
    image_id = "ami-012485deee5681dc0"
    #
    image = conn.list_images(ex_image_ids=[image_id])[0]
    print("Using image: %s" % image)

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
    # clean up resources from previous demos
    #
    ###########################################################################

    # destroy running demo instances
    for instance in conn.list_nodes():
        if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3', 'app-controller',
                             'app-services', 'app-api-1', 'app-api-2']:
            if instance.state is not NodeState.TERMINATED:
                print('Destroying Instance: %s' % instance.name)
                conn.destroy_node(instance)

    # wait until all nodes are destroyed to be able to remove dependent security groups
    nodes_still_running = True
    while nodes_still_running:
        nodes_still_running = False
        time.sleep(3)
        instances = conn.list_nodes()
        for instance in instances:
            # if we see any demo instances still running continue to wait for them to stop
            if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3', 'app-controller',
                                 'app-services', 'app-api-1', 'app-api-2']:
                if instance.state is not NodeState.TERMINATED:
                    nodes_still_running = True
        if nodes_still_running is True:
            print('There are still instances running, waiting for them to be destroyed...')
        else:
            print('No instances running')

    # delete security groups, respecting dependencies (hence deleting 'control' and 'services' first)
    for group in conn.ex_list_security_groups():
        if group in ['control', 'services']:
            print('Deleting security group: %s' % group)
            conn.ex_delete_security_group(group)

    # now we can delete security groups 'api' and 'worker', as 'control' and 'api' depended on them, otherwise AWS will
    # throw DependencyViolation: resource has a dependent object
    for group in conn.ex_list_security_groups():
        if group in ['api', 'worker']:
            print('Deleting security group: %s' % group)
            conn.ex_delete_security_group(group)

    ###########################################################################
    #
    # create security group dependency
    #
    ###########################################################################

    def get_security_group(connection, security_group_name):
        """A helper function to check if security group already exists"""
        print('Checking for existing ' + security_group_name + ' security group...')
        for security_grp in connection.ex_list_security_groups():
            if security_grp == security_group_name:
                print('Security Group ' + security_group_name + ' already exists. Skipping creation.')
                return security_grp['group_id']
        return False

    if not get_security_group(conn, "api"):
        api_security_group_result = conn.ex_create_security_group('api', 'for API services only')
        api_security_group_id = api_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(api_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        conn.ex_authorize_security_group_ingress(api_security_group_id, 80, 80, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
    else:
        api_security_group_id = get_security_group(conn, "api")

    if not get_security_group(conn, "worker"):
        worker_security_group_result = conn.ex_create_security_group('worker', 'for services that run on a worker node')
        worker_security_group_id = worker_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(worker_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
    else:
        worker_security_group_id = get_security_group(conn, "worker")

    if not get_security_group(conn, "control"):
        controller_security_group_result = conn.ex_create_security_group('control',
                                                                         'for services that run on a control node')
        controller_security_group_id = controller_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 80, 80, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        conn.ex_authorize_security_group_ingress(controller_security_group_id, 5672, 5672,
                                                 group_pairs=[{'group_id': worker_security_group_id}], protocol='tcp')
    else:
        controller_security_group_id = get_security_group(conn, "control")

    if not get_security_group(conn, "services"):
        services_security_group_result = conn.ex_create_security_group('services', 'for DB and AMQP services only')
        services_security_group_id = services_security_group_result['group_id']
        conn.ex_authorize_security_group_ingress(services_security_group_id, 22, 22, cidr_ips=['0.0.0.0/0'],
                                                 protocol='tcp')
        # conn.ex_authorize_security_group_ingress(services_security_group_id, 3306, 3306, cidr_ips=['0.0.0.0/0'],
        #                                          group_pairs=[{'group_id': api_security_group_id}], protocol='tcp')
        conn.ex_authorize_security_group_ingress(services_security_group_id, 3306, 3306,
                                                 group_pairs=[{'group_id': api_security_group_id}], protocol='tcp')
        conn.ex_authorize_security_group_ingress(services_security_group_id, 5672, 5672,
                                                 group_pairs=[{'group_id': worker_security_group_id}], protocol='tcp')
        conn.ex_authorize_security_group_ingress(services_security_group_id, 5672, 5672,
                                                 group_pairs=[{'group_id': api_security_group_id}], protocol='tcp')
    else:
        services_security_group_id = get_security_group(conn, "services")

    for security_group in conn.ex_list_security_groups():
        print(security_group)


    # get availability zones
    az = conn.list_locations()
    print(az)


    ###########################################################################
    #
    # create app-services instance (database & messaging) (Amazon AWS EC2)
    #
    ###########################################################################

    # https://git.openstack.org/cgit/openstack/faafo/plain/contrib/install-aws.sh
    # is currently broken, hence the "rabbitctl" lines were added in the example
    # below, see also https://bugs.launchpad.net/faafo/+bug/1679710
    #
    # Thanks to Stefan Friedmann for finding this fix ;)

    userdata_service = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
        -i database -i messaging
    rabbitmqctl add_user faafo guest
    rabbitmqctl set_user_tags faafo administrator
    rabbitmqctl set_permissions -p / faafo ".*" ".*" ".*"
    '''

    print('Starting new app-services instance and wait until it is running...')
    instance_services = conn.create_node(location=az[0],
                                         name='app-services',
                                         image=image,
                                         size=flavor,
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_service,
                                         ex_security_groups=["services"])
    instance_services = conn.wait_until_running(nodes=[instance_services], timeout=timeout, ssh_interface='public_ips')
    services_ip = instance_services[0][0].private_ips[0]
    print(instance_services)

    ###########################################################################
    #
    # create app-api instances (Amazon AWS EC2)
    #
    ###########################################################################

    userdata_api = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
        -i faafo -r api -m 'amqp://faafo:guest@%(services_ip)s:5672/' \
        -d 'mysql+pymysql://faafo:password@%(services_ip)s:3306/faafo'
    ''' % {'services_ip': services_ip}

    print('Starting new app-api-1 instance and wait until it is running...')
    instance_api_1 = conn.create_node(location=az[0],
                                      name='app-api-1',
                                      image=image,
                                      size=flavor,
                                      ex_keyname=keypair_name,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=["api"])

    print('Starting new app-api-2 instance and wait until it is running...')
    instance_api_2 = conn.create_node(location=az[1],
                                      name='app-api-2',
                                      image=image,
                                      size=flavor,
                                      ex_keyname=keypair_name,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=["api"])

    instance_api_1 = conn.wait_until_running(nodes=[instance_api_1], timeout=timeout, ssh_interface='public_ips')
    api_1_ip = instance_api_1[0][0].private_ips[0]
    print("app-api-1 public ip: " + instance_api_1[0][1][0])
    instance_api_2 = conn.wait_until_running(nodes=[instance_api_2], timeout=timeout, ssh_interface='public_ips')
    # currently only api_1_ip is used
    api_2_ip = instance_api_2[0][0].private_ips[0]
    print("app-api-2 public ip: " + instance_api_2[0][1][0])

    ###########################################################################
    #
    # create worker instances (Amazon AWS EC2)
    #
    ###########################################################################

    userdata_worker = '''#!/usr/bin/env bash
    curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
        -i faafo -r worker -e 'http://%(api_1_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    ''' % {'api_1_ip': api_1_ip, 'services_ip': services_ip}

    # userdata_api-api-2 = '''#!/usr/bin/env bash
    # curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install-aws.sh | bash -s -- \
    #     -i faafo -r worker -e 'http://%(api_2_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    # ''' % {'api_2_ip': api_2_ip, 'services_ip': services_ip}

    print('Starting new app-worker-1 instance and wait until it is running...')
    instance_worker_1 = conn.create_node(location=az[0],
                                         name='app-worker-1',
                                         image=image, size=flavor,
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=["worker"])

    print('Starting new app-worker-2 instance and wait until it is running...')
    instance_worker_2 = conn.create_node(location=az[1],
                                         name='app-worker-2',
                                         image=image, size=flavor,
                                         ex_keyname=keypair_name,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=["worker"])

    # do not start worker 3 initially, can be started using scale-out-add-worker.py demo

    # print('Starting new app-worker-3 instance and wait until it is running...')
    # instance_worker_3 = conn.create_node(name='app-worker-3',
    #                                     image=image, size=flavor,
    #                                     networks=[network],
    #                                     ex_keyname=keypair_name,
    #                                     ex_userdata=userdata_worker,
    #                                     ex_security_groups=[worker_security_group])

    print(instance_worker_1)
    print(instance_worker_2)
    # print(instance_worker_3)

    ###########################################################################
    #
    # create load balancer (Amazon AWS ELB)
    #
    ###########################################################################

    elb_provider = loadbalancer_get_driver(loadbalancer_Provider.ELB)
    elb_conn = elb_provider(aws_access_key_id,
                            aws_secret_access_key,
                            token=aws_session_token,
                            region=region_name)

    print("Deleting previously created load balancers in: " + str(elb_conn.list_balancers()))
    for loadbalancer in elb_conn.list_balancers():
        if loadbalancer.name == "lb1":
            print("Deleting Load Balancer: " + str(loadbalancer))
            elb_conn.destroy_balancer(loadbalancer)

    # get suffix (a, b, c, ...) from all availability zones, available in the selected region
    all_availability_zones_in_region = []
    for az in conn.ex_list_availability_zones():
        all_availability_zones_in_region.append(az.name[-1])

    # create new load balancer
    # example uses "classic" ELB with default HTTP health. monitor, you can see the result in the EC2 console, after
    # running this script
    new_load_balancer = elb_conn.create_balancer(
        name='lb1',
        algorithm=Algorithm.ROUND_ROBIN,
        port=80,
        protocol='http',
        members=[],
        ex_members_availability_zones=all_availability_zones_in_region)

    # attach api instances as members to load balancer
    elb_conn.balancer_attach_compute_node(balancer=new_load_balancer, node=instance_api_1[0][0])
    elb_conn.balancer_attach_compute_node(balancer=new_load_balancer, node=instance_api_2[0][0])

    print("Created load balancer: " + str(new_load_balancer))

    # wait for the load balancer to be ready
    while new_load_balancer.state != 2:
        time.sleep(3)
        new_load_balancer = elb_conn.get_balancer(new_load_balancer.id)

    print("\n\nYou can see the instances created in EC2 in AWS Console. You'll also find the load balancer under ELB "
          "there.\n"
          " You can access the faafo application deployed to the loadbalancer at: http://" + new_load_balancer.ip +
          " as soon as instances are detected to be deployed and healthy by the load balancer.")


if __name__ == '__main__':
    main()
