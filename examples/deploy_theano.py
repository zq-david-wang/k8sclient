from k8sclient.Components import ServicePort, ServiceBuilder, ReplicaSetBuilder, HostPathVolume

namespace = "monkey"
name = "theano"
image = "127.0.0.1:30100/library/theano:latest"
# ports
http_port = ServicePort("httpport", 8888, 8888)
# service
http_service = ServiceBuilder("jupyter", namespace, service_type="NodePort").add_port(http_port)
# volume
volume_nvidia = HostPathVolume(
        "nvidia",
        "/opt/nvidia",
        "/opt/lib/nvidia",
        read_only=True
    )
volume_nvidia_tools = HostPathVolume(
        "nvidia-tools",
        "/opt/tools",
        "/opt/lib/tools",
        read_only=True
    )
volume_cuda = HostPathVolume(
        "cuda",
        "/opt/cuda",
        "/opt/cuda-8.0/",
        read_only=True
    )
# replica set
rs = ReplicaSetBuilder(
    name, namespace
).add_container(
    name=name + "-container",
    image=image,
    ports=[http_port],
    requests={'cpu': '0', 'memory': '0', 'alpha.kubernetes.io/nvidia-gpu': '1'},
    limits={'cpu': '0', 'memory': '0', 'alpha.kubernetes.io/nvidia-gpu': '1'},
    volumes=[volume_nvidia, volume_nvidia_tools, volume_cuda]
).attache_service(
    http_service
).set_hostname(name).set_node("10.19.137.148")


def deploy():
    rs.deploy()
    http_service.deploy()


def un_deploy():
    http_service.un_deploy()
    rs.un_deploy()

if __name__ == "__main__":
    un_deploy()
