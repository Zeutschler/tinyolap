import math
import unittest
from unittest import TestCase

from samples.tiny import create_tiny_database
from history import History
from tinyolap.exceptions import InvalidCellOrAreaAddressException


class TestHistory(TestCase):

    def setUp(self) -> None:
        self.db = create_tiny_database()
        self.cube = self.db.cubes["sales"]

    @unittest.skip("Feature not yet implemented.")
    def test_history_initialization(self):

        tm = self.db.history

        address = ("2023", "Jan", "North", "trucks", "Sales")
        tm.append_cube_set("sales", address, None, 1.0)
        tm.append_cube_set("sales", address, 1.0, 2.0)

        address = ("2023", "Feb", "North", "trucks", "Sales")
        tm.append_cube_set("sales", address, None, 1.0)

        address = ("2023", "Mar", "North", "trucks", "Sales")
        tm.append_cube_set("sales", address, None, 1.0)

        tm.undo(1)

        tm.undo(2)
