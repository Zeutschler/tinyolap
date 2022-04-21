from unittest import TestCase

from dimension import Dimension
from tinyolap.database import Database
from tinyolap.exceptions import *


class TestDimensionSubsets(TestCase):
    """Consistency Test for Dimension."""
    pass

    def setUp(self) -> None:
        self.db = Database("test", in_memory=True)

        # setup a dimension
        self.members = ["A", "B", "C", "D", "E", "F"]
        self.dim = self.db.add_dimension("test")\
            .edit().add_member("All", self.members).commit()

        self.other_dim = self.db.add_dimension("other")\
            .edit().add_member("All", ["A", "B", "C"]).commit()

        # create some attributes
        self.names = ["Alfred", "Axel", "Bert", "Cesar", "Dorin", "Ella", "Fred"]
        atts = self.dim.attributes
        names = atts.add("name")
        for m, a in zip(self.members, self.names):
            names[m] = a
        values = atts.add("value")
        for m, a in zip(self.members, range(len(self.members))):
            values[m] = a
        married = atts.add("married")
        for m, a in zip(self.members, [True, False, True, False, True, False, False]):
            married[m] = a


    def callable_function(self, dimension: Dimension, subset):
        return dimension.members


    def test_add_subset(self):
        dim = self.dim
        other_dim = self.other_dim

        a = dim.members["a"]
        b = dim.members["B"]

        a_other = other_dim.members["A"]

        # create some static subsets
        abc = dim.subsets.add_static_subset(name="abc", members=["A", "B", "C"])
        cde = dim.subsets.add_static_subset(name="cde", members=["C", "D", "E"])
        abc_by_member = dim.subsets.add_static_subset(name="abc-member", members=[a, b, "c"])
        with self.assertRaises(Exception):
            abx = dim.subsets.add_static_subset(
                name="abx", members=["A", "B", "X"])  # 'X' does not exist
        with self.assertRaises(Exception):
            abx_by_member = dim.subsets.add_static_subset(
                name="abx", members=[a_other, b, "c"])  # 'a_other' from different dimension

        # create function based subset
        callable = dim.subsets.add_custom_subset("callable", self.callable_function, True)

        # create attribute based subset
        married = dim.subsets.add_attribute_subset("married", "married", True)
        married_gt_3 = dim.subsets.add_attribute_subset("married-gt3", "married", True, "value", lambda v: v > 3)

        test = callable.members
        test = married.members
        test = married_gt_3.members


        # Evaluate the subsets
