# k8sclient
kubernetes python wrapper for data analysis, deployment and test.

## Features
- K8s cluster information retrieve and analysis. (via pandas)
- k8s easy deployment, simple interface to attach service and volumes.
- Some simple test scripts for cluster network health, file system and network throughput.

# Play with k8s cluster using python

- __Installation__
  * pip
  * kubernetes
  * pandas (Only needed for cluster data analysis)
  * k8sclient (wrapper for kubernetes)


- __Collect cluster information and data analysis with pandas__
  * setup
  * pod
  * node
  * service
  * etc.
 
  
- __Deploy pod/replicaset/service and some simple usage/test__
  * pods, volume, service and etc.
  * replicaset
  * network connectivity test
  * file system test (fio), network throughput (iperf), pod stress test and etc
  * service search
  * query api (hubot)
  
## Installation
#### [pip](https://pip.pypa.io/en/stable/installing/)
>Be cautious if you're using a Python install that's managed by your operating system or another package manager. get-pip.py does not coordinate with those tools, and may leave your system in an inconsistent state.
>To install pip via package manager, use package name python-pip
>Python3 is recommented though, not sure thoes numpy/pandas package can work well with python3

```shell
wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
```

#### [kubernetes](https://github.com/kubernetes-incubator/client-python/)
```shell
pip install kubernetes
```
> Usefully documentation links 
   * [auto generated docs](https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/README.md)
   * [api references](https://kubernetes.io/docs/api-reference/v1.6/)


#### [pandas](pandas.pydata.org/pandas-docs/stable/)
```shell
pip install pandas
```

#### k8sclient
```shell
git clone https://github.com/zq-david-wang/k8sclient.git
cd k8sclient && pip install -e .
```

Checkout the notebooks for more examples.
