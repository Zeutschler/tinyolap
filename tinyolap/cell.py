# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
from collections import Iterable
from typing import SupportsFloat

from tinyolap.exceptions import *
from tinyolap.member import Member


# noinspection PyProtectedMember


class Cell(SupportsFloat):
    """
    A Cell is an immutable pointer to a data cell in a cube. Cell objects can
    be used to navigate through data space. In addition, they can be directly
    used in mathematical calculations, as they (almost) behave like a 'float' value.

    .. note::
        Cell objects are also used for the internal rules engine of TinyOlap. They are perfect for being
        handed in to function and methods, as shown in the code fragment below.

        .. code:: python

            from tinyolap.database import Database
            from tinyolap.cell import Cell

            # setup a new database
            cell = cube.create_cell()
            value = cell.value
            idx_address = cell.idx_address  # returns a list e.g. ["member of dim1", "member of dim2" ...]
            cell.move("dim1", move.NEXT)  # move.NEXT
    """

    #: Indicates that either subsequent rules should continue and do the calculation
    #: work or that the cell value, either from a base-level or an aggregated cell,
    #: form the underlying cube should be used.
    CONTINUE = object()
    #: Indicates that rules function was not able return a proper result (why ever).
    NONE = object()
    #: Indicates that the rules functions run into an error. Such errors will be
    #: pushed up to initially calling cell request.
    ERROR = object()

    #: Indicates that the rules functions wants to bypass all rules and get the
    #: underlying base_level or aggregated value from the cube.
    BYPASS_RULES = object()

    # region Initialization
    @classmethod
    def create(cls, cube, names, address, bolt):
        cell = Cell()
        cell._cube = cube
        cell._names = names
        cell._dim_count = len(names)
        cell._address = address
        cell._bolt = bolt
        return cell

    def __init__(self):
        self._cube = None
        self._names = None
        self._address = None
        self._bolt = None
        self._dim_count = -1
        pass

    def __new__(cls):
        return SupportsFloat.__new__(cls)

    # endregion

    # region Properties
    @property
    def value(self):
        """Reads the value of the current cell idx_address from the underlying cube."""
        return self._cube._get(self._bolt)

    @value.setter
    def value(self, value):
        """Writes a value of the current cell idx_address to the underlying cube."""
        self._cube._set(self._bolt, value)

    @property
    def numeric_value(self) -> float:
        """Reads the numeric value of the current cell idx_address from the underlying cube."""
        value = self._cube._get(self._bolt)
        if isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            return float(value)
        else:
            return 0.0

    # endregion

    # region methods
    def alter(self, *args) -> Cell:
        """
        Creates a modified deep copy of a Cell object.

        :param args: One or more modifiers (member names) for at least one dimension of the cube.
            Member names can be in one of the ƒfollowing formats:

               {member} e.g.: clone = c.alter("Mar", ...)
               {cube_name:member} e.g.: clone = c.alter("months:Mar", ...)
               {dimension_index:member} e.g.: clone = c.alter("1:Mar", ...)

            If multiple modifiers for a single dimension are defined, then the last of those will be used.
        :return: A new Cell object.
        """
        modifiers = []

        key_level = 6  # LEVEL
        key_name = 1  # NAME
        # super_level, idx_address, idx_measure = self._bolt
        super_level, idx_address = self._bolt
        idx_address = list(idx_address)
        address = list(self._address)

        for member in args:
            if type(member) is Member:
                # The easy way! The Member object should be properly initialized already.
                raise NotImplementedError("Working on that...")

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(member)
                address[idx_dim] = self._cube._dimensions[idx_dim].member_defs[idx_member][key_name]

                # adjust the super_level
                super_level -= self._cube._dimensions[idx_dim].member_defs[self._bolt[1][idx_dim]][key_level]
                super_level += member_level

                modifiers.append((idx_dim, idx_member))
            else:
                raise TypeError(f"Invalid type '{type(member)}'. Only type 'str' and 'Member are supported.")

        for modifier in modifiers:
            idx_address[modifier[0]] = modifier[1]
        # bolt = (super_level, tuple(idx_address), idx_measure)
        bolt = (super_level, tuple(idx_address))
        return Cell.create(self._cube, self._names, address, bolt)

    def member(self, dimension_and_or_member_name: str) -> Member:
        """
        Create a new Member object from the Cell's current context.
        This can be either the current member of a specific dimension,
        if called with a dimension name, e.g., ``c.member("months")`` .
        Or it can be already a modified member of a dimension, if called
        with a member name, e.g., ``c.member("months:Jul")`` .

        :param dimension_and_or_member_name: Name of the dimension and or member to be returned.

        .. code:: python

            cell = cube.cell("2022", "Jan", "North", "Sales")
            jan = c.member("months")
            jul = c.member("months:Jul")
            jul = c.member("1:Aug")  # 'months' is the second dimension of the cube, so zero-based index is 1.

        :return: A new Member object.
        """
        idx_dim, idx_member, member_level = self._get_member(dimension_and_or_member_name)
        member = Member(self._cube._dimensions[idx_dim], dimension_and_or_member_name, self._cube, idx_dim, idx_member,
                        member_level)
        return member

    # endregion

    # region Cell manipulation via indexing/slicing
    def __getitem__(self, args):
        if not isinstance(args, (str, Member)) and (args[-1] == self.BYPASS_RULES):
            return self._cube._get(self.__item_to_bold(args[:len(args) - 1]), True)
        else:
            value = self._cube._get(self.__item_to_bold(args))
            if value is None:
                return 0.0  # Rules need numeric values
            else:
                return value
            # return self._cube._get(self.__item_to_bold(args))

    def __setitem__(self, args, value):
        self._cube._set(self.__item_to_bold(args), value)

    def __delitem__(self, args):
        self.__setitem__(args, None)
    # endregion

    # region - Dynamic attribute resolving
    def __getattr__(self, name):
        return self.__getitem__(name)

    # def __getattribute__(*args):
    #     print("Class getattribute invoked")
    #     return object.__getattribute__(*args)
    # endregion

    # region Cell manipulation
    def __item_to_bold(self, item):
        """Setting a value through indexing/slicing will temporarily modify the cell idx_address and return
        the value from that cell idx_address. This does NOT modify the cell idx_address of the Cell object.
        To modify the cell idx_address of a Cell, you can call the ``.alter(...)`` method."""

        modifiers = []
        if type(item) is str or not isinstance(item, Iterable):
            item = (item,)

        key_level = 6  # LEVEL
        # super_level, idx_address, idx_measure = self._bolt
        super_level, idx_address = self._bolt
        idx_address = list(idx_address)

        for member in item:
            if type(member) is Member:
                super_level -= self._cube._dimensions[member._idx_dim].member_defs[self._bolt[1][member._idx_dim]][
                    key_level]
                super_level += member._member_level
                modifiers.append((member._idx_dim, member._idx_member))

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(member)
                super_level -= self._cube._dimensions[idx_dim].member_defs[self._bolt[1][idx_dim]][key_level]
                super_level += member_level

                modifiers.append((idx_dim, idx_member))
            else:
                raise TypeError(f"Invalid type '{type(member)}'. Only type 'str' and 'Member are supported.")

        # Finally modify the idx_address and set the value
        for modifier in modifiers:
            idx_address[modifier[0]] = modifier[1]
        # bolt = (super_level, tuple(idx_address), idx_measure)
        bolt = (super_level, tuple(idx_address))
        return bolt

    def _get_member(self, member):
        # The hard way! We need to evaluate where the member is coming from
        # Convention: member names come in one of the following formats:
        #   c["Mar"] = 333.0
        #   c["months:Mar"] = 333.0
        #   c["1:Mar"] = 333.0

        level = self._cube._dimensions[0].LEVEL
        dimensions = self._cube._dimensions
        idx_dim = -1
        pos = member.find(":")
        if pos != -1:
            # lets extract the dimension name and check if it is valid, e.g., c["months:Mar"]
            name = member[:pos].strip()

            # special test for ordinal dim position instead of dim name, e.g., c["1:Mar"] = 333.0
            if name.isdigit():
                ordinal = int(name)
                if 0 <= ordinal < len(self._names):
                    # that's a valid dimension position number
                    idx_dim = ordinal
            if idx_dim == -1:
                if name not in self._cube._dim_lookup:
                    raise TinyOlapInvalidAddressError(f"Invalid member key. '{name}' is not a dimension "
                                                             f"in cube '{self._cube.name}. Found in '{member}'.")
                idx_dim = self._cube._dim_lookup[name]

            # adjust the member name
            member = member[pos + 1:].strip()
            if member not in dimensions[idx_dim]._member_idx_lookup:
                raise TinyOlapInvalidAddressError(f"Invalid member key. '{member}'is not a member of "
                                                         f"dimension '{name}' in cube '{self._cube.name}.")
            idx_member = dimensions[idx_dim]._member_idx_lookup[member]

            member_level = dimensions[idx_dim].member_defs[idx_member][self._cube._dimensions[0].LEVEL]
            return idx_dim, idx_member, member_level

        # No dimension identifier in member name, search all dimensions
        # ...we'll search in reverse order, as we assume that it is more likely,
        #    that inner dimensions are requested through rules.
        for idx_dim in range(self._dim_count - 1, -1, -1):
            if member in dimensions[idx_dim]._member_idx_lookup:
                idx_member = dimensions[idx_dim]._member_idx_lookup[member]
                # adjust the super_level
                member_level = dimensions[idx_dim].member_defs[idx_member][level]
                return idx_dim, idx_member, member_level

        # Still nothing found ? Then it might be just a dimension name or dimension ordinal
        # to reference the current member of that dimension.
        name = member
        # special test for ordinal dim position instead of dim name, e.g., c["1:Mar"] = 333.0
        if type(name) is int or name.isdigit():
            ordinal = int(name)
            if 0 <= ordinal < len(self._names):
                # that's a valid dimension position number
                idx_dim = ordinal
            if idx_dim == -1:
                if name not in self._cube._dim_lookup:
                    raise TinyOlapInvalidAddressError(f"Invalid member key. '{name}' is not a dimension "
                                                             f"in cube '{self._cube.name}. Found in '{member}'.")
                idx_dim = self._cube._dim_lookup[name]

            idx_member = self._bolt[1][idx_dim]
            member_level = dimensions[idx_dim].member_defs[idx_member][level]
            return idx_dim, idx_member, member_level
        else:
            idx_dim = self._cube.get_dimension_ordinal(name)
            if idx_dim > -1:
                idx_member = self._bolt[1][idx_dim]
                member_level = dimensions[idx_dim].member_defs[idx_member][level]
                return idx_dim, idx_member, member_level
                    
        # You loose...
        if idx_dim == -1:
            raise KeyError(f"'{member}' is not a member of any dimension in "
                           f"cube '{self._cube.name}', or a valid reference to any of it's dimensions.")

    # endregion

    # region operator overloading and float behaviour
    def __float__(self) -> float:  # type conversion to float
        return self.numeric_value

    def __index__(self) -> int:  # type conversion to int
        return int(self.numeric_value)

    def __neg__(self):  # - unary operator
        return - self.numeric_value

    def __pos__(self):  # + unary operator
        return self.numeric_value

    def __add__(self, other):  # + operator
        return self.numeric_value + other

    def __iadd__(self, other):  # += operator
        return self.numeric_value + other.numeric_value

    def __radd__(self, other):  # + operator
        return other + self.numeric_value

    def __sub__(self, other):  # - operator
        return self.numeric_value - other

    def __isub__(self, other):  # -= operator
        return self.numeric_value - other

    def __rsub__(self, other):  # - operator
        return other - self.numeric_value

    def __mul__(self, other):  # * operator
        return self.numeric_value * other

    def __imul__(self, other):  # *= operator
        return self.numeric_value * other

    def __rmul__(self, other):  # * operator
        return other * self.numeric_value

    def __floordiv__(self, other):  # // operator (returns an integer)
        return self.numeric_value // other

    def __ifloordiv__(self, other):  # //= operator (returns an integer)
        return self.numeric_value // other

    def __rfloordiv__(self, other):  # // operator (returns an integer)
        return other // self.numeric_value

    def __truediv__(self, other):  # / operator (returns an float)
        return self.numeric_value / other

    def __idiv__(self, other):  # /= operator (returns an float)
        return self.numeric_value / other

    def __rtruediv__(self, other):  # / operator (returns an float)
        return other / self.numeric_value

    def __mod__(self, other):  # % operator (returns a tuple)
        return self.numeric_value % other

    def __imod__(self, other):  # %= operator (returns a tuple)
        return self.numeric_value % other

    def __rmod__(self, other):  # % operator (returns a tuple)
        return other % self.numeric_value

    def __divmod__(self, other):  # div operator (returns a tuple)
        return divmod(self.numeric_value, other)

    def __rdivmod__(self, other):  # div operator (returns a tuple)
        return divmod(other, self.numeric_value)

    def __pow__(self, other, modulo=None):  # ** operator
        return self.numeric_value ** other

    def __ipow__(self, other, modulo=None):  # **= operator
        return self.numeric_value ** other

    def __rpow__(self, other, modulo=None):  # ** operator
        return other ** self.numeric_value

    def __lt__(self, other):  # < (less than) operator
        return self.numeric_value < other

    def __gt__(self, other):  # > (greater than) operator
        return self.numeric_value > other

    def __le__(self, other):  # <= (less than or equal to) operator
        return self.numeric_value <= other

    def __ge__(self, other):  # >= (greater than or equal to) operator
        return self.numeric_value >= other

    def __eq__(self, other):  # == (equal to) operator
        return self.numeric_value == other

    def __and__(self, other):  # and (equal to) operator
        return self.numeric_value and other

    def __iand__(self, other):  # and (equal to) operator
        return self.numeric_value and other

    def __rand__(self, other):  # and (equal to) operator
        return other and self.numeric_value

    def __or__(self, other):  # or (equal to) operator
        return self.numeric_value or other

    def __ior__(self, other):  # or (equal to) operator
        return self.numeric_value or other

    def __ror__(self, other):  # or (equal to) operator
        return other or self.numeric_value

    # endregion

    # region conversion function
    def __abs__(self):
        return self.numeric_value.__abs__()

    def __bool__(self):
        return self.numeric_value.__bool__()

    def __str__(self):
        return self.value.__str__()

    def __int__(self):
        return self.numeric_value.__int__()

    def __ceil__(self):
        return self.numeric_value.__ceil__()
    # endregion
