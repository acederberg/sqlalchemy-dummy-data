from typing import Optional

import docker
from test_sdd import assets
from test_sdd.controllers.docker import Servers
from yaml_settings_pydantic import BaseYamlSettings


class Config(BaseYamlSettings):
    """Configuration for tests and fixtures.

    :attr servers: Configuration for the various servers.
    """

    __yaml_files__ = assets.ubuv("tests.yaml")

    servers: Servers  # type: ignore


class Context:
    """Stuff that will be needed to run views.

    These values should be injected into controllers using a decorator.
    """

    config: Config
    client: docker.DockerClient

    def __init__(
        self,
        _client: Optional[docker.DockerClient],
        _config: Optional[Config],
    ):
        self.config = Config()  # type: ignore
        self.client = docker.from_env()
