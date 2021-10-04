# -*- coding: utf-8 -*-
# Copyright (c) Thomas Zeutschler (Germany).
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
   Dimensions contain a flat or hierarchical list of :ref:`members <members>`.
   Dimensions are used to define the axis of a multi-dimensional :ref:`cube <cubes>`.
"""

import os
from tinyolap.database import Database
from tinyolap.slice import Slice

class Tutor:
    """lorem ipsum"""
    pass

def load():
    """
    Loads the **Tutor** data model from TXT source files (this may take
    a seconds or two). The source TXT files have an awkward and quite
    old format (latin-1 encoded), as they are from a time where XML or
    JSON not have been invented.

    The code in this ``load()`` function is a nice example how to import
    and build a tinyolap database from TXT or CSV files.

    Please review the ``play(database: Database)`` function in this
    module to see how to access data from the **Tutor** database and
    also create a slice. A slice is kind of a very simple report
    format for console output.

    :return: The **Tutor** sample data model as a tinyolap in-memory
    only Database object.
    """

    # 0. setup some meta data needed to setup a tinyolap data model and
    # to import data
    db_name = "tutor_files"
    cube_name = "verkauf"
    measures = ("value", "count")
    dimension_names = ["jahre", "datenart", "regionen", "produkte", "monate", "wertart"]
    dim_count = len(dimension_names)
    root_path = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

    # 1. setup a new tinyolap database
    db = Database(db_name, in_memory=True)

    # 2. create dimensions from the following 6 dimension files:
    # JAHRE.TXT, DATENART.TXT, REGIONEN.TXT, PRODUKTE.TXT,
    # MONATE.TXT, WERTART.TXT
    dimensions = []
    for dim in dimension_names:
        file_name = os.path.join(root_path, "samples", "tutor_files", dim.upper() + ".TXT")
        # add a new dimension to the database
        dim = db.add_dimension(dim)
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

    # 4. Now it's time to import the data into the cube
    file_name = os.path.join(root_path, "samples", "tutor_files", cube_name.upper() + ".TXT")
    empty_rows = 0
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

    # That's it...
    return db


def play(database: Database = load(), console_output: bool = True):
    """ Demonstrates the usage TinyOlap and the Tutor database.
    It create and print some simple reports to the console.

    Either hand in an existing instance of the Tutor database generate
    by the ``load()`` function, or let the ``play()`` function do this
    for you. Please be aware that ±9MB of text files need to be processed,
    so it may take a seconds or two before you see a report.

    :param console_output: Set to ``False``to suppress console output.
    :param database: The tutor_files database generate with the ``load()`` function.
    """
    # 1. get the cube
    cube = database.cubes["verkauf"]
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
    report_definition = {"header": [{"dimension": "datenart", "member": "Ist"},
                                    {"dimension": "regionen", "member": "USA"},
                                    {"dimension": "produkte", "member": "Produkte gesamt"},
                                    {"dimension": "wertart", "member": "Umsatz"}],
                         "columns": [{"dimension": "jahre"}],
                         "rows":    [{"dimension": "monate"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    # You can even skip certain dimensions of the cube.
    # For these, the default member will be selected and
    # they will be automatically added to the header.
    # In addition, dimensions in rows and columns can be nested.
    report_definition = {"columns": [{"dimension": "wertart"}],
                         "rows":    [{"dimension": "jahre"}, {"dimension": "monate"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)


def main():
    play()


if __name__ == "__main__":
    main()
