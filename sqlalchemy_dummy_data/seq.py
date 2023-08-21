import itertools
from typing import Dict, Generator, Iterable, List, Optional, Sequence, Tuple


def unique_permutations(
    elements: Sequence,
) -> Generator[Tuple[int, ...], None, None,]:
    if len(elements) == 1:
        yield (elements[0],)
    else:
        unique_elements = set(elements)
        for first_element in unique_elements:
            remaining_elements = list(elements)
            remaining_elements.remove(first_element)
            for sub_permutation in unique_permutations(remaining_elements):
                yield (first_element, *sub_permutation)


class iters:
    @classmethod
    def count(
        cls, start: Optional[int] = None, stop: Optional[int] = None
    ) -> Generator[int, None, None]:
        """Sould 'work like' range except with indefinite iteration.

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
                continue
            k += 1

    @classmethod
    def _triangled(
        cls, *items: Iterable[int]
    ) -> Generator[Tuple[int, ...], None, None]:
        """Iterate the members of the product of the items such that they act
        like the sequenct described in :meth:`DummyMixins._create_iter_pks`
        when :param:`items` is made of similar items.

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
        for last in last_item:
            for item in cls._triangled(*remaining_items):
                if item[-1] <= last:
                    yield (*item, last)

    @classmethod
    def _squared(cls, *items: Iterable):
        for item in cls._triangled(*items):
            yield from unique_permutations(item)

    @classmethod
    def triangled(
        cls,
        *labels,
        start: Optional[int] = None,
        stop: Optional[int] = None,
    ) -> Iterable[Dict[str, int]]:
        counters = {label: cls.count(start, stop) for label in labels}
        yield from (
            {k: v for k, v in zip(counters, coord)}
            for coord in cls._triangled(*counters.values())
        )
