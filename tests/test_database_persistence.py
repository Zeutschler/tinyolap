from unittest import TestCase
from tinyolap.database import Database
from pathlib import Path


class TestDatabasePersistence(TestCase):

    def setUp(self) -> None:
        self.db_name = "test_database_persistence"
        self.db = Database(self.db_name, in_memory=False)

    def tearDown(self) -> None:
        if self.db:
            self.db.close()
            self.db.delete()

    def test_Database_create(self):

        dim_name1 = "foo"
        members1 = ["a", "b", "c"]
        dim_name2 = "bar"
        members2 = ["a", "b", "c"]
        remove_member_name = "b"
        cube = "cube"

        # create database
        db = self.db  # Database(self.db_name)
        if not db.dimension_exists(dim_name1):
            dim1 = db.add_dimension(dim_name1).edit()
            dim1.add_member(members1)
            dim1.commit()
        if not db.dimension_exists(dim_name2):
            dim2 = db.add_dimension(dim_name2).edit()
            dim2.add_member(members2)
            dim2.commit()
        # close database
        file_path = db.file_path
        db.close()
        # check if file exists
        self.assertTrue(Path(file_path).exists(), "Database file exists.")

        # (re)open the database
        db = Database(self.db_name, in_memory=False)
        self.assertEqual(True, db.dimension_exists(dim_name1), f"Dimension '{dim_name1}' exists.")
        self.assertEqual(True, db.dimension_exists(dim_name2), f"Dimension '{dim_name2}' exists.")
        self.assertEqual(True, len(db.dimensions) == 2, f"Dimension '{dim_name2}' exists.")
        self.assertEqual(True, db.dimensions[dim_name1].member_exists(members1[0]),
                         f"Dimension '{dim_name1}' contains member '{members1[0]}'.")

        # remove members
        dim = db.dimensions[dim_name1]
        dim.edit()
        dim.remove_member(remove_member_name)
        dim.commit()
        self.assertEqual(len(members1) - 1, len(dim.members),
                         f"Dimension '{dim_name1}' contains {len(members1) - 1} members.")
        self.assertEqual(True, db.dimensions[dim_name1].member_exists(members1[0]),
                         f"Dimension '{dim_name1}' contains member '{members1[0]}'.")
        self.assertNotEqual(True, db.dimensions[dim_name1].member_exists(remove_member_name),
                            f"Dimension '{dim_name1}' does not contain member '{remove_member_name}'.")

        # remove dimension
        db.dimension_remove(dim_name1)
        db.dimension_remove(dim_name2)
        self.assertEqual(len(db.dimensions), 0, "Database contains 0 dimension.")

        # finally delete database
        file_path = db.file_path
        db.close()
        db.delete()
        # ensure the file does not exists anymore
        self.assertEqual(Path(file_path).exists(), False, "Database has been successfully removed.")