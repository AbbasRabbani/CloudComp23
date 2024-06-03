import configparser
from os.path import expanduser

# import getpass
# import os
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

# default region
# region_name = 'eu-central-1'
# region_name = 'ap-south-1'

# AWS Academy Labs only allow us-east-1 see our AWS Academy Lab Guide, https://awsacademy.instructure.com/login/
region_name = 'us-east-1'

# keypairs are kept and not deleted, they do not cost anything anyway


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

    # aws_access_key_id = "ASIAX..."
    # aws_secret_access_key = "eGwE12j..."
    # aws_session_token = "FwoGZXIvYXdzEK///////////wEaDE..."


    ###########################################################################
    #
    # delete load balancer (Amazon AWS ELB)
    #
    ###########################################################################

    elb_provider = loadbalancer_get_driver(loadbalancer_Provider.ELB)
    elb_conn = elb_provider(aws_access_key_id,
                            aws_secret_access_key,
                            token=aws_session_token,
                            region=region_name)

    # print("List of load balancers: " + str(elb_conn.list_balancers()))
    for loadbalancer in elb_conn.list_balancers():
        if loadbalancer.name == "lb1":
            print("Deleting Load Balancer" + str(loadbalancer))
            elb_conn.destroy_balancer(loadbalancer)

    ###########################################################################
    #
    # create EC2 connection
    #
    ###########################################################################

    provider = compute_get_driver(compute_Provider.EC2)
    conn = provider(key=aws_access_key_id,
                    secret=aws_secret_access_key,
                    token=aws_session_token,
                    region=region_name)

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
            if instance.name in ['all-in-one', 'app-worker-1', 'app-worker-2', 'app-controller', 'app-services']:
                if instance.state is not NodeState.TERMINATED:
                    nodes_still_running = True
        if nodes_still_running is True:
            print('There are still instances running, waiting for them to be destroyed...')
        else:
            print('No instances running')

    # delete security groups
    for group in conn.ex_list_security_groups():
        # services depends on worker and api, so delete services first...
        if group in ['services']:
            print('Deleting security group: %s' % group)
            conn.ex_delete_security_group(group)

    for group in conn.ex_list_security_groups():
        # control depends on worker, so delete control before worker...
        if group in ['control']:
            print('Deleting security group: %s' % group)
            conn.ex_delete_security_group(group)

    for group in conn.ex_list_security_groups():
        if group in ['worker', 'api']:
            print('Deleting security group: %s' % group)
            conn.ex_delete_security_group(group)

    # release elastic ips
    for elastic_ip in conn.ex_describe_all_addresses():
        if elastic_ip.instance_id is None:
            print('Releasing unused elastic ip %s' % elastic_ip)
            conn.ex_release_address(elastic_ip, domain=elastic_ip.domain)


if __name__ == '__main__':
    main()
