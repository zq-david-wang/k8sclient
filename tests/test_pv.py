from k8sclient.Components import PVCBuilder
from k8sclient.Components import HostPVBuilder
from k8sclient.Components import PodBuilder
from k8sclient.Components import HostPathPVCVolume
from k8sclient.keywords import (
    wait_for_pod_state,
    SUCCEEDED,
    tail_pod_logs,
    delete_pod,
    NOT_FOUND,
    RUNNING
)
import time

namespace = "k8sft"

from k8sclient.K8SClient import k8sclient


def get_pvc_status(pvc):
    r = k8sclient.apiV1.read_namespaced_persistent_volume_claim_status(pvc, namespace)
    print r.status.phase


def test():
    pvc = PVCBuilder("mypvc", namespace)
    pv = HostPVBuilder("10Gi", "mypv")
    pv.attach_pvc(pvc)
    # pv.deploy("/mnt/mypv/mydata/")
    pvc.deploy()


def delete_pv():
    pvc = PVCBuilder("mypvc", namespace)
    pv = HostPVBuilder("10Gi", "mypv")
    pvc.un_deploy()
    pv.un_deploy()


image = "ihub.helium.io:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"


def deploy_pod():
    hostpath_pvc = HostPathPVCVolume(
        'pvcvolume',
        '/mnt/pvc',
        "mypvc"
    )

    pod = PodBuilder(
        "hostpathpvtest",
        namespace
    ).add_container(
        "memcached-pv",
        image=image,
        args=args,
        requests={'cpu': '0', 'memory': '0'},
        limits={'cpu': '0', 'memory': '0'},
        volumes=[hostpath_pvc]
    )
    pod.deploy(restart_policy="Always")


FIO_DIR = "/mnt/fio"
fio_image = "ihub.helium.io:30100/library/alpine-fio:v1"
fio_args = "--output-format=json"


def test_pv_fio():
    pvc = PVCBuilder("myfiopvc", namespace)
    pv = HostPVBuilder("100Gi", "myfiopv")
    pv.attach_pvc(pvc)
    pv.deploy("/mnt/mypv/mydata/")
    pvc.deploy()
    time.sleep(5)
    print "PV/PVC created, creat pod now"
    hostpath_pvc = HostPathPVCVolume(
        'pvcvolume',
        FIO_DIR,
        "myfiopvc"
    )
    pod = PodBuilder(
        "hostpathpvfiotest",
        namespace
    ).set_node("10.19.137.159").add_container(
        "hostpathpvfiotest",
        image=fio_image,
        args=fio_args,
        requests={'cpu': '0', 'memory': '0'},
        limits={'cpu': '0', 'memory': '0'},
        volumes=[hostpath_pvc],
        FIO_DIR=FIO_DIR,
        IOENGINE="mmap"
    )
    pod.deploy()


def stress_pv_fio():
    pvc_name = "myfiopvc"
    for i in range(1000):
        print "round", i
        pvc = PVCBuilder(pvc_name, namespace)
        pv = HostPVBuilder("100Gi", "myfiopv")
        pv.attach_pvc(pvc)
        pv.deploy("/mnt/mypv/mydata/")
        pvc.deploy()
        time.sleep(5)
        print "PV/PVC created, creat pod now"
        hostpath_pvc = HostPathPVCVolume(
            'pvcvolume',
            FIO_DIR,
            pvc_name
        )
        pod_name = "hostpathpvfiotest"
        pod = PodBuilder(
            pod_name,
            namespace
        ).set_node("10.19.137.159").add_container(
            pod_name,
            image=fio_image,
            args=fio_args,
            requests={'cpu': '0', 'memory': '0'},
            limits={'cpu': '0', 'memory': '0'},
            volumes=[hostpath_pvc],
            FIO_DIR=FIO_DIR,
            IOENGINE="mmap",
            FILE_SIZE='64g'
        )
        pod.deploy()
        wait_for_pod_state(namespace, pod_name, timeout=600, expect_status=RUNNING)
        time.sleep(120)
        # delete the pod
        delete_pod(namespace, pod_name)
        wait_for_pod_state(namespace, pod_name, timeout=240, expect_status=NOT_FOUND)
        pvc.un_deploy()
        pv.un_deploy()

if __name__ == "__main__":
    # deploy_pod()
    # test()
    # delete_pv()
    # test_pv_fio()
    stress_pv_fio()
