from k8sclient.Components import ReplicaSetBuilder, PodBuilder, CephFSVolume


namespace = "k8sft"
image = "ihub.helium.io:30100/library/docker-stress:latest"
args = "-m 10 --vm-bytes 128M --timeout 60s --vm-keep"

rs = ReplicaSetBuilder(
    "oomtest", namespace
).set_replicas(4).add_container(
        name="oom-stress",
        image=image,
        args=args,
        limits={'cpu': '200m', 'memory': '512Mi'},
        requests={'cpu': '200m', 'memory': '512Mi'}
)

rs.deploy()

"""
image = "ihub.helium.io:30100/library/docker-stress"
args = "-m 2 --vm-bytes 1G  --timeout 360s"
ceph_monitors = "10.19.137.144:6789,10.19.137.145:6789,10.19.137.146:6789"
ceph_pool = "k8s.monkey"
ceph_fstype = "xfs"
ceph_secret = "ceph-secret"

ceph_fs = CephFSVolume(
            "cephfs",
            "/mnt/fio",
            monitors=ceph_monitors,
            secret_name=ceph_secret,
            fs_path="/",
            sub_path="monkey-fio"
        )

pod = PodBuilder(
    "oomtest",
    namespace
).set_node(
    "10.19.137.154"
).add_container(
    "memory-eater-container",
    image=image,
    args=args,
    requests={'cpu': '0.2', 'memory': '512Mi'},
    limits={'cpu': '0.2', 'memory': '512Mi'},
    volumes=[ceph_fs]
)
pod.deploy(restart_policy="Always")
"""