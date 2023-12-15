import asyncio
import json

from pydantic import BaseModel
from test_sdd.views import flags
from test_sdd.views.base import BaseViews

import docker


class Docker(BaseViews):
    __subcommand__ = "docker"
    __controller__ = "servers"

    @classmethod
    def clean(cls):
        print("Cleaning docker containers.")
        cls.ctx.config.servers.clean()

    @classmethod
    def start(cls, server_ids: flags.OServerIds = None):
        print("Starting all docker containers.")
        task = cls.ctx.config.servers.start(
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
