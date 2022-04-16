# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# *****************************************************************************
# TinyOlap sample database - Enterprise
# A real world data model with real world data volume for financial planning
# and reporting for a large & international enterprise.
# *****************************************************************************
import time

from art import *
from samples.enterprise_model.model import create_database
from tinyolap.slice import Slice
from tinyolap.database import Database


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


if __name__ == "__main__":
    # Playtime!!! ʕ•́ᴥ•̀ʔっ
    play_enterprise()
