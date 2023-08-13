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
    Tuple,
    Type,
    TypeAlias,
)

import pytest
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeMeta, Mapped, mapped_column, registry

SQLAlchemyMetadata = Tuple[Any, DeclarativeMeta]
DummyCases: TypeAlias = Tuple[DeclarativeMeta, ...]
DummyCaseGenerator: TypeAlias = Callable[[SQLAlchemyMetadata], DummyCases]
DummyCaseGeneratorRaw: TypeAlias = Callable[[SQLAlchemyMetadata], DummyCases]


cases: Dict[str, DummyCaseGenerator] = {}


def case(fn: DummyCaseGenerator) -> DummyCaseGenerator:
    cases[fn.__name__] = fn
    return pytest.fixture(fn)


@pytest.fixture
def Cases() -> Dict[str, DummyCases]:
    return {name: case(decl()) for name, case in cases.items()}


def decl() -> SQLAlchemyMetadata:
    r = registry()
    Base = r.generate_base()

    return r, Base


@pytest.fixture
def Decl() -> SQLAlchemyMetadata:
    return decl()


@case
def Cycle(Decl: SQLAlchemyMetadata) -> DummyCases:
    """Generate tables representing an order four cyclic graph."""

    Base: DeclarativeMeta
    _, Base = Decl

    class A(Base):
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("d.id"))

    class B(Base):
        __tablename__ = "b"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("a.id"))

    class C(Base):
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("b.id"))

    class D(Base):
        __tablename__ = "d"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_parent: Mapped[int] = mapped_column(ForeignKey("c.id"))

    return (A, B, C, D)


@case
def Connected(Decl: Tuple[Any, DeclarativeMeta]) -> DummyCases:
    """Completely connected directed graph of of order 5.

    This exists so that we can test primary foreign keys.
    """

    _, Base = Decl

    class A(Base):
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class B(Base):
        __tablename__ = "b"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class C(Base):
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class D(Base):
        __tablename__ = "d"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    class E(Base):
        __tablename__ = "e"
        id: Mapped[int] = mapped_column(primary_key=True)
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_b: Mapped[int] = mapped_column(ForeignKey("b.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)
        id_d: Mapped[int] = mapped_column(ForeignKey("d.id"), primary_key=True)
        id_e: Mapped[int] = mapped_column(ForeignKey("e.id"), primary_key=True)

    return (A, B, C, D, E)


@case
def ManyMany(Decl: Tuple[Any, DeclarativeMeta]) -> DummyCases:
    _, Base = Decl

    class A(Base):
        __tablename__ = "a"
        id: Mapped[int] = mapped_column(primary_key=True)

    class B(Base):
        __tablename__ = "b"
        id_a: Mapped[int] = mapped_column(ForeignKey("a.id"), primary_key=True)
        id_c: Mapped[int] = mapped_column(ForeignKey("c.id"), primary_key=True)

    class C(Base):
        __tablename__ = "c"
        id: Mapped[int] = mapped_column(primary_key=True)

    return (A, B, C)


__all__ = ("Cases", "Cycle", "Connected", "ManyMany")
