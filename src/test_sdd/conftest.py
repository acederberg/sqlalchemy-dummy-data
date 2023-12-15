"""Configuration for all tests and the cli.

Includes docker tools for running tests against multiple SQL flavors.
"""
import asyncio
import logging
from os import path

import docker
import pytest
from sqlalchemy.engine import Engine as SQAEngine
from yaml_settings_pydantic import BaseYamlSettings

from test_sdd.cases import *
from test_sdd.config import Context
from test_sdd.controllers.docker import Server, Servers, WithServers

# =========================================================================== #
# Helprs and constants

PYTEST_CONTEXT = Context()
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
DOCKER_CLIENT_TESTS = docker.from_env()


# =========================================================================== #
# Decorators


def withservers(params):
    config = globals().get("config")
    if config is None:
        raise AssertionError("Could not find ``config``.")
    return WithServers(config.servers, params)


# =========================================================================== #
# Fixtures


# TODO: Start all containers at once
@pytest.fixture(params=[PYTEST_CONTEXT.config], scope="session", autouse=True)
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
    engines = asyncio.run(c.servers.start(client))
    yield engines
    asyncio.run(c.servers.stop(client))


@pytest.fixture(params=[[PYTEST_CONTEXT.config, "mysql"]])
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

    return asyncio.run(ServerConfig.engine(DOCKER_CLIENT_TESTS))
