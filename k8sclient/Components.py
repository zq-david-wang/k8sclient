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
from kubernetes.client import V1PodSecurityContext
from kubernetes.client import V1CephFSVolumeSource
from kubernetes.client import V1EmptyDirVolumeSource
from kubernetes.client import V1EnvVar
from kubernetes.client import V1beta1ReplicaSet
from kubernetes.client import V1PodTemplateSpec
from kubernetes.client import V1LabelSelector
from kubernetes.client import V1beta1ReplicaSetSpec
from kubernetes.client import V1PersistentVolume
from kubernetes.client import V1PersistentVolumeSpec
from kubernetes.client import V1PersistentVolumeClaim
from kubernetes.client import V1PersistentVolumeClaimSpec
from kubernetes.client import V1PersistentVolumeClaimVolumeSource
from kubernetes.client import AppsV1beta1Deployment
from kubernetes.client import AppsV1beta1DeploymentSpec
from kubernetes.client import AppsV1beta1DeploymentStrategy
from kubernetes.client import AppsV1beta1RollingUpdateDeployment
from kubernetes.client.rest import ApiException
import re
from .K8SClient import k8sclient


class ComponentBuilder(object):
    def __init__(self, name, namespace=None, labels=None):
        self.meta = V1ObjectMeta(name=name, namespace=namespace, labels=labels)
        self.containers = []
        self.volumes = []
        self.target_labels = {}
        self.annotations = {}
        self.meta.annotations = self.annotations

    def add_container(self, name, image, image_pull_policy="IfNotPresent", args=None, requests={}, limits={}, probe="", volumes=[], ports=[], **envs):
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
            image_pull_policy=image_pull_policy,
            name=name,
            ports=ports,
            resources=V1ResourceRequirements(requests=requests, limits=limits),
            liveness_probe=probe_object,
            volume_mounts=volume_mounts,
            env=container_env,
        )
        self.containers.append(container)
        return self

    def attache_service(self, service):
        self.target_labels.update(service.selector)
        return self

    def add_annotation(self, key, value):
        self.annotations[key] = value
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


class HostPathPVCVolume(Volume):
    def __init__(self, name, mount, claim_name, read_only=False):
        self.mount = V1VolumeMount(name=name, mount_path=mount, read_only=read_only)
        self.volume = V1Volume(
            name=name,
            persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=claim_name)
        )


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
    def __init__(self, *args, **kwargs):
        super(PodBuilder, self).__init__(*args, **kwargs)
        self.node_name = None

    def set_node(self, node_name):
        self.node_name = node_name
        return self

    def deploy(self, restart_policy="Never", dns_policy="ClusterFirst"):
        spec = V1PodSpec(
            containers=self.containers,
            node_name=self.node_name,
            volumes=self.volumes,
            restart_policy=restart_policy,
            dns_policy=dns_policy,
        )
        if self.meta.labels:
            self.meta.labels.update(self.target_labels)
        else:
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
        self.node_name = None
        self.host_name = None
        self.security_context = None

    def set_node(self, node_name):
        self.node_name = node_name
        return self

    def set_hostname(self, hostname):
        # self.annotations['pod.beta.kubernetes.io/hostname'] = hostname
        self.host_name = hostname
        self.replicas = 1
        return self

    def set_replicas(self, count):
        self.replicas = count
        #
        if 'pod.beta.kubernetes.io/hostname' in self.annotations:
            del self.annotations['pod.beta.kubernetes.io/hostname']
        return self

    def set_poduser(self, uid, vgid):
        self.security_context = V1PodSecurityContext(run_as_user=uid, fs_group=vgid)
        return self

    def _build_rs(self):
        pod_spec = V1PodSpec(
            containers=self.containers,
            volumes=self.volumes,
            node_name=self.node_name,
            hostname=self.host_name,
            security_context=self.security_context,
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


class PVCBuilder(ComponentBuilder):

    def __init__(self, *args, **kwargs):
        super(PVCBuilder, self).__init__(*args, **kwargs)
        self.selector = {"pvc": "mypv-%s-%s" % (self.meta.name, self.meta.namespace)}
        self.meta.annotations = {
            "pv.kubernetes.io/bound-by-controller": "yes",
        }
        self.capacity = None
        self.pvvolume = None

    def set_capacity(self, capacity):
        self.capacity = capacity

    def set_volume(self, volume):
        self.pvvolume = volume

    def deploy(self, access_mode="ReadWriteMany"):
        assert self.capacity
        pvc_spec = V1PersistentVolumeClaimSpec(
            access_modes=[access_mode],
            resources=V1ResourceRequirements(requests={"storage": self.capacity}),
            selector=V1LabelSelector(match_labels=self.selector),
            volume_name=self.pvvolume
        )
        pvc = V1PersistentVolumeClaim(metadata=self.meta, spec=pvc_spec)
        k8sclient.apiV1.create_namespaced_persistent_volume_claim(
            self.meta.namespace,
            body=pvc
        )

    def un_deploy(self):
        return k8sclient.apiV1.delete_namespaced_persistent_volume_claim(
            self.meta.name,
            self.meta.namespace,
            V1DeleteOptions()
        )


class HostPVBuilder(ComponentBuilder):

    def __init__(self, capacity, *args, **kwargs):
        super(HostPVBuilder, self).__init__(*args, **kwargs)
        self.meta.annotations = {
            'io.enndata.user/alpha-pvhostpathmountpolicy': 'keep',
            'io.enndata.user/alpha-pvhostpathquotaforonepod': 'true',
            'pv.kubernetes.io/bound-by-controller': 'yes'
        }
        self.capacity = capacity

    def deploy(self, path, access_mode="ReadWriteMany"):
        if self.meta.labels:
            self.meta.labels.update(self.target_labels)
        else:
            self.meta.labels = self.target_labels
        pv_spec = V1PersistentVolumeSpec(
            access_modes=[access_mode],
            capacity={"storage": self.capacity},
            host_path=V1HostPathVolumeSource(path=path),
            persistent_volume_reclaim_policy='Recycle'
            # claim_ref=V1ObjectReference(),
        )
        pv = V1PersistentVolume(metadata=self.meta, spec=pv_spec)
        k8sclient.apiV1.create_persistent_volume(
            body=pv
        )

    def attach_pvc(self, pvc):
        self.target_labels.update(pvc.selector)
        pvc.set_capacity(self.capacity)
        pvc.set_volume(self.meta.name)

    def un_deploy(self):
        return k8sclient.apiV1.delete_persistent_volume(
            self.meta.name,
            V1DeleteOptions()
        )


class RBDPVBuilder(ComponentBuilder):
    def __init__(self, capacity, image, secret_name, monitors, pool, *args, **kwargs):
        super(RBDPVBuilder, self).__init__(*args, **kwargs)
        self.meta.annotations = {
        }
        self.capacity = capacity
        self.image = image
        self.secret_name = secret_name
        self.monitors = monitors.split(",")
        self.pool = pool

    def deploy(self, access_mode="ReadWriteMany"):
        if self.meta.labels:
            self.meta.labels.update(self.target_labels)
        else:
            self.meta.labels = self.target_labels
        pv_spec = V1PersistentVolumeSpec(
            access_modes=[access_mode],
            capacity={"storage": self.capacity},
            rbd=V1RBDVolumeSource(
                fs_type='xfs',
                image=self.image,
                secret_ref=V1LocalObjectReference(self.secret_name),
                monitors=self.monitors,
                pool=self.pool,
                read_only=False,
            ),
            persistent_volume_reclaim_policy='Recycle'
            # claim_ref=V1ObjectReference(),
        )
        pv = V1PersistentVolume(metadata=self.meta, spec=pv_spec)
        k8sclient.apiV1.create_persistent_volume(
            body=pv
        )

    def attach_pvc(self, pvc):
        self.target_labels.update(pvc.selector)
        pvc.set_capacity(self.capacity)
        pvc.set_volume(self.meta.name)

    def un_deploy(self):
        return k8sclient.apiV1.delete_persistent_volume(
            self.meta.name,
            V1DeleteOptions()
        )


class DeploymentBuilder(ComponentBuilder):
    def __init__(self, *args):
        super(DeploymentBuilder, self).__init__(*args)
        self.replicas = 1
        rs_marks = {"replicaset": self.meta.name}
        self.selector = V1LabelSelector(
            match_labels=rs_marks
        )
        self.target_labels.update(rs_marks)
        self.node_name = None
        self.host_name = None

    def set_node(self, node_name):
        self.node_name = node_name
        return self

    def set_hostname(self, hostname):
        self.annotations['pod.beta.kubernetes.io/hostname'] = hostname
        # self.host_name = hostname
        self.replicas = 1
        return self

    def set_replicas(self, count):
        self.replicas = count
        #
        if 'pod.beta.kubernetes.io/hostname' in self.annotations:
            del self.annotations['pod.beta.kubernetes.io/hostname']
        return self

    def _build_deployment(self):
        pod_spec = V1PodSpec(
            containers=self.containers,
            volumes=self.volumes,
            node_name=self.node_name,
            hostname=self.host_name
        )
        template = V1PodTemplateSpec(
            metadata=V1ObjectMeta(
                labels=self.target_labels,
                annotations=self.annotations or None
            ),
            spec=pod_spec
        )
        strategy = AppsV1beta1DeploymentStrategy(
            type="RollingUpdate",
            rolling_update=AppsV1beta1RollingUpdateDeployment(
                max_surge=0
            )

        )
        deployment_spec = AppsV1beta1DeploymentSpec(
            replicas=self.replicas,
            selector=self.selector,
            template=template,
            strategy=strategy
        )
        deployment = AppsV1beta1Deployment(
            metadata=self.meta,
            spec=deployment_spec
        )
        return deployment

    def deploy(self):
        return k8sclient.apiV1beta1.create_namespaced_deployment(
            self.meta.namespace,
            body=self._build_deployment()
        )

    def un_deploy(self):
        return k8sclient.apiV1beta1.delete_namespaced_deployment(
            name=self.meta.name,
            namespace=self.meta.namespace,
            body=V1DeleteOptions()
        )
