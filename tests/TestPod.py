import unittest
import time
from nose.plugins.attrib import attr
from k8sclient.K8SClient import k8sclient
from kubernetes.client.rest import ApiException


def wait_for_pod_state(namespace, name, timeout, expect_status):
    while timeout > 0:
        r = k8sclient.get_pod_info(namespace, name)
        if r.status.phase == expect_status:
            break
        time.sleep(1)
        timeout -= 1
        if (timeout % 1800) == 0:
            print ">>>>>>>", timeout
            k8sclient.print_pod_stats(namespace)
    assert timeout > 0, "Fail to wait expect status %s, current %s" % (expect_status, r.status.phase)
    return timeout


def wait_for_pod_restart(namespace, name, timeout):
    while timeout > 0:
        r = k8sclient.get_pod_info(namespace, name)
        if r.status.container_statuses[0].restart_count > 0:
            return
        time.sleep(1)
        timeout -= 1
    assert False, "Fail to wait for pod %s to restart" % name


def get_pod_restart_count(namespace, name):
    r = k8sclient.get_pod_info(namespace, name)
    return r.status.container_statuses[0].restart_count


class K8SPodTestCase(unittest.TestCase):
    namespace = "k8sft"
    args = "memcached -m 4096 -u root -v"
    image = "ihub.helium.io:30100/library/memcached:check"
    port_number = 11211
    port_name = "clientport"

    def setUp(self):
        k8sclient.switch_user("admin")

    def tearDown(self):
        # delete all pods under namespace
        # k8sclient.clean_pods(self.namespace)
        pass

    def _create_pod(self, name, probe="", labels=None, node_name=None):
        r = k8sclient.send_create_pod_request(
            namespace=self.namespace,
            name=name,
            args=self.args,
            image=self.image,
            ports={self.port_number: self.port_name},
            probe=probe,
            labels=labels,
            node_name=node_name
        )
        assert r.status.phase == "Pending", r.status.phase
        assert r.kind == "Pod", r.kind
        assert r.metadata.namespace == self.namespace, r.metadata.namespace
        assert r.metadata.name == name, r.metadata.name
        assert r.spec.containers[0].image_pull_policy == "IfNotPresent", r.spec.containers[0].image_pull_policy
        assert r.spec.containers[0].name == name, r.spec.containers[0].name
        assert r.spec.containers[0].ports[0].container_port == self.port_number, r.spec.containers[0].ports[0].container_port
        assert r.spec.containers[0].ports[0].name == self.port_name, r.spec.containers[0].ports[0].name
        assert r.spec.containers[0].ports[0].protocol == "TCP", r.spec.containers[0].ports[0].protocol
        assert r.spec.dns_policy == "ClusterFirst", r.spec.dns_policy
        assert r.spec.restart_policy == "Always", r.spec.restart_policy
        return r

    def _wait_for_pod(self, name, expect_status="Running", timeout=10):
        return wait_for_pod_state(self.namespace, name, timeout, expect_status)

    def _remove_pod(self, name):
        k8sclient.send_remove_pod_request(self.namespace, name)

    def test_create(self):
        name = "pod_test_create"
        self._create_pod(name)
        # wait for running state
        self._wait_for_pod(name, "Running")
        # delete the pod
        self._remove_pod(name)
        with self.assertRaises(ApiException) as cm:
            self._wait_for_pod(name, "xxxxxx")
        assert cm.exception.status == 404, cm.exception

    def test_get_404(self):
        name = "xxxxxx"
        with self.assertRaises(ApiException) as cm:
            self._wait_for_pod(name, "xxxxxx")
        assert cm.exception.status == 404, cm.exception

    def test_create_invalid_name(self):
        names = [
            "~", ")", "a-", "0-", "*", "[", "{", "a0-", "a0[", "a"*64
            ]
        for name in names:
            with self.assertRaises(ApiException) as cm:
                self._create_pod(name)
            assert cm.exception.status == 422, cm.exception

    def test_create_longest_name(self):
        llimit = 63
        name = "a" * llimit
        self._create_pod(name)
        self._wait_for_pod(name, "Running")
        # delete the pod
        self._remove_pod(name)
        with self.assertRaises(ApiException) as cm:
            self._wait_for_pod(name, "xxxxxx")
        assert cm.exception.status == 404, cm.exception

    def test_aliveness_fail(self):
        name = "aliveness-test"
        self._create_pod(name, probe="ls abcd")
        self._wait_for_pod(name, "Running")
        wait_for_pod_restart(self.namespace, name, timeout=30)
        # delete the pod
        self._remove_pod(name)
        with self.assertRaises(ApiException) as cm:
            self._wait_for_pod(name, "xxxxxx")
        assert cm.exception.status == 404, cm.exception

    def test_aliveness_pass(self):
        name = "aliveness-test"
        self._create_pod(name, probe="ls")
        self._wait_for_pod(name, "Running")
        time.sleep(20)
        assert get_pod_restart_count(self.namespace, name) == 0
        # delete the pod
        self._remove_pod(name)
        with self.assertRaises(ApiException) as cm:
            self._wait_for_pod(name, "xxxxxx")
        assert cm.exception.status == 404, cm.exception

    @attr("staging-3")
    def test_service_pod(self):
        # create some pods
        # create service selecting the pods
        name = "pod-service"
        k8sclient.create_service(
            self.namespace,
            name,
            port=self.port_number,
            selector={"app": "test_create_stress"}
        )
        services = k8sclient.list_services(self.namespace)
        service_names = [s.metadata.name for s in services.items]
        assert name in service_names, service_names
        k8sclient.remove_service(self.namespace, name)
        services = k8sclient.list_services(self.namespace)
        service_names = [s.metadata.name for s in services.items]
        assert name not in service_names, service_names

    @attr("staging-4")
    def test_stress_service_pod(self):
        name = "pod-service"
        for i in range(1000):
            k8sclient.create_service(
                self.namespace,
                name,
                port=self.port_number,
                selector={"app": "test_create_stress"}
            )
            time.sleep(3)
            services = k8sclient.list_services(self.namespace)
            service_names = [s.metadata.name for s in services.items]
            assert name in service_names, service_names
            k8sclient.remove_service(self.namespace, name)
            time.sleep(3)
            services = k8sclient.list_services(self.namespace)
            service_names = [s.metadata.name for s in services.items]
            assert name not in service_names, service_names

    @attr("staging-5")
    def test_create_stress2(self):
        interval = 30
        count = 2  # per node
        node_names = k8sclient.list_ready_nodenames()
        node_names = [n for n in node_names if not n.startswith("10.19.140")]
        # node_names = ["10.19.137.147"]
        for n in node_names:
            print n
        name_prefix = "podstresstest"
        for i in range(1, count + 1):
            labels = {"app": "test_create_stress-"+str(i)}
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                self._create_pod(name, labels=labels, node_name=node)
            # create service to bound those pods
            svc_name = "pod-service-"+str(i)
            k8sclient.create_service(
                self.namespace,
                svc_name,
                port=self.port_number,
                selector=labels
            )
            time.sleep(interval)
        # wait for running state
        timeout = count * 30 * len(node_names) + 300
        for i in range(1, count + 1):
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                timeout = self._wait_for_pod(name, timeout=timeout, expect_status="Running")

    @attr("staging-temp")
    def test_temp(self):
        count = 210
        for i in range(1, count + 1):
            svc_name = "pod-service-" + str(i)
            k8sclient.remove_service(
                self.namespace,
                svc_name
            )

    @attr("staging-2")
    def test_create_stress(self):
        interval = 30
        count = 1 # per node
        start_time = time.time()
        node_names = k8sclient.list_ready_nodenames()
        # node_names = [n for n in node_names if not n.startswith("10.19.140")]
        # node_names = ["10.19.137.147"]
        for n in node_names:
            print n
        name_prefix = "podstresstest"
        for i in range(1, count+1):
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                self._create_pod(name, labels={"app": "test_create_stress"}, node_name=node)
            time.sleep(interval)
        # wait for running state
        timeout = count * 30 * len(node_names) + 300
        for i in range(1, count+1):
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                timeout = self._wait_for_pod(name, timeout=timeout, expect_status="Running")
        end_time = time.time()
        print "it took ", end_time - start_time, "s until all pod Running"
        return
        # delete the pod
        for i in range(1, count+1):
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                self._remove_pod(name)
        # wait for 404
        for i in range(1, count+1):
            for node in node_names:
                node_name = '-'.join(node.split('.'))
                name = "-".join([name_prefix, node_name, str(i)])
                with self.assertRaises(ApiException) as cm:
                    self._wait_for_pod(name, timeout=count*10, expect_status="xxxxx")
                assert cm.exception.status == 404, cm.exception
