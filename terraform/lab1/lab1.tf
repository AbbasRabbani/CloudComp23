# Define CloudComp group number
variable "group_number" {
  type = string
  default = "32"
}

## OpenStack credentials can be used in a more secure way by using
## cloud.yaml from https://private-cloud.informatik.hs-fulda.de/project/api_access/clouds.yaml/

# or by using env vars exported from openrc here,
# e.g., using 'export TF_VAR_os_password=$OS_PASSWORD'

# Define OpenStack credentials, project config etc.
locals {
  auth_url        = "https://10.32.4.182:5000/v3"
  user_name       = "CloudComp32"
  user_password = "demo"
  tenant_name     = "CloudComp${var.group_number}"
  #network_name    = "CloudComp${var.group_number}-net"
  router_name     = "CloudComp${var.group_number}-router"
  image_name      = "ubuntu-22.04-jammy-x86_64"
  flavor_name     = "m1.small"
  region_name     = "RegionOne"
  floating_net    = "ext_net"
  dns_nameservers = [ "10.33.16.100" ]
}

# Define OpenStack provider
terraform {
required_version = ">= 0.14.0"
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      # last version before 2.0.0, shows octavia/neutron lbaas deprecation warnings
      # "~> 1.54.1"
      version = ">= 2.0.0"
    }
  }
}

# Configure the OpenStack Provider
provider "openstack" {
  user_name   = local.user_name
  tenant_name = local.tenant_name
  password    = local.user_password
  auth_url    = local.auth_url
  region      = local.region_name
  # due to currenty missing valid certificate
  insecure    = true
}



###########################################################################
#
# create keypair
#
###########################################################################

# import keypair, if public_key is not specified, create new keypair to use
resource "openstack_compute_keypair_v2" "terraform-keypair" {
  name       = "my-terraform-pubkey"
  #public_key = file("~/.ssh/id_rsa.pub")
}



###########################################################################
#
# create security group
#
###########################################################################

resource "openstack_networking_secgroup_v2" "terraform-secgroup" {
  name        = "my-terraform-secgroup"
  description = "for terraform instances"
}

resource "openstack_networking_secgroup_rule_v2" "terraform-secgroup-rule-http" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  #remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.terraform-secgroup.id
}

resource "openstack_networking_secgroup_rule_v2" "terraform-secgroup-rule-ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  #remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.terraform-secgroup.id
}


###########################################################################
#
# create network
#
###########################################################################

resource "openstack_networking_network_v2" "terraform-network-1" {
  name           = "my-terraform-network-1"
  admin_state_up = "true"
}

resource "openstack_networking_subnet_v2" "terraform-subnet-1" {
  name            = "my-terraform-subnet-1"
  network_id      = openstack_networking_network_v2.terraform-network-1.id
  cidr            = "192.168.255.0/24"
  ip_version      = 4
  dns_nameservers = local.dns_nameservers
}

#new ressource here:
resource "openstack_networking_port_v2" "port_1" {
  name            = "port_1"
  network_id      = openstack_networking_network_v2.terraform-network-1.id
  admin_state_up  = "true"
  security_group_ids = [openstack_networking_secgroup_v2.terraform-secgroup.id]

  fixed_ip {
  subnet_id = openstack_networking_subnet_v2.terraform-subnet-1.id
  }
}

data "openstack_networking_router_v2" "router-1" {
  name = local.router_name
}

resource "openstack_networking_router_interface_v2" "router_interface_1" {
  router_id = data.openstack_networking_router_v2.router-1.id
  subnet_id = openstack_networking_subnet_v2.terraform-subnet-1.id
}



###########################################################################
#
# create instances
#
###########################################################################

resource "openstack_compute_instance_v2" "terraform-instance-1" {
  name              = "my-terraform-instance-1"
  image_name        = local.image_name
  flavor_name       = local.flavor_name
  key_pair          = openstack_compute_keypair_v2.terraform-keypair.name
  security_groups   = [openstack_networking_secgroup_v2.terraform-secgroup.name]

  depends_on = [openstack_networking_subnet_v2.terraform-subnet-1]

  network {
    #uuid = openstack_networking_network_v2.terraform-network-1.id
    port = openstack_networking_port_v2.port_1.id
  }

  user_data = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get -y install apache2
    rm /var/www/html/index.html
    cat > /var/www/html/index.html << INNEREOF
    <!DOCTYPE html>
    <html>
      <body>
        <h1>It works!</h1>
        <p>hostname</p>
      </body>
    </html>
    INNEREOF
    sed -i "s/hostname/terraform-instance-1/" /var/www/html/index.html
    sed -i "1s/$/ terraform-instance-1/" /etc/hosts
  EOF
}



###########################################################################
#
# assign floating ip to instance
#
###########################################################################
resource "openstack_networking_floatingip_v2" "fip_1" {
  pool    = local.floating_net
}

resource "openstack_networking_floatingip_associate_v2" "terraform-instance-1-ip" {
  floating_ip = openstack_networking_floatingip_v2.fip_1.address
  port_id     = openstack_networking_port_v2.port_1.id

}

# does work, though openstack_compute_floatingip_associate_v2 is deprecated, 
# openstack_compute_instance_v2.terraform-instance-1.network[0].port is empty after instance creation: ""
#
#resource "openstack_networking_floatingip_associate_v2" "terraform-instance-1-ip" {
#  floating_ip = openstack_networking_floatingip_v2.fip_1.address
#  port_id = openstack_compute_instance_v2.terraform-instance-1.network[0].port
#}
#
# even better, as soon as openstack_compute_instance_v2.terraform-instance-1.network[0].port is not "":
#resource "openstack_networking_floatingip_v2" "fip_1" {
#  pool    = local.floating_net
#  port_id = openstack_compute_instance_v2.terraform-instance-1.network[0].port
#}

output "vip_addr" {
  value = openstack_networking_floatingip_v2.fip_1
}
