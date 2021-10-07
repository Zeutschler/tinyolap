# -*- coding: utf-8 -*-
# Copyright (c) Thomas Zeutschler (Germany).
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import itertools
import math

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
    dim_products.add_member("best sellers", ["sports", "motorcycles"])
    dim_products.commit()

    # Measures
    measures = ["Sales", "Cost", "Profit"]

    # Now we can create our 'sales'*' cube, which is then a 5-dimensional cube.
    cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products], measures)
    cube.add_formula("[Profit] = [Sales] - [Cost]")

    # That's it...
    return db


def play(database: Database = load(), console_output: bool = True):
    """ Demonstrates the usage TinyOlap and the Tiny database.
    It creates and print some simple reports to the console.

    :param console_output: Set to ``False``to suppress console output.
    :param database: The Tiny database generate by the ``load()`` function.
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

    # You can also go through the database object, if this is more convenient for you
    database["sales", "2021", "Jan", "North", "motorcycles", "Sales"] = 123.0
    value = database["sales", "2021", "Jan", "North", "motorcycles", "Sales"]

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
                         "columns": [{"dimension": "months", "member": ["Jan", "Feb", "Mar", "Q1", "Q2", "Year"]}],
                         "rows": [{"dimension": "products"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    # You can even skip certain dimensions of the cube.
    # For these, the default member will be selected and
    # they will be automatically added to the header.
    # In addition, dimensions in rows and columns can be nested.
    # And you can set a report title.
    report_definition = {"title": "What a fancy report...",
                         "columns": [{"dimension": "months", "member": ["Q1", "Q2", "Q3", "Q4", "Year"]}],
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
        cube.set(address, float(randrange(5, 100)))

    # Lets print the same report again
    if console_output:
        report.refresh()
        print(report)


def play_advanced_business_logic(database: Database = load(), console_output: bool = False):
    """ Demonstrates the implementation of advanced business logic in TinyOlap.
    :param console_output: Set to ``False``to suppress console output.
    :param database: The Tiny database generate by the ``load()`` function.
    """
    cube = database.cubes["sales"]

    # 1. Lets fill the entire cube with random numbers.
    #   For the Tiny database this will creates 3 * 12 * 4 * 6 * 2 = 1,728 unique addressable cube cells.
    #   including all aggregations, we'll get 4 * 17 * 5 * 9 * 2 = 6,120 unique addressable cube cells.
    addresses = itertools.product(("2021", "2022", "2023"),
                                  ("Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
                                  ("North", "South", "West", "East"),
                                  ("trucks", "motorcycles", "coupe", "sedan", "sports", "van"),
                                  ("Sales", "Cost"))
    for address in addresses:
        cube.set(address, float(randrange(5, 100)))

    # *************************************************************************
    # 2. Lets create a Cursor and see how it basically works
    c = cube.create_cursor("2022", "Jan", "North", "trucks", "Sales")

    # Cursors behave (more or less) like float values,
    # ...but on direct assignment you need to be a bit careful:
    a = c.value    # as 'a = c' would only copy the reference to the Cursor object,
                   # so we need to explicitly ask for .value
    a = float(c)   # ...would be an alternative approach to ask for the numeric value of 'c'
    a = c.numeric_value   # ...or this, in order to be sure to strictly get the numerical value.
                          # 'c.value' will return whatever is in the database. 'c.numeric_value' converts it to float.

    # Once you start to do math, you are fine and can do almost anything e.g.:
    a = c * 2.0
    a = math.sin(c)
    a = math.sqrt(a + c ** 2)  # ...or whatever you want to do

    # Write back to the database is also straight forward. Just
    c.value = round(abs(math.sin(c)), 3) * 100.0

    # *************************************************************************
    # 3. Lets assume you want another cursor, closely related to the one we have already created.
    # "we want the 'Feb' value. You can either create another cursor as show above...
    d = cube.create_cursor("2022", "Feb", "North", "trucks", "Sales")
    # ...or you can just 'shift' your cursor TEMPORARILY to another cell address, by defining what should change.
    # This will NOT change the cursor from 'Jan' to 'Feb', it will just return the value for 'Feb' and will then
    # forget about that.
    d = c["Feb"]
    # Another advantage as this approach using indexing/slicing is the fact that you can
    # directly write back to the database using the same syntax.
    c["Feb"] = d * 2.0

    # RECOMMENDATION: Even if you want to access 'Jan'(what is defined by the cursor itself),
    #                 it is good practice to ALWAYS use slicers, even is you don need to.
    #                 This greatly improves the readability and consistency of your code.
    # Both of the follwong staments are identical:
    q1 = c + c["Feb"] + c["Mar"]         # Who knows what 'c' is about?
    q1 = c["Jan"] + c["Feb"] + c["Mar"]  # THIS IS GOOD PRACTISE !!!

    # Let's see what else we can do...
    if c["Q1"] != c["Jan"] + c["Feb"] + c["Mar"]:
        print("This should never be printed, as Q1 is the parent member for Jan, Feb and Mar.")

    # You can also shift multiple dimensions.
    # The order of dimensions doesn't matter, they get automatically sorted.
    delta_prev_year = c["Q1"] - c["Q1", "2021"]
    delta_prev_year_in_percent = round(delta_prev_year / c["Q1", "2021"] * 100.0, 2)

    # Or you can build whatever ratios you want...
    sport_cars_in_percent = c["sports"] / c["Total"] * 100.0
    # ALARM !!!! WARNING !!!! ERROR !!!!
    # Here we might run into a problem: while 'sports' is a unique member key over all dimensions
    # of the cube, the member 'Total' is not. 'Total' is defined for two dimensions, for 'products'
    # and 'regions' dimension.
    # WARNING: You have no guarantee and control on what dimension the cursor will actually modify.

    # But the solution to this problem is very easy, you just need to explicitly hand in the dimension name...
    #   cursor[dimension_name:member_name]
    # BRAVO !!! Now your save, at least almost...
    sport_cars_in_percent = c["sports"] / c["products:Total"] * 100.0

    # *************************************************************************
    # 4. Let's get down to business.
    # When you'll build a lot of business logic, often with dedicated functions
    # or classes (e.g. for calculation an amortization or a forecast using ML,
    # or to read/write data from a web service, a database or an ERP system),
    # THEN the above 'manual' approach of doing calculations might get complex.
    #
    # The best way is to further encapsulate and reuse your business logic.
    # One solution is to define lambda functions like this...

    sport_cars_in_percent = lambda x: x["products:sports"] / x["products:Total"] * 100.0
    # Now you can reuse this function for whatever cursor you like:
    kpi = sport_cars_in_percent(c)









def main():
    play()
    play_advanced_business_logic()


if __name__ == "__main__":
    main()
