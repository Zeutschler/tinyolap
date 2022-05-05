from __future__ import annotations
import re
import fnmatch
from typing import TypeVar, Generic
from collections.abc import Iterable

T = TypeVar("T")


class HybridDict(Iterable[Generic[T]]):
    """
    A generic case in-sensitive hybrid dictionary/list, with an optional
    'items are from the same source' guarantee for set operations.
    """

    def __init__(self, items: Iterable[T] = tuple[T](), source=None):
        """
        Initializes a new HybridDict[T].
        :param items: The items to be contained in the HybridDict[T].
        :param source: An (optional) source object to ensure that set operations
        are executed only on items of the same source object.
        """
        if not isinstance(items, Iterable):
            items = (items, )
        self._list: list[T] = list(items)
        self._dict: dict[str, T] = {str(item).lower(): item for item in items}
        self._source = source

    @property
    def source(self):
        """Returns the (optional) source object of the HybridDict[T]."""
        return self._source

    def pop(self,item):
        """Removes the item at the given index from the list and returns the removed item."""
        if type(item) is int:
            # member by index
            value = self._list.pop(item)
            del(self._dict[str(item).lower()])
            return value
        else:
            # member by key, ...or even pattern search
            value = self._dict.pop(str(item).lower())
            while value in self._list:
                self._list.remove(item)
            return value

    def __getitem__(self, item) -> T:
        if type(item) is int:
            # member by index
            return self._list[item]
        else:
            # member by key, ...or even pattern search
            return self._dict[str(item).lower()]

    def __setitem__(self, item, value) -> T:
        if type(item) is int:
            # member by index
            raise TypeError("Setting only supported for not int datatypes.")
        else:
            # member by key
            key = str(item).lower()
            if key in self._dict:
                self._dict[key] = value
            else:
                self._dict[key] = value
                self._list.append(value)

    def __delitem__(self, item):
        if type(item) is T:
            while item in self._list:
                self._list.remove(item)
            del self._dict[str(item).lower()]
        elif type(item) is int:
            value = self._list[item]
            self._list.remove(value)
            for k, v in self._dict.copy():
                if v == value:
                    del self._dict[k]
        else:
            the_item = self._dict[str(item).lower()]
            while the_item in self._list:
                self._list.remove(the_item)
            del self._dict[str(item).lower()]

    def __iter__(self) -> T:
        for item in self._list:
            yield item

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
        Appends an item or an Iterable of items to the HybridDict[T].
        :param item: The HybridDict[T] to be appended.
        :return: The HybridDict[T].
        """
        if item is Iterable:
            for i in item:
                self._list.append(i)
                self._dict[str(i)] = i
        else:
            self._list.append(item)
            self._dict[str(item)] = item
        return self

    def remove(self, item: T) -> HybridDict[T]:
        """
        Removes an item from the HybridDict[T].
        :param item: The HybridDict[T] to be removed.
        :return: The HybridDict[T].
        """
        self.__delitem__(item)
        return self

    def clone(self) -> HybridDict[T]:
        """
        Creates a 1:1 copy of the HybridDict[T]. The items and source will not get cloned, but re-referenced.
        :return:
        """
        return HybridDict[T](items=self._list, source=self.source)

    def clear(self) -> HybridDict[T]:
        """
        Clears the contents of the HybridDict[T].
        :return: The HybridDict[T] itself
        """
        self._list = list[T]()
        self._dict = dict[str, T]()
        return self

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

    def sort(self, reverse: bool = True) -> HybridDict[T]:
        """Returns a sorted version of the HybridDict[T].
        :param reverse: Flag to trigger reserve oder sorting.
        :return: The extracted member list.
        """
        return HybridDict[T](source=self._source, items= self._list.copy().sort(key=str, reverse=reverse))

    def select(self, *args) -> HybridDict[T]:
        """Select certain items from HybridDict[T]. The result will not contain doublets.
        :param args: Single 'keys', 'int:indexes' or 'T' objects or lists of such (being of type 'Iterable')
            that represent members or pattern to select members.
        :return: The extracted member list.
        """
        members = []
        for arg in args:
            if type(arg) is Iterable:
                for a in arg:
                    members.extend(self.select(arg))
            elif type(arg) is T:
                if arg in self._list:
                    members.append(self._dict[str(arg)])
            elif type(arg) is int:
                members.append(self._list[arg])
            else:
                arg = str(arg)
                if any((c in '*?[]') for c in arg):
                    members.extend(self.filter(arg))
                else:
                    members.extend([m for m in self._list if str(m) == arg])

        distinct = list(set(members))
        return HybridDict[T](items=[self._dict[name] for name in distinct], source=self._source)

    def contains(self, item) -> bool:
        """Checks whether a specific item (or item name) is contained in the HybridDict[T]."""
        if type(item) is T:
            return item in self._list
        else:
            key = str(item).lower()
            return key in self._dict

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

    def match(self, regular_expression_string: str) -> HybridDict[T]:
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
    def names(self) -> tuple[str]:
        """Returns the keys of the HybridDict[T]."""
        return tuple([str(value) for value in self._dict.values()])

    @property
    def items(self) -> tuple[T]:
        """Returns the items of the HybridDict[T]."""
        t: tuple[T] = tuple(self._list)
        return t


