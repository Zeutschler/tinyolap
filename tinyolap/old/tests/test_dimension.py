from unittest import TestCase
from tinyolap.old.dimension import Dimension


class DimensionTest(TestCase):
    pass

    def test_flat_dimension(self):

        members = [f"member_{i:03d}" for i in range(100)]
        parents = []
        root_members = members
        dim = Dimension("SomeDimension")
        dim.edit_begin()
        for member in members:
            dim.member_add(member)
        self.execute_dimension_test(dim, members, parents, root_members)
        dim.edit_commit()

    def test_hierarchical_dimension(self):
        members = [f"member_{i:03d}" for i in range(25)]
        parents = [f"parent_{i:03d}" for i in range(5)]
        root_members = ["total"]
        dim = Dimension("SomeDimension")
        dim.edit_begin()
        for member in members:
            dim.member_add( member, description=f"Description for {member}")
        for index, member in enumerate(members):
            parent = f"parent_{(index % 5):03d}"
            dim.member_add(parent, member, f"Description for {parent}")
        for parent in parents:
            dim.member_add(root_members[0], parent, f"Description for {root_members[0]}")
        parents = parents + root_members
        self.execute_dimension_test(dim, members, parents, root_members)
        dim.edit_commit()

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
