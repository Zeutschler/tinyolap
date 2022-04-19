from __future__ import annotations
import re
import fnmatch
from typing import TypeVar, Generic
from collections.abc import Sequence

T = TypeVar("T")


class HybridDict(Sequence[Generic[T]]):
    """
    A generic case in-sensitive hybrid dictionary/list, with an optional
    'items are from the same source' guarantee for set operations.
    """

    def __init__(self, items: Sequence[T] = tuple[T](), source=None):
        """
        Initializes a new HybridDict[T].
        :param items: The items to be contained in the HybridDict[T].
        :param source: An (optional) source object to ensure that set operations
        are executed only on items of the same source object.
        """
        self._list: list[T] = list(items)
        self._dict: dict[str, T] = {str(item).lower(): item for item in items}
        self._source = source

    @property
    def source(self):
        """Returns the (optional) source object of the HybridDict[T]."""
        return self._source

    def __getitem__(self, item) -> T:
        if type(item) is int:
            return self._list[item]
        else:
            return self._dict[str(item).lower()]

    def __len__(self):
        return len(self._list)

    def __add__(self, other: HybridDict[T]) -> HybridDict[T]:
        if (self._source and other._source) and (self._source is not other._source):
            raise ValueError(f"'add' operation failed on HybridDict[{type(T)}]. "
                             f"Sources [{type(self._source)}: {str(self._source)}] and "
                             f"[{type(other._source)}: {str(other._source)}] are not identical.")
        if self._source:
            source = self._source
        else:
            source = other._source
        return HybridDict[T](items=self._list + other._list, source=source)

    def __repr__(self) -> str:
        if self._list:
            count = len(self._list)
            text = f"HybridDict[{', '.join([str(m) for m in self._list[:min(3, count)]])}"
            if count > 3:
                return text + f", ...]"
            return text + f"]"
        return "HybridDict[]"

    def __str__(self) -> str:
        return self.__repr__()

    def __contains__(self, item) -> bool:
        if type(item) is T:
            return item in self._list
        else:
            key = str(item).lower()
            return key in self._dict

    def __eq__(self, other):
        return self._list.__eq__(other._list)

    def append(self, item: T) -> HybridDict[T]:
        """
        Appends an item of another HybridDict[T] .
        :param item: The HybridDict[T] to be appended.
        :return: The joined HybridDict[T].
        """
        self._list.append(item)
        self._dict[str(item)] = item
        return self

    def clone(self) -> HybridDict[T]:
        """
        Creates a 1:1 copy of the HybridDict[T]. The items and source will not get cloned, but re-referenced.
        :return:
        """
        return HybridDict[T](items=self._list, source=self.source)

    def distinct(self) -> HybridDict[T]:
        """
        Returns HybridDict[T] with distinct values. Doublets will be removed.
        :return:
        """
        return HybridDict[T](items=set(self._list), source=self._source)

    def intersect(self, other: HybridDict[T]) -> HybridDict[T]:
        """Return the intersection of two HybridDict[T] as a new HybridDict[T].
           (i.e. all items that are contained in both sets.)"""
        if (self._source and other._source) and (self._source is not other._source):
            raise ValueError(f"Method 'intersection' failed on HybridDict[{type(T)}]. "
                             f"Sources [{type(self._source)}: {str(self._source)}] and "
                             f"[{type(other._source)}: {str(other._source)}] are not identical.")
        if self._source:
            source = self._source
        else:
            source = other._source
        return HybridDict[T](items=set(self._list).intersection(set(other._list)), source=source)

    def difference(self, other: HybridDict[T]) -> HybridDict[T]:
        """Return the difference of two HybridDict[T] as a new HybridDict[T].
           (i.e. all elements that are contained in this set but not in the other.)"""
        if (self._source and other._source) and (self._source is not other._source):
            raise ValueError(f"Method 'difference' failed on HybridDict[{type(T)}]. "
                             f"Sources [{type(self._source)}: {str(self._source)}] and "
                             f"[{type(other._source)}: {str(other._source)}] are not identical.")
        if self._source:
            source = self._source
        else:
            source = other._source
        return HybridDict[T](items=set(self._list).difference(set(other._list)), source=source)

    def union(self, other: HybridDict[T]) -> HybridDict[T]:
        """Return the union of to HybridDict[T] as a new HybridDict[T].
           (i.e. all elements that are contained in either set.)"""
        if (self._source and other._source) and (self._source is not other._source):
            raise ValueError(f"Method 'union' failed on HybridDict[{type(T)}]. "
                             f"Sources [{type(self._source)}: {str(self._source)}] and "
                             f"[{type(other._source)}: {str(other._source)}] are not identical.")
        if self._source:
            source = self._source
        else:
            source = other._source
        return HybridDict[T](items=set(self._list).union(set(other._list)), source=source)

    def filter(self, pattern: str) -> HybridDict[T]:
        """Provides wildcard pattern matching and filtering on the keys of the items in the HybridDict[T].

            * matches everything
            ? matches any single character
            [seq] matches any character in seq
            [!seq] matches any character not in seq

        :param pattern: The wildcard pattern to filter the member list.
        :return: The filtered member list.
        """
        filtered = fnmatch.filter(self.keys, pattern)
        return HybridDict[T](items=[self._dict[name] for name in filtered], source=self._source)

    def match(self, regular_expression_string: str):
        """Provides regular expression pattern matching and filtering on the keys of the items in the HybridDict[T].

        :param regular_expression_string: The regular expression string to filter the member list.
        :return: The filtered member list.
        """
        regex = re.compile(regular_expression_string)
        return HybridDict[T](items=[self._dict[name] for name in self.keys if regex.search(name)], source=self._source)

    @property
    def first(self) -> T:
        """Returns the first item from the HybridDict[T]."""
        if self._list:
            return self._list[0]
        raise IndexError("The HybridDict[T] is empty.")

    @property
    def last(self) -> T:
        """Returns the last member in the member list"""
        if self._list:
            return self._list[-1]
        raise IndexError("The HybridDict[T] is empty.")

    def count(self, x) -> int:
        """
        Return the total number of occurrences of an item in the HybridDict[T].
        :param x: The member to be counted.
        :return: The number of occurrences.
        """
        return len([m for m in self._list if m == x])

    @property
    def keys(self) -> tuple[str]:
        """Returns the keys of the HybridDict[T]."""
        return tuple(self._dict.keys())

    @property
    def items(self) -> tuple[T]:
        """Returns the items of the HybridDict[T]."""
        t: tuple[T] = tuple(self._list)
        return t


