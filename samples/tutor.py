# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# *****************************************************************************
# TinyOlap sample database - 'Tutor'
# A legacy OLAP samaple database, shipped with MIS Alea (now Infor BI OLAP)
# in the last century. In german language, but quite easy to understand.
# *****************************************************************************

import os
import time
import psutil
from art import *

from tinyolap.cell import Cell
from tinyolap.decorators import rule
from tinyolap.rules import RuleScope
from tinyolap.database import Database
from tinyolap.slice import Slice

FILES_FOLDER = "tutor_model"

def load_tutor(console_output: bool = False):
    """
    Loads the **Tutor** data model from TXT source files (this may take
    a seconds or two). The source TXT files have an awkward and quite
    old number_format (latin-1 encoded), as they are from a time where XML or
    JSON not have been invented.

    The code in this ``load()`` function is a nice example how to import
    and build a tinyolap database from TXT or CSV files.

    Please review the ``play(database: Database)`` function in this
    module to see how to access data from the **Tutor** database and
    also create a slice. A slice is kind of a very simple report
    number_format for console output.

    :return: The **Tutor** sample data model as a tinyolap in-memory
    only Database object.
    """

    if console_output:
        print("Creating the 'tutor' data model.")
        print("Importing Tutor database from CSV file (1,000 records per dot). Please wait...")

    start = time.time()
    initially_used_memory = psutil.Process().memory_info().rss / (1024 * 1024)

    # 0. setup some meta data needed to setup a tinyolap data model and
    # to import data
    db_name = "tutor"
    cube_name = "verkauf"
    measures = ("value", "count")
    dimension_names = ["jahre", "datenart", "regionen", "produkte", "monate", "wertart"]
    dim_count = len(dimension_names)
    root_path = os.path.dirname(os.path.abspath(__file__))

    # 1. setup a new tinyolap database
    db = Database(db_name, in_memory=True)

    # 2. create dimensions from the following 6 dimension files:
    # JAHRE.TXT, DATENART.TXT, REGIONEN.TXT, PRODUKTE.TXT, MONATE.TXT, WERTART.TXT
    dimensions = []
    for dim_name in dimension_names:
        file_name = os.path.join(root_path, FILES_FOLDER, dim_name.upper() + ".TXT")
        # add a new dimension to the database
        dim = db.add_dimension(dim_name)
        # open the dimension for editing (adding or removing members)
        dim.edit()

        # Now let's read from the dimension the awkward abd old
        # txt files and add the members. As the structure of these
        # files does not match to what tinyolap natively supports
        # for importing dimensions,the code looks quite complex
        # and ugly.
        empty_rows = 0
        parent = ""
        with open(file_name, encoding='latin-1') as file:
            while line := [t.strip() for t in file.readline().rstrip().split("\t")]:
                if len(line) == 1:
                    empty_rows += 1
                    if empty_rows > 5:
                        break
                    continue

                level = line[0]
                member = line[1]
                if len(line) > 2:
                    weight = float(line[2])
                else:
                    weight = 1.0

                if level.upper() == "C":
                    dim.add_member(member)
                    parent = member
                elif level.upper() == "N":
                    dim.add_member(member)
                else:
                    dim.add_member(parent, member)

        # when we're done, we need to commit the changes we did on the dimension.
        dim.commit()
        dimensions.append(dim)

    # 3. create cube
    cube = db.add_cube(cube_name, dimensions, measures)

    # 4. Add rules
    cube.register_rule(rule_delta)
    cube.register_rule(rule_profit_contribution)
    cube.register_rule(rule_price)

    # 4. Now it's time to import the data from a CSV file into the cube
    file_name = os.path.join(root_path, FILES_FOLDER, cube_name.upper() + ".TXT")
    empty_rows = 0
    r = 0
    with open(file_name, encoding='latin-1') as file:
        while line := [t.strip() for t in file.readline().rstrip().split("\t")]:
            if len(line) == 1:
                empty_rows += 1
                if empty_rows > 5:
                    break
                continue
            address = tuple(line[: dim_count])
            value = float(line[dim_count])
            # write a value to the database
            cube.set(address, value)

            r = r + 1
            if r > 0 and console_output and r % 1_000 == 0:
                print(".", end="")
                if console_output and r % 10_000 == 0:
                    print(f" {r / 135_443:.0%} ", end="")


    # Some statistics...
    duration = time.time() - start
    if console_output:
        print()
        memory_consumption = round(psutil.Process().memory_info().rss / (1024 * 1024) - initially_used_memory, 0)
        print(f"Info: Importing Tutor database from CSV in {duration:.3} sec.")
        print(f"Info: Memory consumption of Tutor database containing {cube.cells_count:,} values "
              f"is ±{memory_consumption:,} MB, "
              f"±{round(memory_consumption / cube.cells_count * 1000, 2)} kB per value.\n")

    # That's it...
    duration = time.time()
    db.export(db.name + "_export", True)
    if console_output:
        print(f"export database in {time.time() - duration:.3} sec")
    return db


@rule("verkauf", ["Abweichung"])
def rule_delta(c: Cell):
    return c["Ist"] - c["Plan"]


@rule("verkauf", ["DB1"], scope=RuleScope.ALL_LEVELS, volatile=False)
def rule_profit_contribution(c: Cell):
    return c["Umsatz"] - c["variable Kosten"]


@rule("verkauf", ["Preis"], scope=RuleScope.AGGREGATION_LEVEL)
def rule_price(c: Cell):
    umsatz = c["Umsatz"]
    menge = c["Menge"]
    if menge != 0.0:
        return umsatz / menge
    else:
        return "-"


def play_tutor(console_output: bool = True):
    """ Demonstrates the usage TinyOlap and the Tutor database.
    It create and print some simple reports to the console.

    Either hand in an existing instance of the Tutor database generate
    by the ``load()`` function, or let the ``play()`` function do this
    for you. Please be aware that ±9MB of text files need to be processed,
    so it may take a seconds or two before you see a report.

    :param console_output: Set to ``False``to suppress console output.
    :param database: The Tutor database generate with the ``load()`` function.
    """

    if console_output:
        tprint("TinyOlap",font="Slant")

    database: Database = load_tutor(console_output)


    # 1. get the cube
    cube = database.cubes["verkauf"]
    if console_output:
        print(f"Fact table rows of 'verkauf' := {cube.cells_count}")
        print(f"Index size of cube 'verkauf' := {cube._facts.index.get_size()}")
        print(f"Index count of cube 'verkauf' := {cube._facts.index.get_count()}")

    # Caching - to experience the raw speed of the database,
    # we'll switch it off. For real world use cases, caching
    # greatly improves performance and therefore is on (True)
    # by default.
    cube.caching = False

    # 2. Let's read some cells.
    # Just define the member you want to get data from for each
    # of the cubes dimension and your done.
    # The first cell request is a 'base level cell', it returns a
    # single value that is actually stored in the database.
    value = cube["1993", "Ist", "USA", "ProView VGA 12", "Januar", "Umsatz"]
    if console_output:
        print(f"verkauf:[('1993, 'Ist', 'USA', 'ProView VGA 12', 'Januar', 'Umsatz')] := {value}")

    # The next 3 cell requests are addressing 'aggregated cells'.
    # They aggregate multiple 'base level cells', the first request
    # alone about ±90,000 base level cells on-the-fly. TinyOlap
    # does not utilize any pre-aggregations, but uses simple caching
    # to return aggregated values more efficiently.
    value = cube["1993", "Ist", "Welt gesamt", "Produkte gesamt", "Januar", "Umsatz"]
    value = cube["1993", "Ist", "Welt Gesamt", "Produkte gesamt", "Jahr gesamt", "Umsatz"]
    value = cube["Alle Jahre", "Abweichung", "Welt gesamt", "Produkte gesamt", "Jahr gesamt", "DB1"]

    # 3. Write back goes like this...
    # Please be aware that you - by default - can only write to
    # base level cells, as aggregated cells are not stored in
    # the database and will be calculated on-the-fly.
    cube["1993", "Ist", "USA", "ProView VGA 12", "Januar", "Umsatz"] = value + 1.0

    # 4. Finally, let's create and print some simple reports
    # using slices.
    # Slices are plain Python dictionaries and describe the row
    # and columns layout of a slice through a cube. In addition
    # you can define filters that needs to be put in the header.
    # ``member`` can be single member or a list of members.
    # If you skip the ``member`` definition, then the default member
    # of the dimension will be selected and used.
    report_definition = {"title": "Report with rules calculations",
                         "header": [{"dimension": "jahre", "member": "1994"},
                                    {"dimension": "regionen", "member": "Welt Gesamt"},
                                    {"dimension": "produkte", "member": "Produkte gesamt"},
                                    {"dimension": "monate", "member": "Jahr Gesamt"}],
                         "columns": [{"dimension": "datenart"}],
                         "rows": [{"dimension": "wertart"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    report_definition = {"title": "Report - Sales by years and months",
                         "header": [{"dimension": "datenart", "member": "Ist"},
                                    {"dimension": "regionen", "member": "Welt Gesamt"},
                                    {"dimension": "produkte", "member": "Produkte gesamt"},
                                    {"dimension": "wertart", "member": "Umsatz"}],
                         "columns": [{"dimension": "jahre"}],
                         "rows": [{"dimension": "monate"}]}
    cube.reset_counters()
    cube.caching = True
    start = time.time()
    report = Slice(cube, report_definition)
    if console_output:
        duration = time.time() - start
        cells = report.grid_rows_count * report.grid_cols_count
        print(report)
        # print(report)
        print(f"\nReport with {report.grid_rows_count:,} rows x {report.grid_cols_count:,} columns ="
              f" {cells:,} cells executed in {duration:.3} sec. "
              f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
              f"thereof {cube.counter_cell_requests - cells:,} by rules."
              f"\n\t{cube.counter_rule_requests:,} rules executed"
              f"\n\t{cube._aggregation_counter:,} cell aggregations calculated")


def main():
    play_tutor()


if __name__ == "__main__":
    main()
