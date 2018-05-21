from k8sclient.Components import (
    ServicePort,
    PodBuilder,
    ServiceBuilder,
)
from k8sclient.keywords import (
    cleanup_pods,
    cleanup_services,
    list_ready_nodes,
    pod_exec,
    wait_for_pod_state,
    RUNNING
)
import re
import json
pattern = re.compile("(\w+)\s+(\d+)m([.\d]+)s")
namespace = "k8sft"
image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"
client_port = ServicePort("clientport", 11211, 11211)


nodes = [_ for _ in list_ready_nodes() if not _.startswith("10.19.138")][-1::-1]
node_count = len(nodes)
service_per_pod = 40


def deploy_services(nr=0):
    service_id_start = service_per_pod * node_count * nr
    for n in nodes:
        pod_name = "memcached-%d-%s" % (nr, "-".join(n.split(".")), )
        pod = PodBuilder(
            pod_name,
            namespace,
        ).set_node(
            n
        ).add_container(
            pod_name,
            image=image,
            args=args,
            ports=[client_port],
            requests={'cpu': '0', 'memory': '0'},
            limits={'cpu': '0', 'memory': '0'}
        )
        services = [
            ServiceBuilder("service-memcached-%d" % (i+service_id_start), namespace).add_port(client_port)
            for i in range(service_per_pod)
            ]
        for s in services:
            pod.attache_service(s)
            s.deploy()
        pod.deploy()
        service_id_start += service_per_pod


def test_time(nr=0):
    total = node_count * service_per_pod * (nr+1)
    testnodes = [
        # "10.19.137.140",
        # "10.19.137.148",
        "10.19.137.148",
        # "10.19.140.8",
    ]
    ipvsnodes = [
        "10.19.137.148",
    ]
    for n in testnodes:
        pod_name = "memcached-%d-%s" % (nr, "-".join(n.split(".")), )
        o = pod_exec(namespace, pod_name, ["bash", "-c",
"time for c in {1..10}; do for i in {1..%d}; do echo > /dev/tcp/service-memcached-$i/11211; done; done" % (total-1)],
                     timeout=600)
        for l in o.split("\n"):
            ll = l.strip()
            if not ll:
                continue
            if "real" in ll or "user" in ll or "sys" in ll:
                continue
            print ll
        r = {"node": n, "service_count": total}
        if n in ipvsnodes:
            r['kube-proxy'] = "ipvs"
        else:
            r['kube-proxy'] = "iptables"
        for m in pattern.findall(o):
            r[m[0]+"_time"] = int(m[1]) * 60 + float(m[2])
        print json.dumps(r), ","


def clean_up():
    cleanup_pods(namespace=namespace)
    cleanup_services(namespace)


def deploy_10kservices():
    service_id_start = 0
    total_services = []
    for nr in range(9):
        for n in nodes:
            pod_name = "memcached-%d-%s" % (nr, "-".join(n.split(".")), )
            pod = PodBuilder(
                pod_name,
                namespace,
            ).set_node(
                n
            ).add_container(
                pod_name,
                image=image,
                args=args,
                ports=[client_port],
                requests={'cpu': '0', 'memory': '0'},
                limits={'cpu': '0', 'memory': '0'}
            )
            services = [
                ServiceBuilder("service-memcached-%d" % (i+service_id_start), namespace).add_port(client_port)
                for i in range(service_per_pod)
                ]
            for s in services:
                pod.attache_service(s)
            pod.deploy()
            wait_for_pod_state(namespace, pod_name, timeout=600, expect_status=RUNNING)
            total_services += services
            service_id_start += service_per_pod
    print "pod are all running, deploy %d services now..." % len(total_services)
    for s in total_services:
        s.deploy()


if __name__ == "__main__":
    clean_up()
    # deploy_services(0)
    # test_time(0)
    # deploy_services(1)
    # test_time(1)
    # deploy_services(2)
    # test_time(2)
    # deploy_services(3)
    # test_time(3)
    # deploy_services(4)
    # deploy_services(5)
    # deploy_services(6)
    # deploy_services(7)
    # deploy_services(8)
    # test_time(8)
    # deploy_10kservices()
