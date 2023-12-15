from typing import Optional

import docker
from yaml_settings_pydantic import BaseYamlSettings

from test_sdd import assets
from test_sdd.controllers.docker import Servers


class Config(BaseYamlSettings):
    """Configuration for tests and fixtures.

    :attr servers: Configuration for the various servers.
    """

    __yaml_files__ = assets.Assets.ubuv("tests.yaml")

    servers: Servers  # type: ignore


class Context:
    """Stuff that will be needed to run views.

    These values should be injected into controllers using a decorator.
    """

    config: Config
    client: docker.DockerClient

    def __init__(
        self,
        _client: Optional[docker.DockerClient] = None,
        _config: Optional[Config] = None,
    ):
        self.config = Config()  # type: ignore
        self.client = docker.from_env()
