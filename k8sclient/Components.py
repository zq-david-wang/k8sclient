from kubernetes.client import V1ObjectMeta
from kubernetes.client import V1DeleteOptions
from kubernetes.client import V1Namespace
from kubernetes.client import V1Pod
from kubernetes.client import V1Container
from kubernetes.client import V1ContainerPort
from kubernetes.client import V1PodSpec
from kubernetes.client import V1ResourceRequirements
from kubernetes.client import V1Probe
from kubernetes.client import V1ExecAction
from kubernetes.client import V1Service
from kubernetes.client import V1ServiceSpec
from kubernetes.client import V1ServicePort
from kubernetes.client import V1VolumeMount
from kubernetes.client import V1Volume
from kubernetes.client import V1HostPathVolumeSource
from kubernetes.client import V1RBDVolumeSource
from kubernetes.client import V1LocalObjectReference
from kubernetes.client import V1LimitRange
from kubernetes.client import V1LimitRangeSpec
from kubernetes.client import V1LimitRangeItem
from kubernetes.client import V1CephFSVolumeSource
from kubernetes.client import V1EmptyDirVolumeSource
from kubernetes.client import V1EnvVar
from kubernetes.client import V1beta1ReplicaSet
from kubernetes.client import V1PodTemplateSpec
from kubernetes.client import V1LabelSelector
from kubernetes.client import V1beta1ReplicaSetSpec
from kubernetes.client.rest import ApiException
import re
from .K8SClient import k8sclient


class ComponentBuilder(object):
    def __init__(self, name, namespace, labels=None):
        self.meta = V1ObjectMeta(name=name, namespace=namespace, labels=labels)
        self.containers = []
        self.volumes = []
        self.target_labels = {}
        self.annotations = {}

    def add_container(self, name, image, args=None, requests={}, limits={}, probe="", volumes=[], ports=[], **envs):
        ports = [p.pod_port for p in ports]
        probe_object = None
        if probe:
            probe_action = V1ExecAction(re.split(r" +", probe))
            probe_object = V1Probe(probe_action, initial_delay_seconds=5, period_seconds=3)
        if args is not None:
            args = re.split(r" +", args)
        self.volumes.extend([v.volume for v in volumes if v.volume not in self.volumes])
        volume_mounts = [v.mount for v in volumes]
        container_env = [V1EnvVar(name=k, value=str(v)) for k, v in envs.items()]
        container = V1Container(
            args=args,
            image=image,
            name=name,
            ports=ports,
            resources=V1ResourceRequirements(requests=requests, limits=limits),
            liveness_probe=probe_object,
            volume_mounts=volume_mounts,
            env=container_env
        )
        self.containers.append(container)
        return self

    def attache_service(self, service):
        self.target_labels.update(service.selector)
        return self


class ServicePort(object):
    def __init__(self, name, container_port, port, protocol="TCP"):
        self.service_port = V1ServicePort(name=name, port=port, protocol=protocol)
        self.pod_port = V1ContainerPort(name=name, container_port=container_port)


class ServiceBuilder(object):
    def __init__(self, name, namespace, service_type="ClusterIP"):
        self.meta = V1ObjectMeta(name=name, namespace=namespace)
        self.ports = []
        self.service_type = service_type
        self.selector = {name + "-service": name}

    def add_port(self, port):
        if port not in self.ports:
            self.ports.append(port.service_port)
        return self

    def deploy(self, force=False):
        spec = V1ServiceSpec(
            selector=self.selector,
            type=self.service_type,
            ports=self.ports
        )
        body = V1Service(metadata=self.meta, spec=spec)
        try:
            k8sclient.apiV1.create_namespaced_service(self.meta.namespace, body)
        except ApiException as e:
            if e.status != 409 or not force:
                raise e
            k8sclient.remove_service(self.meta.namespace, self.meta.name)
            k8sclient.apiV1.create_namespaced_service(self.meta.namespace, body)

    def un_deploy(self):
        return k8sclient.apiV1.delete_namespaced_service(
            self.meta.name,
            self.meta.namespace
        )


class Volume(object):
    def __init__(self):
        self.mount = None
        self.volume = None


class HostPathVolume(Volume):
    def __init__(self, name, mount, path, read_only=True):
        self.mount = V1VolumeMount(name=name, mount_path=mount, read_only=read_only)
        self.volume = V1Volume(name=name, host_path=V1HostPathVolumeSource(path=path))


class EmptyDirVolume(Volume):
    def __init__(self, name, mount, read_only=False):
        self.mount = V1VolumeMount(name=name, mount_path=mount, read_only=read_only)
        self.volume = V1Volume(name=name, empty_dir=V1EmptyDirVolumeSource())


class RBDVolume(Volume):
    def __init__(self, name, mount, fs_type, image, monitors, pool, secret_name, sub_path, user="admin", read_only=False):
        self.mount = V1VolumeMount(name=name, mount_path=mount, read_only=read_only, sub_path=sub_path)
        self.volume = V1Volume(name=name, rbd=V1RBDVolumeSource(
            fs_type=fs_type,
            image=image,
            monitors=monitors.split(","),
            pool=pool,
            secret_ref=V1LocalObjectReference(secret_name),
            read_only=read_only,
            user=user
        ))


class CephFSVolume(Volume):
    def __init__(self, name, mount, monitors, secret_name, fs_path, sub_path, user="admin", read_only=False):
        self.mount = V1VolumeMount(name=name, mount_path=mount, read_only=read_only, sub_path=sub_path)
        self.volume = V1Volume(name=name, cephfs=V1CephFSVolumeSource(
            monitors=monitors.split(","),
            path=fs_path,
            secret_ref=V1LocalObjectReference(secret_name),
            read_only=read_only,
            user=user
        ))


class PodBuilder(ComponentBuilder):
    def __init__(self, *args):
        super(PodBuilder, self).__init__(*args)
        self.node_name = None

    def set_node(self, node_name):
        self.node_name = node_name
        return self

    def deploy(self, restart_policy="Never"):
        spec = V1PodSpec(
            containers=self.containers,
            node_name=self.node_name,
            volumes=self.volumes,
            restart_policy=restart_policy
        )
        self.meta.labels = self.target_labels
        pod = V1Pod(spec=spec, metadata=self.meta)
        return k8sclient.apiV1.create_namespaced_pod(self.meta.namespace, body=pod)

    def un_deploy(self):
        return k8sclient.apiV1.delete_namespaced_pod(
            self.meta.name,
            self.meta.namespace,
            V1DeleteOptions()
        )


class ReplicaSetBuilder(ComponentBuilder):
    def __init__(self, *args):
        super(ReplicaSetBuilder, self).__init__(*args)
        self.replicas = 1
        rs_marks = {"replicaset": self.meta.name}
        self.selector = V1LabelSelector(
            match_labels=rs_marks
        )
        self.target_labels.update(rs_marks)

    def set_hostname(self, hostname):
        self.annotations['pod.beta.kubernetes.io/hostname'] = hostname
        self.replicas = 1
        return self

    def replicas(self, count):
        self.replicas = count
        #
        if 'pod.beta.kubernetes.io/hostname' in self.annotations:
            del self.annotations['pod.beta.kubernetes.io/hostname']
        return self

    def _build_rs(self):
        pod_spec = V1PodSpec(
            containers=self.containers,
            volumes=self.volumes
        )
        template = V1PodTemplateSpec(
            metadata=V1ObjectMeta(
                labels=self.target_labels,
                annotations=self.annotations or None
            ),
            spec=pod_spec
        )
        rs_spec = V1beta1ReplicaSetSpec(
            replicas=self.replicas,
            selector=self.selector,
            template=template
        )
        rs = V1beta1ReplicaSet(
            metadata=self.meta,
            spec=rs_spec
        )
        return rs

    def deploy(self):
        return k8sclient.apiV1beta1.create_namespaced_replica_set(
            self.meta.namespace,
            body=self._build_rs()
        )

    def un_deploy(self):
        pods = k8sclient.collect_pods_info(self.meta.namespace)
        for pod in pods:
            if pod.name.find(self.meta.name) != -1:
                k8sclient.send_remove_pod_request(self.meta.namespace, pod.name)

        return k8sclient.apiV1beta1.delete_namespaced_replica_set(
            name=self.meta.name,
            namespace=self.meta.namespace,
            body=V1DeleteOptions()
        )

