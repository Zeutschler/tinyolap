from unittest import TestCase
from tinyolap.database import Database
from tinyolap.exceptions import *


class TestDimensionAttributes(TestCase):
    """Consistency Test for Dimension."""
    pass

    def setUp(self) -> None:
        self.db = Database("test", in_memory=True)
        self.dim = self.db.add_dimension("test").edit().add_many("All", ["A", "B", "C"]).commit()


    def test_add_and_set_attributes(self):
        dim = self.dim
        att = dim.attributes

        # write string attributes
        att.add("name", str)
        att["name"]["All"] = "Alfred"
        att["name"]["A"] = "Axel"
        att["name"]["B"] = "Bert"
        att["name"]["C"] = "Cesar"
        with self.assertRaises(Exception):
            att["name"]["C"] = True
        with self.assertRaises(Exception):
            att["name"]["C"] = 123.456

        father = att.add("father", str)
        father["All"] = "John"
        father["A"] = "John"

        # write int attributes
        age = att.add("age", int)
        age["A"] = 34
        age["B"] = 45
        age["C"] = 19
        with self.assertRaises(Exception):
            age["C"] = True
        with self.assertRaises(Exception):
            age["C"] = 123.456
        with self.assertRaises(Exception):
            age["C"] = "TinyOlap"

        # read attributes
        self.assertEqual("Alfred", dim.attributes["name"]["All"])
        self.assertEqual("Cesar", dim.attributes["name"]["C"])

        self.assertEqual(None, dim.attributes["age"]["All"])
        self.assertEqual(34, dim.attributes["age"]["A"])

        self.assertEqual("John", father["All"])
        self.assertEqual("John", father["A"])
        self.assertEqual(None, father["B"])

        # filter attributes
        members = list(age.filter(34))
        self.assertEqual(["A"], members)

        members = list(att["name"].filter("A*"))
        self.assertEqual(["All", "A"], members)

        # match attributes (regex)
        members = list(att["name"].match("A.f"))
        self.assertEqual(["All",], members)
