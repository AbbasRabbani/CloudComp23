"""Example for Cloud Computing Course Master AI / GSD"""

# This script demonstrates how to use libcloud to start an instance in an OpenStack environment.
# The script will create and install a new SSH key pair, create a security group, start an instance
# and deploy a demo app (faafo) using cloud-init and assign a floating IP to the instance.
#
# cloud-init is a multi-distribution package that handles early initialization of a cloud instance.
# It is supported by many major cloud providers, including OpenStack.
# cloud-init documentation: https://cloudinit.readthedocs.io/en/latest/

# Needed if the password should be prompted for:
# import getpass
import os
import sys

# For our new Charmed OpenStack private cloud, we need to specify the path to the root
# CA certificate
import libcloud.security
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

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
KEYPAIR_NAME = 'CloudGroup23_KeyPair'
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
    auth_password = "CloudComp23"

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
        print('Keypair ' + KEYPAIR_NAME + ' already exists. Skipping import.')
    else:
        print('adding keypair...')
        conn.import_key_pair_from_file(KEYPAIR_NAME, PUB_KEY_FILE)

    for keypair in conn.list_key_pairs():
        print(keypair)

    ###########################################################################
    #
    # create security group dependency
    #
    ###########################################################################

    print('Checking for existing security group...')
    security_group_name = 'all-in-one'
    security_group_exists = False
    all_in_one_security_group = ''
    for security_group in conn.ex_list_security_groups():
        if security_group.name == security_group_name:
            all_in_one_security_group = security_group
            security_group_exists = True

    if security_group_exists:
        print('Security Group ' + all_in_one_security_group.name + ' already exists. '
              'Skipping creation.')
    else:
        all_in_one_security_group = conn.ex_create_security_group(security_group_name,
                                                                  'network access for '
                                                                  'all-in-one application.')
        conn.ex_create_security_group_rule(all_in_one_security_group, 'TCP', 80, 80)
        conn.ex_create_security_group_rule(all_in_one_security_group, 'TCP', 22, 22)

    for security_group in conn.ex_list_security_groups():
        print(security_group)

    ###########################################################################
    #
    # create all-in-one instance
    #
    ###########################################################################

    hsfd_faafo_cloud_init_script = 'https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/master/faafo/contrib/install.sh'  # noqa: E501 pylint: disable=line-too-long
    # testing / faafo dev branch:
    # hsfd_faafo_cloud_init_script = 'https://gogs.informatik.hs-fulda.de/srieger/cloud-computing-msc-ai-examples/raw/branch/dev_faafo/faafo/contrib/install.sh'  # noqa: E501 pylint: disable=line-too-long

    userdata = '#!/usr/bin/env bash\n' \
               f'curl -L -s {hsfd_faafo_cloud_init_script} | bash -s -- ' \
               '-i faafo -i messaging -r api -r worker -r demo\n'
    print('\nUsing cloud-init userdata:\n"' + userdata + '"\n')

    print('Checking for existing instance...')
    instance_name = 'all-in-one'
    instance_exists = False
    testing_instance = ''
    for instance in conn.list_nodes():
        if instance.name == instance_name:
            testing_instance = instance
            instance_exists = True

    if instance_exists:
        print('Instance ' + testing_instance.name + ' already exists. Skipping creation.')
        exit()
    else:
        print('Starting new all-in-one instance and wait until it is running...')
        testing_instance = conn.create_node(name=instance_name,
                                            image=image,
                                            size=flavor,
                                            networks=[network],
                                            ex_keyname=KEYPAIR_NAME,
                                            ex_userdata=userdata,
                                            ex_security_groups=[all_in_one_security_group])
        conn.wait_until_running(nodes=[testing_instance], timeout=120, ssh_interface='private_ips')

    ###########################################################################
    #
    # assign all-in-one instance floating ip
    #
    ###########################################################################

    private_ip = None
    if len(testing_instance.private_ips):
        private_ip = testing_instance.private_ips[0]
        print(f'Private IP found: {private_ip}')

    public_ip = None
    if len(testing_instance.public_ips):
        public_ip = testing_instance.public_ips[0]
        print(f'Public IP found: {public_ip}')

    print('Checking for unused Floating IP...')
    unused_floating_ip = None
    for floating_ip in conn.ex_list_floating_ips():
        if not floating_ip.node_id:
            unused_floating_ip = floating_ip
            break

    if not unused_floating_ip and len(conn.ex_list_floating_ip_pools()):
        pool = conn.ex_list_floating_ip_pools()[0]
        print(f'Allocating new Floating IP from pool: {pool}')
        unused_floating_ip = pool.create_floating_ip()

    if public_ip:
        print('Instance ' + testing_instance.name + ' already has a public ip. Skipping attachment.')
    elif unused_floating_ip:
        conn.ex_attach_floating_ip_to_node(testing_instance, unused_floating_ip)

    actual_ip_address = None
    if public_ip:
        actual_ip_address = public_ip
    elif unused_floating_ip:
        actual_ip_address = unused_floating_ip.ip_address
    elif private_ip:
        actual_ip_address = private_ip

    print('\n\n#### Deployment finished\n\n')
    print('After some minutes, as soon as cloud-init installed required packages and the\n'
          'faafo app, (First App Application For OpenStack) fractals demo will be available\n'
          f'at http://{actual_ip_address}\n')

    print('You can use ssh to login to the instance using your private key. Default user name for official Ubuntu\n'
          f'Cloud Images is: ubuntu, so you can use, e.g.: "ssh -i ~/.ssh/id_rsa ubuntu@{actual_ip_address}" if your\n'
          'private key is in the default location.\n\n'
          'After login, you can list available fractals using "faafo list". \n'
          'To request the generation of new fractals, you can use "faafo create".\n\n'
          'You can also see other options to use the faafo example cloud service using "faafo -h".\n\n'
          'If you cannot start faafo command and/or do not see the webpage, you can check the Instance Console Log of\n'
          'the instance, e.g., in OpenStack web interface or look at "tail -f /var/log/cloud-init*.log" for the\n'
          'cloud-init log files.\n')


if __name__ == '__main__':
    main()
