from k8sclient.K8SClient import k8sclient

namespace = "k8sft"
args = "memcached -m 4096 -u root -v"
image = "127.0.0.1:30100/library/memcached:check"
port_number = 11211
port_name = "clientport"
node = "10.19.137.154"


def deploy():
    label1 = {"app": "test_service-1"}
    label2 = {"app": "test_service-2"}
    k8sclient.send_create_pod_request(
        namespace=namespace,
        name="pod-1",
        args=args,
        image=image,
        ports={port_number: port_name},
        labels=label1,
        node_name=node
    )
    k8sclient.create_service(
        namespace,
        "service-1",
        port=port_number,
        selector=label1
    )
    k8sclient.send_create_pod_request(
        namespace=namespace,
        name="pod-2",
        args=args,
        image=image,
        ports={port_number: port_name},
        labels=label2,
        node_name=node
    )
    k8sclient.create_service(
        namespace,
        "service-2",
        port=port_number,
        selector=label2
    )


def undeploy():
    k8sclient.remove_service(namespace, "service-1")
    k8sclient.remove_service(namespace, "service-2")
    k8sclient.send_remove_pod_request(namespace, "pod-1")
    k8sclient.send_remove_pod_request(namespace, "pod-2")

if __name__ == "__main__":
    # deploy()
    undeploy()
