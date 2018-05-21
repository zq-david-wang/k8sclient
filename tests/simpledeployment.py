from k8sclient.Components import DeploymentBuilder
from k8sclient.Components import PVCBuilder
from k8sclient.Components import HostPVBuilder
from k8sclient.Components import PodBuilder
from k8sclient.Components import HostPathPVCVolume

namespace = "k8sft"
image = "127.0.0.1:30100/library/memcached:check3"
args = "memcached -m 1028 -u root -v"

image2 = "ihub.helium.io:30100/library/alpine-iperf"
server_args = "iperf -f M -i 1 -m -s"


create_pv = False
if create_pv:
    pvc = PVCBuilder("mytestpvc", namespace)
    pv = HostPVBuilder("1Gi", "mytestpv")
    pv.attach_pvc(pvc)
    pv.deploy("/mnt/mypv/mydata/")
    pvc.deploy()
else:
    hostpath_pvc = HostPathPVCVolume(
        'pvcvolume',
        "/data",
        "mytestpvc"
    )
    DeploymentBuilder(
        "deploymenttest", namespace
    ).set_replicas(3).add_container(
        name="memcached",
        image=image,
        args=args,
        requests=None,
        limits=None,
        volumes=[hostpath_pvc],
    ).deploy()

