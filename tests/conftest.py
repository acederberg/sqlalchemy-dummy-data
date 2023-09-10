"""Configuration for all tests and the cli.

Includes docker tools for running tests against multiple SQL flavors.
"""
import asyncio
import functools
import logging
import typing
from os import path
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Set,
    TypeAlias,
    TypeVar,
)
from uuid import uuid4

import docker
import pytest
import typing_extensions
from docker.models.containers import Container as DockerContainer
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.engine import URL
from sqlalchemy.engine import Engine as SQAEngine
from sqlalchemy.engine import create_engine
from typing_extensions import ParamSpec, Self
from yaml_settings_pydantic import BaseYamlSettings

from .cases import ormCases, ormConnected, ormCycle, ormDecl, ormManyMany

# =========================================================================== #
# Helprs and constants

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
CONTAINER_BASENAME: str = "sqadd"


def ubuv(fn: str) -> str:
    return path.realpath(path.join(path.dirname(__file__), "..", fn))


T = ParamSpec("T")
S = TypeVar("S")


def asyncronize(fn: Callable[T, S]) -> Callable[T, Coroutine[Any, Any, S]]:
    async def wrapper(*args: T.args, **kwargs: T.kwargs):
        loop = asyncio.get_event_loop()
        p = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(None, p)

    return wrapper


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

    class Servers(BaseModel):
        """Configurations for the various servers to run tests on.

        :attr servers: Individual configurations for the servers to run in
            docker.
        :attr keep: Keep the docker containers after the test? If not, then
            the containers and all of their data will be lost. This will
            determine how this instance works as a context manager.
        :attr concurrent: Run tests concurrently.
        """

        class Server(BaseModel):
            """Configuration for a server to run tests on.

            :attr host: Host specification. See :class:`Host`.
            :attr container: container specification. See :class:`Container`.
            """

            class Host(BaseModel):
                """Specifications for the docker container that has been run.

                :attr host: The ip address or hostname for the running container.
                :attr port: The port on which the mysql containers are running.
                :attr database: The database to work within for this connection.
                :attr username: The username to run the tests within the container
                    with.
                :attr password: The password for the user specified by
                    :attr:`username`.
                """

                host: str = "localhost"
                port: int = 3306
                database: str = "tests"
                username: str = "test_user"
                password: str = Field(default_factory=uuid4)

            class Container(BaseModel):
                """Specifications for the docker container.

                Note that the env variables to be passed to the container will
                be in :class:`Host`. I'd like to store defaults for these
                values in `YAML`.

                :attr image: The docker image.
                :attr name: The name of the docker container.
                :attr env_username: The name of the environment variable used
                    to set the initial username for the container.
                :attr env_password: :attr:`env_username`'s password.
                :attr env_initdb: The name of the environment variable used to
                    set the initial database. Usually the initial user has
                    permissions on this db.
                :attr env: Any other environment variables.
                """

                image: str = "mysql:8"
                name: Optional[str] = None
                env_username: str = "MYSQL_USER"
                env_password: str = "MYSQL_PASSWORD"
                env_initdb: str = "MYSQL_DATABASE"
                env: Optional[Dict[str, str]] = None

            def env(self) -> Dict[str, str]:
                """Create environment variables for the container.

                Note that most containerized sql instances have environment
                variables for setting up a username, password, and database
                on start. This function will likely determine how this happens
                in the container.
                """

                environ = {
                    self.container.env_username: self.host.username,
                    self.container.env_password: self.host.password,
                    self.container.env_initdb: self.host.database,
                }
                if (rest := self.container.env) is not None:
                    environ.update(rest)
                return environ

            def container_name(self) -> str:
                """Generate a container name."""
                return self.container.name or "-".join(
                    (
                        CONTAINER_BASENAME,
                        self.container.image.replace(":", "-").replace("_", "-"),
                        self.driver or "default",
                    )
                )

            def url(self) -> URL:
                """Create a URL to connect to the database."""
                scheme = (
                    f"{self.dialect}.{self.driver}"
                    if self.driver is not None
                    else self.dialect
                )
                return URL.create(scheme, **self.host.model_dump())

            def engine(self) -> SQAEngine:
                """Get a connection pool for the server."""
                logger.debug(
                    "Generating engine for container `%s`.",
                    self.container_name(),
                )
                return create_engine(url=self.url())

            def get(self, client: docker.DockerClient) -> DockerContainer | None:
                """Attempt to find the container state associated with this
                configuration.

                :param client: A ``docker.DockerClient`` instance.
                :returns: JSON response from the DockerClient.
                """
                name = self.container_name()
                logger.debug("Searching for container `%s`.", name)
                available: List[DockerContainer]
                available = client.containers.list(all=True)  # type: ignore
                return next(  # type: ignore
                    (c for c in available if c.name == name),
                    None,
                )

            @asyncronize
            def start(self, client: docker.DockerClient) -> SQAEngine:
                """Start the container associated with this configuration.

                :param client: A ``docker.DockerClient`` instance.
                """
                name = self.container_name()
                container: DockerContainer | None = self.get(client)
                if container is None:
                    logger.debug("Starting container `%s`.", name)
                    container = client.containers.run(
                        self.container.image,  # type: ignore
                        detach=True,
                        environment=self.env(),
                        labels=["sdd-tests"],
                        name=name,
                    )

                    logger.debug("Verifying existence and state of `%s`.", name)
                    if container is None:
                        msg = f"Failed to create container `{name}`."
                        raise AssertionError(msg)
                    elif container.status == "Exited":
                        msg = f"Container `{name}` exited unexpectedly."
                        raise AssertionError(msg)
                else:
                    logger.debug("`%s` already exists.", name)

                if container.status != "running":
                    logger.debug(
                        "Container `%s` exists but is not running."
                        " Attempting to start.",
                        name,
                    )
                    container.start()

                    """
                    if container.status != "running":
                        print(container.logs())
                        raise AssertionError(f"Failed to restart `{name}`.")
                    """

                return self.engine()

            @asyncronize
            def stop(self, client: docker.DockerClient, force: bool = False) -> None:
                """Stop the container associated with this configuration.

                :param client: A ``docker.DockerClient`` instance.
                """
                name = self.container_name()
                if container := self.get(client):
                    if force:
                        logger.debug(
                            "Not keeping container `%s`.",
                            name,
                        )
                        container.stop()
                    else:
                        logger.debug("Keeping container `%s`.", name)
                else:
                    logger.debug("No container `%s`, cannot remove.", name)

            driver: Optional[str] = None
            dialect: str = "mysql"
            host: Host
            container: Container
            id: str

        async def start(
            self,
            client: docker.DockerClient,
            server_ids: Optional[Iterable[str]] = None,
        ) -> List[SQAEngine]:
            """Start the SQL docker containers for testing against various SQL
            dialects.

            :param client: A ``docker.DockerClient`` instance.
            :param server_ids: Containers as identified by `Container.id`. This
                is not the docker container id.
            :returns: All engines for te various mysql instances.
            """
            logger.info("Starting test containers.")
            if not server_ids:
                server_ids = self.servers_included
            tasks = (s.start(client) for s in self.servers if s.id in server_ids)
            servers = await asyncio.gather(*tasks)
            return servers

        async def stop(
            self,
            client: docker.DockerClient,
            server_ids: Optional[Iterable[str]] = None,
            force: bool = False,
        ) -> None:
            """Stop the SQL docker containers for these tests when :attr:`keep`
            is ``False``.

            :param client: A ``docker.DockerClient`` instance.
            """
            if not force and self.keep:
                logger.info("Keeping containers.")
                return

            logger.info("Killing test containers.")
            if not server_ids:
                server_ids = self.servers_included
            tasks = (s.stop(client, force) for s in self.servers if s.id in server_ids)
            await asyncio.gather(*tasks)

        def clean(self, client: docker.DockerClient) -> None:
            """Clean up all existing containers specified by this
            configuration."""

            logger.warning("Removing test containers.")
            containers: List[DockerContainer] = list(
                container
                for server in self.servers
                if (container := server.get(client)) is not None
            )

            for container in containers:
                container.remove()

        # Defaults for containers
        # Applying these should overwrite
        # common_password: Optional[str]
        # common_username: Optional[str]
        # common_database: Optional[str]
        # @model_validator(mode="after")
        # def apply_common(self, data: Any) -> Self:
        #     for server in self.servers:
        #         for attr in {"password", "username", "database"}:
        #             setattr(server, attr,
        #         server.host
        #     ...

        # Meta
        servers_included: Set[str]  # List of ids. Defaults to all.
        servers: List[Server]
        keep: bool = True
        concurrent: bool = True

        @model_validator(mode="after")
        def check_servers_included(self, data: Any) -> Self:
            logger.debug("Checking `servers_included`.")
            if not len(self.servers_included):
                self.servers_included = {s.id for s in self.servers}
            else:
                self.servers_included = {
                    server.id
                    for server in self.servers
                    if server.id in self.servers_included
                }
                self.servers = [
                    server
                    for server in self.servers
                    if server.id in self.servers_included
                ]

            logger.debug(
                "Checking that `servers_included` and `servers` are sufficient."
            )
            if not self.servers_included:
                raise AssertionError(
                    "No servers included, please check that "
                    "`config.servers.servers_included` contains only valid "
                    "`id` entries."
                )
            if not self.servers:
                raise AssertionError("`servers` must not be falsy.")

            return self

    servers: Servers


config = Config()  # type: ignore


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
def ServerConfig(request) -> Config.Servers.Server:
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
def Engine(ServerConfig: Config.Servers.Server) -> SQAEngine:
    """Get an engine for this particular server configuration.

    See :func:`ServerConfig`.
    """

    return ServerConfig.engine()


# =========================================================================== #
# Decorators.

T = ParamSpec("T")


class WithServers:
    """Decorate a test class to run on many servers.

    Intended pattern should be

    .. code:: python

        @WithServers({
            "arg": ["first arg", "second arg", "third arg"],
        })
        class SomeTestWithServers():
            def test_1(self, Engine, arg):
                ...

            def test_2(self, Engine, arg):
                ...

    or

    .. code:: python

        @WithServers()
        def some_test_with_servers(self, Engine):
            ...
    """

    def __init__(self, params: Optional[Dict[str, Iterable]] = None):
        """Params should be labeled iterables of parameters for parametrized
        functions. Do not not provide
        """
        self.params = params if params is not None else dict()

    def __call__(self, class_or_fn):
        """Add class/function parametrization."""
        paramnames = "Engine, " + ", ".join(self.params.keys())
        params = list(
            zip(
                [s.driver for s in config.servers.servers],
                *self.params.values(),
            )
        )
        p = pytest.mark.parametrize(paramnames, params, indirect=["Engine"])
        return p(class_or_fn)


@WithServers(
    {
        "arg": (_args := ["first arg", "second arg", "third arg"]),
    }
)
class TestWithServers:
    def test_it_works(self, Engine, arg):
        assert isinstance(Engine, SQAEngine)
        assert arg in _args
