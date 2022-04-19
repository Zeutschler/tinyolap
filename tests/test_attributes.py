from unittest import TestCase
from tinyolap.database import Database
from tinyolap.exceptions import *


class TestDimensionAttributes(TestCase):
    """Consistency Test for Dimension."""
    pass

    def setUp(self) -> None:
        self.db = Database("test", in_memory=True)
        self.dim = self.db.add_dimension("test").edit().add_member("All", ["A", "B", "C"]).commit()

    def test_add_and_set_attributes(self):
        dim = self.dim

        att = dim.attributes
        att.add("name", str)
        att["name"]["A"] = "Axel"
        att["name"]["B"] = "Bert"
        att["name"]["C"] = "Cesar"

        age = att.add("age", int)
        age["A"] = 34
        age["B"] = 45
        age["C"] = 19

        father = att.add("father", str)
        father["All"] = "John"
        father["A"] = "John"

