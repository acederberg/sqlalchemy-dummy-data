"""CLI.

Do not add logging in here besides in `WithTyper`. Functions should be simple 
enough that they do not require logging.
"""
import logging
from typing import Annotated, Iterable, List

import docker

from test_sdd.config import Context
from test_sdd.views import Views


def main():
    Views.ctx = Context() # type: ignore
    Views.propogate_ctx()
    Views.__typer__()
