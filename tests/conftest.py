"""Configuration for all tests and the cli.

Includes docker tools for running tests against multiple SQL flavors.
"""
import logging
from os import path

import pytest
from sqlalchemy.engine import Engine as SQAEngine
from yaml_settings_pydantic import BaseYamlSettings

import docker

from .cases import *
from .docker import Server, Servers, WithServers

# =========================================================================== #
# Helprs and constants

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


def ubuv(fn: str) -> str:
    return path.realpath(path.join(path.dirname(__file__), "..", fn))


# =========================================================================== #
# Configuration


# TODO: Long term plan should be to run docker tests concurrently for many
# drivers so that we know it works with various sql flavors. Concurency will
# be implemented in pipelines by providing different configuration instances.
class Config(BaseYamlSettings):
    """Configuration for tests and fixtures.

    :attr servers: Configuration for the various servers.
    """

    __yaml_files__ = ubuv("tests.yaml")

    servers: Servers


config = Config()  # type: ignore


# =========================================================================== #
# Decorators


def withservers(params):
    config = globals().get("config")
    if config is None:
        raise AssertionError("Could not find ``config``.")
    return WithServers(config.servers, params)


@withservers(
    {
        "arg": (_args := ["first arg", "second arg", "third arg"]),
    },
)
class TestWithServers:
    def test_it_works(self, Engine, arg):
        assert isinstance(Engine, SQAEngine)
        assert arg in _args


# =========================================================================== #
# Fixtures


# TODO: Start all containers at once
@pytest.fixture(params=[config], scope="session", autouse=True)
def Servers(request):
    """Start and stop servers. This should only happen once per ``pytest```
    call.

    DO NOT USE THIS. You probably just want to use `Engine` to get an engine
    for a particular container. If you want to parametrize your tests with
    various engines use :class:`WithServers`.

    :param request: ``param`` should be the desired configuration instance.
    """
    c = request.param
    if not isinstance(c, Config):
        raise ValueError("Parameter must be an instance of TestConfig.")

    client = docker.from_env()
    engines = c.servers.start(client)
    yield engines
    c.servers.stop(client)


@pytest.fixture(params=[[config, "mysql"]])
def ServerConfig(request) -> Server:
    """Look for the server configuration with the driver ``request.params[1]``."""
    config, driver = request.param
    if (
        server_configuration := next(
            (s for s in config.servers.servers),
            None,
        )
    ) is None:
        raise ValueError(f"No server configuration for driver `{driver}`.")
    return server_configuration


@pytest.fixture
def Engine(ServerConfig: Server) -> SQAEngine:
    """Get an engine for this particular server configuration.

    See :func:`ServerConfig`.
    """

    return ServerConfig.engine()
