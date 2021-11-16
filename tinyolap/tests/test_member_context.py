from unittest import TestCase

from tinyolap.database import Database


class TestMember(TestCase):

    def setUp(self) -> None:
        self.db = Database("attribute_test", in_memory=True)
        self.dim = self.db.add_dimension("attributes").edit()
        self.dim.add_member("All", ["A", "B", "C"])
        self.dim.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_next(self):

        all = self.dim.member_context("All")
        self.assertTrue(all.has_next())
        self.assertEqual("A", str(all.next()))

        a = self.dim.member_context("A")
        self.assertTrue(a.has_next())
        self.assertEqual("B", str(a.next()))

        b = self.dim.member_context("B")
        self.assertTrue(b.has_next())
        self.assertEqual("C", str(b.next()))

        c = self.dim.member_context("C")
        self.assertFalse(c.has_next())
        with self.assertRaises(Exception):
            x = c.next()

    def test_previous(self):

        all = self.dim.member_context("All")
        self.assertFalse(all.has_previous())
        with self.assertRaises(Exception):
            x = all.previous()

        a = self.dim.member_context("A")
        self.assertTrue(a.has_previous())
        self.assertEqual("All", str(a.previous()))

        b = self.dim.member_context("B")
        self.assertTrue(b.has_previous())
        self.assertEqual("A", str(b.previous()))

        c = self.dim.member_context("C")
        self.assertTrue(c.has_previous())
        self.assertEqual("B", str(c.previous()))

    def test_various_tests_missing(self):
        self.fail("Various tests on object MemberContext missing. Keep writing tests Bro... ;-)")
