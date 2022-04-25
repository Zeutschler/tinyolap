from unittest import TestCase
import os
from pathlib import Path
import time

from samples.enterprise import create_database
from slice import Slice
from tinyolap.database import Database
from tinyolap.cube import Cube
from tinyolap.view import View, ViewAxis, ViewCell, ViewAxisPosition
from tinyolap.dimension import Dimension
from random import randrange


class TestView(TestCase):

    def setUp(self):
        # delete database if exists
        self.database = create_database(num_legal_entities=10, num_products=10, num_employees=50, console_output=False)

    def test_create_view(self, console_output: bool = False):
        db = self.database
        db.caching = False
        cube = db.cubes[0]
        view = View(cube)
        cube.reset_counters()

        start = time.time()
        view.refresh()
        duration = time.time() - start
        print(f"\nView with {len(view.row_axis):,} rows x {len(view.column_axis):,} columns, in total {len(view):,} cells refreshed in {duration:.3} sec, "
              f"{int(len(view) / duration):,} cells/sec. ")
        print(f"\taggregation := {cube.counter_aggregations:,}, {int(cube.counter_aggregations / duration):,} agg/sec. ")

        print(view.as_console_output())
        print(f"size of json to send to client: {len(view.to_json()):,} bytes")
        print(view.to_json())


