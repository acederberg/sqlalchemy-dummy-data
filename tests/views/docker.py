import asyncio
import json

from pydantic import BaseModel
from sdd_tests.conftest import config
from sdd_tests.views import flags
from sdd_tests.views.base import BaseViews

import docker


class Docker(BaseViews):
    __subcommand__ = "docker"

    @classmethod
    def clean(cls):
        print("Cleaning docker containers.")
        config.servers.clean(cls.ctx)

    @classmethod
    def start(cls, server_ids: flags.OServerIds = None):
        print("Starting all docker containers.")
        task = config.servers.start(
            cls.ctx,
            server_ids=server_ids,
        )
        asyncio.run(task)

    @classmethod
    def stop(
        cls,
        server_ids: flags.OServerIds = None,
        force: flags.OForce = False,
    ):
        print("Stopping docker containers")
        asyncio.run(
            config.servers.stop(
                cls.ctx,
                server_ids=server_ids,
                force=force,
            )
        )

    @classmethod
    def hosts(cls, server_ids: flags.OServerIds = None):
        print("Hosts")
        result = asyncio.run(config.servers.hosts(cls.ctx, server_ids=server_ids))
        print(json.dumps(result, indent=2))
