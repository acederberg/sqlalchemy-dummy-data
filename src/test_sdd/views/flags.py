from typing import Annotated, List

import typer

OServerIds = Annotated[None | List[str], typer.Option()]
OForce = Annotated[bool, typer.Option()]
