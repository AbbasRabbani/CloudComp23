"""Example for Cloud Computing Course Master AI / GSD"""


# This script demonstrates how to use libcloud to cleanup all instances used in the demos
# for our OpenStack private cloud environment.

# import getpass
import os
import sys

import time
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

# For our new Charmed OpenStack private cloud, we need to specify the path to the
# root CA certificate
import libcloud.security
libcloud.security.CA_CERTS_PATH = ['./root-ca.crt']
# Disable SSL certificate verification (not recommended for production)
# libcloud.security.VERIFY_SSL_CERT = False

# Please use 1-29 for X in the following variable to specify your group number.
# (will be used for the username, project etc., as coordinated in the lab sessions)

group_number = os.environ.get('GROUP_NUMBER')
if group_number is None:
    sys.exit('Please set the GROUP_NUMBER environment variable to your group number,\n'
             'e.g., on Windows:\n'
             '  "$env:GROUP_NUMBER=0" or "set GROUP_NUMBER=0"\n'
             'or on Linux/MacOS:\n'
             '  "export GROUP_NUMBER=0" or "set GROUP_NUMBER=0"')


###############################################################################################
#
#  no changes necessary below this line in this example
#
###############################################################################################

# web service endpoint of the private cloud infrastructure
# auth_url = 'https://private-cloud.informatik.hs-fulda.de:5000'
AUTH_URL = 'https://10.32.4.182:5000'
# auth_url = 'https://private-cloud2.informatik.hs-fulda.de:5000'
# your username in OpenStack
AUTH_USERNAME = 'CloudComp' + str(group_number)
# your project in OpenStack
PROJECT_NAME = 'CloudComp' + str(group_number)
# A network in the project the started instance will be attached to
PROJET_NETWORK = 'CloudComp' + str(group_number) + '-net'

# The image to look for and use for the started instance
# ubuntu_image_name = "Ubuntu 18.04 - Bionic Beaver - 64-bit - Cloud Based Image"
UBUNTU_IMAGE_NAME = "auto-sync/ubuntu-jammy-22.04-amd64-server-20240319-disk1.img"

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

    # libcloud.security.VERIFY_SSL_CERT = False

    provider = get_driver(Provider.OPENSTACK)
    conn = provider(AUTH_USERNAME,
                    auth_password,
                    ex_force_auth_url=AUTH_URL,
                    ex_force_auth_version='3.x_password',
                    ex_tenant_name=PROJECT_NAME,
                    ex_force_service_region=REGION_NAME)
#                    ex_domain_name=domain_name)

    ###########################################################################
    #
    # clean up resources from previous demos
    #
    ###########################################################################

    # destroy running demo instances
    for instance in conn.list_nodes():
        if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3',
                             'app-controller',
                             'app-services', 'app-api-1', 'app-api-2']:
            print(f'Destroying Instance: {instance.name}')
            conn.destroy_node(instance)

    # wait until all nodes are destroyed to be able to remove depended security groups
    nodes_still_running = True
    while nodes_still_running:
        nodes_still_running = False
        time.sleep(3)
        instances = conn.list_nodes()
        for instance in instances:
            # if we see any demo instances still running continue to wait for them to stop
            if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-worker-3',
                                 'app-controller', 'app-services', 'app-api-1', 'app-api-2']:
                nodes_still_running = True
                print('There are still instances running, waiting for them to be destroyed...')

    # delete security groups
    for group in conn.ex_list_security_groups():
        if group.name in ['control', 'worker', 'api', 'services']:
            print(f'Deleting security group: {group.name}')
            conn.ex_delete_security_group(group)


if __name__ == '__main__':
    main()
