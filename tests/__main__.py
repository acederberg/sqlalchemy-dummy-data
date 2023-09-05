"""CLI.

Do not add logging in here besides in `WithTyper`. Functions should be simple 
enough that they do not require logging.
"""
import json
import logging
from typing import Annotated, List

import docker
import typer
from pydantic import BaseModel

from .conftest import config

DOCKER_CLIENT = docker.from_env()
logger = logging.getLogger(__name__)


class WithTyper(type):
    __typer__: typer.Typer

    def __new__(cls, name, bases, namespace):
        logger.info("Processing `%s`.", name)
        namespace["__typer__"] = typer.Typer()
        commands = {
            key
            for key, value in namespace.items()
            if isinstance(value, classmethod) and not key.startswith("_")
        }

        cls.add_children(name, bases, namespace)
        T = type(name, bases, namespace)
        cls.add_commands(T, commands)
        return T

    @classmethod
    def add_commands(cls, T, commands):
        # Uses type since cannot decorate classmethods until the class in
        # created.
        t = T.__typer__
        for command in commands:
            t.command(command)(getattr(T, command))

    @classmethod
    def add_children(cls, name, bases, namespace):
        children = namespace.get("__children__")
        if children is None:
            return

        logger.debug("Adding subcommands to `%s`.", name)
        child_attrs = {"__subcommand__", "__typer__"}
        child_msg = "Cannot add child `{0}`, attribute(s) `{1}` required."

        msg = []
        for child in children:
            missing = {attr for attr in child_attrs if not hasattr(child, attr)}
            if missing:
                msg.append(child_msg.format(child.__name__, missing))
            else:
                logger.debug("Adding subcommand `%s` to `%s`.", child.__name__, name)
                namespace["__typer__"].add_typer(
                    child.__typer__, name=child.__subcommand__
                )

        if msg:
            msg = "\n".join(f"  - {m}" for m in msg)
            raise ValueError(
                "The following errors were raised when trying to add children "
                "to `{}`:\n" + msg
            )


class CommandsDocker(metaclass=WithTyper):
    __subcommand__ = "docker"

    @classmethod
    def clean(cls):
        print("Cleaning docker containers.")
        config.servers.clean(DOCKER_CLIENT)

    @classmethod
    def start(cls):
        print("Starting docker containers.")
        config.servers.start(DOCKER_CLIENT)

    @classmethod
    def stop(cls):
        print("Stopping docker containers")
        config.servers.start(DOCKER_CLIENT)


class CommandsConfig(metaclass=WithTyper):
    __subcommand__ = "config"

    @classmethod
    def show(cls, path: Annotated[str, typer.Argument()] = None):
        thing: List[BaseModel] | BaseModel = config
        if path:
            for q in path.split("."):
                try:
                    if q.isdigit():
                        if isinstance(thing, list):
                            thing = thing[int(q)]
                        else:
                            print(
                                f"Path `{path}` invalid at `{q}`. Cannot "
                                "index non-list."
                            )
                            raise typer.Exit(2)
                    else:
                        thing = getattr(thing, q)
                except (KeyError, IndexError, AttributeError):
                    print(f"Path `{path}` invalid at `{q}`. ")
                    raise typer.Exit(1)

        print("Interpretted configuration:")
        if isinstance(thing, list):
            out = [t.model_dump() for t in thing]  # type: ignore
            print(json.dumps(out, indent=2))
        else:
            print(json.dumps(thing.model_dump(), indent=2))


class Commands(metaclass=WithTyper):
    __subcommand__ = None
    __children__ = [CommandsConfig, CommandsDocker]


if __name__ == "__main__":
    Commands.__typer__()
