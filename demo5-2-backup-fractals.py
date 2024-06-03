

import getpass
import json
import os

import libcloud
import libcloud.security
import requests
from libcloud.storage.providers import get_driver
from libcloud.storage.types import Provider

# HS-Fulda Private Cloud
auth_url = 'https://192.168.72.40:5000'
region_name = 'RegionOne'
domain_name = "hsfulda"

api_ip = '192.168.72.102'


def main():
    ###########################################################################
    #
    # get credentials
    #
    ###########################################################################

    if "OS_PROJECT_NAME" in os.environ:
        project_name = os.environ["OS_PROJECT_NAME"]
    else:
        project_name = eval(input("Enter your OpenStack project:"))

    if "OS_USERNAME" in os.environ:
        auth_username = os.environ["OS_USERNAME"]
    else:
        auth_username = eval(input("Enter your OpenStack username:"))

    if "OS_PASSWORD" in os.environ:
        auth_password = os.environ["OS_PASSWORD"]
    else:
        auth_password = getpass.getpass("Enter your OpenStack password:")

    ###########################################################################
    #
    # create connection
    #
    ###########################################################################

    libcloud.security.VERIFY_SSL_CERT = False

    provider = get_driver(Provider.OPENSTACK_SWIFT)
    swift = provider(auth_username,
                     auth_password,
                     ex_force_auth_url=auth_url,
                     ex_force_auth_version='3.x_password',
                     ex_tenant_name=project_name,
                     ex_force_service_region=region_name,
                     ex_domain_name=domain_name)

    ###########################################################################
    #
    # create container
    #
    ###########################################################################

    container_name = 'fractals'
    containers = swift.list_containers()
    container = False
    for con in containers:
        if con.name == container_name:
            container = con

    if not container:
        container = swift.create_container(container_name=container_name)

    print(container)

    ###########################################################################
    #
    # backup existing fractals to container
    #
    ###########################################################################

    endpoint = 'http://' + api_ip
    params = { 'results_per_page': '-1' }
    response = requests.get('%s/v1/fractal' % endpoint, params=params)
    data = json.loads(response.text)
    for fractal in data['objects']:
        response = requests.get('%s/fractal/%s' % (endpoint, fractal['uuid']), stream=True)
        container.upload_object_via_stream(response.iter_content(), object_name=fractal['uuid'])

    for object_data in container.list_objects():
        print(object_data)


if __name__ == '__main__':
    main()
