"""CLI.

Do not add logging in here besides in `WithTyper`. Functions should be simple 
enough that they do not require logging.
"""
import asyncio
import json
import logging
from typing import Annotated, Iterable, List

import docker
import typer
from pydantic import BaseModel
from test_sdd.config import Config, Context
from test_sdd.views import Views

DOCKER_CLIENT = docker.from_env()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    Views.ctx = Context()
    Views.__typer__()
