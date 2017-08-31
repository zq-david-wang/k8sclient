from k8sclient.K8SClient import k8sclient
import time
import datetime

uid = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
global_service = "health-check" + uid
node_names = k8sclient.list_ready_nodenames()
# node_names = [n for n in node_names if n != "10.19.140.12"]
namespace = "health-check"
image = "127.0.0.1:30100/library/memcached:check"
args = "memcached -m 4096 -u root -v"
port_number = 11211
port_name = "clientport"
glabel = {"app": "health-check"}


def wait_for_pod_state(name, timeout):
    while timeout > 0:
        r = k8sclient.get_pod_info(namespace, name)
        if r.status.phase == "Running":
            print name, "is running."
            return True
        time.sleep(1)
        timeout -= 1
    print "Fail to wait for pod %s Running" % name, r.status.phase
    return False


def _deploy_on_node(node):
    name_prefix = "-".join(node.split(".")) + uid
    label1 = {name_prefix + "-app": "test_service-1"}
    pod_label1 = label1.copy()
    pod_label1.update(glabel)
    label2 = {name_prefix + "-app": "test_service-2"}
    pod_label2 = label2.copy()
    pod_label2.update(glabel)
    pod1 = name_prefix + "-pod-1"
    pod2 = name_prefix + "-pod-2"
    service1 = "service-1-" + name_prefix
    service2 = "service-2-" + name_prefix
    k8sclient.send_create_pod_request(
        namespace=namespace,
        name=pod1,
        args=args,
        image=image,
        ports={port_number: port_name},
        labels=pod_label1,
        node_name=node,
        requests={'cpu': '0'},
        #limits={'cpu': '1200m'}
    )
    k8sclient.create_service(
        namespace,
        service1,
        port=port_number,
        selector=label1
    )
    k8sclient.send_create_pod_request(
        namespace=namespace,
        name=pod2,
        args=args,
        image=image,
        ports={port_number: port_name},
        labels=pod_label2,
        node_name=node,
        requests={'cpu': '0'},
        #limits={'cpu': '1200m'}
    )
    k8sclient.create_service(
        namespace,
        service2,
        port=port_number,
        selector=label2
    )


def _deploy_global_service():
    k8sclient.create_service(
        namespace,
        global_service,
        port=port_number,
        selector=glabel
    )


def _undeploy(node):
    name_prefix = "-".join(node.split(".")) + uid
    k8sclient.remove_service(namespace, "service-2-" + name_prefix, throw_exp=False)
    k8sclient.remove_service(namespace, "service-1-" + name_prefix, throw_exp=False)
    k8sclient.send_remove_pod_request(namespace, name_prefix + "-pod-1", throw_exp=False)
    k8sclient.send_remove_pod_request(namespace, name_prefix + "-pod-2", throw_exp=False)


def _undeploy_global_service():
    k8sclient.remove_service(namespace, global_service, throw_exp=False)


def cleanup():
    k8sclient.clean_pods(namespace=namespace)
    k8sclient.clean_services(namespace)


def check_running(node):
    name_prefix = "-".join(node.split(".")) + uid
    pod1 = name_prefix + "-pod-1"
    pod2 = name_prefix + "-pod-2"
    ok = True
    ok &= wait_for_pod_state(pod1, 240)
    ok &= wait_for_pod_state(pod2, 120)
    return ok


def check_service(pod, service, retry=3):
    print "-checking service %s on pod %s." % (service, pod)
    while retry > 0:
        try:
            r = k8sclient.pod_exec(namespace, pod, ["/opt/check.sh", service])
            if r.find("Error executing in Docker Container") == -1:
                return True
        except Exception as e:
            pass
        print "retry %s on %s." % (service, pod)
        retry -= 1
    print "Fail to connect to %s on pod %s" % (service, pod)
    return False


def check_ping(pod, ip, retry=3):
    print "-checking ping %s on pod %s." % (ip, pod)
    while retry > 0:
        r = k8sclient.pod_exec(namespace, pod, ["bash", "-c", "ping %s -c 2 -w 5" % ip])
        if r.find("Error executing in Docker Container") == -1:
            return True
        print "retry ping %s on %s" % (ip, pod)
        retry -= 1
    print "Fail to ping %s on pod %s" % (ip, pod)
    return False


def check_local(node):
    name_prefix = "-".join(node.split(".")) + uid
    pod1 = name_prefix + "-pod-1"
    pod2 = name_prefix + "-pod-2"
    pod2_ip = k8sclient.get_pod_info(namespace, pod2).status.pod_ip
    service1 = "service-1-" + name_prefix
    service2 = "service-2-" + name_prefix
    ok = True
    ok &= check_service(pod1, service1)
    ok &= check_service(pod1, service2)
    ok &= check_service(pod1, pod2_ip)
    ok &= check_service(pod1, global_service)
    return ok


def check_cross(node1, node2):
    name_prefix1 = "-".join(node1.split(".")) + uid
    pod1 = name_prefix1 + "-pod-2"
    name_prefix2 = "-".join(node2.split(".")) + uid
    service2 = "service-2-" + name_prefix2
    pod2 = name_prefix2 + "-pod-2"
    pod2_ip = k8sclient.get_pod_info(namespace, pod2).status.pod_ip
    ok = True
    ok &= check_service(pod1, service2)
    ok &= check_service(pod1, pod2_ip)
    ok &= check_ping(pod1, node2)
    ok &= check_ping(pod1, node1)
    return ok


def check_connections():
    cleanup()
    [_deploy_on_node(node) for node in node_names]
    _deploy_global_service()
    running_nodes = [node for node in node_names if check_running(node)]
    # check
    ok = True
    for node1, node2 in zip(running_nodes, running_nodes[1:]+[running_nodes[0]]):
        print "checking", node1
        # if "10.19.140" not in node1:
        #     print "skip", node1
        #     continue
        ok &= check_local(node1)
        ok &= check_cross(node1, node2)
    if not ok:
        print "error found. Remove those pod/service(%s) manually after fixed." % uid
        return
    for node in running_nodes:
        _undeploy(node)
    _undeploy_global_service()
    print "No network issue found within running pods."


if __name__ == "__main__":
    check_connections()
