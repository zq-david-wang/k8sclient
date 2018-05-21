from k8sclient.Components import (
    PodBuilder,
)
namespace = "k8sft"
image = "127.0.0.1:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"


pod = PodBuilder(
    "justtest",
    namespace,
    labels={"network-restrict-internal-only": "oops"}
).add_container(
    "justtest",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
    RESTRICTED_INTERNAL_ONLY="1"
)
pod.deploy()


# limits larger than node allocable: running
