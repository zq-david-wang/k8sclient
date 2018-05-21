from k8sclient.Components import (
    ServicePort,
    PodBuilder,
    ServiceBuilder,
)
from k8sclient.keywords import (
    cleanup_pods,
    cleanup_services,
)
namespace = "k8sft"
image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"
client_port = ServicePort("clientport", 11211, 11211)


def deploy(node):
    pod = PodBuilder(
        "memcached-1",
        namespace,
    ).set_node(
        node
    ).add_container(
        "pod-memcached-1",
        image=image,
        args=args,
        ports=[client_port],
        requests={'cpu': '200m', 'memory': '256Mi'},
        limits={'cpu': '1', 'memory': '512Mi'}
    )
    for i in range(3000):
        s = ServiceBuilder("service-memcached-%d" % i, namespace).add_port(client_port)
        s.deploy()
        pod.attache_service(s)
    pod.deploy()


def clean_up():
    cleanup_pods(namespace=namespace)
    cleanup_services(namespace)

if __name__ == "__main__":
    clean_up()
    # deploy("10.19.138.179")
