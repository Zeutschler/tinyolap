from unittest import TestCase
from tinyolap.database import Database


class TestDimensionSubsets(TestCase):
    """Testing Attributed for Dimensions."""
    pass

    def setUp(self) -> None:
        self.db = Database("attribute_test", in_memory=True)
        self.dim = self.db.add_dimension("attributes").edit()
        self.dim.add_many("All", ["A", "B", "C"])
        self.dim.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_subset_creation(self):
        dim = self.dim

        dim.subsets.add("subset", ("A", "B"))
        self.assertTrue("subset" in dim.subsets)
        self.assertTrue("SuBsEt" in dim.subsets)
        self.assertFalse("  subset  " in dim.subsets)
        self.assertFalse("non_existing_subset" in dim.subsets)

        self.assertTrue("A" in dim.subsets["subset"])
        self.assertTrue("B" in dim.subsets["subset"])
        self.assertFalse("C" in dim.subsets["subset"])

        self.assertEqual(("A", "B"), tuple(dim.subsets["subset"].members.names))

        self.assertEqual(1, dim.subsets_count())

        with self.assertRaises(BaseException):
            dim.add_subset("this is an invalid name", ("A", "B"))
        with self.assertRaises(BaseException):
            dim.add_subset("subset", ("A", "B"))
        with self.assertRaises(TypeError):
            dim.add_subset("invalid_name_but_wrong_type_of_members", "A")

        dim.subsets.remove("subset")
        self.assertEqual(0, dim.subsets_count())
        self.assertFalse(dim.has_subset("subset"))

        # add again
        dim.subsets.add("subset", ("A", "B"))
        self.assertTrue(dim.has_subset("subset"))
        self.assertEqual(("A", "B"), tuple(dim.get_subset("subset")))
        self.assertEqual(1, dim.subsets_count())
        # clean up
        dim.subsets.remove("subset")


    def test_subset_change_by_member_removal(self):
        dim = self.dim

        dim.add_subset("subset", ("A", "B", "C"))

        dim.edit()
        dim.remove_member("B")
        dim.commit()

        self.assertTrue(dim.has_subset("subset"))
        self.assertTrue(dim.subset_contains("subset", "A"))
        self.assertTrue(dim.subset_contains("subset", "C"))
        self.assertFalse(dim.subset_contains("subset", "B"))
        self.assertEqual(("A", "C"), tuple(dim.get_subset("subset")))

        # clean up
        dim.remove_subset("subset")



