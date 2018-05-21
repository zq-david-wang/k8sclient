from k8sclient.keywords import (
    list_ready_nodes,
    cleanup_pods,
    cleanup_services,
    is_pod_running,
)
from k8sclient.Components import (
    ServicePort,
    PodBuilder,
    ServiceBuilder,
)
import time

nodes = list_ready_nodes()
nodes = [n for n in nodes if n.startswith("10.19.137")]
global_service_name = "stress-pod"
namespace = "k8sft"
image = "ihub.helium.io:30100/library/memcached:check"
args = "memcached -m 32 -u root -v"
client_port = ServicePort("clientport", 11211, 11211)
global_service = ServiceBuilder(global_service_name, namespace).add_port(client_port)
counts = [0] * len(nodes)
readys = [True] * len(nodes)
dones = [False] * len(nodes)
node_marks = ["-".join(n.split(".")) for n in nodes]
POD_PER_NODE = 400


def stress_pod():
    total = 0
    start = time.time()
    while not all(dones):
        # deploy ready nodes
        for i, n in enumerate(nodes):
            pod_id = counts[i]
            if dones[i]:
                continue
            pod_name = ("pod-%s-%d" % (node_marks[i], pod_id))
            if readys[i]:
                # create a new pod
                PodBuilder(
                    pod_name,
                    namespace,
                ).set_node(
                    n
                ).add_container(
                    pod_name,
                    image=image,
                    args=args,
                    ports=[client_port],
                    requests={'cpu': '0', "memory": '0'},
                    limits = {'cpu': '1', "memory": '32Mi'}
                ).attache_service(
                    global_service
                ).deploy()
                readys[i] = False
                # print "creating", pod_name
            else:
                # check for current pod running
                readys[i] = is_pod_running(namespace, pod_name)
                if readys[i]:
                    total += 1
                    counts[i] += 1
                if counts[i] >= POD_PER_NODE:
                    print "It took %ds to deploy %d pod on %s" % (int(time.time()-start), POD_PER_NODE, n)
                    # print n, "is done~!", "total", total
                    dones[i] = True
        time.sleep(3)
    print "it took", time.time() - start, "s"


def cleanup():
    cleanup_pods(namespace=namespace)
    # cleanup_services(namespace)


# global_service.deploy(force=True)
# stress_pod()
cleanup()
