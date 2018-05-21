from k8sclient.keywords import (
    list_ready_nodes,
    wait_for_pod_state,
    SUCCEEDED,
    tail_pod_logs,
    delete_pod,
    NOT_FOUND,
    remove_pod
)
from k8sclient.Components import (
    PodBuilder,
)
import argparse
import time


parser = argparse.ArgumentParser()
parser.add_argument("--queryserver", type=str, help="ip:port of k8s api server.", default="10.19.138.173:7999")
args = parser.parse_args()
query_server = args.queryserver

image = "ihub.helium.io:30100/library/python-tools:v20171212-2"
args = "dnscheck.py --queryserver=%s" % query_server
namespace = "k8sft"
nodes = list_ready_nodes()


def test_all():
    has_error = False
    for n in nodes:
        pod_name = "dnscheck-" + "-".join(n.split("."))
        remove_pod(namespace, pod_name)
        print "Deploying", pod_name
        PodBuilder(
            pod_name,
            namespace,
        ).set_node(
            n
        ).add_container(
            pod_name + "-container",
            image=image,
            args=args,
            limits={'cpu': '0', 'memory': '0'},
            requests={'cpu': '0', 'memory': '0'},
        ).deploy()
    for n in nodes:
        pod_name = "dnscheck-" + "-".join(n.split("."))
        # wait to complete
        wait_for_pod_state(namespace, pod_name, timeout=600, expect_status=SUCCEEDED)
        logs = tail_pod_logs(namespace, pod_name).strip()
        # delete the pod
        delete_pod(namespace, pod_name)
        wait_for_pod_state(namespace, pod_name, timeout=240, expect_status=NOT_FOUND)
        print "Test finished on ", pod_name
        print logs
        if "PASS" not in logs:
            has_error = True
    if has_error:
        exit(1)


def test(node):
    print node
    pod_name = "dnscheck-" + "-".join(node.split("."))
    PodBuilder(
        pod_name,
        namespace,
    ).set_node(
        node
    ).add_container(
        pod_name + "-container",
        image=image,
        args=args,
        limits={'cpu': '0', 'memory': '0'},
        requests={'cpu': '0', 'memory': '0'},
    ).deploy()
    # wait to complete
    wait_for_pod_state(namespace, pod_name, timeout=3600, expect_status=SUCCEEDED)
    logs = tail_pod_logs(namespace, pod_name).strip()
    # delete the pod
    delete_pod(namespace, pod_name)
    wait_for_pod_state(namespace, pod_name, timeout=240, expect_status=NOT_FOUND)
    print logs


def test_300():
    count = 20
    mynodes = [n for n in nodes if not n.startswith("10.19.138")]
    has_error = False
    for i in range(count):
        for n in mynodes:
            pod_name = "dnscheck-" + "-".join(n.split(".")) + "-" + str(i)
            remove_pod(namespace, pod_name)
            print "Deploying", pod_name
            PodBuilder(
                pod_name,
                namespace,
            ).set_node(
                n
            ).add_container(
                pod_name + "-container",
                image=image,
                args=args,
                limits={'cpu': '0', 'memory': '0'},
                requests={'cpu': '0', 'memory': '0'},
            ).deploy()
        time.sleep(1)
    for i in range(count):
        for n in mynodes:
            pod_name = "dnscheck-" + "-".join(n.split(".")) + "-" + str(i)
            # wait to complete
            wait_for_pod_state(namespace, pod_name, timeout=600, expect_status=SUCCEEDED)
            logs = tail_pod_logs(namespace, pod_name).strip()
            # delete the pod
            delete_pod(namespace, pod_name)
            wait_for_pod_state(namespace, pod_name, timeout=240, expect_status=NOT_FOUND)
            print "Test finished on ", pod_name
            for l in logs.split("\n"):
                if "api4ns" in l:
                    continue
                    print l
            if "PASS" not in logs:
                has_error = True
    if has_error:
        exit(1)
# test("10.19.137.154")
test_all()
# test_300()
