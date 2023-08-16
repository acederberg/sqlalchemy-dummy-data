import json
from os import path
from typing import Any

import yaml

PATH_ROOT = path.realpath(path.join(path.dirname(__file__), ".."))
PATH_TESTS = path.join(PATH_ROOT, "tests")
PATH_ASSETS = path.join(PATH_TESTS, "assets")


class Assets:
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
