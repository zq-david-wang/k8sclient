from k8sclient.Components import (
    PodBuilder,
    HostPathVolume
)
namespace = "k8sft"
image = "127.0.0.1:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"

volume_nvidia = HostPathVolume(
        "containers",
        "/data/docker/containers",
        "/data/docker/containers",
        read_only=True
    )

pod = PodBuilder(
    "justtest",
    namespace,
).set_node(
    "10.19.140.6"
).add_container(
    "justtest",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
    volumes=[volume_nvidia],
)
pod.deploy()


# limits larger than node allocable: running
