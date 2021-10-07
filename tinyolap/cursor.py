from __future__ import annotations

from collections import Iterable
from typing import SupportsFloat
# noinspection PyProtectedMember

from custom_exceptions import *
from tinyolap.member import Member


class Cursor(SupportsFloat):
    """
    A Cursor is a pointer to a cell in a cube. Cursors can used for navigation through data space.
    In addition they can be used in mathematical calculations as they (almost) behave as a 'float' value.

    .. information::
        Cursors are also used for the internal rules engine of TinyOlap. They are perfect for being
        handed in to function and methods, as shown in the code fragment below.

        .. code:: python

            from tinyolap.database import Database
            from tinyolap.cursor import Cursor

            # setup a new database
            cursor = cube.create_cursor()
            value = cursor.value
            address = cursor.address  # returns a list e.g. ["member of dim1", "member of dim2" ...]
            cursor.move("dim1", move.NEXT)  # move.NEXT
    """

    # region Initialization
    @classmethod
    def create(cls, cube, dim_names, address, bolt):
        cursor = Cursor()
        cursor._cube = cube
        cursor._dim_names = dim_names
        cursor._address = address
        cursor._bolt = bolt
        return cursor

    def __init__(self):
        self._cube = None
        self._dim_names = None
        self._address = None
        self._bolt = None
        pass

    def __new__(cls):
        return SupportsFloat.__new__(cls)

    # endregion

    # region Properties
    @property
    def value(self):
        """Reads the value of the current cursor address from the underlying cube."""
        return self._cube._get(self._bolt)

    @value.setter
    def value(self, value):
        """Writes a value of the current cursor address to the underlying cube."""
        self._cube._set(self._bolt, value)

    @property
    def numeric_value(self) -> float:
        """Reads the numeric value of the current cursor address from the underlying cube."""
        value = self._cube._get(self._bolt)
        if isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            return float(value)
        else:
            return 0.0

    # endregion

    # region Cursor manipulation
    # region Cursor manipulation via indexing/slicing
    def __getitem__(self, item):
        return self._cube._get(self.__item_to_bold(item))

    def __setitem__(self, item, value):
        self._cube._set(self.__item_to_bold(item), value)

    def __delitem__(self, item):
        self.__setitem__(item, None)

    def __item_to_bold(self, item):
        """Setting a value through indexing/slicing will temporarily modify the cell address and return
        the value from that cell address. This does NOT modify the cell address of a Cursor object.
        To modify the cell address of a Cursor, you can call the ``.alter(...)`` method."""

        modifiers = []
        if type(item) is str or not isinstance(item, Iterable):
            item = (item,)

        key_level = 6  # LEVEL
        super_level, idx_address, idx_measure = self._bolt
        idx_address = list(idx_address)

        for member in item:
            if type(member) is Member:
                super_level -= self._cube._dimensions[member._idx_dim].members[self._bolt[1][member._idx_dim]][key_level]
                super_level += member._member_level
                modifiers.append((member._idx_dim, member._idx_member))

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(member)
                super_level -= self._cube._dimensions[idx_dim].members[self._bolt[1][idx_dim]][key_level]
                super_level += member_level

                modifiers.append((idx_dim, idx_member))
            else:
                raise TypeError(f"Invalid type '{type(member)}'. Only type 'str' and 'Member are supported.")

        # Finally modify the address and set the value
        for modifier in modifiers:
            idx_address[modifier[0]] = modifier[1]
        bolt = (super_level, tuple(idx_address), idx_measure)
        return bolt

    def _get_member(self, member_name: str):
        # The hard way! We need to evaluate where the member is coming from
        # Convention: member names come in one of the following formats:
        #   c["Mar"] = 333.0
        #   c["months:Mar"] = 333.0
        #   c["1:Mar"] = 333.0
        level = self._cube._dimensions[0].LEVEL
        dimensions = self._cube._dimensions
        idx_dim = -1
        pos = member_name.find(":")
        if pos != -1:
            # lets extract the dimension name and check if it is valid, e.g., c["months:Mar"]
            dim_name = member_name[:pos].strip()

            # special test for ordinal dim position instead of dim name, e.g., c["1:Mar"] = 333.0
            if dim_name.isdigit():
                ordinal = int(dim_name)
                if ordinal >= 0 and ordinal < len(self._dim_names):
                    # that's a valid dimension position number
                    idx_dim = ordinal
            if idx_dim == -1:
                if dim_name not in self._cube._dim_lookup:
                    raise InvalidCellAddressException(f"Invalid member key. '{dim_name}' is not a dimension "
                                                      f"in cube '{self._cube.name}. Found in '{member_name}'.")
                idx_dim = self._cube._dim_lookup[dim_name]

            # adjust the member name
            member_name = member_name[pos + 1:].strip()
            if member_name not in dimensions[idx_dim].member_idx_lookup:
                raise InvalidCellAddressException(f"Invalid member key. '{member_name}'is not a member of "
                                                  f"dimension '{dim_name}' in cube '{self._cube.name}.")
            idx_member = dimensions[idx_dim].member_idx_lookup[member_name]

            member_level = dimensions[idx_dim].members[idx_member][self._cube._dimensions[0].LEVEL]
            return idx_dim, idx_member, member_level

        # No dimension identifier in member name, search all dimensions
        for idx, dim in enumerate(dimensions):
            if member_name in dim.member_idx_lookup:
                idx_dim = idx
                idx_member = dim.member_idx_lookup[member_name]
                # adjust the super_level
                member_level = dimensions[idx_dim].members[idx_member][level]
                return idx_dim, idx_member, member_level

        if idx_dim == -1:
            raise InvalidCellAddressException(f"'{member_name}'is not a member of "
                                              f"any dimension in cube '{self._cube.name}.")

    # endregion

    def alter(self, *args) -> Cursor:

        modifiers = []

        key_level = 6  # LEVEL
        key_name = 1   # NAME
        super_level, idx_address, idx_measure = self._bolt
        idx_address = list(idx_address)
        address = list(self._address)

        for member in args:
            if type(member) is Member:
                # The easy way! The Member object should be properly initialized already.
                raise NotImplementedError("Working on that...")

            elif type(member) is str:
                idx_dim, idx_member, member_level = self._get_member(member)
                address[idx_dim] = self._cube._dimensions[idx_dim].members[idx_member][key_name]

                # adjust the super_level
                super_level -= self._cube._dimensions[idx_dim].members[self._bolt[1][idx_dim]][key_level]
                super_level += member_level

                modifiers.append((idx_dim, idx_member))
            else:
                raise TypeError(f"Invalid type '{type(member)}'. Only type 'str' and 'Member are supported.")

        for modifier in modifiers:
            idx_address[modifier[0]] = modifier[1]
        bolt = (super_level, tuple(idx_address), idx_measure)
        return Cursor.create(self._cube, self._dim_names, address, bolt)

    def create_member(self, member_name: str) -> Member:
        """
        Create a new Member object from the Cursor's context.
        :param member_name: Name of the member. Supported formats (samples):
            c["Mar"] = 333.0  # member name only
            c["months:Mar"] = 333.0  # dimension name and member name separated by ':'
            c["1:Mar"] = 333.0  # ordinal position of the dimension with the cube and member name
        :return: Member object.
        """
        idx_dim, idx_member, member_level = self._get_member(member_name)
        member = Member(self._cube._dimensions[idx_dim], member_name, self._cube, idx_dim, idx_member, member_level)
        return member

    # region Operator Overloading and float behaviour
    def __float__(self) -> float:  # type conversion to float
        return self.numeric_value

    def __index__(self) -> int:  # type conversion to int
        return int(self.numeric_value)

    # https://docs.python.org/3/reference/datamodel.html
    def __neg__(self):  # + operator
        return - self.numeric_value

    def __pos__(self):  # += operator
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

    # region conversion function
    def __abs__(self):
        return self.numeric_value.__abs__()

    def __bool__(self):
        return self.numeric_value.__bool__()

    def __str__(self):
        return self.numeric_value.__str__()

    def __int__(self):
        return self.numeric_value.__int__()

    def __ceil__(self):
        return self.numeric_value.__ceil__()
