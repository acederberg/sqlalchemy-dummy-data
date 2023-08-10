"""Test case generators and test case helpers.


"""
import functools
from typing import Callable, ClassVar, List, Tuple, TypeAlias

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeMeta, Mapped, mapped_column, registry

DummyCases: TypeAlias = Tuple[DeclarativeMeta, ...]
DummyCaseGenerator: TypeAlias = Callable[[], DummyCases]
DummyCaseGeneratorRaw: TypeAlias = Callable[[DeclarativeMeta], DummyCases]


class Cases:
    cases: ClassVar[List[DummyCaseGenerator]] = []

    registry: registry  # type: ignore
    Base: DeclarativeMeta

    def __init__(self):
        self.registry = registry()
        self.Base = self.registry.generate_base()

    def __call__(self, fn: DummyCaseGeneratorRaw) -> DummyCaseGenerator:
        @functools.wraps(fn)
        def wrapper() -> DummyCases:
            results = fn(self.Base)
            return results

        self.cases.append(wrapper)

        return wrapper


@Cases()
def cycle(Base: DeclarativeMeta) -> DummyCases:
    """Generate tables representing an order four cyclic graph."""

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


@Cases()
def connected(Base: DeclarativeMeta) -> DummyCases:
    """Completely connected directed graph of of order 5.

    This exists so that we can test primary foreign keys.
    """

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


@Cases()
def many_many(Base: DeclarativeMeta) -> DummyCases:
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
