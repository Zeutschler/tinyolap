import math
import unittest
from unittest import TestCase

from samples.tiny import create_tiny_database
from tinyolap.exceptions import TinyOlapInvalidAddressError


class TestCell(TestCase):

    def setUp(self) -> None:
        self.db = create_tiny_database()
        self.cube = self.db.cubes["sales"]

    def test_initialization(self):
        c = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        with self.assertRaises(Exception) as context:
            c = self.cube.cell("2022", "Jan")
        self.assertEqual(type(TinyOlapInvalidAddressError()), type(context.exception))

    def test_cell_manipulation(self):
        a = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        b = self.cube.cell("2022", "Feb", "North", "trucks", "Sales")
        a.value = 2.0
        b.value = 123.0

        c = a.alter("Feb")  # c now point the same cell idx_address for "Feb" as b. They do the same thing.
        self.assertEqual(b, c)

        # IMPORTANT: 'c' still points to the "Feb" cell idx_address.
        # Using slicers is just temporary shift of the cell idx_address.
        c["Mar"] = 333.0
        c["months:Mar"] = 333.0  # save method to not stumble over duplicate member names in different dimensions
        c["1:Mar"] = 333.0       # an even saver method, 0 ... [dims-1] use this if cubes contain 1 dimension multiple times.
        value = c["Mar"]
        self.assertEqual(c, b)   # still, c will return 123.0

        # Member object
        april = c.member("Apr")
        c[april] = 42
        c["2023", april] = 333.0
        jan = april.first  # first() returns 'Jan', as 'Jan' is the first member in the dim.
        c[april] = 42
        self.assertEqual("months", april.dimension.name)   # still, c will return 123.0
        self.assertEqual("Apr", str(april))   # still, c will return 123.0
        self.assertEqual("Apr", april.name)   # still, c will return 123.0
        self.assertEqual("months:Apr", april.qualified_name)   # still, c will return 123.0
        self.assertEqual(42.0, c[april])
        self.assertEqual(a.value, c["Jan"])

        c.value = 987.0  # sets a new value to "Feb", so b will show the same result,
        self.assertEqual(c, b)

    def test_value(self):
        c = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        temp = c.value
        c.value = True
        self.assertEqual(True, c.value)
        c.value = 1.0
        self.assertEqual(1.0, c.value)
        c.value = "Hello World"
        self.assertEqual("Hello World", c.value)
        c.value = temp
        self.assertEqual(temp, c.value)

    def test_numeric_value(self):
        c = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        c.value = 13.0
        self.assertEqual(13.0, c)

    def test_overloaded_operators(self):
        c_a = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        c_b = self.cube.cell("2022", "Feb", "North", "trucks", "Sales")
        c_a.value = 2.0
        c_b.value = 3.0
        f = c_b.value

        # float and cell (et vice versa)
        self.assertEqual(2.0, c_a)
        self.assertEqual(3.0, f)
        r = c_a + f
        self.assertEqual(5.0, r)
        r = f + c_a
        self.assertEqual(5.0, r)
        r = c_a - f
        self.assertEqual(-1.0, r)
        r = f - c_a
        self.assertEqual(1.0, r)
        r = f * c_a
        self.assertEqual(6.0, r)
        r = c_a * f
        self.assertEqual(6.0, r)
        # todo: to be continued for all overloaded operators

        # cell and cell
        self.assertEqual(2.0, c_a)
        self.assertEqual(3.0, c_b)
        r = c_a + c_b
        self.assertEqual(5.0, r)
        r = c_b + c_a
        self.assertEqual(5.0, r)
        r = c_a - c_b
        self.assertEqual(-1.0, r)
        r = c_b - c_a
        self.assertEqual(1.0, r)
        r = c_b * c_a
        self.assertEqual(6.0, r)
        r = c_a * c_b
        self.assertEqual(6.0, r)
        # todo: to be continued for all overloaded operators

    def test_math_operation(self):
        c = self.cube.cell("2022", "Jan", "North", "trucks", "Sales")
        c.value = 2.0
        f = 2.0

        # test various math operations
        self.assertEqual(math.sin(f), math.sin(c))
        self.assertEqual(math.atan2(f, c), math.atan2(c, f))
        self.assertEqual(math.floor(f), math.floor(c))
        self.assertEqual(math.log10(f), math.log10(c))
        # todo: to be continued for all overloaded operators


if __name__ == '__main__':
    unittest.main()
