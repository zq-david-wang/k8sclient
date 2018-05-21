from k8sclient.dataframes import collect_all_endpoints

_endpoint_infos, endpoint_ip_ports = collect_all_endpoints()

port_list = endpoint_ip_ports[(endpoint_ip_ports.protocol == 'TCP') & (endpoint_ip_ports.target_kind == 'Pod')][['ip', 'port', "node_name", "target_namespace", "target_name"]]
port_list = port_list.drop_duplicates()
# b.groupby(["node_name", "ip"]).agg(lambda x: x.sample()).reset_index()

from k8sclient.keywords import (
    list_ready_nodes,
    cleanup_pods,
    get_pod_ip,
    pod_exec,
    is_pod_running,
)
from k8sclient.K8SClient import (
    PodBuilder,
)
import time

nodes = list_ready_nodes()
namespace = "health-check"
image = "ihub.helium.io:30100/library/memcached:check2"
args = "memcached -m 1028 -u root -v"
# node_marks = {n: "-".join(n.split(".")) for n in nodes}


def _wait_for_pod_ready(timeout=420):
    ready = [False for _ in nodes]
    start = time.time()
    while True:
        if all(ready):
            break
        for i, n in enumerate(nodes):
            if ready[i]:
                continue
            pod_name = pod_names[n]
            ready[i] = is_pod_running(namespace, pod_name)
            if ready[i]:
                print pod_name, "is Running."
        if time.time() - start > timeout:
            break
        time.sleep(3)
    return [nodes[i] for i, r in enumerate(ready) if r]


pod_names = {}
for n in nodes:
    node_mark = "-".join(n.split("."))
    pod_name = "check-pod-on-%s" % (node_mark, )
    pod_names[n] = pod_name
    pod = PodBuilder(
        pod_name,
        namespace,
    ).set_node(
        n
    ).add_container(
        pod_name,
        image=image,
        args=args,
        requests={'cpu': '0', 'memory': '0'}
    )
    # pod.deploy()


ready_nodes = _wait_for_pod_ready()


def _check(pod, server, port):
    return pod_exec(namespace, pod, ["/opt/check2.sh", str(server), str(port)])

# get active ports
active_ports = []
for index, row in port_list.iterrows():
    r = _check(pod_names[row['node_name']], row['ip'], row['port'])
    if r:
        active_ports.append(row)

for n in ready_nodes:
    print "checking on", n
    for row in active_ports:
        if n == row['node_name']:
            continue
        r = _check(pod_names[n], row['ip'], row['port'])
        if not r:
            print n, "fail to connect", row

