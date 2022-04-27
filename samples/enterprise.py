# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# *****************************************************************************
# TinyOlap sample database - Enterprise
# A real world data model with real world data volume for financial planning
# and reporting for a large & international enterprise.
# *****************************************************************************
import math
import time

from art import *
from samples.enterprise_model.model import create_database
from tinyolap.slice import Slice
from tinyolap.database import Database
from view import View


def play_enterprise(console_output=True):
    if console_output:
        tprint("TinyOlap", font="Slant")

    # The following 'create_database' call wraps a best practice approach
    # to create real world & complex data models. Just follow the code to explore...
    #    1. Have a dedicated module (or class) to create and/or alter your data model
    #    2. Have a dedicated module for data import, export, maintenance and (quality) testing.
    #    3. Put additional master data into separate files (xlsx, csv, txt, json...)
    #    4. Have at least one dedicated module for your business logic. For very complex
    #       data models, you can have multiple files to separate different domains of business logic,
    #       e.g. separate 'profit and loss calculations and KPIs' from 'HR logic'.
    db: Database = create_database(name="TinyCorp", database_directory=None, num_legal_entities=25, num_products=100,
                                   num_employees=200, console_output=console_output)

    if console_output:
        products = db.dimensions["products"]
        sales = db.cubes["sales"]

        report_definition = {"title": "A highly aggregated sales report",
                             "columns": [{"dimension": "periods",
                                          "member": ["Jan", "Feb", "Mar", "Q1", "Q2", "Q3", "Q4", "Year"]}],
                             "rows": [{"dimension": "products",
                                       "member": [products.get_root_members()[0], ] +
                                                  products.member_get_children(products.get_root_members()[0])}]}
        start = time.time()
        sales.reset_counters()
        report = Slice(sales, report_definition)
        print(report)
        duration = time.time() - start
        print(f"Execution in {duration:.4} sec, {sales.counter_cell_requests:,}x cells, "
              f"{sales.counter_aggregations:,}x aggregations, {sales.counter_rule_requests:,}x rules")


def benchmark_view(loops: int = 100, console_output: bool = True):
    db: Database = create_database(name="TinyCorp", database_directory=None, num_legal_entities=25, num_products=100,
                                   num_employees=200, console_output=console_output)
    db.caching = True
    cube = db.cubes["sales"]
    cube.reset_counters()
    start = time.time()
    aggregations = 0
    cells = 0
    rules = 0
    view = None
    for l in range(loops):
        view = View(cube, use_first_root_members_for_filters=True, random_view=True)
        view.refresh()
        stat = view.statistics
        aggregations += stat.executed_cell_aggregations
        cells += stat.cells_count
        rules += stat.executed_rules
    duration = time.time() - start
    print(f"\nReading {loops:,}x times a view with on avg. {int(round(cells / loops,0))} cells "
          f"from cube '{cube.name}' "
          f"in {duration:.6} sec, "
          f"\n\t∑ {cells:,} cells, "
          f"∑ {aggregations:,} aggregations, "
          f"∑ {rules:,} rules, "
          f"∑ {loops:,} views, "
          f"∑ {cube.counter_cache_hits:,} cache hits ({round(cube.counter_cache_hits/cells,2):.0%}) "
          f"\n\t{round(duration/loops,6):.6} sec/view, "
          f"{round(loops / duration, 0):,} views/sec, "
          f"{round(cells / duration, 0):,} cells/sec, "
          f"{round(aggregations / duration, 0):,} agg./sec ")

    # print(view.as_console_output())

if __name__ == "__main__":
    # Playtime!!! ʕ•́ᴥ•̀ʔっ
    # play_enterprise()
    benchmark_view(loops=100)
