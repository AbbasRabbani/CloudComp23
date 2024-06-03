"""Example for Cloud Computing Course Master AI / GSD"""

# This script demonstrates how to use libcloud to start an instance in an OpenStack environment.
# The script will start an instance, list all instances, and then destroy the instance again.
#
# The script uses the libcloud library to interact with the OpenStack API.
# Need to install libcloud first: pip install apache-libcloud
#
# libCloud: https://libcloud.apache.org/
# libCloud API documentation: https://libcloud.readthedocs.io/en/latest/
# OpenStack API documentation: https://developer.openstack.org/
# this code was initially based on the former tutorial:
#   https://developer.openstack.org/firstapp-libcloud/

# Only needed for the password prompt:
# import getpass

# For our new Charmed OpenStack private cloud, we need to specify the path to the
# root CA certificate
import libcloud.security
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

libcloud.security.CA_CERTS_PATH = ['./root-ca.crt']
# Disable SSL certificate verification (not recommended for production)
# libcloud.security.VERIFY_SSL_CERT = False

# Please use 1-29 for 0 in the following variable to specify your group number.
# (will be used for the username, project etc., as coordinated in the lab sessions)

GROUP_NUMBER = 23


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
AUTH_USERNAME = 'CloudComp' + str(GROUP_NUMBER)
# your project in OpenStack
PROJECT_NAME = 'CloudComp' + str(GROUP_NUMBER)
# A network in the project the started instance will be attached to
PROJECT_NETWORK = 'CloudComp' + str(GROUP_NUMBER) + '-net'

# The image to look for and use for the started instance
# ubuntu_image_name = "Ubuntu 18.04 - Bionic Beaver - 64-bit - Cloud Based Image"
#UBUNTU_IMAGE_NAME = "auto-sync/ubuntu-jammy-22.04-amd64-server-20240319-disk1.img"
UBUNTU_IMAGE_NAME = "ubuntu-22.04-jammy-x86_64"

# default region
REGION_NAME = 'RegionOne'
# domain to use, "default" for local accounts, formerly "hsfulda" for LDAP accounts etc.
# domain_name = "default"


def main():  # noqa: C901 pylint: disable=too-many-branches,too-many-statements,too-many-locals,missing-function-docstring
    # get the password from user
    # auth_password = getpass.getpass("Enter your OpenStack password:")
    auth_password = "CloudComp23"

    # instantiate a connection to the OpenStack private cloud
    # make sure to include ex_force_auth_version='3.x_password', as needed in our environment
    provider = get_driver(Provider.OPENSTACK)

    print(f"Opening connection to {AUTH_URL} as {AUTH_USERNAME}...")

    conn = provider(AUTH_USERNAME,
                    auth_password,
                    ex_force_auth_url=AUTH_URL,
                    ex_force_auth_version='3.x_password',
                    ex_tenant_name=PROJECT_NAME,
                    ex_force_service_region=REGION_NAME)
    #               ex_domain_name=domain_name)

    print("Getting images and selecting desired one...")
    print("=========================================================================")

    # get a list of images offered in the cloud context (e.g. Ubuntu 20.04, cirros, ...)
    images = conn.list_images()
    image = ''
    for img in images:
        if img.name == UBUNTU_IMAGE_NAME:
            image = img
            print(img)

    print("Getting flavors...")
    print("=========================================================================")

    # get a list of flavors offered in the cloud context (e.g. m1.small, m1.medium, ...)
    flavors = conn.list_sizes()
    for flavor in flavors:
        print(flavor)

    print("Selecting desired flavor...")
    print("=========================================================================")

    # get the flavor with id 2
    flavor_id = '2'
    flavor = conn.ex_get_size(flavor_id)
    print(flavor)

    print("Selecting desired network...")
    print("=========================================================================")

    # get a list of networks in the cloud context
    networks = conn.ex_list_networks()
    network = ''
    for net in networks:
        if net.name == PROJECT_NETWORK:
            network = net

    print("Create instance 'testing'...")
    print("=========================================================================")

    # create a new instance with the name "testing"
    # make sure to provide networks (networks={network}) the instance should be attached to
    instance_name = 'testing'
    testing_instance = conn.create_node(name=instance_name, image=image, size=flavor,
                                        networks={network})
    print(testing_instance)

    print("Showing all running instances...")
    print("=========================================================================")

    # show all instances (running nodes) in the cloud context
    instances = conn.list_nodes()
    for instance in instances:
        print(instance)

    print("Destroying instance...")
    print("=========================================================================")

    # destroy the instance we have just created
    conn.destroy_node(testing_instance)


# method that is called when the script is started from the command line
if __name__ == '__main__':
    main()
