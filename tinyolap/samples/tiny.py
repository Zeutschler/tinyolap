# -*- coding: utf-8 -*-
# Copyright (c) Thomas Zeutschler (Germany).
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import itertools
import os
from tinyolap.database import Database
from tinyolap.slice import Slice
from random import uniform, randrange


def load():
    """
    Creates a very simple (tiny) database for 'actual sales figures',
    just by code. Although the database is super minimalistic, it
    already explains the key concepts of TinyOlap.

    :return: The **Tiny** sample data model as a tinyolap in-memory
    only Database object.
    """

    # 1. create a new database
    db = Database("tiny", in_memory=True)

    # 2. create some dimensions.
    # Please note, that dimension need to be set into *edit mode* by calling
    # the ``edit()`` method in order to change the dimension, add or remove
    # members. The edit mode must be closed with a call to the ``commit()``
    # method.
    dim_years = db.add_dimension("years")
    dim_years.edit()
    dim_years.add_member("2021")
    dim_years.add_member("2022")
    dim_years.add_member("2023")
    # To add an aggregated member just add it, followed by a list that
    # contains the children that the member should aggregate.
    # The following command would even the only one you would have needed
    # to create the 'years' dimension, as children that do not exist
    # will be automatically added. So, beware of typos.
    dim_years.add_member("All years", ["2021", "2022", "2023"])
    dim_years.commit()

    # You can also add multiples members by using a list or tuple of
    # members. Even further, you can also create parent child
    # relations for a list of members (as shown for Q1 to Q4) by
    # providing a list of lists or tuples for the children.
    dim_months = db.add_dimension("months")
    dim_months.edit()
    dim_months.add_member(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    dim_months.add_member(["Q1", "Q2", "Q3", "Q4"],
                          [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                           ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    dim_months.add_member("Year", ("Q1", "Q2", "Q3", "Q4"))
    dim_months.commit()

    dim_regions = db.add_dimension("regions")
    dim_regions.edit()
    dim_regions.add_member("Total", ("North", "South", "West", "East"))
    dim_regions.commit()

    # You can also create unbalanced hierarchies as show below,
    # where cars are subdivided into car types but trucks and motorcycles
    # are not subdivided.
    # In addition you can assign members to multiple parents as show
    # below with 'core business' which adds up sports cars and motorcycles.
    dim_products = db.add_dimension("products")
    dim_products.edit()
    dim_products.add_member("Total", ["cars", "trucks", "motorcycles"])
    dim_products.add_member("cars", ["coupe", "sedan", "sports", "van"])
    dim_products.add_member("core business", ["sports", "motorcycles"])
    dim_products.commit()

    # Measures
    measures = ["Sales", "Cost", "Profit"]

    # Now we can create our 'sales'*' cube, which is then a 5-dimensional cube.
    cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products], measures)
    cube.add_formula("[Profit] = [Sales] - [Cost]")

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
    :param database: The Tutor database generate with the ``load()`` function.
    """
    # 1. get the cube
    cube = database.cubes["sales"]
    # Caching - to experience the raw speed of the database,
    # we'll switch it off. For real world use cases, caching
    # greatly improves performance and therefore is on (True)
    # by default.

    # 2. Let's read some cells.
    # Just define the member you want to get data from for each
    # of the cubes dimension and your done.
    # The first cell request is a 'base level cell', it returns a
    # single value that is actually stored in the database.
    # disable caching
    cube.caching = False

    # Writing and reading cell values can be done by direct cell indexing
    cube["2021", "Jan", "North", "motorcycles", "Sales"] = 123.0
    value = cube["2021", "Jan", "North", "motorcycles", "Sales"]
    if console_output:
        print(f'sales({["2021", "Jan", "North", "motorcycles", "Sales"]}) := {value}')

    # You can also delete cell values, either by setting them to
    # ``None`` or by explicitly deleting them.
    cube["2022", "Jan", "North", "trucks", "Sales"] = 123.0
    # The following two statements are identical
    cube["2022", "Jan", "North", "trucks", "Sales"] = None
    del cube["2022", "Jan", "North", "trucks", "Sales"]

    # Another approach to read and write values is to use the the
    # ``set()`` and ``get()`` methods. The advantage of these
    # methods is, that you can hand over one single tuple (preferred)
    # or a list instead of a list of individual string.
    address = ("2021", "Jan", "North", "sedan", "Sales")
    cube.set(address, 456.0)
    value = cube.get(address)
    if console_output:
        print(f"sales({address}) := {value}")


    # Finally, you can create simple reports for console output
    # using slices.
    # Slices are plain Python dictionaries and describe the row
    # and columns layout of a slice through a cube. In addition
    # you can define filters that needs to be put in the header.
    # ``member`` can be single member or a list of members.
    # If you skip the ``member`` definition, then the default member
    # of the dimension will be selected and used.
    report_definition = {"header": [{"dimension": "years", "member": "2021"},
                                    {"dimension": "regions", "member": "Total"}],
                         "columns": [{"dimension": "months"}],
                         "rows": [{"dimension": "products"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    # You can even skip certain dimensions of the cube.
    # For these, the default member will be selected and
    # they will be automatically added to the header.
    # In addition, dimensions in rows and columns can be nested.
    report_definition = {"columns": [{"dimension": "months"}],
                         "rows": [{"dimension": "years"}, {"dimension": "regions"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    # Lets fill the entire cube with random numbers.
    # WARNING. The next statement is dangerous in high dimensional space
    # or with many members. For this tiny database it creates already
    # 3 * 12 * 4 * 6 * 2 = 1,728 cells.
    addresses = itertools.product(("2021", "2022", "2023"),
                                       ("Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
                                        ("North", "South", "West", "East"),
                                        ("trucks", "motorcycles", "coupe", "sedan", "sports", "van"),
                                        ("Sales", "Cost")
                                       )
    for address in addresses:
        cube.set(address, float(randrange(50, 1000)))

    # Lets print the same report again
    if console_output:
        report = Slice(cube, report_definition)
        print(report)


def main():
    play()


if __name__ == "__main__":
    main()
