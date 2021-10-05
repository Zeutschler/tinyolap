import math
import unittest
from unittest import TestCase

import tiny
from cursor import Cursor
from tinyolap.custom_exceptions import InvalidCellAddressException


class TestCursor(TestCase):

    def setUp(self) -> None:
        self.db = tiny.load()
        self.cube = self.db.cubes["sales"]

    def test_initialization(self):
        c = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
        with self.assertRaises(Exception) as context:
            c = self.cube.create_cursor("2022", "Jan")
        self.assertEqual(type(InvalidCellAddressException()), type(context.exception))

    def test_cursor_manipulation(self):
        a = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
        b = self.cube.create_cursor("2022", "Feb", "North", "trucks", "Sales")
        a.value = 2.0
        b.value = 123.0

        c = a.alter(("months", "Feb"))
        value_c = c


    def test_value(self):
        c = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
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
        c = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
        c.value = 13.0
        self.assertEqual(13.0, c)

    def test_overloaded_operators(self):
        c_a = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
        c_b = self.cube.create_cursor("2022", "Feb", "North", "trucks", "Sales")
        c_a.value = 2.0
        c_b.value = 3.0
        f = c_b.value

        # float and cursor (et vice versa)
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

        # cursor and cursor
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
        c = self.cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")
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
