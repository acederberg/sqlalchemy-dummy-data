"""Tools to solve the 'monotonic sequencing problem'. That is, given some
primary keys, the sequences easiest to generate tend to be constant in most
dimensions which results in data where relationships are concentrated in some
small subset of the entire data. In my opinion, this is less than desirable.

An example of that discussed above would be where a table `T` has the foreign
keys `a` and `b` and the available keys `X = set(range(10))`. If we use 
`itertools.product(X, X)` but only generate 10 entries in `T` then all of the 
new entries will have `a == 1`.
"""

import itertools
from typing import Dict, Generator, Iterable, List, Optional, Protocol, Tuple, TypedDict

from typing_extensions import NotRequired, Unpack

# =========================================================================== #
# TYPING GARBAGE
#
# For now I have to use a stupid protocol. Read more about typing novelties:
#
# https://peps.python.org/pep-0677/
# https://peps.python.org/pep-0612/


class KwargsSequencer(TypedDict):
    """Keyword arguments that sequencers must ac`cept.

    :attr start: Least integer to iterate.
    :attr stop: Greatest integer to iterate.
    """

    start: NotRequired[Optional[int]]
    stop: NotRequired[Optional[int]]


class SequencerCallable(Protocol):
    """Call sigature for so-called 'sequencer'.

    It should work like the following:

    .. code:: python
        def test(fn: Optional[SequencerCallable] = None) -> None:
            # Proof of concept

            if fn is None:
                fn = iters.squared
            assert fn
            fn("idClient", "idThing", start=2)

            # MyPy should complain.
            # bar: SequencerCallable = int
    """

    def __call__(
        self, *labels: str, **kwargs: Unpack[KwargsSequencer]
    ) -> Iterable[Dict[str, int]]:
        """Call sigature for so-called 'sequencer'.

        Sequencers are used to 'mix up' the available primary/foreign keys such
        that data is not 'to similar'.

        :param labels: Names of the primary keys. Determines the dimension of
            the sequence. Labels output of the sequence.
        :param kwargs: Keyword arguments for sequencers. For complete details,
            see :class:`KwargsSequencer`s documentation.
        :returns: An iterable (ideally a generator) returning dictionaries of
            sequence members as labeled by their respective :param:`labels`.
        """
        ...


# =========================================================================== #
# Sequencers


class iters:
    @classmethod
    def count(
        cls, start: Optional[int] = None, stop: Optional[int] = None
    ) -> Generator[int, None, None]:
        """Sould 'work like' range except with optional indefinite iteration.

        :param start: 1 if not overridden.
        :param stop: Iteration will terminate at this value if specified.
        """

        start = start or 1
        if stop is not None and start > stop:
            msg = "`start` parameter must be less than or equal to `stop` "
            msg += "parameter."
            raise ValueError(msg)

        k = start
        while True:
            yield k
            if stop is not None and k >= stop:
                break
            k += 1

    @classmethod
    def _triangled(
        cls, *items: Iterable[int]
    ) -> Generator[Tuple[int, ...], None, None]:
        """Generate the sequence defined by the upper triangle of the product
        iterated columnwise (in the 2d case) or the higher dimensional
        analogues of this.

        :param items: The things to make the product from.
        :returns: See function description.
        """

        n = len(items)
        if not n:
            raise ValueError("Arguments must have length of 1 or greater.")
        elif n == 1:
            yield from ((item,) for item in items[0])
            return

        last_item: Iterable[int]
        remaining_items: List[Iterable[int]]
        last_item, *remaining_items = items
        for item in cls._triangled(*remaining_items):
            for last in last_item:
                if item[0] >= last:
                    yield (last, *item)

    @classmethod
    def _squared(
        cls,
        *items: Iterable,
    ) -> Generator[Tuple[int, ...], None, None]:
        """Like :meth:`_triangled` but with reflections by permutation.

        :param items: See :meth:`_triangled`.
        :returns: See function description.
        """
        for item in cls._triangled(*items):
            yield from set(itertools.permutations(item))

    @classmethod
    def triangled(
        cls,
        *labels: str,
        **kwargs: Unpack[KwargsSequencer],
    ) -> Generator[Dict[str, int], None, None]:
        """See documentation of :meth:`_triangled` for a description of
        sequence members and :class:`SequencerCallable` for parameter
        descriptions.
        """
        counters = {label: cls.count(**kwargs) for label in labels}
        yield from (
            {k: v for k, v in zip(counters, coord)}
            for coord in cls._triangled(*counters.values())
        )

    @classmethod
    def squared(
        cls, *labels: str, **kwargs: Unpack[KwargsSequencer]
    ) -> Generator[Dict[str, int], None, None]:
        """See documentation of :meth:`_triangled` for a description of
        sequence members and :class:`SequencerCallable` for parameter
        descriptions.
        """
        counters = {label: cls.count(**kwargs) for label in labels}
        yield from (
            {k: v for k, v in zip(counters, coord)}
            for coord in cls._squared(*counters.values())
        )
