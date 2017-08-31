import docker
from docker.errors import APIError
import re
from .K8SClient import ComponentBuilder


class DockerClient(object):
    def __init__(self):
        self.docker_client = docker.from_env(version="1.24")
        try:
            self.docker_client.info()
        except APIError as e:
            message = e.response.json()['message']
            m = re.search(r".*server API version:([ 0-9.]+).*", message)
            if m:
                self.docker_client = docker.from_env(version=m.group(1).strip())
            else:
                raise e

    def deploy(self, components):
        networks = [n.name for n in self.docker_client.networks.list()]
        for comp in components:
            if not isinstance(comp, ComponentBuilder):
                continue
            # create network for namespace
            if comp.meta.namespace not in networks:
                self.docker_client.networks.create(comp.meta.namespace)
            for c in comp.containers:
                # create containers
                self.docker_client.containers.run(
                    image=c.image,
                    command=c.args,
                    detach=True,
                    environment={}
                )
                pass
