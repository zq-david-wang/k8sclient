"""
This script is used for testing network bandwidth left for sending traffic in a single channel.
"""
from k8sclient.keywords import (
    list_ready_nodes,
    get_pod_ip,
    wait_for_pod_state,
    RUNNING,
    SUCCEEDED,
    tail_pod_logs,
    delete_pod,
    remove_pod,
    NOT_FOUND,
    register_cluster,
    switch_cluster,
    cleanup_pods,
    cleanup_services,
)
from k8sclient.Components import PodBuilder, ServicePort
import re
import time
import random

register_cluster("yancheng", "~/.kube/config-yancheng")
register_cluster("shanghai", "~/.kube/config-shanghai")
# switch_cluster("yancheng")

image = "ihub.helium.io:30100/library/alpine-iperf"
server_args = "iperf -f M -i 1 -m -s"
client_args = r"iperf -f M -t 60 -i 1 -c %s"
namespace = "k8sft"
nodes = list_ready_nodes()
random.shuffle(nodes)
server_port = ServicePort("serverport", 5001, 5001)
global_server_name = "iperf-server"
glimit = {'cpu': '0', 'memory': '8Gi'}
grequest = {'cpu': '0', 'memory': '0'}


def run_server(server_node, client_nodes):
    server_pod_name = "server-" + "-".join(server_node.split("."))
    PodBuilder(
        server_pod_name, namespace
    ).add_container(
        name=server_pod_name + "-container",
        image=image,
        args=server_args,
        limits=glimit,
        requests=grequest,
        ports=[server_port]
    ).set_node(server_node).deploy()

    # wait for server pod running
    wait_for_pod_state(namespace, server_pod_name, timeout=600, expect_status=RUNNING)
    time.sleep(10)
    # get server pod ip
    server_pod_ip = get_pod_ip(namespace, server_pod_name)
    client_count = 0
    for node in client_nodes:
        client_count += 1
        PodBuilder(
            "iperf-client-%d" % client_count, namespace
        ).add_container(
            name="iperf-client-container-%d" % client_count,
            image=image,
            args=client_args % server_pod_ip,
            limits=glimit,
            requests=grequest,
        ).set_node(node).deploy()
    for i in range(1, client_count+1):
        wait_for_pod_state(namespace, "iperf-client-%d" % i, timeout=600, expect_status=SUCCEEDED)
        logs = tail_pod_logs(namespace, "iperf-client-%d" % i, lines=20).strip()
        print logs.split("\n")[-1]
    # get server log
    # logs = tail_pod_logs(namespace, server_pod_name, lines=100).strip()
    # print logs


def cleanup():
    cleanup_pods(namespace=namespace)
    cleanup_services(namespace)


cleanup()
target_server = "10.19.137.154"
client_servers = [n for n in nodes if n != target_server]
# run_server(target_server, ["10.19.248.26"]*6)
run_server(target_server, ["10.19.137.140", "10.19.137.141"])
cleanup()
