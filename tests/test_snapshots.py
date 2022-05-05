import math
import unittest
from unittest import TestCase

from samples.tiny import create_tiny_database
from tinyolap.exceptions import TinyOlapInvalidAddressError


class TestSnapshot(TestCase):

    def setUp(self) -> None:
        self.db = create_tiny_database()
        self.cube = self.db.cubes["sales"]

    def test_create_snapshot(self):
        self.db.snapshots.create()


if __name__ == '__main__':
    unittest.main()
