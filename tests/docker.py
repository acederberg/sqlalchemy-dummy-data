import asyncio
import functools
import logging
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    TypeVar,
)
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.engine import URL
from sqlalchemy.engine import Engine as SQAEngine
from sqlalchemy.engine import create_engine
from typing_extensions import ParamSpec, Self

import docker
from docker.models.containers import Container as DockerContainer

# =========================================================================== #
# Helprs and constants

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
CONTAINER_BASENAME: str = "sqadd"


T = ParamSpec("T")
S = TypeVar("S")


def asyncronize(fn: Callable[T, S]) -> Callable[T, Coroutine[Any, Any, S]]:
    async def wrapper(*args: T.args, **kwargs: T.kwargs):
        loop = asyncio.get_event_loop()
        p = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(None, p)

    return wrapper


# =========================================================================== #
# Configurations and their methods.


class Host(BaseModel):
    """Specifications for the docker container that has been run.

    The ip address of the host will be determined by using the docker library
    and the user shouldn't need to provide it.

    ..
        :attr host: The ip address or hostname for the running container.

    :attr port: The port on which the mysql containers are running.
    :attr database: The database to work within for this connection.
    :attr username: The username to run the tests within the container
        with.
    :attr password: The password for the user specified by
        :attr:`username`.
    """

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


class Server(BaseModel):
    """Configuration for a server to run tests on.

    :attr host: Host specification. See :class:`Host`.
    :attr container: container specification. See :class:`Container`.
    """

    driver: Optional[str] = None
    dialect: str = "mysql"
    container: Container
    hostspec: Host
    id: str

    def env(self) -> Dict[str, str]:
        """Create environment variables for the container.

        Note that most containerized sql instances have environment
        variables for setting up a username, password, and database
        on start. This function will likely determine how this happens
        in the container.
        """

        environ = {
            self.container.env_username: self.hostspec.username,
            self.container.env_password: self.hostspec.password,
            self.container.env_initdb: self.hostspec.database,
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

    async def url(self, client: docker.DockerClient) -> URL:
        """Create a URL to connect to the database."""
        scheme = (
            f"{self.dialect}.{self.driver}"
            if self.driver is not None
            else self.dialect  #
        )
        host_ips = await self.host(client)
        if host_ips is None:
            raise ValueError(f"No ips for container with id `{self.id}`.")
        elif (host_ip := host_ips.get("bridge")) is None:
            raise ValueError("Bridge networking required.")
        return URL.create(
            scheme,
            host=host_ip,
            **self.hostspec.model_dump(),
        )

    async def engine(self, client: docker.DockerClient) -> SQAEngine:
        """Get a connection pool for the server."""
        logger.debug(
            "Generating engine for container `%s`.",
            self.container_name(),
        )
        return create_engine(url=await self.url(client))

    def get(self, client: docker.DockerClient) -> DockerContainer | None:
        """Attempt to find the container state associated with this
        configuration.

        Not async for now.

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
    def inspect(self, client: docker.DockerClient) -> Dict[str, Any] | None:
        container = self.get(client)
        if container is None:
            return None

        name = container.name
        inspected = client.api.inspect_container(name)
        return inspected

    async def host(self, client: docker.DockerClient) -> Dict[str, str] | None:
        result = await self.inspect(client)
        if result is None:
            return None

        networks = result["NetworkSettings"]["Networks"]
        return {name: spec["IPAddress"] for name, spec in networks.items()}

    async def start(self, client: docker.DockerClient) -> SQAEngine:
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
                "Container `%s` exists but is not running." " Attempting to start.",
                name,
            )
            container.start()

            """
            if container.status != "running":
                print(container.logs())
                raise AssertionError(f"Failed to restart `{name}`.")
            """

        return await self.engine(client)

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


class Servers(BaseModel):
    """Configurations for the various servers to run tests on.

    :attr servers: Individual configurations for the servers to run in
        docker.
    :attr keep: Keep the docker containers after the test? If not, then
        the containers and all of their data will be lost. This will
        determine how this instance works as a context manager.
    :attr concurrent: Run tests concurrently.
    """

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
                server for server in self.servers if server.id in self.servers_included
            ]

        logger.debug("Checking `servers_included` and `servers` falsy.")
        if not self.servers_included:
            raise AssertionError(
                "No servers included, please check that "
                "`config.servers.servers_included` contains only valid "
                "`id` entries."
            )
        if not self.servers:
            raise AssertionError("`servers` must not be falsy.")

        return self

    async def hosts(
        self, client, server_ids: Optional[Iterable[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        if not server_ids:
            server_ids = self.servers_included
        tasks = {s.id: s.host(client) for s in self.servers if s.id in server_ids}
        hosts = await asyncio.gather(*tasks.values())

        return {k: v for k, v in zip(tasks, hosts)}

    async def start(
        self,
        client: docker.DockerClient,
        server_ids: Optional[Iterable[str]] = None,
    ) -> List[SQAEngine]:
        """Start the SQL docker containers for testing against various SQL
        dialects.

        :param client: A ``docker.DockerClient`` instance.
        :param server_ids: Containers as identified by `Container.id`. This
            is not the docker container id. If none are provided, then all
            servers will be started.
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
        :param server_ids: The :attr:`Server.id`s of the servers to stop. This
            is not the docker container id. If none are provided, then all
            servers will be stopped.
        :param force: Stop even when keep is true.
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

    def __init__(
        self,
        servers: Servers,
        params: Optional[Dict[str, Iterable]] = None,
    ):
        """Params should be labeled iterables of parameters for parametrized
        functions. Do not not provide
        """
        self.servers = servers
        self.params = params if params is not None else dict()

    def __call__(self, class_or_fn):
        """Add class/function parametrization."""
        paramnames = "Engine, " + ", ".join(self.params.keys())
        params = list(
            zip(
                [s.driver for s in self.servers.servers],
                *self.params.values(),
            )
        )
        p = pytest.mark.parametrize(paramnames, params, indirect=["Engine"])
        return p(class_or_fn)
