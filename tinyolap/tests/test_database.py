from unittest import TestCase
from tinyolap.database import Database

class Test(TestCase):

    def setUp(self) -> None:
        self.db = Database("dim_test")
        self.db_im = Database("dim_test_im", in_memory=True)
        self.db_name = "dimtest"

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_database(self):
        # self.fail()
        pass

    def test_Database_create_and_delete(self):

        dim_name = "years"
        member_name = ["1999", "2000", "2001"]
        remove_member_name = "2000"

        # create and close database
        db = Database(self.db_name)
        dim = db.add_dimension(dim_name)
        dim.edit()
        dim.add_member(member_name)
        dim.commit()
        file_path = db.file_path
        db.close()

        # check if file exists
        self.assertEqual(Path(file_path).exists(), True, "Database file exists.")

        # reopen the database
        db = Database(self.db_name)
        self.assertEqual(True, db.dimension_exists(dim_name), f"Dimension '{dim_name}' exists.")
        self.assertEqual(True, db.dimensions[dim_name].member_exists(member_name[0]),
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