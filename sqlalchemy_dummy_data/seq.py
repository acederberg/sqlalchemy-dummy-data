import itertools
from typing import Generator, Iterable, List, Tuple


class iters:
    @classmethod
    def count(cls, start: int = None, stop: int = None) -> Generator[int, None, None]:
        k = start or 1
        while True:
            yield k
            if stop is not None and start >= stop:
                continue
            k += 1

    @classmethod
    def triangled(cls, *items: Iterable[int]) -> Iterable[Tuple[int, ...]]:
        """Iterate"""
        n = len(items)
        if not n:
            raise ValueError("Arguments must have length of 1 or greater.")
        elif n == 1:
            return items[0]
        elif n == 2:
            yield from (
                (a, b)
                for k, a in enumerate(items[0])
                for j, b in enumerate(items[1])
                if j <= k
            )
            return
        first_item: Iterable[int]
        remaining_items: List[Iterable[int]]
        first_item, *remaining_items = items
        for first in first_item:
            for item in cls.triangled(*remaining_items):
                yield (
                    first,
                    *item,
                )

    @classmethod
    def squared(cls, *items: Iterable):
        for item in cls.triangled(*items):
            yield from itertools.permutations(item)
