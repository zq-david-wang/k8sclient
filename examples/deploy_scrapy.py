from k8sclient.K8SClient import RBDVolume, PodBuilder, CephFSVolume
from k8sclient.keywords import (
    wait_for_pod_state,
    RUNNING,
    delete_pod,
    NOT_FOUND
)

namespace = "monkey"
image = "127.0.0.1:30100/library/scrapy_images:v20170615"
args = "scrapy crawl neteasy -a entry_url=http://tieba.baidu.com -a domain=tieba.baidu.com -a img_link_key=sign"
# node = "10.19.137.154"
# name = "scrapy-images-tieba-2"
# ceph_monitors = "10.19.137.144:6789,10.19.137.145:6789,10.19.137.146:6789"
ceph_monitors = "10.19.248.14:6789,10.19.248.15:6789,10.19.248.16:6789"
ceph_pool = "monkey"
ceph_fstype = "xfs"
ceph_secret = "ceph-secret"



data_set = {
    "scrapy-tieba-2": {
        "url": "http://tieba.baidu.com",
        "domain": "tieba.baidu.com",
        "node": "10.19.248.21"
    },
    "scrapy-neteasy-2": {
        "url": "http://www.163.com",
        "domain": "163.com",
        "node": "10.19.248.13"
    },
    "scrapy-jd-2": {
        "url": "http://www.jd.com",
        "domain": "jd.com",
        "node": "10.19.248.14"
    },
    "scrapy-tianya-2": {
        "url": "http://www.tianya.cn",
        "domain": "tianya.cn",
        "node": "10.19.248.15"
    },
    "scrapy-sina": {
        "url": "http://www.sina.com.cn",
        "domain": "sina.com.cn",
        "node": "10.19.248.16"
    },
    "scrapy-qq": {
        "url": "http://news.qq.com",
        "domain": "qq.com",
        "node": "10.19.248.17"
    },
    "scrapy-baidu": {
        "url": "http://news.baidu.com",
        "domain": "baidu.com",
        "node": "10.19.248.18"
    },
    "scrapy-hao123": {
        "url": "http://news.hao123.com",
        "domain": "hao123.com",
        "node": "10.19.248.22"
    },
    "scrapy-chinanews": {
        "url": "http://www.chinanews.com",
        "domain": "chinanews.com",
        "node": "10.19.248.20"
    },

    "scrapy-3jy": {
        "url": "http://www.3jy.com",
        "domain": "3jy.com",
        "node": "10.19.248.23"
    },
    "scrapy-xxhh": {
        "url": "http://www.xxhh.com",
        "domain": "xxhh.com",
        "node": "10.19.248.24"
    },
    "scrapy-duowan": {
        "url": "http://tu.duowan.com",
        "domain": "duowan.com",
        "node": "10.19.248.25"
    },
    "scrapy-mop": {
        "url": "http://tt.mop.com",
        "domain": "mop.com",
        "node": "10.19.248.27"
    },
    "scrapy-huanqiu": {
        "url": "http://photo.huanqiu.com/funnypicture/",
        "domain": "huanqiu.com",
        "node": "10.19.248.28"
    },
    "scrapy-xiaopena": {
        "url": "http://www.xiaopena.com/qutu/",
        "domain": "xiaopena.com",
        "node": "10.19.248.29"
    },
    "scrapy-sogo": {
        "url": "http://pic.sogou.com/",
        "domain": "sogou.com",
        "node": "10.19.248.30"
    },
}


def deploy_1(scrapy_name, url, domain, node):
    # volume
    try:
        volume = CephFSVolume(
            "cephfs",
            "/tmp",
            monitors=ceph_monitors,
            secret_name=ceph_secret,
            fs_path="scrapy",
            sub_path=scrapy_name
        )
        PodBuilder(
            scrapy_name,
            namespace,
        ).set_node(
            node
        ).add_container(
            scrapy_name,
            image=image,
            args="scrapy crawl neteasy -a entry_url=%s -a domain=%s" % (url, domain),
            volumes=[volume],
            requests={'cpu': 2, 'memory': "8Gi"},
            limits={'cpu': 4, 'memory': "16Gi"},
        ).deploy()
    except:
        return
    wait_for_pod_state(namespace, scrapy_name, 60, RUNNING)


def un_deploy(name):
    delete_pod(namespace, name)
    wait_for_pod_state(namespace, name, 60, NOT_FOUND)


def un_deploy_all():
    for k in data_set.keys():
        try:
            un_deploy(k)
        except:
            pass

if __name__ == "__main__":
    # deploy()
    for k in data_set.keys():
        print "deploying", k
        deploy_1(k, data_set[k]['url'], data_set[k]['domain'], data_set[k]['node'])
    # un_deploy_all()
