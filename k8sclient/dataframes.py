from .keywords import (
    list_namespaced_pods,
    list_namespaces,
    list_nodes,
    list_namespaced_services,
    list_all_services,
    list_namespaced_endpoints,
    list_all_endpoints,
)
import pandas as pd
import re

resource_pattern = re.compile(r"([\d.]+)([mKGMi]{0,2})")
cpu_parser = {
    'm': lambda x: float(x)/1000,
    'Ki': lambda x: float(x)/1000000,
    "": lambda x: float(x)
}
memory_parser = {
    'Gi': lambda x: float(x),
    'G': lambda x: float(x),
    "Mi": lambda x: float(x)/1024,
    "M": lambda x: float(x)/1024,
    "m": lambda x: float(x)/(1024*1024*1024),
    "Ki": lambda x: float(x)/(1024*1024),
    "K": lambda x: float(x)/(1024*1024),
    "": lambda x: float(x)/(1024*1024*1024)
}


def parse_resource(resource, parser):
    m = resource_pattern.match(resource)
    if not m:
        return 0
    r = parser[m.group(2)](m.group(1))
    return r


def _parse_pod(pod):
    """return dict for pod, containers, volumes, mounts, labels"""
    pod_id = pod.metadata.uid
    labels = []
    if hasattr(pod.metadata, "labels") and pod.metadata.labels:
        for k, v in pod.metadata.labels.items():
            labels.append({"name": k, "value": v, "pod_id": pod_id})
    owners = []
    if hasattr(pod.metadata, "owner_references") and pod.metadata.owner_references:
        for o in pod.metadata.owner_references:
            owners.append({
                "pod_id": pod_id, "api_version": o.api_version,
                "block_owner_deletion": o.block_owner_deletion,
                "controller": o.controller,
                "kind": o.kind,
                "name": o.name,
                "uid": o.uid
            })
    containers = []
    envs = []
    volumes = []
    volume_mounts = []
    if hasattr(pod.spec, "containers") and pod.spec.containers:
        for c in pod.spec.containers:
            containers.append({
                "args": " ".join(c.args) if c.args else "",
                "command": " ".join(c.command) if c.command else "",
                "image": c.image,
                "image_pull_policy": c.image_pull_policy,
                "name": c.name,
                "rcpu": parse_resource(c.resources.requests['cpu'], cpu_parser) if c.resources.requests and 'cpu' in c.resources.requests else 0,
                "rmemory": parse_resource(c.resources.requests['memory'], memory_parser) if c.resources.requests and 'memory' in c.resources.requests else 0,
                "lcpu": parse_resource(c.resources.limits['cpu'], cpu_parser) if c.resources.limits and 'cpu' in c.resources.limits else 0,
                "lmemory": parse_resource(c.resources.limits['memory'], memory_parser) if c.resources.limits and 'memory' in c.resources.limits else 0,
                "state": "unknown",
                "restart_count": 0,
                "pod_id": pod_id

            })
            if c.env:
                for e in c.env:
                    envs.append({
                        "pod_id": pod_id,
                        "container": c.name,
                        "name": e.name,
                        "value": e.value
                    })
            if c.volume_mounts:
                for m in c.volume_mounts:
                    volume_mounts.append({
                        "pod_id": pod_id,
                        "container": c.name,
                        "mount_path": m.mount_path,
                        "name": m.name,
                        "ro": m.read_only,
                        "sub_path": m.sub_path,
                    })
    if hasattr(pod.status, "container_statuses") and pod.status.container_statuses:
        for cs in pod.status.container_statuses:
            _state = "unknown"
            if cs.state.running:
                _state = "running"
            elif cs.state.terminated:
                _state = "terminated"
            elif cs.state.waiting:
                _state = "waiting"

            for c in containers:
                if c['name'] == cs.name:
                    c['ready'] = cs.ready
                    c['restart_count'] = cs.restart_count
                    c['state'] = _state
                    break

    if hasattr(pod.spec, "volumes") and pod.spec.volumes:
        for v in pod.spec.volumes:
            vs = v.to_dict()
            _info = {"name": v.name, "pod_id": pod_id}
            for _k, _v in vs.items():
                if _v is None or _k == "name":
                    continue
                _info.update(_v)
                _info['vtype'] = _k
                break
            volumes.append(_info)
    pod_info = pd.DataFrame([{
        "namespace": pod.metadata.namespace,
        "pod": pod.metadata.name,
        "cluster_name": pod.metadata.cluster_name,
        "ctime": pod.metadata.creation_timestamp,
        "uid": pod.metadata.uid,
        "dns_policy": pod.spec.dns_policy,
        "host_ipc": pod.spec.host_ipc,
        "host_network": pod.spec.host_network,
        "host_pid": pod.spec.host_pid,
        "node_name": pod.spec.node_name,
        # "node_selector": pod.spec.node_selector,
        "restart_policy": pod.spec.restart_policy,
        "host_ip": pod.status.host_ip,
        "pod_ip": pod.status.pod_ip,
        "phase": pod.status.phase,
        "stime": pod.status.start_time,
    }])
    labeldf = pd.DataFrame(labels)
    ownerdf = pd.DataFrame(owners)
    containerdf = pd.DataFrame(containers)
    envdf = pd.DataFrame(envs)
    mountdf = pd.DataFrame(volume_mounts)
    volumedf = pd.DataFrame(volumes)
    return {
        "pod": pod_info,
        "label": labeldf,
        "owner": ownerdf,
        "container": containerdf,
        "env": envdf,
        "mount": mountdf,
        "volume": volumedf
    }


def _parse_pods(pods):
    infos = [_parse_pod(p) for p in pods]
    data_frames = ["pod", "label", "owner", "container", "env", "mount", "volume"]
    r = {}
    for item in data_frames:
        _items = [i[item] for i in infos if not i[item].empty]
        if _items:
            r[item] = pd.concat(_items, ignore_index=True)
        else:
            print item, "empty"
    return r


def collect_namespaced_pods(namespace):
    pods = list_namespaced_pods(namespace)
    return _parse_pods(pods)


def collect_all_pods():
    namespaces = list_namespaces()
    pods = sum([list_namespaced_pods(n) for n in namespaces], [])
    return _parse_pods(pods)


def _collect_node(node):
    schedulable = not node.spec.unschedulable
    info = {
        "name": node.metadata.name,
        "uid": node.metadata.uid,
        "schedulable": schedulable,
        "nvidiagpu": int(node.status.allocatable['alpha.kubernetes.io/nvidia-gpu']) if "alpha.kubernetes.io/nvidia-gpu" in node.status.allocatable else 0,
        "a-cpu": parse_resource(node.status.allocatable['cpu'], cpu_parser),
        "a-memory": parse_resource(node.status.allocatable['memory'], memory_parser),
        "a-pods": int(node.status.allocatable['pods']),
        "c-cpu": parse_resource(node.status.capacity['cpu'], cpu_parser),
        "c-memory": parse_resource(node.status.capacity['memory'], memory_parser),
    }
    for c in node.status.conditions:
        info[c.type] = c.status
    info.update(node.metadata.labels)
    return info


def collect_nodes():
    return pd.DataFrame([_collect_node(n) for n in list_nodes()])


def _parse_port(port, service_id):
    return {
        "name": port.name,
        "node_port": str(port.node_port),
        "port": str(port.port),
        "protocol": port.protocol,
        "target_port": str(port.target_port),
        "service_id": service_id,
    }


def _parse_external_ips(ip, service_id):
    return {
        "external_ip": ip,
        "service_id": service_id
    }


def _collect_services(services):
    sinfo = []
    ports = []
    eips = []
    for s in services:
        info = {
            'namespace': s.metadata.namespace,
            'name': s.metadata.name,
            'type': s.spec.type,
            "creation": s.metadata.creation_timestamp,
            # "external_ip": str(s.spec.external_i_ps),
            "external_name": s.spec.external_name,
            "uid": s.metadata.uid,
        }
        sinfo.append(info)
        ports += [_parse_port(p, s.metadata.uid) for p in s.spec.ports]
        if s.spec.external_i_ps:
            eips += [_parse_external_ips(p, s.metadata.uid) for p in s.spec.external_i_ps]
    return pd.DataFrame(sinfo), pd.DataFrame(ports), pd.DataFrame(eips)


def collect_namespaced_services(namespace):
    # return pd.DataFrame([_collect_service(s) for s in list_namespaced_services(namespace=namespace)])
    return _collect_services(list_namespaced_services(namespace=namespace))


def collect_services():
    # namespaces = list_namespaces()
    # return pd.concat([collect_namespaced_services(n) for n in namespaces], ignore_index=True)
    return _collect_services(list_all_services())


def _collect_endpoints(endpoints):
    infos = []
    ip_port_maps = []
    for e in endpoints:
        info = {
            'namespace': e.metadata.namespace,
            'creation_timestamp': e.metadata.creation_timestamp,
            'name': e.metadata.name,
            'uid': e.metadata.uid
        }
        infos.append(info)
        if hasattr(e, "subsets") and e.subsets:
            for s in e.subsets:
                if not s.addresses :
                    continue
                addresses = []
                ports = []
                for addr in s.addresses:
                    if not addr.target_ref:
                        continue
                    addresses.append({
                        "hostname": addr.hostname,
                        "ip": addr.ip,
                        "endpoint_id": e.metadata.uid,
                        "node_name": addr.node_name,
                        "target_kind": addr.target_ref.kind,
                        "target_name": addr.target_ref.name,
                        "target_namespace": addr.target_ref.namespace,
                        "target_uid": addr.target_ref.uid,
                    })
                if not addresses:
                    continue
                for port in s.ports:
                    ports.append({
                        "name": port.name,
                        "port": port.port,
                        "protocol": port.protocol,
                        "endpoint_id": e.metadata.uid,
                    })
                ip_port_map = pd.merge(pd.DataFrame(addresses), pd.DataFrame(ports), on="endpoint_id", how="outer")
                ip_port_maps.append(ip_port_map)

    return pd.DataFrame(infos), pd.concat(ip_port_maps, ignore_index=True)


def collect_namespaced_endpoints(namespace):
    return _collect_endpoints(list_namespaced_endpoints(namespace=namespace))


def collect_all_endpoints():
    return _collect_endpoints(list_all_endpoints())
