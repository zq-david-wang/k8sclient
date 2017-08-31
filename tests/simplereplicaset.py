from k8sclient.Components import ReplicaSetBuilder

namespace = "health-check"
image = "127.0.0.1:30100/library/memcached:check2"
args = "memcached -m 1028 -u root -v"

ReplicaSetBuilder(
    "rstest", namespace
).add_container(
    name="rstest-container",
    image=image,
    args=args,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
).deploy()

