from k8sclient.keywords import (
    list_ready_nodes,
    wait_for_pod_state,
    SUCCEEDED,
    tail_pod_logs,
    delete_pod,
    NOT_FOUND
)
from k8sclient.Components import (
    PodBuilder,
    RBDVolume,
    CephFSVolume,
    EmptyDirVolume
)

image = "127.0.0.1:30100/library/alpine-fio:v1"
args = "--output-format=json"
namespace = "monkey"
nodes = list_ready_nodes()
FIO_DIR = "/mnt/fio"
ceph_monitors = "10.19.137.144:6789,10.19.137.145:6789,10.19.137.146:6789"
ceph_pool = "monkey"
ceph_fstype = "xfs"
ceph_secret = "ceph-secret"  # need create beforehand
# must match the regex [a-z0-9]([-a-z0-9]*[a-z0-9])?
empty_dir = EmptyDirVolume("empty-dir-fio", FIO_DIR)
ceph_fs = CephFSVolume(
            "cephfs",
            FIO_DIR,
            monitors=ceph_monitors,
            secret_name=ceph_secret,
            fs_path="/",
            sub_path="monkey-fio"
        )
rbd = RBDVolume(
        "rbd",
        FIO_DIR,
        fs_type=ceph_fstype,
        image="default",
        pool=ceph_pool,
        monitors=ceph_monitors,
        secret_name=ceph_secret,
        sub_path="fio",
    )

volumes = {
    # "empty_dir": empty_dir,
    # "rbd": rbd,
    "ceph_fs": ceph_fs
}
# io_engines = ["libaio", "mmap", "posixaio", "sync"]
io_engines = ["mmap"]


def test(node):
    print node
    pod_name = "fio-" + "-".join(node.split("."))
    reports = []
    for n, v in volumes.items():
        print n
        for e in io_engines:
            print e
            PodBuilder(
                pod_name,
                namespace,
            ).set_node(
                node
            ).add_container(
                pod_name + "-container",
                image=image,
                args=args,
                limits={'cpu': '1', 'memory': '2Gi'},
                requests={'cpu': '0', 'memory': '0'},
                volumes=[v],
                FIO_DIR=FIO_DIR,
                IOENGINE=e,
                FILE_SIZE="64g"
            ).deploy()
            # wait to complete
            wait_for_pod_state(namespace, pod_name, timeout=3600, expect_status=SUCCEEDED)
            logs = tail_pod_logs(namespace, pod_name).strip()
            # delete the pod
            delete_pod(namespace, pod_name)
            wait_for_pod_state(namespace, pod_name, timeout=240, expect_status=NOT_FOUND)
            # report = json.loads(logs)
            report = eval(logs)
            for job in report["jobs"]:
                print "READ:", job['read']['bw'], "KB/s"
                print "WRITE:", job['write']['bw'], "KB/s"
            reports.append({
                "vtype": n,
                "io_engine": e,
                "read(KB/s)": report["jobs"][0]['read']['bw'],
                "write(KB/S)": report["jobs"][0]['write']['bw']
            })
    return reports

r = test("10.19.137.148")
