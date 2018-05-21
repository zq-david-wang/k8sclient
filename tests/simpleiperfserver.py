from k8sclient.Components import (
    PodBuilder,
)
namespace = "k8sft"
image = "127.0.0.1:30100/library/alpine-iperf"
args = "iperf -f M -i 1 -m -s"
client_args = r"iperf -f M -t 10 -i 1 -c %s"


pod = PodBuilder(
    "iperfserver",
    namespace,
).set_node(
    "192.168.57.102"
).add_container(
    "server",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
)
#).add_annotation("security.alpha.kubernetes.io/unsafe-sysctls", "net.core.somaxconn=512")
pod.deploy()


# limits larger than node allocable: running
