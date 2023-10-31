import json
from typing import Annotated, Iterable, List

import typer
from pydantic import BaseModel
from test_sdd.views.base import BaseViews


class Config(BaseViews):
    __subcommand__ = "config"

    @classmethod
    def show(cls, path: Annotated[str, typer.Argument()] = None):
        thing: List[BaseModel] | BaseModel = cls.config
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
                    elif q == "*":
                        print("`*` expressions are not yet supported.")
                        typer.Exit(3)
                    else:
                        thing = getattr(thing, q)
                except (KeyError, IndexError, AttributeError):
                    print(f"Path `{path}` invalid at `{q}`. ")
                    raise typer.Exit(1)

        print("Interpretted configuration:")
        if isinstance(thing, Iterable):
            out = [t.model_dump() if hasattr(t, "model_dump") else t for t in thing]  # type: ignore
            print(json.dumps(out, indent=2, default=str))
        elif isinstance(thing, dict):
            print(json.dumps(thing, indent=2, default=str))
        else:
            print(
                json.dumps(
                    thing.model_dump() if hasattr(thing, "model_dump") else thing,
                    indent=2,
                    default=str,
                )
            )
