import itertools
from unittest import TestCase
from tinyolap.database import Database


class TestDatabaseOperations(TestCase):

    def setUp(self) -> None:
        self.db_name = "test_database_member_removal"
        self.db: Database

    def tearDown(self) -> None:
        self.db.close()
        self.db.delete()

    def test_database_member_removal_and_add_again(self):
        name1 = "foo"
        members1 = ["a", "b", "c"]
        name2 = "bar"
        members2 = ["x", "y", "z"]
        total_member = "total"
        cube_name = "cube"

        # setup database
        db = Database(self.db_name, in_memory=True)
        self.db = db
        dim1 = db.add_dimension(name1).edit()
        dim1.add_member(total_member, members1)
        dim1.commit()
        dim2 = db.add_dimension(name2).edit()
        dim2.add_member(total_member, members2)
        dim2.commit()
        cube = db.add_cube(cube_name, [dim1, dim2])

        # fill database entirely 3 * 3 = 9 values
        for address in list(itertools.product(members1, members2)):
            cube[address[0], address[1]] = 1.0

        # validate cube values
        self.assertEqual(9.0, cube[total_member, total_member])
        for address in list(itertools.product(members1, members2)):
            self.assertEqual(1.0, cube[address[0], address[1]])
        for member in members1:
            self.assertEqual(3.0, cube[member, total_member])
        for member in members2:
            self.assertEqual(3.0, cube[total_member, member])

        # remove member_defs
        dim1.edit()
        dim1.remove_member("b")
        dim1.commit()

        members1.remove("b")

        # validate cube values
        self.assertEqual(6.0, cube[total_member, total_member])
        for address in list(itertools.product(members1, members2)):
            self.assertEqual(1.0, cube[address[0], address[1]])
        for member in members1:
            self.assertEqual(3.0, cube[member, total_member])
        for member in members2:
            self.assertEqual(2.0, cube[total_member, member])

        # remove member_defs
        dim1.edit()
        dim1.add_member(total_member, "b")
        dim1.commit()
        members1.append("b")

        # re-fill database entirely 1 * 3 = 9 values
        for member in members2:
            cube["b", member] = 1.0

        # validate cube values
        self.assertEqual(9.0, cube[total_member, total_member])
        for address in list(itertools.product(members1, members2)):
            self.assertEqual(1.0, cube[address[0], address[1]])
        for member in members1:
            self.assertEqual(3.0, cube[member, total_member])
        for member in members2:
            self.assertEqual(3.0, cube[total_member, member])
