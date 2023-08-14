import inspect
import json
from typing import Dict, List, Type

from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy_dummy_data import DummyMetaMixins

from .cases import Cases


class TestCases:
    def validate_output(self, name: str, output: Cases):
        """Inspect output from a `case`."""

        def fmt(k: int, T: Type) -> str:
            return (
                f"Return value in position `{k}` of `{name}` has "
                f"incorrect type `{T}` (expected type `DeclarativeMeta`."
            )

        if not isinstance(output, tuple):
            yield "case"

        bad = (
            fmt(k, type(elem))
            for k, elem in enumerate(output)
            if not isinstance(elem, DeclarativeMeta)
        )
        yield from bad

    def format_output(self, msgs: Dict[str, List[str]]):
        msg = "Some `cases` did not pass validation. Detail `"
        msg = json.dumps(msgs, indent=2, default=str) + "`"
        return msg

    def test_cases(self, ormCases):
        msgs = {
            name: o
            for name, case_output in ormCases.items()
            if (o := tuple(self.validate_output(name, case_output)))
        }
        if msgs:
            raise AssertionError(self.format_output(msgs))


class TestDummyMetaMixins:
    def test_classvars_unassigned(self):
        # Assigining these would be stupid, hence this test.
        attrs = ("tables", "tablesnames", "fks", "pks", "pknames", "fknames")
        assert not all(hasattr(DummyMetaMixins, attr) for attr in attrs)

    def test_get_fks(self, ormCycle):
        ...
