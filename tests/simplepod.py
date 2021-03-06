from k8sclient.Components import (
    PodBuilder,
)
namespace = "k8sft"
image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"


pod = PodBuilder(
    "justtest",
    namespace,
    labels={"network-restrict-internal-only": "oops"}
).set_node(
    "10.19.137.159"
).add_container(
    "justtest",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
    RESTRICTED_INTERNAL_ONLY="1"
)
# .add_annotation("security.alpha.kubernetes.io/unsafe-sysctls", "net.core.somaxconn=512")
pod.deploy(dns_policy="Default")


# limits larger than node allocable: running
