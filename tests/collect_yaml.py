import os
import errno
from kubernetes import client, config
from os.path import expanduser
import yaml
import urllib3
import re
urllib3.disable_warnings()


ignore_lists = [
    "creation_timestamp",
    "resource_version",
    "self_link",
    "uid",
    "claim_ref",
    "status",
    "generation",
]

ignored_annotations = [
    re.compile(r".*enndata.console.*"),
    re.compile(r".*revision.*"),
    re.compile(r".*enndata.kubelet.*"),
]


def clean_annotation(d):
    for k, v in d.items():
        for p in ignored_annotations:
            if p.match(k):
                del d[k]


def clean_dict(d):
    if type(d) == list or type(d) == tuple:
        for entry in d:
            clean_dict(entry)
        return
    if type(d) != dict:
        return
    for k, v in d.items():
        if (v is None) or (k in ignore_lists):
            del d[k]
        else:
            if k == "annotations":
                clean_annotation(d[k])
            clean_dict(d[k])


def yaml_out(d):
    clean_dict(d)
    return yaml.safe_dump(d, allow_unicode=True, default_flow_style=False)


def _make_dir(directory):
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

local_client = config.new_client_from_config(expanduser("~/.kube/config-collect"))
k8s_apis = {
    "CoreV1Api": client.CoreV1Api(local_client),
    "BatchV2alpha1Api": client.BatchV2alpha1Api(local_client),
    "ExtensionsV1beta1Api": client.ExtensionsV1beta1Api(local_client),
    "AppsV1beta1Api": client.AppsV1beta1Api(local_client),
    "StorageV1Api": client.StorageV1Api(local_client),
    "RbacAuthorizationV1alpha1Api": client.RbacAuthorizationV1alpha1Api(local_client),
}
api_map = {
    "cron_job": 'BatchV2alpha1Api',
    "daemon_set": 'ExtensionsV1beta1Api',
    "deployment": 'ExtensionsV1beta1Api',
    "replica_set": 'ExtensionsV1beta1Api',
    "stateful_set": 'AppsV1beta1Api',
    "replication_controller": 'CoreV1Api',
    "storage_class": "StorageV1Api",
    "role": "RbacAuthorizationV1alpha1Api",
    "role_binding": "RbacAuthorizationV1alpha1Api",
    "network_policy": 'ExtensionsV1beta1Api',
}


def get_api(component_type):
    api = "CoreV1Api"
    if component_type in api_map:
        api = api_map[component_type]
    return k8s_apis[api]

namespaces = [i.metadata.name for i in get_api('namespace').list_namespace().items]


def collect_namespaced(name):
    directory = "./collects/%s/" % name
    _make_dir(directory)
    api = get_api(name)
    func = getattr(api, "list_namespaced_%s" % name)
    for namespace in namespaces:
        items = func(namespace).items
        if len(items) == 0:
            continue
        _make_dir(directory + namespace)
        for item in items:
            if item.metadata.owner_references:
                continue
            r = yaml_out(item.to_dict())
            with open(os.path.join(directory, namespace, item.metadata.name+".yaml"), "w") as f:
                f.write(r)


def collect_global(name):
    directory = "./collects/%s/" % name
    _make_dir(directory)
    api = get_api(name)
    func = getattr(api, "list_%s" % name)
    for item in func().items:
        r = yaml_out(item.to_dict())
        with open(os.path.join(directory, item.metadata.name+".yaml"), "w") as f:
            f.write(r)


collect_global("node")
collect_global("namespace")
collect_global("persistent_volume")
collect_global("storage_class")

collect_namespaced("cron_job")
collect_namespaced("daemon_set")
collect_namespaced("deployment")
collect_namespaced("replica_set")
collect_namespaced("replication_controller")
collect_namespaced("stateful_set")
collect_namespaced("service")
collect_namespaced("config_map")
collect_namespaced("secret")
collect_namespaced("persistent_volume_claim")
collect_namespaced("limit_range")
collect_namespaced("resource_quota")
collect_namespaced("role")
collect_namespaced("role_binding")
collect_namespaced("service_account")
collect_namespaced("network_policy")



