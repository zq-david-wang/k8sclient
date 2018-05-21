from k8sclient.Components import (
    ReplicaSetBuilder,
    RBDVolume,
    ServicePort,
    ServiceBuilder,
)


image = "127.0.0.1:30100/library/jenkins:alpine"
namespace = "monkey"

MOUNT_DIR = "/var/jenkins_home"
ceph_monitors = "10.19.137.144:6789,10.19.137.145:6789,10.19.137.146:6789"
ceph_pool = "k8sft"
ceph_fstype = "xfs"
ceph_secret = "ceph-secret"  # need create beforehand

rbd = RBDVolume(
        "jenkinsrbd",
        MOUNT_DIR,
        fs_type=ceph_fstype,
        image="default",
        pool=ceph_pool,
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        sub_path="jenkins",
    )


http_port = ServicePort("httpport", 8080, 8080)
http_service = ServiceBuilder("jenkins-ui", namespace, service_type="NodePort").add_port(http_port)

rs = ReplicaSetBuilder(
    "myjenkins", namespace
).set_poduser(1000, 1000).add_container(
    name="myjenkins-container",
    image=image,
    requests={'cpu': '0', 'memory': '0'},
    limits={'cpu': '0', 'memory': '0'},
    ports=[http_port],
    volumes=[rbd],
).attache_service(
    http_service
).set_node("10.19.137.149")

http_service.deploy()
# rs.deploy()

