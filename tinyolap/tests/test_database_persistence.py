from unittest import TestCase
from tinyolap.database import Database
from pathlib import Path
import time


class TestDatabasePersistence(TestCase):

    def setUp(self) -> None:
        self.db_name = "test_database_persistence"
        self.db = Database(self.db_name, in_memory=False)

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_Database_create(self):

        dim_name1 = "foo"
        members1 = ["a", "b", "c"]
        dim_name2 = "bar"
        members2 = ["a", "b", "c"]
        cube = "cube"

        # create database
        db = Database(self.db_name)
        dim1 = db.add_dimension(dim_name1).edit()
        dim1.add_member(members1)
        dim1.commit()
        dim2 = db.add_dimension(dim_name2).edit()
        dim2.add_member(members2)
        dim2.commit()
        # close database
        file_path = db.file_path
        db.close()
        # check if file exists
        self.assertEqual(Path(file_path).exists(), True, "Database file exists.")

        # (re)open the database
        db = Database(self.db_name)
        self.assertEqual(True, db.dimension_exists(dim_name1), f"Dimension '{dim_name1}' exists.")
        self.assertEqual(True, db.dimension_exists(dim_name2), f"Dimension '{dim_name2}' exists.")
        self.assertEqual(True, db.dimension_count, f"Dimension '{dim_name2}' exists.")
        self.assertEqual(True, db.dimensions[dim_name].member_exists(members[0]),
                         f"Dimension '{dim_name}' contains member '{member_name[0]}'.")

        # remove members
        dim = db.dimensions[dim_name]
        dim.edit()
        dim.member_remove(remove_member_name)
        dim.commit()
        self.assertEqual(len(member_name) - 1, len(dim.members),
                         f"Dimension '{dim_name}' contains {len(member_name) - 1} members.")
        self.assertEqual(True, db.dimensions[dim_name].member_exists(member_name[0]),
                         f"Dimension '{dim_name}' contains member '{member_name[0]}'.")
        self.assertNotEqual(True, db.dimensions[dim_name].member_exists(remove_member_name),
                            f"Dimension '{dim_name}' does not contain member '{remove_member_name}'.")

        # remove dimension
        db.dimension_remove(dim_name)
        self.assertEqual(len(db.dimensions), 0, "Database contains 0 dimension.")

        # delete database
        file_path = db.file_path
        db.close()
        db.delete()
        # ensure the file does not exists anymore
        self.assertEqual(Path(file_path).exists(), False, "Database has been successfully removed.")