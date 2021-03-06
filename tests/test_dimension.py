from unittest import TestCase
from tinyolap.database import Database
from tinyolap.exceptions import *


class TestDimension(TestCase):
    """Consistency Test for Dimension."""
    pass

    def setUp(self) -> None:
        self.db = Database("dim_test", in_memory=True)

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_duplicate_dimension(self):
        dim = self.db.add_dimension("doublet")
        with self.assertRaises(TinyOlapDuplicateKeyError):
            self.db.add_dimension("doublet")
        self.db.dimension_remove("doublet")

    def test_member_naming_conventions(self):
        dim = self.db.add_dimension("naming")

        valid_names = ["we", "are", "all", "valid", "address", "123","ððð➜₥ℌ℉≥∭♖☀︎☀⚽︎︎"]
        invalid_names = ["no \t tabs", "no \n new lines", "no \r carriage return"]

        dim.edit()
        for name in valid_names:
            dim.add_many(name)

        for name in invalid_names:
            with self.assertRaises(KeyError):
                dim.add_many(name)
        dim.commit()

        for name in valid_names:
            self.assertTrue(dim.member_exists(name))

        dim.clear()
        self.db.dimension_remove("naming")

    def test_circular_member_hierarchy(self):
        dim = self.db.add_dimension("non_circular").edit()
        dim.add_many("All", ["A", "B", "C"])
        dim.commit()
        self.db.dimension_remove("non_circular")

        dim = self.db.add_dimension("circular").edit()
        dim.add_many("All", ["A", "B", "C"])
        dim.add_many("A", ["A1", "A2", "A3"])
        with self.assertRaises(BaseException):
            dim.add_many("A1", ["All"])
        dim.commit()
        self.db.dimension_remove("circular")

    def test_children_and_parents(self):
        dim = self.db.add_dimension("children_and_parents").edit()
        dim.add_many("All", ["A", "B", "C"])
        dim.add_many("A", ["A1", "A2", "A3"])
        dim.add_many("A1", ["A1.1", "A1.1", "A1.1"])
        dim.commit()

        member = dim.member("A")
        self.assertEqual(member.children.first.name, "A1")
        self.assertEqual(member.parents.first.name, "All")


        self.db.dimension_remove("children_and_parents")

    def test_flat_dimension(self):
        members = [f"member_{i:03d}" for i in range(100)]
        parents = []
        root_members = members
        dim = self.db.add_dimension("flat_dimension").edit()
        for member in members:
            dim.add_many(member)
        dim.commit()
        self.execute_dimension_test(dim, members, parents, root_members)

    def test_hierarchical_dimension(self):
        members = [f"member_{i:03d}" for i in range(16)]
        parents = [f"parent_{i:03d}" for i in range(4)]
        root_members = ["total"]
        dim = self.db.add_dimension("SomeDimension").edit()
        for member in members:
            dim.add_many(member=member, description=f"Description for {member}")
        for index, member in enumerate(members):
            parent = f"parent_{(index % 4):03d}"
            dim.add_many(parent, member, description=f"Description for {parent}")
        for parent in parents:
            dim.add_many(root_members[0], parent, description=f"Description for {root_members[0]}")
        parents = parents
        dim.commit()
        self.execute_dimension_test(dim, members, parents, root_members)

    def execute_dimension_test(self, dim, members, parents, root_members):
        all_members = set(members).union(set(parents).union(set(root_members)))
        self.assertEqual(len(dim), len(all_members))
        self.assertEqual(len(dim.get_members()), len(all_members))
        self.assertEqual(len(dim.get_leaves()), len(members))
        if dim.get_top_level() > 0:
            self.assertEqual(len(dim.get_aggregated_members()), len(parents) + len(root_members))
        self.assertEqual(len(dim.get_root_members()), len(root_members))
        self.assertEqual(len(dim.get_members_by_level(0)), len(members))
        self.assertEqual(len(dim.get_members_by_level(1)), len(parents))
        if dim.get_top_level() > 1:
            self.assertEqual(len(dim.get_members_by_level(2)), len(root_members))
        for member in members:
            self.assertTrue(dim.member_exists(member))
        for member in parents:
            self.assertTrue(dim.member_exists(member))
        for member in root_members:
            self.assertTrue(dim.member_exists(member))

        self.assertFalse(dim.member_exists("Peter Parker"))
        dim.rename_member(members[0], "Peter Parker")
        self.assertFalse(dim.member_exists(members[0]))
        self.assertTrue(dim.member_exists("Peter Parker"))
        if parents:
            dim.rename_member(parents[0], "Louise Lane")
            self.assertFalse(dim.member_exists(parents[0]))
            self.assertTrue(dim.member_exists("Louise Lane"))
        dim.clear()
        self.assertEqual(len(dim), 0)

