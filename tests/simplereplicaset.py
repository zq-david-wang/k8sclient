from k8sclient.Components import ReplicaSetBuilder

namespace = "k8sft"
image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"

image2 = "ihub.helium.io:30100/library/alpine-iperf"
server_args = "iperf -f M -i 1 -m -s"

ReplicaSetBuilder(
    "rstest1", namespace
).add_container(
    name="memcached",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '1', 'memory': '512Mi'},
).add_annotation("io.enndata.dns/pod.enable", "true").deploy()


ReplicaSetBuilder(
    "rstest2", namespace
).add_container(
    name="iperf",
    image=image2,
    args=server_args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '1', 'memory': '512Mi'},
).add_annotation("io.enndata.dns/pod.enable", "true").deploy()


# io.enndata.dns/pod.enable=true

