from k8sclient.K8SClient import PodBuilder, CephFSVolume
from k8sclient.keywords import delete_pod
import random

image = "127.0.0.1:30100/library/python-tools:v20170619"
namespace = "monkey"
ceph_monitors = "10.19.248.14:6789,10.19.248.15:6789,10.19.248.16:6789"
ceph_secret = "ceph-secret"

nodes = [
    "10.19.248.31",
    "10.19.248.32",
    "10.19.248.33",
    "10.19.248.34",
    "10.19.248.35",
    "10.19.248.36",
    "10.19.248.37",
    "10.19.248.38",
    "10.19.248.39",
    "10.19.248.40",
]


def deploy(name, node=None):
    if node is None:
        node = random.choice(nodes)
    volume = CephFSVolume(
        "cephfs",
        "/tmp",
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        fs_path="jokefiles",
        sub_path=name
    )
    PodBuilder(
        name,
        namespace,
    ).set_node(
        node
    ).add_container(
        name,
        image=image,
        args="toomanyfiles.py",
        volumes=[volume],
        BATCH_SIZE=10000,
        BATCH_COUNT=1000
    ).deploy()


def deploy_bigfile(name, node=None):
    if node is None:
        node = random.choice(nodes)
    volume = CephFSVolume(
        "cephfs",
        "/tmp",
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        fs_path="jokefiles",
        sub_path=name
    )
    PodBuilder(
        name,
        namespace,
    ).set_node(
        node
    ).add_container(
        name,
        image=image,
        args="bigfiles.py",
        volumes=[volume],
    ).deploy()


def un_deploy(name):
    delete_pod(namespace, name)

if __name__ == "__main__":
    deploy_bigfile("bigfile")
    #for i in range(9):
    #    deploy("joke-%d" % i, nodes[i])
        # un_deploy("joke-%d" % i)

