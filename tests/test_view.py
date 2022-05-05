import json
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
        view = View(cube, name="sample report")
        cube.reset_counters()

        start = time.time()
        view.refresh()
        duration = time.time() - start
        if console_output:
            print(f"\nView with {len(view.row_axis):,} rows x {len(view.column_axis):,} columns, in total {len(view):,} cells refreshed in {duration:.3} sec, "
                  f"{int(len(view) / duration):,} cells/sec. ")
            print(f"\taggregation := {cube.counter_aggregations:,}, {int(cube.counter_aggregations / duration):,} agg/sec. ")

            print(view.to_console_output())
            print(f"size of json to send to client: {len(view.to_json()):,} bytes")
            # print(view.to_json())
            # print(json.dumps(view.definition, indent=2))

        # Get the view definition from the view and create a new view from the definition,
        # the output should be identical for both views.
        view_from_def = View(cube, name="should be identical to sample report",
                             definition=view.definition).refresh()
        if console_output:
            print(view_from_def.to_console_output())
        # due to random command this does not work anymore:
        #     self.assertEqual(len(view_from_def.to_console_output()), len(view.to_console_output()))
        #     self.assertEqual(view_from_def.to_console_output(), view.to_console_output())

        # Test various of report variations
        definitions = [self.view_with_dim_names_only(),
                       self.view_with_dim_names_as_string_only(),
                       self.view_with_cols_only(),
                       self.view_with_rows_only(),
                       {},    # view without rows and columns
                       None,  # default report
                       self.view_with_nested_rows(),
                       self.view_with_nested_cols(),
                       self.view_with_nested_rows_and_cols(),
                       ]
        for d in definitions:
            view = View(cube=cube, definition=d).refresh()
            if console_output:
                print(view.to_console_output())

        # WARNING: ...the following test will run over 30 seconds.
        # view = View(cube=cube, definition=self.view_with_no_filters()).refresh()
        # print(view.as_console_output())

    def test_random_view_loop(self, console_output: bool = True):
        db = self.database
        cube = db.cubes[0]
        loops = 10
        cells = 0
        aggs = 0

        start = time.time()
        for l in range(loops):
            view = View(cube=cube, definition=None, random_view=True).refresh()
            cells += view.statistics.executed_cell_requests
            aggs += view.statistics.executed_cell_aggregations
            output = view.to_dict()
        duration = time.time() - start
        if console_output:
            print(f"\n{loops:,}x views with in total {cells:,}x cells and {aggs:,}x aggregations processed in {duration:.3} sec, "
                  f"{int(loops / duration):,} views/sec. ",
                  f"{int(cells / duration):,} cells/sec. ",
                  f"{int(aggs / duration):,} aggregations/sec. ",
                  )


    def view_with_no_filters(self):
        return {
                "title": "nested rows",
                "rows": {"dimensions": ["periods", "companies"]},
                "columns": {"dimensions": ["pnl", "years", "datatype"]}
                }

    def view_with_nested_rows_and_cols(self):
        return {
                "title": "nested rows",
                "filters": {"dimensions": ["pnl"]},
                "rows": {"dimensions": ["periods", "companies"]},
                "columns": {"dimensions": ["years", "datatype"]}
                }

    def view_with_nested_rows(self):
        return {
                "title": "nested rows",
                "filters": {"dimensions": ["pnl", "companies"]},
                "rows": {"dimensions": ["years", "periods"]},
                "columns": {"dimensions": ["datatype"]}
                }

    def view_with_nested_cols(self):
        return {
                "title": "nested rows",
                "filters": {"dimensions": ["pnl", "companies"]},
                "rows": {"dimensions": ["periods"]},
                "columns": {"dimensions": ["years", "datatype"]}
                }


    def view_with_cols_only(self):
        return {"title": "no rows", "columns": {"dimensions": "pnl"}}

    def view_with_rows_only(self):
        return {"title": "no cols", "rows": {"dimensions": "pnl"}}


    def view_with_missing_dims(self):
        return {
                "cube": "pnl",
                "name": "view_with_dim_missing_dims",
                "title": "view_with_dim_missing_dims",
                "rows": {"dimensions": "periods"},
                "columns": {"dimensions": "pnl"}
                }

    def view_with_dim_names_only(self):
        return {
                "cube": "pnl",
                "name": "view_with_dim_names_only",
                "title": "view_with_dim_names_only",
                "filters": {"dimensions": ["datatype", "years", "periods"]},
                "rows": {"dimensions": ["companies"]},
                "columns": {"dimensions": ["pnl"]}
                }

    def view_with_dim_names_as_string_only(self):
        return {
                "cube": "pnl",
                "name": "view_with_dim_names_as_string_only",
                "title": "view_with_dim_names_as_string_only",
                "filters": {"dimensions": "datatype, years, periods"},
                "rows": {"dimensions": "companies"},
                "columns": {"dimensions": "pnl"}
                }


