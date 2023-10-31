from .base import BaseViews
from .config import Config
from .docker import Docker


class Views(BaseViews):
    __subcommand__ = None
    __children__ = [Config, Docker]
