from k8sclient.Components import (
    PodBuilder,
)
namespace = "k8sft"
image = "ihub.helium.io:30100/library/hbasestandalone:latest"
args = "sleep 36000"


pod = PodBuilder(
    "hbasestandalone",
    namespace
).set_node(
    "10.19.140.15"
).add_container(
    "justtest",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
)
pod.deploy()


# limits larger than node allocable: running
