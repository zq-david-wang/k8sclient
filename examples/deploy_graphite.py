from k8sclient.K8SClient import ServicePort, ServiceBuilder, ReplicaSetBuilder

namespace = "k8sft"
name = "graphite"
image = "127.0.0.1:30100/yangtze/graphite-statsd"
# ports
udp_port = ServicePort("dataport", 8125, 8125, protocol="UDP")
http_port = ServicePort("httpport", 80, 80)
# service
udp_service = ServiceBuilder("graphite", namespace).add_port(udp_port)
http_service = ServiceBuilder("graphite-ui", namespace, service_type="NodePort").add_port(http_port)
# replica set
rs = ReplicaSetBuilder(
    name, namespace
).add_container(
    name=name + "-container",
    image=image,
    ports=[udp_port, http_port]
).attache_service(
    http_service
).attache_service(
    udp_service
).set_hostname(name)


def deploy():
    rs.deploy()
    udp_service.deploy()
    http_service.deploy()


def un_deploy():
    udp_service.un_deploy()
    http_service.un_deploy()
    rs.un_deploy()

if __name__ == "__main__":
    # deploy()
    un_deploy()
