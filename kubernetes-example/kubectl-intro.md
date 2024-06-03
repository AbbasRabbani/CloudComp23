# Introduction to kubectl 

## Prerequisites

For using this you must install the following tools: 

- Python 
- Pip
- Kubectl 
- Openstack-Client

### Python 

Install python and pip for your OS, if it is not installed. This is already done at the NetLab PCs.

### Installing kubectl and arkade

Run this in a **bash** terminal to download arkade and install kubectl:

For windows you can use e.g. the **Git Bash** terminal.

```bash
curl -sLS https://dl.get-arkade.dev | sh
arkade get kubectl
# To load the path to the binary
export PATH=$PATH:$HOME/.arkade/bin/
```

With arkade you can also install other tools: ```arkade get``` to see all possibilities.

### Openstack Client

To install the Openstack client and the magnum package:

If you are using Windows, you must start the bash terminal with **Administrator** privileges!

```bash
pip3 install openstackclient python-magnumclient
# Download the Openstack RC File from your Openstack account
# Load the file
source {USERNAME}-openrc.sh
```

### Download the kubeconfig 

Download the kubeconfig file for your cluster from OpenStack.

```bash
# Before using this, check if Openstack RC File is loaded!
openstack coe cluster config {CLUSTER_NAME}
# Then run the given command in terminal
export ...
# Now you are able to run kubectl commands at your Kubernetes cluster
```

## Deployment of the needed description in kubernetes

These are two approaches to create the description in Kubernetes: 

```bash
# create a namespace 
kubectl create namespace web-test

# Then choose one of the following ways:
# (1) Create the description
kubectl create -f nginx.yml -f service.yml

# (2) Create or update descriptions if existing
kubectl apply -f nginx.yml -f service.yml
```

## To show it is working

Here are some useful commands:

```bash
# show nodes
kubectl get nodes

# show pods for our namespace
kubectl get -n web-test pods 

# show deployments for our namespace
kubectl get -n web-test deployment

# show services for our namespace
kubectl get -n web-test service

# show logs of deployed nginx instances
kubectl logs -n web-test deployment/nginx-deployment
```

## Scaling up and down

```bash
# scale up instances to 5
kubectl scale -n web-test deployment/nginx-deployment --replicas=5

# scale down instances again to 3
kubectl scale -n web-test deployment/nginx-deployment --replicas=3

```


## To see it is working in the browser ;)

The nginx instances are reachable at the floating ips of the **node**-instances at port **30007** in our case.


## Many other things can be done ;)

- Autoscaling 
- Detailled Service functions (LoadBalancer, ...)
- Dashboard
- FaaS Setup ;) 
- ...


## Appendix

### Nginx description

*nginx.yml:*
```yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: web-test
spec:
  selector:
    matchLabels:
      app: nginx-deployment
  replicas: 3 # tells deployment to run 3 pods matching the template
  template:
    metadata:
      labels:
        app: nginx-deployment
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80

```

### Nginx service description

*service.yml:*
```yml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: web-test
spec:
  type: NodePort
  selector:
    app: nginx-deployment
  ports:
      # By default and for convenience, the `targetPort` is set to the same value as the `port` field.
    - port: 80
      targetPort: 80
      # Optional field
      # By default and for convenience, the Kubernetes control plane will allocate a port from a range (default: 30000-32767)
      nodePort: 30007
```