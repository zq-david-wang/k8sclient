from k8sclient.Components import ReplicaSetBuilder, PodBuilder, CephFSVolume


namespace = "k8sft"
image = "alpine"
args = "ls"

rs = ReplicaSetBuilder(
    "oomtest", namespace
).set_replicas(3).add_container(
        name="oom-stress",
        image=image,
        args=args,
        limits={'cpu': '1', 'memory': '512Mi'},
        requests={'cpu': '1', 'memory': '512Mi'}
)

rs.deploy()
