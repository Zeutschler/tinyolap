from unittest import TestCase
from tinyolap.dimension import Dimension
from tinyolap.database import Database
from tinyolap.custom_exceptions import *

class TestDimension(TestCase):
    """Consistency Test for Dimension."""
    pass

    def setUp(self) -> None:
        self.db = Database("dim_test", in_memory=True)

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_dimension_naming_conventions(self):
        valid_keys = ["we", "are", "all", "valid", "keys", "123"]
        invalid_keys = ["WE", "_are", "  all", "in valid", "&", "/", "!","§","$", "%", "(", "and many others..."]
        for k in valid_keys:
            self.assertNotEqual(None, self.db.add_dimension(k))
        for k in invalid_keys:
            self.assertRaises(InvalidKeyException, self.db.add_dimension(k))

    def test_duplicate_dimension(self):
        dim = self.db.add_dimension("doublet")
        self.assertRaises(DuplicateKeyException, self.db.add_dimension("doublet"))

    def test_member_naming_conventions(self):
        # todo: Implement test
        self.assertTrue(False, msg="test not implemented")

    def test_circular_member_hierarchy(self):
        # todo: Implement test
        self.assertTrue(False, msg="test not implemented")

    def test_too_deep_member_hierarchy(self):
        # todo: Implement test
        self.assertTrue(False, msg="test not implemented")

    def test_consistency_on_add_remove_add_member(self):
        # todo: Implement test
        self.assertTrue(False, msg="test not implemented")

    def test_attribute_table(self):
        # todo: Implement test
        self.assertTrue(False, msg="test not implemented")



    def test_flat_dimension(self):
        members = [f"member_{i:03d}" for i in range(100)]
        parents = []
        root_members = members
        dim = self.db.add_dimension("flat_dimension").edit()
        for member in members:
            dim.add_member(member)
        self.execute_dimension_test(dim, members, parents, root_members)
        dim.commit()

    def test_hierarchical_dimension(self):
        members = [f"member_{i:03d}" for i in range(100)]
        parents = [f"parent_{i:03d}" for i in range(10)]
        root_members = ["total"]
        dim = self.db.add_dimension("SomeDimension")
        for index, member in enumerate(members):
            parent = f"parent_{(index % 10):03d}"
            dim.add_member(member, parent, f"Description for {member}")
        for parent in parents:
            dim.add_member(parent, root_members[0], f"Description for {parent}")
        parents = parents + root_members

        self.execute_dimension_test(dim, members, parents, root_members)

    def execute_dimension_test(self, dim, members, parents, root_members):
        self.assertEqual(len(dim), len(members) + len(parents))
        self.assertEqual(len(dim.get_members()), len(members) + len(parents))
        self.assertEqual(len(dim.get_leave_members()), len(members))
        self.assertEqual(len(dim.get_aggregated_members()), len(parents))
        self.assertEqual(len(dim.get_root_members()), len(root_members))
        self.assertEqual(len(dim.get_members_by_level(0)), len(members))
        for member in members:
            self.assertTrue(dim.member_exists(member))
        for parent in parents:
            self.assertTrue(dim.member_exists(parent))

        self.assertFalse(dim.member_exists("Peter Parker"))
        dim.member_rename(members[0], "Peter Parker")
        self.assertFalse(dim.member_exists(members[0]))
        self.assertTrue(dim.member_exists("Peter Parker"))
        if parents:
            dim.member_rename(parents[0], "Louise Lane")
            self.assertFalse(dim.member_exists(parents[0]))
            self.assertTrue(dim.member_exists("Louise Lane"))

        dim.clear()
        self.assertEqual(len(dim), 0)

