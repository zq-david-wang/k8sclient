from k8sclient.Components import ServicePort, ServiceBuilder, ReplicaSetBuilder, HostPathVolume

namespace = "monkey"
image = "openjdk-bash:jre-alpine3.7"
# args = "java -cp /opt/zookeeper/zookeeper-3.4.9.jar:/opt/zookeeper/lib/slf4j-api-1.6.1.jar:/opt/zookeeper/lib/slf4j-log4j12-1.6.1.jar:/opt/zookeeper/lib/log4j-1.2.16.jar:/opt/zookeeper/conf  org.apache.zookeeper.server.quorum.QuorumPeerMain /opt/zookeeper/conf/zoo.cfg"
args = "/opt/zookeeper/bin/zkServer.sh start /opt/zookeeper/conf/zoo.cfg"

# args = "sleep 3600"
# ports
client_port = ServicePort("clientport", 2181, 2181)
server_port_1 = ServicePort("serverport1", 2888, 2888)
server_port_2 = ServicePort("serverport2", 3888, 3888)

# volume
volume_pack = HostPathVolume(
        "zkpack",
        "/opt/zookeeper",
        "/data/zookeeper/pack",
        read_only=True
    )

# replica set
nodes = [
    "",
    "192.168.57.101",
    "192.168.57.102",
    "192.168.57.103",
]
for i in range(1, 4):
    name = "zk-%d" % i
    service = ServiceBuilder(name, namespace, service_type="NodePort")
    service.add_port(client_port)
    service.add_port(server_port_1)
    service.add_port(server_port_2)
    volume_data = HostPathVolume(
        "zkdata",
        "/var/lib/zookeeper",
        "/data/zookeeper/zk-%d" % i,
        read_only=False
    )
    rs = ReplicaSetBuilder(
        name, namespace
    ).add_container(
        name=name + "-container",
        image=image,
        args=args,
        ports=[client_port, server_port_1, server_port_2],
        volumes=[volume_pack, volume_data]
    ).attache_service(
        service
    ).set_hostname(name).set_node(nodes[i])
    # service.un_deploy()
    # rs.un_deploy()

    service.deploy()
    rs.deploy()

