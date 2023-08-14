"""Test case generators and test case helpers.

:type SQLAlchemyOrmTuple: Type alias for the tuple of important sqlalchemy orm
    objects used to setup declarative sqlalchemy.
:type RawCases: A tuple of types used to generate orm objects (without 
    inheritance). It is important that these types not use the orm or 
    metaclasses when returned from their owning functions (usually a function
    decorated with :func:`as_case`).
:type Cases: A tuple of sqlalchemy orm objects.
:type DummyCaseGenerator: Call signature for cases after decoration.
:type DummyCaseGeneratorRaw: Call signature for cases before decoration.
:const cases: A dictionary of all of the cases (populated by the :func:`as_case`
    decorator). This should not be modified.
"""
import functools
import inspect
from typing import Any, Callable, Dict, Tuple, Type, TypeAlias

import pytest
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeMeta, Mapped, mapped_column, registry
from sqlalchemy_dummy_data import create_dummy_meta

SQLAlchemyOrmTuple = Tuple[Any, DeclarativeMeta]
RawCases: TypeAlias = Tuple[Type, ...]
Cases: TypeAlias = Tuple[DeclarativeMeta, ...]
DummyCaseGenerator: TypeAlias = Callable[[SQLAlchemyOrmTuple, Any], Cases]
DummyCaseGeneratorRaw: TypeAlias = Callable[[], RawCases]


cases: Dict[str, DummyCaseGenerator] = {}


def as_case(fn: DummyCaseGeneratorRaw) -> DummyCaseGenerator:
    """Turn a function returning types into a function returning these types
    with the necessary sqlalchemy pieces needed to function in the context of
    a database.

    :param fn: A fuction with no parameters returing a tuple of types (these
        should look like sqlalchemy orm models without inheritance from
        `Base`).
    :raises ValueError: When :param:`fn` has a bad signature.
    :returns: Decorated :param:`fn` as a parametrizable pytest fixture that
        uses the pytest fixture :func:`ormDecl`. The parameter should be set
        to `True` when the dummy data metaclass from :func:`create_dummy_meta`
        is to be used. This function will raise a `ValueError` when arguments/
        fixutres/the `request` is malformed.
    """
    sig = inspect.signature(fn)
    _msg = f"Invalid signature for `{fn.__name__}`."
    if sig.parameters:
        raise ValueError(_msg + " Expected no parameters.")
    elif sig.return_annotation != RawCases:
        _msg += " Should return `RawCases`,  not `{0}`"
        raise ValueError(_msg.format(sig.return_annotation))

    def wrapper(ormDecl: SQLAlchemyOrmTuple, request=None) -> Cases:
        param = getattr(request, "param", None)
        hasparam = request is not None and param is not None
        if hasparam and not isinstance(param, bool):
            _msg = f"Cannot parametrize `{0}` with non-boolean value `{1}`."
            raise ValueError(_msg.format(fn.__name__, param))
        elif not isinstance(ormDecl, tuple) or len(ormDecl) != 2:
            raise ValueError("`ormDecl` must be a tuple of length 2.")

        Base: DeclarativeMeta
        _, Base = ormDecl

        T: Type[type]
        T = type if not hasparam else create_dummy_meta(Base)  # type: ignore
        Raw = fn()

        return tuple(T(R.__name__, (R, Base), {}) for R in Raw)

    # `functools` wrap and sig
    # Keep sig bc `wraps` overwrites
    sig = inspect.signature(wrapper)
    wrapper = functools.wraps(fn)(wrapper)
    setattr(wrapper, "__signature__", sig)
    cases[wrapper.__name__] = wrapper

    # `pytest` wrap
    wrapper = pytest.fixture(wrapper)
    return wrapper


@pytest.fixture
def ormCases(request) -> Dict[str, Cases]:
    """Return a mapping of all orm :type:`Cases` as specified by
    :const:`cases`.
    """
    return {name: case(decl(), request) for name, case in cases.items()}


def decl() -> SQLAlchemyOrmTuple:
    """Create the sqlalchemy orm boilerplate stuff."""
    r = registry()
    Base = r.generate_base()

    return r, Base


@pytest.fixture
def ormDecl() -> SQLAlchemyOrmTuple:
    f"{decl.__doc__}"
    return decl()


@as_case
def ormCycle() -> RawCases:
    """Tables representing an order four cyclic graph."""

    class A:
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("d.id"))

    class B:
        __tablename__ = "b"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("a.id"))

    class C:
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("b.id"))

    class D:
        __tablename__ = "d"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("c.id"))

    return (A, B, C, D)


@as_case
def ormConnected() -> RawCases:
    """Tables representing a completely connected directed graph of of order 5.

    This exists so that we can test primary foreign keys.
    """

    class A:
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class B:
        __tablename__ = "b"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class C:
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class D:
        __tablename__ = "d"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class E:
        __tablename__ = "e"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    return (A, B, C, D, E)


@as_case
def ormManyMany() -> RawCases:
    """Tables representing a many to many relationship as described by the
    SQLAlchemy2 docs."""

    class A:
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)

    class B:
        __tablename__ = "b"
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)

    class C:
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)

    return (A, B, C)


__all__ = ("ormCases", "ormCycle", "ormConnected", "ormManyMany")
