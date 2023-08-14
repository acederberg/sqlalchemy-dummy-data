import json
from typing import Dict, List, Type

import pytest
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

    def check_output_attrs(self, tables, attr: str, expect: bool):
        bad = tuple(table for table in tables if hasattr(table, attr) != expect)

        if len(bad):
            print(hasattr(tables[0], "get_fks"), expect)
            msg = "\n".join(f"-  {b.__name__}" for b in bad)
            msg = f"The following tables were {{0}}missing `get_fks`: \n{msg}"
            raise AssertionError(msg.format("not " if not expect else ""))

    @pytest.mark.parametrize(
        "ormCycle, expect", [(True, True), (False, False)], indirect=["ormCycle"]
    )
    def test_parametrize(self, ormCycle, expect):
        self.check_output_attrs(ormCycle, "get_pks", expect)


class TestDummyMetaMixins:
    def test_classvars_unassigned(self):
        # Assigining these would be stupid, hence this test.
        attrs = ("tables", "tablesnames", "fks", "pks", "pknames", "fknames")
        assert not all(hasattr(DummyMetaMixins, attr) for attr in attrs)
