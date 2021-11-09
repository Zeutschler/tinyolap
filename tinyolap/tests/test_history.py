import math
import unittest
from unittest import TestCase

from samples.tiny import load_tiny
from history import History
from tinyolap.custom_errors import InvalidCellAddressException


class TestHistory(TestCase):

    def setUp(self) -> None:
        self.db = load_tiny()
        self.cube = self.db.cubes["sales"]

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
