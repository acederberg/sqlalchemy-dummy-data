"""
"""
import itertools
import logging
from typing import (
    Any,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    TypeAlias,
    TypedDict,
    overload,
)

from sqlalchemy import Column, Select, inspect, select
from sqlalchemy.orm import DeclarativeMeta, InstrumentedAttribute
from typing_extensions import NotRequired, Self, Unpack

from sqlalchemy_dummy_data.seq import KwargsSequencer, SequencerCallable, iters

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Constants

__version__ = "0.0.0"
logger = logging.getLogger(__name__)


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Types

Pks: TypeAlias = Dict[str, Dict[str, List[int]]]
IterFks: TypeAlias = Generator[Dict[str, int], None, None]


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% #
# Definitions that should not be used directly by consumers in most cases.


class KwargsFks(TypedDict):
    exclude_primary: NotRequired[bool]
    only_primary: NotRequired[bool]


class KwargsIterFks(KwargsFks, KwargsSequencer):
    ...


class BaseDummyMeta:
    """
    :attr tables: A mapping from table names to table mapped class name.
    :attr tablenames: Set of all tablenames.
    :attr fks: A mapping from tablenames to a mapping of primary key names
        to their respective `InstrumentedAttribute`s.
    :attr pks: Like :attr:`fks` but for primary keys.
    :attr pknames: Set of primary key names.
    :attr fknames: Set of foreign key names.
    """

    tables: ClassVar[Dict[str, "DeclarativeMeta | DummyMixins"]]
    tablenames: ClassVar[Set[str]]
    fks: ClassVar[Dict[str, Dict[str, Column]]]
    pks: ClassVar[Dict[str, Dict[str, Column]]]
    pknames: ClassVar[Set[str]]
    fknames: ClassVar[Set[str]]

    @classmethod
    def _registerTable(cls, Table):
        """Collect a bunch of metadata about the models for model methods.

        :param name: Name of the table.
        :param Table: A type instance created by `__new__`.
        :returns: Nothing.
        """

        name = Table.__tablename__
        cls.tablenames.add(name)

        table_details = inspect(Table)
        cls.pks[name] = {p.name: p for p in table_details.primary_key}
        cls.fks[name] = {
            name: column
            for name, column in table_details.columns.items()
            if column.foreign_keys
        }
        cls.pknames.update(cls.pks[name].keys())
        cls.fknames.update(cls.fks[name].keys())
        cls.tables[name] = Table


class DummyMixins:
    """Methods that I'd rather not wrap in the class created by
    :func:`create_dummy_meta` as it makes it rather unreadable and assists in
    testing.

    """

    # ======================================================================= #
    # INTERNALS
    #
    # `__dunders__`

    __tablename__: ClassVar[str]
    __dummies__: ClassVar[BaseDummyMeta]

    # ======================================================================= #
    # CONVENIENCES
    #
    # `get` prefixed methods.

    @classmethod
    def get_fks(cls, **kwargs: Unpack[KwargsFks]) -> Dict[str, Column]:
        """Get the foreign keys for `cls`.

        :param exclude_primary: When `True`, only return foreign keys that are
            also primary keys.
        :returns: A dictionary of foreign key names mapping to the foreign key
            `InstrumentedAttribute`s.
        """
        f = cls.__dummies__.fks[cls.__tablename__]
        match [
            kwargs.get("exclude_primary", False),
            kwargs.get("only_primary", False),
        ]:
            case [True, True]:
                msg = "Cannot use both `exclude_primary` and `only_primary`."
                raise ValueError(msg)
            case [True, False]:
                # non primary
                return {tn: ia for tn, ia in f.items() if not ia.primary_key}
            case [False, True]:
                # non foreign.
                return {tn: ia for tn, ia in f.items() if ia.primary_key}
            case _:
                # all.
                return f

    @classmethod
    def get_fk_owners(
        cls, **kwargs: Unpack[KwargsFks]
    ) -> Dict[str, DeclarativeMeta | Self]:
        """Get owners of the various foreign keys.

        :param exclude_primary: Exclude results for primary foreign keys.
        :returns: A mapping of tablenames to tables for the foreign keys of
            `cls`.
        """
        fks = cls.get_fks(**kwargs)
        return {
            fname: cls.__dummies__.tables[fk.column.table.name]
            for fname, ff in fks.items()
            for fk in ff.foreign_keys
        }

    @classmethod
    def get_pks(cls) -> Dict[str, Column]:
        """Get the primary keys of `cls`.

        :returns: A mapping of primary key names to their respective
            `InstrumentedAttribute`.
        """
        return cls.__dummies__.pks[cls.__tablename__]

    @classmethod
    def get_pk(cls, name: str) -> Column:
        return cls.get_pks()[name]

    # ======================================================================= #
    # FOREIGN KEY AND PRIMARY FOREIGN KEY ITERATION.
    #
    # `create` prefixed methods and their helpers.

    @classmethod
    @overload
    def _create_coproduct(
        cls,
        all_pks: None,
        /,
        **kwargs: Unpack[KwargsFks],
    ) -> Dict[str, Select]:
        ...

    @classmethod
    @overload
    def _create_coproduct(
        cls,
        all_pks: Pks,
        /,
        **kwargs: Unpack[KwargsFks],
    ) -> Dict[str, List[int]]:
        ...

    @classmethod
    def _create_coproduct(
        cls,
        all_pks: None | Pks,
        /,
        **kwargs: Unpack[KwargsFks],
    ) -> Dict[str, List[int]] | Dict[str, Select]:
        """Get a tables potential foreign keys and return them as a `dict` of
        lists when providing `all_pks`. Otherwise, return the queries that will
        generate `all_pks`. I cannot say which is more efficient.

        :param primary: Only primary foreign keys.
        :returns: See desc.
        """

        def select_fks(name, owner_name) -> List[int] | Select:
            if all_pks is not None:
                return all_pks[owner_name][name]
            else:
                return select(
                    cls.__dummies__.tables[owner_name].get_pk(name)  # type: ignore
                )

        fk_owners = cls.get_fk_owners(**kwargs)
        fk_coproduct: Dict[str, Select] | Dict[str, List[int]] = {
            name: select_fks(name, owner.__tablename__)  # type: ignore
            for name, owner in fk_owners.items()
        }
        return fk_coproduct

    # TODO:
    @classmethod
    def _create_iter_fks(
        cls,
        all_pks: Optional[Pks],
        sequencer: Optional[SequencerCallable] = None,
        **kwargs: Unpack[KwargsIterFks],
    ) -> Generator[Dict[str, int], None, None]:
        """Returns a generator of key/value mappings. This should expend all
        values in the cartesian product of the foreign keys specfied by
        :param:`kwargs`.

        This should iter fks without adding repitions/randomness. Such
        behavior should be placed in the consuming function.

        :param kwargs: See :meth:`get_fks`.
        """

        skwargs: KwargsSequencer

        if all_pks is not None:
            if "start" in kwargs or "stop" in kwargs:
                msg = "Cannot specify both `all_pks` and `start` or `stop`."
                raise ValueError(msg)
            X = all_pks[cls.__tablename__].values()
            skwargs = KwargsSequencer(
                start=max(min(x) for x in X),
                stop=min(max(x) for x in X),
            )
        else:
            skwargs = KwargsSequencer(
                {  # type: ignore
                    key: value
                    for key in ("start", "stop")
                    if (value := kwargs.pop(key, None)) is not None
                }
            )

        if sequencer is None:
            sequencer = iters.squared

        coproduct = cls._create_coproduct(all_pks, **kwargs)
        yield from sequencer(*coproduct, **skwargs)

    @classmethod
    def _create_iter_pks(
        cls,
        all_pks: Optional[Pks],
        sequencer: Optional[SequencerCallable] = iters.squared,
        **kwargs: Unpack[KwargsSequencer],
    ) -> Generator[Dict[str, int], None, None]:
        """Iterates primary key values.

        An Aside About The Sequence
        -----------------------------------------------------------------------

        Due to the case where a table has both foreign and domestic(?) primary
        keys it is easiest to auto generate primary key values instead of auto
        incrementing them. To avoiad creating primary keys where one part is
        constant (where the primary key vectors all belong to some non-trivial
        affine subspace) we have to ensure that these values are mixed nicely,
        further we do not want to `zip` because then the foreign and domestic
        parts of the keys increment 'together'.

        Finally, I'd like to be able to switch out the algorithm to do this as
        well as apply this in :meth:`create_iter_fks`. Ideally these sequences
        will be somewhat randomized.
        """

        if all_pks is not None:
            if "start" in kwargs:
                raise ValueError("Cannot specify both `all_pks` and `start`.")
            else:
                kwargs["start"] = max(
                    max(thing) for thing in all_pks[cls.__tablename__].values()
                )

        if sequencer is None:
            sequencer = iters.squared

        pks = cls.get_pks()
        yield from sequencer(*pks, **kwargs)

    @classmethod
    def create_iter_fks(cls, all_pks: Pks) -> IterFks:
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

        # These can be large, keep them as generators for lower memory use.
        # What about cases where the foreign primary keys do not form the
        # entire primary key but only a part of it.
        pk_fks = cls._create_iter_fks(all_pks, only_primary=True)
        fks = cls._create_iter_fks(all_pks, exclude_primary=True)
        pks = cls._create_iter_pks(all_pks)

        while (
            (pk := next(pks)) is not None
            and (fk := next(fks)) is not None
            and (pk_fk := next(pk_fks)) is not None
        ):
            pk_fk = next(pk_fks)
            yield dict(**pk_fk, **fk, **pk)

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

    class DummyMeta(BaseDummyMeta):
        """Metaclass for dummy data generation.

        Documentation on class attributes can be found on the instances.

        """

        tables = dict()
        tablenames = set()
        fks = dict()
        pks = dict()
        pknames = set()
        fknames = set()

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
        #         util.comparesigs(DummyMixins.createDummyArgs, fn)

        def __new__(cls, name, bases, dict_):
            """Register and create type."""

            # Check that 'createDummyArgs' is defined:
            # cls._verifyCreateDummyArgs(name, bases, dict_)

            # Create and register instance.
            dict_["__dummies__"] = cls
            T = type(name, (Base, DummyMixins, *bases), dict_)
            cls._registerTable(T)
            return T

    return DummyMeta


__all__ = (
    "create_dummy_meta",
    "DummyMixins",
)
