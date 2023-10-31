"""Assets loading.

:const PATH_ROOT: Path to the project root.
:const PATH_TESTS: Path to the project tests.
:const PATH_ASSETS: Path to the project test assets.
"""
import json
from os import path
from typing import Any

import yaml

PATH_ROOT = path.realpath(path.join(path.dirname(__file__), ".."))
PATH_TESTS = path.join(PATH_ROOT, "tests")
PATH_ASSETS = path.join(PATH_TESTS, "assets")


class Assets:
    """Load files from assets.

    :meth asset: Create path to an asset.
    :meth yaml: Load a yaml asset.
    :meth json: Load a json asset.
    """

    @classmethod
    def asset(cls, name: str) -> str:
        return path.join(PATH_ASSETS, name)

    @classmethod
    def yaml(cls, name) -> Any:
        with open(cls.asset(name), "r") as file:
            return yaml.load(file, yaml.SafeLoader)

    @classmethod
    def json(cls, name) -> Any:
        with open(cls.asset(name), "r") as file:
            return json.load(file)
