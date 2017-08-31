from k8sclient.keywords import (
    list_ready_nodes,
    cleanup_pods,
    cleanup_services,
    get_pod_ip,
    pod_exec,
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
import random
import time
import sys
import re

register_cluster("yancheng", "~/.kube/config-yancheng")
register_cluster("shanghai", "~/.kube/config-shanghai")

if len(sys.argv) > 1:
    switch_cluster(sys.argv[1])

nodes = list_ready_nodes()
uid = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
global_service_name = "health-check" + uid
namespace = "health-check"
image = "127.0.0.1:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"
client_port = ServicePort("clientport", 11211, 11211)
global_service = ServiceBuilder(global_service_name, namespace).add_port(client_port)
pod_ips = {}
node_marks = {n: "-".join(n.split(".")) for n in nodes}
CREATE = 0
DELETE = 1
SUCCESS_MARK = "CHECK_PASS"


def _get_pod_ip(pod):
    if pod in pod_ips:
        return pod_ips[pod]
    pod_ip = get_pod_ip(namespace, pod)
    pod_ips[pod] = pod_ip
    return pod_ip


def deploy(node, action=CREATE):
    node_mark = "-".join(node.split("."))
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
            requests={'cpu': '0', 'memory': '0'}
        ).attache_service(
            service
        ).attache_service(
            global_service
        )
        if action == CREATE:
            pod.deploy()
            service.deploy()
        else:
            pod.un_deploy()
            service.un_deploy()


def cleanup():
    cleanup_pods(namespace=namespace)
    cleanup_services(namespace)


def _check_service(pod, service, timeout):
    o = pod_exec(namespace, pod, ["/opt/check.sh", service], timeout=timeout)
    if o.find(SUCCESS_MARK) == -1:
        return False
    return True


def check_service(pod, service):
    # give it a retry
    return _check_service(pod, service, timeout=15) or \
           _check_service(pod, service, timeout=15)


def _check_ping(pod, ip):
    o = pod_exec(namespace, pod, ["bash", "-c", "ping %s -c 2 -w 5" % ip], timeout=60)
    m = re.search("(\d+) packets received", o)
    if not m:
        return False
    if int(m.group(1)) == 0:
        return False
    return True


def check_ping(pod, ip):
    return _check_ping(pod, ip) or _check_ping(pod, ip)


def check_pod(pod, targets):
    for target in targets:
        if not check_service(pod, target):
            return "Fail to connect %s on %s." % (target, pod)


def check_host(pod, hosts):
    for host in hosts:
        if not check_ping(pod, host):
            return "Fail to ping %s on %s." % (host, pod)


def check_local(node):
    id_1 = random.randint(0, 1)
    id_2 = (id_1 + 1) % 2
    node_mark = node_marks[node]
    pod_1 = ("pod-%s-%d" % (node_mark, id_1)) + uid
    pod_2 = ("pod-%s-%d" % (node_mark, id_2)) + uid
    pod_2_ip = _get_pod_ip(pod_2)
    pod_1_service = ("service-%s-%d" % (node_mark, id_1)) + uid
    pod_2_service = ("service-%s-%d" % (node_mark, id_2)) + uid
    err = []
    r = check_pod(pod_1, [pod_2_ip, pod_2_service, global_service_name, pod_1_service])
    if r:
        print r
        err.append(r)
    return err


def check_cross(node_1, node_2):
    if node_1 == node_2:
        return []
    id_1 = random.randint(0, 1)
    node_1_mark = node_marks[node_1]
    pod_1 = ("pod-%s-%d" % (node_1_mark, id_1)) + uid

    id_2 = random.randint(0, 1)
    node_2_mark = node_marks[node_2]
    pod_2 = ("pod-%s-%d" % (node_2_mark, id_2)) + uid
    pod_2_service = ("service-%s-%d" % (node_2_mark, id_2)) + uid
    pod_2_ip = _get_pod_ip(pod_2)
    err = []
    r = check_pod(pod_1, [pod_2_ip, pod_2_service])
    if r:
        err.append(r)
        print r
    r = check_host(pod_1, [node_1, node_2])
    if r:
        err.append(r)
        print r
    return err


def _wait_for_pod_ready(timeout=420):
    ready = [False for _ in nodes]
    start = time.time()
    while True:
        if all(ready):
            break
        for i, n in enumerate(nodes):
            if ready[i]:
                continue
            node_mark = node_marks[n]
            pod_1 = ("pod-%s-%d" % (node_mark, 1)) + uid
            pod_2 = ("pod-%s-%d" % (node_mark, 0)) + uid
            ready[i] = (is_pod_running(namespace, pod_1) and is_pod_running(namespace, pod_2))
            if ready[i]:
                print pod_1, pod_2, "is Running."
        if time.time() - start > timeout:
            break
        time.sleep(3)
    return [nodes[i] for i, r in enumerate(ready) if r]

cleanup()
global_service.deploy()
for n in nodes:
    deploy(n, CREATE)
# wait for pod ready
ready_nodes = _wait_for_pod_ready()
unready_nodes = set(nodes) - set(ready_nodes)
if unready_nodes:
    print "Following node not ready to run simple pod:"
    for n in unready_nodes:
        print n

print "Start testing among ready nodes"
errors = []
for n1 in ready_nodes:
    print "checking", n1
    errors += check_local(n1)
    for n2 in ready_nodes:
        errors += check_cross(n1, n2)

if not errors:
    cleanup()
    print "No network connection issue found"
    if unready_nodes:
        exit(1)
else:
    print "Network issue found. Manually cleanup the pods after fixing the network issue."
    exit(1)





