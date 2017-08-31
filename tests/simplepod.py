from k8sclient.Components import (
    PodBuilder,
)
namespace = "health-check"
image = "127.0.0.1:30100/library/memcached:check2"
args = "memcached -m 1028 -u root -v"


pod = PodBuilder(
    "justtest",
    namespace,
).set_node(
    "10.19.137.154"
).add_container(
    "justtest",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
)
pod.deploy()
