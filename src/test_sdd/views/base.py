import logging
from typing import Optional

import typer
from test_sdd.config import Context

import docker

DOCKER_CLIENT = docker.from_env()
logger = logging.getLogger(__name__)


class ViewsMixins:
    ctx: Context
    __typer__: typer.Typer
    __subcommand__: Optional[str]


class ViewsMeta(type):
    """Transform into typer"""

    def __new__(cls, name, bases, namespace):
        logger.info("Processing `%s`.", name)
        namespace["__typer__"] = typer.Typer()
        commands = {
            key
            for key, value in namespace.items()
            if isinstance(value, classmethod) and not key.startswith("_")
        }

        cls.add_children(name, bases, namespace)
        T = super().__new__(cls, name, bases, namespace)
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


class BaseViews(ViewsMixins, metaclass=ViewsMeta):
    ...
