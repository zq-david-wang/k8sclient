from k8sclient.K8SClient import PodBuilder
from k8sclient.keywords import delete_pod
import time

namespace = "k8sft"
image = "127.0.0.1:30100/library/docker-stress"


def deploy(name, node, args):
    PodBuilder(
        name, namespace
    ).add_container(
        name=name + "-container",
        image=image,
        args=args,
        limits={'cpu': '16', 'memory': '64Gi'},
        requests={'cpu': '0', 'memory': '0'},
    ).set_node(node).deploy()


def un_deploy(name):
    delete_pod(namespace, name)


if __name__ == "__main__":

    # deploy cpu stress
    # deploy("cpu-stress", "10.19.137.153", "--cpu 8  --timeout 60s")
    # time.sleep(120)
    # un_deploy()
    # memory stress
    for i in range(6):
        deploy("memory-stress-%d" % i, "10.19.137.154", "-m 6 --vm-hang 60 --vm-bytes 2G  --timeout 90s")
    time.sleep(150)
    for i in range(6):
        un_deploy("memory-stress-%d" % i)
