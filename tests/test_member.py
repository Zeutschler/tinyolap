import unittest
from unittest import TestCase

from tinyolap.database import Database


class TestMember(TestCase):

    def setUp(self) -> None:
        self.db = Database("attribute_test", in_memory=True)
        dim = self.db.add_dimension("member_defs").edit()
        dim.add_member("All", ["A", "B", "C"])
        dim.add_member("A", ["A1", "A2", "A3"])
        dim.add_member("A1", ["A1.1", "A1.2", "A1.3"])
        dim.add_member("BC", ["B", "C"])
        dim.commit()
        self.dim = dim

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_children_parents_leaves_and_roots(self):

        all = self.dim.member("All")
        a = self.dim.member("A")
        a1 = self.dim.member("A1")
        c = self.dim.member("C")
        self.assertEqual(a.children.first, a1)
        self.assertEqual(a.children.first.name, "A1")

        self.assertEqual(a.parents.first, all)
        self.assertEqual(a.parents.first.name, "All")

        # expected content of leaves := [A1.1, A1.2, A1.3, A2, A3]
        self.assertEqual(a.leaves.first.name, "A1.1")
        self.assertEqual(a.leaves[1].name, "A1.2")
        self.assertEqual(a.leaves.last.name, "A3")
        self.assertEqual(len(a.leaves), 5)

        # expected content of roots := [All, BC]
        self.assertEqual(c.roots.first.name, "All")
        self.assertEqual(c.roots[1].name, "BC")
        self.assertEqual(len(c.roots), 2)

    def test_next_and_previous(self):
        all = self.dim.member("All")
        a = self.dim.member("A")
        b = self.dim.member("B")
        c = self.dim.member("C")

        # test next
        self.assertTrue(all.has_next)
        self.assertEqual("A", str(all.next))

        self.assertTrue(a.has_next)
        self.assertEqual("B", str(a.next))

        self.assertTrue(b.has_next)
        self.assertEqual("C", str(b.next))

        # test previous
        self.assertTrue(a.has_previous)
        self.assertEqual("All", str(a.previous))

        self.assertTrue(b.has_previous)
        self.assertEqual("A", str(b.previous))

        self.assertTrue(c.has_previous)
        self.assertEqual("B", str(c.previous))

        self.assertFalse(all.has_previous)
        with self.assertRaises(Exception):
            x = all.previous

    @unittest.skip("Various tests not yet implemented. Keep writing tests Bro... ;-)")
    def test_various_tests_missing(self):
        self.fail("Various tests on object Member missing. Keep writing tests Bro... ;-)")
