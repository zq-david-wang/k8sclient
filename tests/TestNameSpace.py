import unittest
import time
from nose.plugins.attrib import attr
import re

from k8sclient.K8SClient import k8sclient
from kubernetes.client.rest import ApiException


def create_namespace(name):
    r = k8sclient.send_create_namespace_request(name)
    assert r.status.phase == 'Active', r
    assert r.metadata.name == name, r


def remove_namespace(name):
    r = k8sclient.send_remove_namespace_request(name)
    assert eval(r.status)['phase'] == 'Terminating', r


def wait_for_no_namespace(name, timeout=120, interval=1):
    m = re.compile(name)
    i = 0
    while i < timeout:
        r = k8sclient.get_all_namespaces()
        exist = False
        for n in r:
            if m.match(n):
                exist = True
                break
        if not exist:
            break
        i += interval
        time.sleep(interval)
    assert i < timeout, "THe namespace %s is still there" % name


class K8SNameSpaceTestCase(unittest.TestCase):
    def setUp(self):
        k8sclient.switch_user("admin")

    def tearDown(self):
        pass

    def test_create(self):
        name = "k8s-function-test"
        create_namespace(name)
        remove_namespace(name)
        # wait for no namespace
        wait_for_no_namespace(name)
        with self.assertRaises(ApiException) as cm:
            remove_namespace(name)
        assert cm.exception.status == 404, cm.exception

    @attr("stress")
    def staging_create_stress(self):
        prefix = "k8s-create-namespace-stress-"
        count = 10
        for i in range(count):
            name = prefix + "%d" % (i, )
            create_namespace(name)
            remove_namespace(name)
        wait_for_no_namespace(prefix+r"\d+", count*6, 5)
        for i in range(count):
            name = prefix + "-%d" % (i,)
            with self.assertRaises(ApiException) as cm:
                remove_namespace(name)
            assert cm.exception.status == 404, cm.exception


class K8sNameSpaceKeyStoneTestCase(unittest.TestCase):
    def setUp(self):
        k8sclient.switch_user("david")

    def test_create(self):
        name = "k8s-normal-user-namespace-invalid"
        with self.assertRaises(ApiException) as cm:
            create_namespace(name)
        assert cm.exception.status == 403, cm.exception
