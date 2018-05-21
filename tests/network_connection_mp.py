from k8sclient.keywords import (
    list_ready_nodes,
    cleanup_pods,
    cleanup_services,
    is_pod_running,
    switch_cluster,
    register_cluster,
)
from k8sclient.Components import (
    ServicePort,
    PodBuilder,
    ServiceBuilder,
)
import datetime
import time
import sys
from subprocess import PIPE, Popen
import shlex
import argparse


register_cluster("yancheng", "~/.kube/config-yancheng")
register_cluster("shanghai", "~/.kube/config-shanghai")
parser = argparse.ArgumentParser()
parser.add_argument("--cluster", type=str, help="Which cluster is under testing.", default="shanghai")
parser.add_argument("--batchsize", type=int, help="parallel degree.", default=6)
parser.add_argument("--namespace", type=str, help="namespace used for the test", default="health-check")
args = parser.parse_args()

cluster = args.cluster
switch_cluster(cluster)
cluster_configs = {
    "shanghai": ["~/.kube/config-shanghai-1", "~/.kube/config-shanghai-2", "~/.kube/config-shanghai-3"],
    "yancheng": ["~/.kube/config-yancheng-1", "~/.kube/config-yancheng-2", "~/.kube/config-yancheng-3"]
}
batchsize = args.batchsize

uid = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
# uid = "-2017-08-23-16-27-17"
namespace = args.namespace
global_service_name = namespace + uid
image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"
client_port = ServicePort("clientport", 11211, 11211)
global_service = ServiceBuilder(global_service_name, namespace).add_port(client_port)
SUCCESS_MARK = "CHECK_PASS"


def _get_node_mark(node):
    return "-".join(node.split("."))


def deploy(node):
    node_mark = _get_node_mark(node)
    for i in range(2):
        pod_name = ("pod-%s-%d" % (node_mark, i)) + uid
        service_name = ("service-%s-%d" % (node_mark, i)) + uid
        service = ServiceBuilder(service_name, namespace).add_port(client_port)
        pod = PodBuilder(
            pod_name,
            namespace,
        ).set_node(
            node
        ).add_container(
            pod_name,
            image=image,
            args=args,
            ports=[client_port],
            requests={'cpu': '0', 'memory': '0'},
            limits={'cpu': '0', 'memory': '0'}
        ).attache_service(
            service
        ).attache_service(
            global_service
        )
        pod.deploy()
        service.deploy()


def cleanup():
    cleanup_pods(namespace=namespace)
    cleanup_services(namespace)


def _wait_for_pod_ready(nodes, timeout=420):
    ready = [False for _ in nodes]
    start = time.time()
    while True:
        if all(ready):
            break
        for i, n in enumerate(nodes):
            if ready[i]:
                continue
            node_mark = _get_node_mark(n)
            pod_1 = ("pod-%s-%d" % (node_mark, 1)) + uid
            pod_2 = ("pod-%s-%d" % (node_mark, 0)) + uid
            ready[i] = (is_pod_running(namespace, pod_1) and is_pod_running(namespace, pod_2))
            if ready[i]:
                print pod_1, pod_2, "is Running."
        if time.time() - start > timeout:
            break
        time.sleep(3)
    return [nodes[i] for i, r in enumerate(ready) if r]


if __name__ == "__main__":
    cleanup()
    global_service.deploy()
    nodes = list_ready_nodes()
    # nodes = ["10.19.137.140", "10.19.137.141", "10.19.137.142"]
    for n in nodes:
        deploy(n)
    # wait for pod ready
    ready_nodes = _wait_for_pod_ready(nodes)
    unready_nodes = set(nodes) - set(ready_nodes)
    if unready_nodes:
        print "Following node not ready to run simple pod:"
        for n in unready_nodes:
            print n

    print "wait for everything ready"
    time.sleep(180)
    print "Start testing among ready nodes"
    error_mark = False
    # start multiple process to check
    cmd = r"python network_check.py --clusterconfig %s --namespace %s --node %s --uid=%s"
    if batchsize <= 0:
        batches = [ready_nodes]
    else:
        batches = [ready_nodes[i:i + batchsize] for i in xrange(0, len(ready_nodes), batchsize)]
    configs = cluster_configs[cluster]
    configc = len(configs)
    index = 0
    for batch in batches:
        print "parallel testing ", ",".join(batch)
        ps = [Popen(shlex.split(cmd % (configs[i % configc], namespace, n, uid)), stderr=PIPE)
              for i, n in enumerate(batch)]
        for p in ps:
            _, _err = p.communicate()
            if _err:
                error_mark = True
                print _err
    if not error_mark:
        cleanup()
        print "No network connection issue found"
        if unready_nodes:
            print "But some node is not able to run new pod, maybe docker process is hung."
            exit(1)
    else:
        print "Network issue found. Manually cleanup the pods after fixing the network issue."
        exit(1)
