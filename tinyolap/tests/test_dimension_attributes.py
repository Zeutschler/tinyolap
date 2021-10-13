import datetime
from unittest import TestCase
from tinyolap.dimension import Dimension
from tinyolap.database import Database
from tinyolap.custom_errors import *


class TestDimensionAttributes(TestCase):
    """Testing Attributed for Dimensions."""
    pass

    def setUp(self) -> None:
        self.db = Database("attribute_test", in_memory=True)
        self.dim = self.db.add_dimension("attributes").edit()
        self.dim.add_member("All", ["A", "B", "C"])
        self.dim.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_attribute_creation(self):
        dim = self.dim

        dim.add_attribute("name", str)
        dim.add_attribute("desc", str)
        dim.add_attribute("bool", bool)
        dim.add_attribute("anything")
        dim.add_attribute("date", datetime.date)
        dim.add_attribute("datetime", datetime.datetime)
        dim.add_attribute("123", int)

        with self.assertRaises(InvalidKeyError):
            self.db.add_dimension("no spaces please")
        with self.assertRaises(InvalidKeyError):
            self.db.add_dimension(" no_spaces_please ")
        with self.assertRaises(InvalidKeyError):
            self.db.add_dimension("%&(&%§?````?)")

        self.assertTrue(dim.has_attribute("name"))
        self.assertTrue(dim.has_attribute("NaMe"))
        self.assertTrue(dim.has_attribute("desc"))
        self.assertFalse(dim.has_attribute("unavailable_attribute"))

        dim.remove_attribute("desc")
        self.assertFalse(dim.has_attribute("desc"))
        dim.add_attribute("desc", str)
        self.assertTrue(dim.has_attribute("desc"))

        dim.set_attribute("name", "A", "John")
        dim.set_attribute("name", "B", "Paul")
        dim.set_attribute("name", "C", "Mary")
        dim.set_attribute("name", "A", "Peter")
        self.assertEqual("Peter", dim.get_attribute("name", "A"))
        self.assertEqual("Paul", dim.get_attribute("name", "B"))

        dim.del_attribute_value("name", "B")
        self.assertEqual(None, dim.get_attribute("name", "B"))
        dim.set_attribute("name", "B", "Paul")
        self.assertEqual("Paul", dim.get_attribute("name", "B"))

        dim.remove_attribute("name")
        dim.add_attribute("name", str)

        self.assertNotEqual("Peter", dim.get_attribute("name", "A"))
        self.assertNotEqual("Paul", dim.get_attribute("name", "B"))
        self.assertEqual(None, dim.get_attribute("name", "A"))
        self.assertEqual(None, dim.get_attribute("name", "B"))

        dim.set_attribute("name", "A", "John")
        dim.set_attribute("name", "B", "Paul")
        dim.set_attribute("name", "C", "Mary")
        all_pauls = dim.get_members_by_attribute("name", "Paul")
        self.assertEqual("B", all_pauls[0])
        self.assertEqual(1, len(all_pauls))

        dim.set_attribute("name", "C", "Paul")
        all_pauls = dim.get_members_by_attribute("name", "Paul")
        self.assertTrue("B" in all_pauls)
        self.assertTrue("C" in all_pauls)
        self.assertFalse("A" in all_pauls)
        self.assertEqual(2, len(all_pauls))

        # This second call should access cache
        all_pauls = dim.get_members_by_attribute("name", "Paul")

        # This should delete the cache for member queries for paul.
        all_pauls = dim.set_attribute("name", "C", "Paul")
