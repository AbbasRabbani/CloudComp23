"""Example for Cloud Computing Course Master AI / GSD"""

# This script demonstrates how to use libcloud to start an instance in an OpenStack environment.
# The script will start multiple instances splitting up the faafo monolithic application into
# a microservice architecture with scalable api (controller) and worker instances using a
# message queue and a database

# Needed if the password should be prompted for:
# import getpass
import os
import sys
import time

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

# For our new Charmed OpenStack private cloud, we need to specify the path to the root
# CA certificate
import libcloud.security
libcloud.security.CA_CERTS_PATH = ['./root-ca.crt']
# Disable SSL certificate verification (not recommended for production)
# libcloud.security.VERIFY_SSL_CERT = False

# Please use 1-29 as environment variable GROUP_NUMBER to specify your group number.
# (will be used for the username, project etc., as coordinated in the lab sessions)

group_number = os.environ.get('GROUP_NUMBER')
if group_number is None:
    sys.exit('Please set the GROUP_NUMBER environment variable to your group number,\n'
             'e.g., on Windows:\n'
             '  "$env:GROUP_NUMBER=0" or "set GROUP_NUMBER=0"\n'
             'or on Linux/MacOS:\n'
             '  "export GROUP_NUMBER=0" or "set GROUP_NUMBER=0"')


# web service endpoint of the private cloud infrastructure
# auth_url = 'https://private-cloud.informatik.hs-fulda.de:5000'
AUTH_URL = 'https://10.32.4.182:5000'
# auth_url = 'https://private-cloud2.informatik.hs-fulda.de:5000'
# your username in OpenStack
AUTH_USERNAME = 'CloudComp' + str(group_number)
print(f'Using username: {AUTH_USERNAME}\n')
# your project in OpenStack
PROJECT_NAME = 'CloudComp' + str(group_number)
# A network in the project the started instance will be attached to
PROJECT_NETWORK = 'CloudComp' + str(group_number) + '-net'

# The image to look for and use for the started instance
# ubuntu_image_name = "Ubuntu 18.04 - Bionic Beaver - 64-bit - Cloud Based Image"
#UBUNTU_IMAGE_NAME = "auto-sync/ubuntu-jammy-22.04-amd64-server-20240319-disk1.img"
UBUNTU_IMAGE_NAME = "ubuntu-22.04-jammy-x86_64"

# The public key to be used for SSH connection, please make sure, that you have the
# corresponding private key
#
# id_rsa.pub should look like this (standard sshd pubkey format):
# ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAw+J...F3w2mleybgT1w== user@HOSTNAME
KEYPAIR_NAME = 'srieger-pub'
PUB_KEY_FILE = '~/.ssh/id_rsa.pub'

FLAVOR_NAME = 'm1.small'


# default region
REGION_NAME = 'RegionOne'
# domain to use, "default" for local accounts, formerly "hsfulda" for LDAP accounts etc.
# domain_name = "default"


def main():  # noqa: C901 pylint: disable=too-many-branches,too-many-statements,too-many-locals,missing-function-docstring
    ###########################################################################
    #
    # get credentials
    #
    ###########################################################################

    # if "OS_PASSWORD" in os.environ:
    #     auth_password = os.environ["OS_PASSWORD"]
    # else:
    #     auth_password = getpass.getpass("Enter your OpenStack password:")
    auth_password = "demo"

    ###########################################################################
    #
    # create connection
    #
    ###########################################################################

    provider = get_driver(Provider.OPENSTACK)
    conn = provider(AUTH_USERNAME,
                    auth_password,
                    ex_force_auth_url=AUTH_URL,
                    ex_force_auth_version='3.x_password',
                    ex_tenant_name=PROJECT_NAME,
                    ex_force_service_region=REGION_NAME)
    #               ex_domain_name=domain_name)

    ###########################################################################
    #
    # get image, flavor, network for instance creation
    #
    ###########################################################################

    images = conn.list_images()
    image = ''
    for img in images:
        if img.name == UBUNTU_IMAGE_NAME:
            image = img

    flavors = conn.list_sizes()
    flavor = ''
    for flav in flavors:
        if flav.name == FLAVOR_NAME:
            flavor = conn.ex_get_size(flav.id)

    networks = conn.ex_list_networks()
    network = ''
    for net in networks:
        if net.name == PROJECT_NETWORK:
            network = net

    ###########################################################################
    #
    # create keypair dependency
    #
    ###########################################################################

    print('Checking for existing SSH key pair...')
    keypair_exists = False
    for keypair in conn.list_key_pairs():
        if keypair.name == KEYPAIR_NAME:
            keypair_exists = True

    if keypair_exists:
        print(('Keypair ' + KEYPAIR_NAME + ' already exists. Skipping import.'))
    else:
        print('adding keypair...')
        conn.import_key_pair_from_file(KEYPAIR_NAME, PUB_KEY_FILE)

    for keypair in conn.list_key_pairs():
        print(keypair)

    ###########################################################################
    #
    # clean up resources from previous demos
    #
    ###########################################################################

    # destroy running demo instances
    for instance in conn.list_nodes():
        if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2',
                             'app-worker-3', 'app-controller',
                             'app-services', 'app-api-1', 'app-api-2']:
            print(f'Destroying Instance: ${instance.name}')
            conn.destroy_node(instance)

    # wait until all nodes are destroyed to be able to remove depended security groups
    nodes_still_running = True
    while nodes_still_running:
        nodes_still_running = False
        time.sleep(3)
        instances = conn.list_nodes()
        for instance in instances:
            # if we see any demo instances still running continue to wait for them to stop
            if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-controller']:
                nodes_still_running = True
        print('There are still instances running, waiting for them to be destroyed...')

    # delete security groups
    for group in conn.ex_list_security_groups():
        if group.name in ['control', 'worker', 'api', 'services']:
            print(f'Deleting security group: ${group.name}')
            conn.ex_delete_security_group(group)

    ###########################################################################
    #
    # create security group dependency
    #
    ###########################################################################

    def get_security_group(connection, security_group_name):
        """A helper function to check if security group already exists"""
        print(('Checking for existing ' + security_group_name + ' security group...'))
        for security_grp in connection.ex_list_security_groups():
            if security_grp.name == security_group_name:
                print(('Security Group ' + security_group_name +
                       ' already exists. Skipping creation.'))
                return worker_security_group
        return False

    if not get_security_group(conn, "api"):
        api_security_group = conn.ex_create_security_group('api', 'for API services only')
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(api_security_group, 'TCP', 22, 22)
    else:
        api_security_group = get_security_group(conn, "api")

    if not get_security_group(conn, "worker"):
        worker_security_group = conn.ex_create_security_group(
            'worker', 'for services that run on a worker node')
        conn.ex_create_security_group_rule(worker_security_group, 'TCP', 22, 22)
    else:
        worker_security_group = get_security_group(conn, "worker")

    if not get_security_group(conn, "control"):
        controller_security_group = conn.ex_create_security_group(
            'control', 'for services that run on a control node')
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(controller_security_group, 'TCP', 5672, 5672,
                                           source_security_group=worker_security_group)

    if not get_security_group(conn, "services"):
        services_security_group = conn.ex_create_security_group(
            'services', 'for DB and AMQP services only')
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 22, 22)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 3306, 3306,
                                           source_security_group=api_security_group)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 5672, 5672,
                                           source_security_group=worker_security_group)
        conn.ex_create_security_group_rule(services_security_group, 'TCP', 5672, 5672,
                                           source_security_group=api_security_group)
    else:
        services_security_group = get_security_group(conn, "services")

    for security_group in conn.ex_list_security_groups():
        print(security_group)

    ###########################################################################
    #
    # get floating ip helper function
    #
    ###########################################################################

    def get_floating_ip(connection):
        """A helper function to re-use available Floating IPs"""
        unused_floating_ip = None
        for float_ip in connection.ex_list_floating_ips():
            if not float_ip.node_id:
                unused_floating_ip = float_ip
                break
        if not unused_floating_ip:
            pool = connection.ex_list_floating_ip_pools()[0]
            unused_floating_ip = pool.create_floating_ip()
        return unused_floating_ip

    ###########################################################################
    #
    # create app-services instance (database & messaging)
    #
    ###########################################################################

    userdata_service = '#!/usr/bin/env bash\n' \
               'curl -L -s https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-' \
               'examples/raw/master/faafo/contrib/install.sh | bash -s -- ' \
               '-i database -i messaging\n'
    print('\nUsing cloud-init userdata for service:\n"' + userdata_service + '"\n')

    print('Starting new app-services instance and wait until it is running...')
    instance_services = conn.create_node(name='app-services',
                                         image=image,
                                         size=flavor,
                                         networks=[network],
                                         ex_keyname=KEYPAIR_NAME,
                                         ex_userdata=userdata_service,
                                         ex_security_groups=[services_security_group])
    instance_services = conn.wait_until_running(nodes=[instance_services], timeout=120,
                                                ssh_interface='private_ips')[0][0]
    services_ip = instance_services.private_ips[0]

    ###########################################################################
    #
    # create app-api instances
    #
    ###########################################################################

    userdata_api = '#!/usr/bin/env bash\n' \
                   'curl -L -s https://gogs.informatik.hs-fulda.de/srieger/' \
                   'cloud-computing-msc-ai-examples/raw/master/faafo/contrib/' \
                   'install.sh | bash -s -- ' \
                   f'-i faafo -r api -m "amqp://faafo:guest@{services_ip}:5672/" ' \
                   f'-d "mysql+pymysql://faafo:password@{services_ip}:3306/faafo"'
    print('\nUsing cloud-init userdata for api:\n"' + userdata_api + '"\n')

    print('Starting new app-api-1 instance and wait until it is running...')
    instance_api_1 = conn.create_node(name='app-api-1',
                                      image=image,
                                      size=flavor,
                                      networks=[network],
                                      ex_keyname=KEYPAIR_NAME,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=[api_security_group])

    print('Starting new app-api-2 instance and wait until it is running...')
    instance_api_2 = conn.create_node(name='app-api-2',
                                      image=image,
                                      size=flavor,
                                      networks=[network],
                                      ex_keyname=KEYPAIR_NAME,
                                      ex_userdata=userdata_api,
                                      ex_security_groups=[api_security_group])

    instance_api_1 = conn.wait_until_running(nodes=[instance_api_1], timeout=120,
                                             ssh_interface='private_ips')[0][0]
    api_1_ip = instance_api_1.private_ips[0]
    instance_api_2 = conn.wait_until_running(nodes=[instance_api_2], timeout=120,
                                             ssh_interface='private_ips')[0][0]
    # api_2_ip = instance_api_2.private_ips[0]

    for instance in [instance_api_1, instance_api_2]:
        floating_ip = get_floating_ip(conn)
        conn.ex_attach_floating_ip_to_node(instance, floating_ip)
        print(('allocated %(ip)s to %(host)s' % {'ip': floating_ip.ip_address,
                                                 'host': instance.name}))

    ###########################################################################
    #
    # create worker instances
    #
    ###########################################################################

    userdata_worker = '#!/usr/bin/env bash\n' \
                      'curl -L -s https://gogs.informatik.hs-fulda.de/srieger/' \
                      'cloud-computing-msc-ai-examples/raw/master/faafo/contrib/' \
                      'install.sh | bash -s -- ' \
                      f'-i faafo -r worker -e "http://{api_1_ip}" '\
                      f'-m "amqp://faafo:guest@{services_ip}:5672/"'
    print('\nUsing cloud-init userdata for worker:\n"' + userdata_worker + '"\n')


    # userdata_api-api-2 = '''#!/usr/bin/env bash
    # curl -L -s ''' + hsfd_faafo_cloud_init_script + ''' | bash -s -- \
    #     -i faafo -r worker -e 'http://%(api_2_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    # ''' % {'api_2_ip': api_2_ip, 'services_ip': services_ip}

    print('Starting new app-worker-1 instance and wait until it is running...')
    instance_worker_1 = conn.create_node(name='app-worker-1',
                                         image=image, size=flavor,
                                         networks=[network],
                                         ex_keyname=KEYPAIR_NAME,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=[worker_security_group])

    print('Starting new app-worker-2 instance and wait until it is running...')
    instance_worker_2 = conn.create_node(name='app-worker-2',
                                         image=image, size=flavor,
                                         networks=[network],
                                         ex_keyname=KEYPAIR_NAME,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=[worker_security_group])

    # do not start worker 3 initially, can be started using scale-out-add-worker.py demo

    #print('Starting new app-worker-3 instance and wait until it is running...')
    #instance_worker_3 = conn.create_node(name='app-worker-3',
    #                                     image=image, size=flavor,
    #                                     networks=[network],
    #                                     ex_keyname=keypair_name,
    #                                     ex_userdata=userdata_worker,
    #                                     ex_security_groups=[worker_security_group])

    print(instance_worker_1)
    print(instance_worker_2)
    #print(instance_worker_3)


if __name__ == '__main__':
    main()
