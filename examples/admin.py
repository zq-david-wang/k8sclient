from k8sclient.keywords import apply_resource_limit, list_namespaces


def apply_limit():
    apply_resource_limit("k8sft")


def apply_limit_shanghai():
    namespaces = list_namespaces()
    specials = ['health-check', 'kube-system', "haproxy", "4tools", "terminal-perf-0", "terminal-perf-1", "terminal-perf-2", "terminal-perf-3", "terminal-perf-4"]
    for n in namespaces:
        if n in specials:
            print "%s is special, just ignore it." % n
            apply_resource_limit(n, min_cpu=None, min_memory=None, replace=False)
            continue
        apply_resource_limit(n, replace=False)

if __name__ == "__main__":
    apply_limit_shanghai()

