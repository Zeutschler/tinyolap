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

        # in comparision to slice
        self.create_slice(cube)


    def create_slice(self, cube:Cube):
        cube.reset_counters()
        dims = [{"dimension": dim} for dim in cube.dimension_names]
        count = len(dims)
        for d in range(len(dims)):
            members = cube.dimensions[d].members  #  db.dimensions[dims[d]["dimension"]].get_members()
            dims[d]["member"] = members[0].name
        nested_dims_in_rows = 1
        header_dims = dims[: cube.dimensions_count - 1 - nested_dims_in_rows]
        next_dim = len(header_dims)
        col_members_count = len(cube.get_dimension(dims[next_dim]["dimension"]))
        row_members_count = len(cube.get_dimension(dims[next_dim + 1]["dimension"]))
        row_dims = [{"dimension": dims[len(header_dims)]["dimension"]}]
        column_dims = [{"dimension": d["dimension"]} for d in dims[len(header_dims) + 1:]]
        # if (nested_dims_in_rows < 2) and (col_members_count > row_members_count):
        #    column_dims, row_dims = row_dims, column_dims  # put the dim with more member_defs into the rows

        report_def = {"title": f"Random report on cube <strong>{cube.name}</strong> "
                               f"from databse <strong>{cube._database.name}</strong>",
                      "header": header_dims, "columns": column_dims, "rows": row_dims}
        # Execute the report

        start = time.time()
        slice = Slice(cube, report_def)
        duration = time.time() - start

        print(f"\nSlice refreshed in {duration:.3} sec, "
              f"{int(cube.counter_cell_requests / duration):,} cells/sec. ")
        print(f"\taggregation := {cube.counter_aggregations:,}, {int(cube.counter_aggregations / duration):,} agg/sec. ")
        print(slice.as_console_output())
