import json
import logging
import re
from typing import ClassVar, Dict, List, Tuple, Type

import pytest
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeMeta, InstrumentedAttribute
from sqlalchemy_dummy_data import DummyMixins, Pks

from .assets import Assets
from .cases import Cases

logger = logging.getLogger(__name__)


class TestCases:
    def validate_output(self, name: str, output: Cases):
        """Inspect output from a `case`."""

        logger.debug("Validating output of case `%s`.", name)

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

    def format_output(self, msgs: Dict[str, Tuple[str, ...]]):
        msg = "Some `cases` did not pass validation. Detail `"
        msg = json.dumps(msgs, indent=2, default=str) + "`"
        return msg

    def test_cases(self, ormCases):
        logger.debug("Validating output of all `ormCases`.")
        msgs = {
            name: o
            for name, case_output in ormCases.items()
            if (o := tuple(self.validate_output(name, case_output)))
        }
        if msgs:
            raise AssertionError(self.format_output(msgs))

    def check_output_attrs(self, tables, attr: str, expect: bool):
        bad = tuple(t for t in tables if hasattr(t, attr) != expect)

        if len(bad):
            print(hasattr(tables[0], "get_fks"), expect)
            msg = "\n".join(f"-  {b.__name__}" for b in bad)
            msg = f"The following tables were {{0}}missing `get_fks`: \n{msg}"
            raise AssertionError(msg.format("not " if not expect else ""))

    @pytest.mark.parametrize(
        "ormCycle, expect",
        [(True, True), (False, False)],
        indirect=["ormCycle"],
    )
    def test_parametrize(self, ormCycle, expect):
        logger.debug("Verifying `ormCycle` fixture parametrization.")
        self.check_output_attrs(ormCycle, "get_pks", expect)


class TestDummyMixins:
    """Test the methods defined on :class:`DummyMixins` that do not require
    a database connection.

    :attr pattern_owner: Regular expression to determine a columns foreign key
        owner from the `repr` of that `Column`.
    """

    all_pks: ClassVar[Pks] = Assets.yaml("ormCycleAllPks.yaml")
    pattern_owner: ClassVar[re.Pattern] = re.compile(
        "ForeignKey\\('(?P<owner>\\w*)\\.(?P<id>\\w*)'\\)"
    )

    def test_cycle(self, ormCycle):
        # Use symetry to make assertions. ... -> D -> A -> B -> C -> D -> ...

        logger.info("Checking metaclass methods on `ormCycle`.")
        for k, table in enumerate(ormCycle):
            logger.debug("Checking foreign keys for `%s`.", name := table.__name__)
            fks = table.get_fks()
            assert isinstance(fks, dict)
            if n := len(fks) != 1:
                msg = f"Expected at most one edge per node, got `{n}`."
                raise AssertionError(msg)

            # Get owner with grep. Only doing this once for now.
            logger.debug("Checking ownership of the foreign key(s) of `%s`.", name)
            id_parent = fks["id_parent"]
            assert isinstance(id_parent, Column)
            matched = self.pattern_owner.search(repr(id_parent))
            if matched is None:
                print("1", repr(fks["id_parent"]))
                msg = "Could not find anything to match `{0}`."
                raise AssertionError(msg.format(self.pattern_owner.pattern))
            owner = matched.group("owner")
            expect_owner = ormCycle[(k - 1) % len(ormCycle)].__name__.lower()
            assert owner == expect_owner
            assert matched.group("id") == "id"

            # Check grep owner against computed.
            computed_owners = table.get_fk_owners()
            assert isinstance(computed_owners, dict)
            if len(computed_owners) != 1:
                msg = "Number of owners of foreign keys should equal number "
                raise AssertionError(msg + "of foreign keys.")

            computed_owner = computed_owners["id_parent"].__tablename__
            assert computed_owner == expect_owner

            # Check primary keys.
            logger.debug("Checking primary keys.")
            pks = table.get_pks()
            if (n := len(pks)) != 1:
                raise AssertionError("Expected only only primary key.")

            assert pks["id"].name == "id"

            # Check primary foreign keys. This table defines none.
            fks = table.get_fks(only_primary=True)
            assert not fks

    def test_connected(self, ormConnected):
        for k, table in enumerate(ormConnected):
            logger.debug("Checking foreign keys for `%s`.", name := table.__name__)
            fks = table.get_fks(exclude_primary=True)
            assert not fks, "This table has no 'pure' foreign keys."

            fks = table.get_fks(only_primary=True)
            expected_fks = {
                f"id_{table.__tablename__}"
                for j, table in enumerate(ormConnected)
                if j != k
            }
            assert len(expected_fks) == 4
            if len(fks) != 4:
                msg = "Expected 4 edges in a completely connected graph."
                raise AssertionError(msg)
            elif len(bad := set(fks) - expected_fks):
                raise AssertionError(f"Unexpected foreign keys: `{bad}`.")

            logger.debug("Checking ownership of the foreign key(s) of `%s`.", name)
            fk_owners = table.get_fk_owners(exclude_primary=True)
            assert not len(fk_owners), "This table has no 'pure' foreign keys."

            fk_owners = table.get_fk_owners(only_primary=True)

            logger.debug("Checking primary keys.")
            pks = table.get_pks()
            if (n := len(pks)) != 5:
                msg = f"Expected only 5 primary keys, got `{n}`."
                raise AssertionError(msg)

    def test_get_fk(self, ormConnected):
        "Unit tests for `_create_coproduct`."
        a, *_ = ormConnected
        with pytest.raises(ValueError) as err:
            a.get_fks(exclude_primary=True, only_primary=True)

        assert "Cannot use both" in str(err.value)

        all_fks = a.get_fks()
        assert len(all_fks) == 4

        primary_fks = a.get_fks(only_primary=True)
        assert len(primary_fks) == 4

        pure_fks = a.get_fks(exclude_primary=True)
        assert len(pure_fks) == 0

    def test__create_coproduct_no_db(self, ormConnected: Cases):
        "Unit tests for `_create_coproduct`."
        a: DummyMixins
        a, *_ = ormConnected  # type: ignore
        coproduct: Dict[str, List[int]] = a._create_coproduct(self.all_pks)
        assert len(coproduct) == 4

        coproduct = a._create_coproduct(self.all_pks, only_primary=True)
        assert len(coproduct) == 4

        coproduct = a._create_coproduct(self.all_pks, exclude_primary=True)
        assert len(coproduct) == 0

    def test__create_iter_fks(self, ormConnected: Cases):
        "Unit tests for `_create_iter_fks`."
        a: DummyMixins
        a, *_ = ormConnected  # type: ignore

        # Check the size of the entire product.
        product = tuple(a._create_iter_fks(self.all_pks, only_primary=True))
        assert len(product) == 4**4

        # Check the size of subsets where one coordinate is constant.
        for key in ("id_b", "id_c", "id_d", "id_e"):
            assert sum(1 for fk in product if fk[key] == 1) == 4**3

        # Check the size of subsets where two coordinates are constant.
        assert (
            sum(1 for coord in product if coord["id_b"] == 2 and coord["id_c"] == 3)
            == 4**2
        )

        # Ensure that every entry occurs at most once
        assert len(set(tuple(v.values()) for v in product)) == 4**4
