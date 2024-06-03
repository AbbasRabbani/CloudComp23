"""Example for Cloud Computing Course Master AI / GSD"""

# This script demonstrates how to use libcloud to start an instance in an OpenStack environment.
# The script will add an additional worker to a running faafo example application

# Needed if the password should be prompted for:
# import getpass
import os
import sys
# import time

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
    # get fixed a ip for service and api instance
    # (better would be shared IP for the cluster etc.)
    #
    ###########################################################################

    # find service instance
    for instance in conn.list_nodes():
        if instance.name == 'app-services':
            services_ip = instance.private_ips[0]
            print(('Found app-services fixed IP to be: ', services_ip))
        if instance.name == 'app-api-1':
            api_1_ip = instance.private_ips[0]
            print(('Found app-api-1 fixed IP to be: ', api_1_ip))


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
                return security_grp
        return False

    if not get_security_group(conn, "worker"):
        worker_security_group = conn.ex_create_security_group(
            'worker', 'for services that run on a worker node')
        conn.ex_create_security_group_rule(worker_security_group, 'TCP', 22, 22)
    else:
        worker_security_group = get_security_group(conn, "worker")

    for security_group in conn.ex_list_security_groups():
        print(security_group)


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

    # userdata-api-2 = '''#!/usr/bin/env bash
    # curl -L -s ''' + hsfd_faafo_cloud_init_script + ''' | bash -s -- \
    #     -i faafo -r worker -e 'http://%(api_2_ip)s' -m 'amqp://faafo:guest@%(services_ip)s:5672/'
    # ''' % {'api_2_ip': api_2_ip, 'services_ip': services_ip}

    print('Starting new app-worker-3 instance and wait until it is running...')
    instance_worker_3 = conn.create_node(name='app-worker-3',
                                         image=image, size=flavor,
                                         networks=[network],
                                         ex_keyname=KEYPAIR_NAME,
                                         ex_userdata=userdata_worker,
                                         ex_security_groups=[worker_security_group])

    print(instance_worker_3)

if __name__ == '__main__':
    main()
