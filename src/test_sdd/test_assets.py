from os import path

from . import assets


class TestAssets:
    def test_consts_exist(self):
        bad = {
            key: value
            for key in ("PATH_ROOT", "PATH_TESTS", "PATH_ASSETS")
            if not path.isdir(value := getattr(assets, key))
        }
        if len(bad):
            _ = ", ".join(f"`{key} => {value}`" for key, value in bad.items())
            raise AssertionError(
                "The following `PATH` constants do not resolve to directories:" f" {_}."
            )
