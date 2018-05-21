from k8sclient.Components import PodBuilder
from k8sclient.keywords import delete_pod, wait_for_pod_state, SUCCEEDED, remove_pod

namespace = "k8sft"
image = "ihub.helium.io:30100/library/docker-stress"


def deploy(name, node, args):
    PodBuilder(
        name, namespace
    ).add_container(
        name=name + "-container",
        image=image,
        args=args,
        limits={'cpu': '0', 'memory': '512Mi'},
        requests={'cpu': '0', 'memory': '0'},
    ).set_node(node).deploy()


def un_deploy(name):
    delete_pod(namespace, name)


if __name__ == "__main__":

    # deploy cpu stress
    client_pod_name = "cpu-stress"
    # deploy(client_pod_name, "10.19.137.148", "--cpu 8  --timeout 300s")
    deploy(client_pod_name, "10.19.137.148", " -m 10 --vm-bytes 128M --timeout 60s --vm-keep")
    wait_for_pod_state(namespace, client_pod_name, timeout=600, expect_status=SUCCEEDED)
    remove_pod(namespace, client_pod_name)
    # time.sleep(120)
    # un_deploy()
    # memory stress
    # for i in range(6):
    #     deploy("memory-stress-%d" % i, "10.19.137.154", "-m 6 --vm-hang 60 --vm-bytes 2G  --timeout 90s")
    # time.sleep(150)
    # for i in range(6):
    #     un_deploy("memory-stress-%d" % i)
