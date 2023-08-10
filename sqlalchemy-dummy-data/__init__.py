"""
"""
import itertools
from typing import Any, ClassVar, Dict, Generator, List, Set, Type, TypeAlias

from sqlalchemy import inspect
from sqlalchemy.orm import InstrumentedAttribute
from typing_extensions import Self

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Constants

__version__ = "0.0.0"

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Types

Pks: TypeAlias = Dict[str, Dict[str, List[int]]]
IterFks: TypeAlias = Generator[Dict[str, int], None, None]
IterSelf: TypeAlias = Generator[Self, None, None]  # type: ignore

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Definitions that should not be used directly by consumers in most cases.


class DummyMetaMixins:
    """Methods that I'd rather not wrap in the class created by
    :func:`create_dummy_meta` as it makes it rather unreadable and assists in
    testing.

    :attr __prefix__: Prefix for table names.
    :attr tables: A mapping from table names to table mapped class name.
    :attr tablenames: Set of all tablenames.
    :attr fks: A mapping from tablenames to a mapping of primary key names
        to their respective `InstrumentedAttribute`s.
    :attr pks: Like :attr:`fks` but for primary keys.
    :attr pknames: Set of primary key names.
    :attr fknames: Set of foreign key names.

    """

    # ======================================================================= #
    # INTERNALS
    #
    # DO NOT ASSIGN! THESE WILL BE ASSIGENED INSIDE :func:`create_dummy_meta`.
    # These are defined here for optimal editor functionality.

    __prefix__: ClassVar[str]

    tables: ClassVar[Dict[str, Any]]
    tablenames: ClassVar[Set[str]]
    fks: ClassVar[Dict[str, Dict[str, InstrumentedAttribute]]]
    pks: ClassVar[Dict[str, Dict[str, InstrumentedAttribute]]]
    pknames: ClassVar[Set[str]]
    fknames: ClassVar[Set[str]]

    # ======================================================================= #
    # CONVENIENCES
    #
    # `get` prefixed methods.

    @classmethod
    def get_fks(cls, primary=False) -> Dict[str, InstrumentedAttribute]:
        """Get the foreign keys for `cls`.

        :param primary: When `True`, only return foreign keys that are also
            primary keys.
        :returns: A dictionary of foreign key names mapping to the foreign key
            `InstrumentedAttribute`s.
        """
        f = cls.fks[cls.__name__]
        if not primary:
            return f
        return {tn: ia for tn, ia in f.items() if ia.primary_key}

    @classmethod
    def get_fk_owners(cls, primary=False) -> Dict[str, str]:
        """Get owners of the various foreign keys.

        :returns: A mapping of tablenames to tables for the foreign keys of
            `cls`.
        """
        fks = cls.get_fks(primary=primary)
        return {
            fname: cls.tables[fk.column.table.name.replace(cls.__prefix__, "")]
            for fname, ff in fks.items()
            for fk in ff.foreign_keys
        }

    @classmethod
    def get_pks(cls) -> Dict[str, InstrumentedAttribute]:
        """Get the primary keys of `cls`.

        :returns: A mapping of primary key names to their respective
            `InstrumentedAttribute`.
        """
        return cls.pks[cls.__name__]

    # ======================================================================= #
    # FOREIGN KEY AND PRIMARY FOREIGN KEY ITERATION.
    #
    # `create` prefixed methods and their helpers.

    # TODO:
    @classmethod
    def create_iter_fks(
        cls, pks: Pks, repeat: int = 1, primary: bool = False
    ) -> IterFks:  # type: ignore
        """Because whe need values to put into foreign key values. These values
        will be generated lazily.

        There are three cases that this function should cover:

        1. Iterate unique pairs of keys. This is for the case where a table has
           primary keys that are also foreign keys.
        2. Iterate non-unique pairs of keys. This could be where non-unique
            foreign-keys should be generated.
        3. A combination of the both of these.

        :param Model: The model to iterate foreign key combinations forl
        :param pks: A record of existing primary keys.
        :param primary: Return keys as primary-foreign keys. This will
            result in yielding of repeated results - the output is not unique.
        """

        ...

    @classmethod
    def _create_coproduct(cls, all_pks, primary=False) -> Dict[str, List[int]]:
        """Get a tables potential foreign keys and return them as a `dict` of
        tuples.

        :param primary: Only primary foreign keys.
        :returns: See desc.
        """
        fk_owners = cls.get_fk_owners(primary=primary)
        fk_coproduct: Dict[str, List[int]] = {
            fkname: all_pks[fkowner.name] for fkname, fkowner in fk_owners.items()
        }
        return fk_coproduct

    # TODO:
    @classmethod
    def _create_iter_fks(cls, coproduct: Dict[str, List[int]], repeat: int = 1):
        yield from (
            {key: coord for key, value in zip(coproduct, coord)}
            for coord in itertools.product(coproduct.values())
            for _ in range(repeat)
        )

    # @classmethod
    # def createDummies(cls, table, pks: Pks) -> Generator[Self, None, None]:
    #     """Returns a generator of dummies. Will create as many as possible from
    #     the provided foreign keys.
    #     :param pks: A dictionary of primary keys.
    #     :returns: A generator of `cls` instances.
    #     """
    #     iter_fks = create_iter_fks(cls, pks)
    #     yield from (
    #         {
    #             **fks.cls.createDummyArgs(),
    #             **cls.createMixinDummyArgs(),
    #         }
    #         for fks in iter_fks
    #     )


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Consumer functions.


def create_dummy_meta(Base) -> Type:
    """Use this to create a metaclass instance for dummy data generation.

    :returns: A dummy data metaclass.
    """

    class DummyMeta(DummyMetaMixins):
        """Metaclass for dummy data generation.

        Documentation on class attributes can be found on the instances.

        """

        tables = dict()
        tablenames = set()
        fks = dict()
        pks = dict()
        pknames = set()
        fknames = set()

        @classmethod
        def _registerTable(cls, name, Table):
            """Collect a bunch of metadata about the models for model methods.

            :param name: Name of the table.
            :param Table: A type instance created by `__new__`.
            :returns: Nothing.
            """

            cls.tablenames.add(name)

            i = inspect(Table)
            cls.pks[name] = {p.name: p for p in i.primary_key}
            cls.fks[name] = {
                name: column
                for name, column in i.columns.items()
                if column.foreign_keys
            }
            cls.pknames.update(cls.pks[name].keys())
            cls.fknames.update(cls.fks[name].keys())
            cls.tables[name] = Table

        #     @classmethod
        #     def _verifyCreateDummyArgs(cls, name, bases, dict_):
        #         """Verify the call signature of the `createDummyArgs` method required
        #         on each model instance. Parameter names match those of `__new__`.
        #         :raises ValueError: When `createDummyArgs`'s call signature is
        #             incorrect or is altogether absent.
        #         :returns: Nothing.
        #         """
        #         if dict_.get("__no_dummies__", False):
        #             return
        #         elif (fn := dict_.get(meth := "createDummyArgs")) is None:
        #             msg = f"Missing method `{meth}` of table `{name}`."
        #             raise ValueError(msg)
        #         util.comparesigs(DummyMetaMixins.createDummyArgs, fn)

        def __new__(cls, name, bases, dict_):
            """Register and create type."""

            # Check that 'createDummyArgs' is defined:
            # cls._verifyCreateDummyArgs(name, bases, dict_)

            # Create and register instance.
            T = type(name, (Base, DummyMetaMixins, *bases), dict_)
            cls._registerTable(name, T)
            return T

    return DummyMeta


__all__ = (
    "create_dummy_meta",
    "DummyMetaMixins",
)
