from k8sclient.K8SClient import HostPathVolume, PodBuilder
from k8sclient.keywords import (
    wait_for_pod_state,
    RUNNING,
    delete_pod,
    NOT_FOUND
)
import time
import random


namespace = "monkey"
image = "127.0.0.1:30100/library/python-tools:v20170605-5"
args = "dockerlog.py"
node = "10.19.137.151"
name = "dockerselflog"


def deploy():
    # volume
    volume = HostPathVolume(
        "containers",
        "/apt/containers",
        "/data/docker/containers"
    )
    PodBuilder(
        name,
        namespace,
        node_name=node
    ).add_container(
        name,
        image=image,
        args=args,
        volumes=[volume]
    ).deploy()
    wait_for_pod_state(namespace, name, 60, RUNNING)


def un_deploy():
    delete_pod(namespace, name)
    wait_for_pod_state(namespace, name, 60, NOT_FOUND)


if __name__ == "__main__":
    for i in range(10000):
        print "round", i
        deploy()
        print "pod is running"
        time.sleep(random.randint(1, 3))
        un_deploy()
        print "pod is gone"




