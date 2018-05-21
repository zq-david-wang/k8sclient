from k8sclient.keywords import (
    list_ready_nodes,
    wait_for_pod_state,
    SUCCEEDED,
    tail_pod_logs,
    delete_pod,
    NOT_FOUND
)
from k8sclient.Components import (
    PodBuilder,
    HostPathVolume,
    RBDVolume,
    CephFSVolume,
    EmptyDirVolume
)
from k8sclient.Components import PVCBuilder
from k8sclient.Components import RBDPVBuilder, HostPathPVCVolume

image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 32 -u root -v"
namespace = "monkey"

MOUNT_DIR = "/mnt/rbd"
ceph_monitors = "10.19.137.144:6789,10.19.137.145:6789,10.19.137.146:6789"
ceph_pool1 = "k8s.monkey"
ceph_pool2 = "k8sft"
ceph_fstype = "xfs"
ceph_secret = "ceph-secret"  # need create beforehand

rbd1 = RBDVolume(
        "rbd1",
        MOUNT_DIR,
        fs_type=ceph_fstype,
        image="default",
        pool=ceph_pool1,
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        sub_path="rbd",
    )

rbd2 = RBDVolume(
        "rbd2",
        MOUNT_DIR,
        fs_type=ceph_fstype,
        image="default",
        pool=ceph_pool2,
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        sub_path="rbd",
    )


def create_pv():
    pvc1 = PVCBuilder("mypvc1", namespace)
    pv1 = RBDPVBuilder("128Mi", image="default", secret_name=ceph_secret, monitors=ceph_monitors, pool=ceph_pool1, name="mypv1")
    pv1.attach_pvc(pvc1)
    # pv1.deploy(access_mode="ReadWriteOnce")
    pvc1.deploy()
    pvc2 = PVCBuilder("mypvc2", namespace)
    pv2 = RBDPVBuilder("128Mi", image="default", secret_name=ceph_secret, monitors=ceph_monitors, pool=ceph_pool2, name="mypv2")
    pv2.attach_pvc(pvc2)
    # pv2.deploy(access_mode="ReadWriteOnce")
    pvc2.deploy()


def test():
    pvc1 = HostPathPVCVolume(
        'pvcvolume1',
        '/mnt/pvc',
        "mypvc1"
    )
    pvc2 = HostPathPVCVolume(
        'pvcvolume2',
        '/mnt/pvc',
        "mypvc2"
    )

    PodBuilder(
        "rbd1",
        namespace,
    ).set_node(
        "10.19.137.151"
    ).add_container(
        "rbd1-container",
        image=image,
        args=args,
        requests={'cpu': '0', 'memory': '0'},
        limits={'cpu': '0', 'memory': '0'},
        volumes=[pvc1],
    ).deploy()

    PodBuilder(
        "rbd2",
        namespace,
    ).set_node(
        "10.19.140.7"
    ).add_container(
        "rbd2-container",
        image=image,
        args=args,
        requests={'cpu': '0', 'memory': '0'},
        limits={'cpu': '0', 'memory': '0'},
        volumes=[pvc2],
    ).deploy()


# create_pv()
test()
