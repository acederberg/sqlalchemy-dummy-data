"""Test case generators and test case helpers.


"""
import functools
import inspect
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
    Type,
    TypeAlias,
)

import pytest
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeMeta, Mapped, mapped_column, registry
from sqlalchemy_dummy_data import create_dummy_meta

SQLAlchemyMetadata = Tuple[Any, DeclarativeMeta]
RawDummyCases: TypeAlias = Tuple[Type, ...]
DummyCases: TypeAlias = Tuple[DeclarativeMeta, ...]
DummyCaseGenerator: TypeAlias = Callable[[SQLAlchemyMetadata, Any], DummyCases]
DummyCaseGeneratorRaw: TypeAlias = Callable[[], RawDummyCases]


cases: Dict[str, DummyCaseGenerator] = {}


def case(fn: DummyCaseGeneratorRaw) -> DummyCaseGenerator:
    sig = inspect.signature(fn)
    _msg = f"Invalid signature for `{fn.__name__}`."
    if sig.parameters:
        raise ValueError(_msg + " Expected no parameters.")
    elif sig.return_annotation != RawDummyCases:
        print(sig.return_annotation)
        print(RawDummyCases)
        _msg += " Should return `RawDummyCases`,  not `{0}`"
        raise ValueError(_msg.format(sig.return_annotation))

    def wrapper(Decl: SQLAlchemyMetadata, request=None) -> DummyCases:
        param = getattr(request, "param", None)
        hasparam = request is not None and param is not None
        if hasparam and not isinstance(param, bool):
            _msg = f"Cannot parametrize `{0}` with non-boolean value `{1}`."
            raise ValueError(_msg.format(fn.__name__, param))
        elif not isinstance(Decl, tuple) or len(Decl) != 2:
            raise ValueError("`Decl` must be a tuple of length 2.")

        Base: DeclarativeMeta
        _, Base = Decl

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
def Cases(request) -> Dict[str, DummyCases]:
    return {name: case(decl(), request) for name, case in cases.items()}


def decl() -> SQLAlchemyMetadata:
    r = registry()
    Base = r.generate_base()

    return r, Base


@pytest.fixture
def Decl() -> SQLAlchemyMetadata:
    return decl()


@case
def Cycle() -> RawDummyCases:
    """Generate tables representing an order four cyclic graph."""

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


@case
def Connected() -> RawDummyCases:
    """Completely connected directed graph of of order 5.

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


@case
def ManyMany() -> RawDummyCases:
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


__all__ = ("Cases", "Cycle", "Connected", "ManyMany")
