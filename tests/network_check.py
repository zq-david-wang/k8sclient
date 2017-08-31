from k8sclient.keywords import (
    list_ready_nodes,
    get_pod_ip,
    pod_exec,
    is_pod_running,
    switch_cluster,
    register_cluster,
)

import random
import sys
import re
import argparse
import time


parser = argparse.ArgumentParser()
parser.add_argument("--clusterconfig", type=str, help="Which cluster is under testing.")
parser.add_argument("--namespace", type=str, help="The namespace under which pods/services would be checked.")
parser.add_argument("--node", type=str, help="The node where the test would be originated.")
parser.add_argument("--uid", type=str, help="UID for this test session.")
args = parser.parse_args()
register_cluster("target", args.clusterconfig)
switch_cluster("target")
print "Test %s,  using config: %s" % (args.node, args.clusterconfig)
SUCCESS_MARK = "CHECK_PASS"


def _check_pod_running(n):
    node_mark = "-".join(n.split("."))
    pod_1 = ("pod-%s-%d" % (node_mark, 0)) + args.uid
    pod_2 = ("pod-%s-%d" % (node_mark, 1)) + args.uid
    return is_pod_running(args.namespace, pod_1) and is_pod_running(args.namespace, pod_2)

nodes = list_ready_nodes()
target_nodes = [n for n in nodes if _check_pod_running(n)]
if args.node not in target_nodes:
    print "Pods for uid %s is not running on %s" % (args.uid, args.node)
    exit(1)

namespace = args.namespace
uid = args.uid
global_service_name = "health-check" + uid


def _get_node_mark(node):
    return "-".join(node.split("."))


def _check_service(pod, service, timeout):
    s = time.time()
    o = pod_exec(namespace, pod, ["/opt/check.sh", service], timeout=timeout)
    if o.find(SUCCESS_MARK) == -1:
        print "Fail to check %s on %s, error message: [%s]. it took %s" % (service, pod, o, str(time.time() - s))
        return False
    return True


def _get_pod_ip(pod):
    return get_pod_ip(namespace, pod)


def check_service(pod, service):
    # give it a retry
    return _check_service(pod, service, timeout=30) or \
           _check_service(pod, service, timeout=30)


def _check_ping(pod, ip):
    o = pod_exec(namespace, pod, ["bash", "-c", "ping %s -c 2 -w 5" % ip], timeout=60)
    m = re.search("(\d+) packets received", o)
    if not m:
        print o
        return False
    if int(m.group(1)) == 0:
        print o
        return False
    return True


def check_ping(pod, ip):
    return _check_ping(pod, ip) or _check_ping(pod, ip)


def check_pod(pod, targets):
    for target in targets:
        if not check_service(pod, target):
            return "Fail to connect %s on %s." % (target, pod)


def check_host(pod, hosts):
    for host in hosts:
        if not check_ping(pod, host):
            return "Fail to ping %s on %s." % (host, pod)


def check_local(n):
    id_1 = random.randint(0, 1)
    id_2 = (id_1 + 1) % 2
    node_mark = "-".join(n.split("."))
    pod_1 = ("pod-%s-%d" % (node_mark, id_1)) + uid
    # pod_1_ip = _get_pod_ip(pod_1)
    pod_1_service = ("service-%s-%d" % (node_mark, id_1)) + uid
    pod_2 = ("pod-%s-%d" % (node_mark, id_2)) + uid
    pod_2_ip = _get_pod_ip(pod_2)
    pod_2_service = ("service-%s-%d" % (node_mark, id_2)) + uid
    err = []
    r = check_pod(pod_1, [pod_2_ip, pod_2_service, global_service_name, pod_1_service])
    if r:
        print r
        err.append(r)
    return err


def check_cross(node_1, node_2):
    # print "check cross", node_1, node_2
    if node_1 == node_2:
        return []
    id_1 = random.randint(0, 1)
    node_1_mark = _get_node_mark(node_1)
    pod_1 = ("pod-%s-%d" % (node_1_mark, id_1)) + uid

    id_2 = random.randint(0, 1)
    node_2_mark = _get_node_mark(node_2)
    pod_2 = ("pod-%s-%d" % (node_2_mark, id_2)) + uid
    pod_2_service = ("service-%s-%d" % (node_2_mark, id_2)) + uid
    pod_2_ip = _get_pod_ip(pod_2)
    err = []
    r = check_pod(pod_1, [pod_2_ip, pod_2_service])
    if r:
        err.append(r)
        print r
    r = check_host(pod_1, [node_1, node_2])
    if r:
        err.append(r)
        print r
    return err


if __name__ == "__main__":
    start = time.time()
    errors = []
    errors += check_local(args.node)
    for o in target_nodes:
        if o == args.node:
            continue
        errors += check_cross(args.node, o)

    # print "Test Done [%s]" % str(errors)
    if errors:
        sys.stderr.write("\n".join(errors))
    dt = time.time() - start
    print "Finish test on %s, it took %ss." % (args.node, dt)
