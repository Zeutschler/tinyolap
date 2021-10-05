from __future__ import annotations
from typing import SupportsFloat
# noinspection PyProtectedMember

from custom_exceptions import *


class Cursor(SupportsFloat):
    """
    A Cursor is a pointer to a cell that can be adapted for easy navigation through data space,
    and for simplified cells access and mathematical operations of cells. Cursor implements most
    methods implemented for class float.

    .. information::
        Cursors are also used for the internal rules engine of TinyOlap. They are perfect for being
        handed in to function and methods, as shown in the code fragment below.

        .. code:: python

            from tinyolap.database import Database
            from tinyolap.cursor import Cursor

            # setup a new database
            database = Database("foo")
            cursor = Cursor(Database.cubes["bar"])
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
        # self._numeric_value = 0.0
        # self._value = None
        self._cube = None
        self._dim_names = None
        self._address = None
        self._bolt = None
        pass

    def __new__(cls):
        return SupportsFloat.__new__(cls)

    #endregion

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

    # region Cursor Manipulation
    def alter(self, *args) -> Cursor:
        # valid and set arguments
        new_address = list(self._address)
        super_level, idx_address, idx_measure = self._bolt
        idx_address = list(idx_address)
        level = self._cube._dimensions[0].LEVEL
        dimensions = self._cube._dimensions
        for arg in args:
            if not isinstance(arg, (list, tuple)):
                raise InvalidKeyException(f"Tuple ([dimension:str], [member:str] expected but '{str(arg)}' found.")
            dim_name= arg[0]
            member_name = arg[1]

            if dim_name not in self._dim_names:
                raise InvalidCellAddressException(f"'{dim_name}'is not a dimension of cube '{self._cube.name}.")
            idx_dim = self._dim_names[dim_name]
            if member_name not in dimensions[idx_dim].member_idx_lookup:
                raise InvalidCellAddressException(f"'{dim_name}'is not a dimension of cube '{self._cube.name}.")

            idx_member = dimensions[idx_dim].member_idx_lookup[member_name]

            # adjust the old super level
            super_level -= dimensions[idx_dim].members[idx_address[idx_dim]][level]
            super_level += dimensions[idx_dim].members[idx_member][level]

            idx_address[idx_dim] = idx_member
            new_address[idx_dim] = member_name

        new_bolt = (super_level, tuple(idx_address), idx_measure)
        return Cursor.create(self._cube, self._dim_names, new_address, new_bolt)


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
