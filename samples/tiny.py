# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import itertools
import math
import time
from art import *

import tinyolap.cell_context
from area import Area
from tinyolap.decorators import rule
from tinyolap.database import Database
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.slice import Slice
from random import randrange


def load_tiny(console_output: bool = False) -> Database:
    """
    Creates a very simple (tiny) database for 'actual sales figures',
    just by code. Although the database is super minimalistic, it
    already explains the key concepts of TinyOlap.

    :return: The **Tiny** sample data model as a tinyolap in-memory
    only Database object.
    """

    if console_output:
        print(f"Creating the 'tiny' data model. Please wait...")

    # ************************
    # 1. create a new database
    db = Database("tiny", in_memory=True)

    # ************************
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

    # Finally lets add a measures-dimension for our business logic,
    # here a super simple 'profit & loss' schema.
    dim_measures = db.add_dimension("measures")
    dim_measures.edit()
    dim_measures.add_member(["Sales", "Cost", "Profit", "Profit in %"])
    dim_measures.commit()

    # You can also add some nice number formatting to dimension measures
    # e.g. for number and percentage formatting. MemberContext formatting follows
    # the standard Python formatting specification at
    # <https://docs.python.org/3/library/string.html#format-specification-mini-language>.
    dim_measures.member_set_format("Profit in %", "{:.2%}")  # e.g. this would number_format 0.864 as '86.40%'-

    # ************************
    # 3. Now we can create our 'sales'*' cube, which is actually a 5-dimensional cube.
    cube = db.add_cube("sales", [dim_years, dim_months, dim_regions, dim_products, dim_measures])

    # ************************
    # 4. And now we come to the most powerful capability of TinyOlap and this is **Rules**.
    # Rules are simple Python methods or function and allow you to add custom business logic
    # to you data model. Whatever that might be, from simple math calculations up to AI-powered
    # automated forecasting - the sky is the limit.
    # Here we define 2 very simple functions that calculate 'Profit' and 'Profit in %' form the
    # measure dimension. The Python rules functions are defined directly below. Use the ``@rule``
    # decorator you need to specify for what cube the rule should be used and what member (e.g. ['Profit']) or
    # member combination (e.g. [..., 'Jan', 'Profit']) the rule should actually calculate.
    # For further detailed on how to define and write rules, please refer the TinyOlap documentation.
    # Rules are a big and complex topic!!! Once you've understood the concept, it gets very easy.
    cube.add_rule(rule_profit)
    cube.add_rule(rule_profit_in_percent)

    # That's it! Your first TinyOlap database is ready to use...
    return db


@rule("sales", ["Profit"])
def rule_profit(c: tinyolap.cell_context.CellContext):
    return c["Sales"] - c["Cost"]


@rule("sales", ["Profit in %"], scope=RuleScope.ALL_LEVELS, volatile=False)
def rule_profit_in_percent(c: tinyolap.cell_context.CellContext):
    sales = c["Sales"]
    profit = c["Profit"]
    if sales:
        return profit / sales
    return None


def play_tiny(console_output: bool = True):
    """ Demonstrates the usage TinyOlap and the Tiny database.
    It creates and print some simple reports to the console.

    :param console_output: Set to ``False``to suppress console output.
    """

    if console_output:
        tprint("TinyOlap", font="Slant")

    # 1. get the cube
    database = load_tiny()
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
    report_definition = {"title": "There are just 2 values (123.0 and 456.0) in the cube.",
                         "header": [{"dimension": "years", "member": "2021"},
                                    {"dimension": "regions", "member": "Total"}],
                         "columns": [{"dimension": "months", "member": ["Jan", "Feb", "Mar", "Q1", "Q2", "Year"]}],
                         "rows": [{"dimension": "products"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    report_definition = {"title": "A report where we can see our rules for Profit and Profit% in action.",
                         "columns": [{"dimension": "months",
                                      "member": ["Jan", "Feb", "Mar", "Q1", "Q2", "Q3", "Q4", "Year"]}],
                         "rows": [{"dimension": "measures"}]}
    report = Slice(cube, report_definition)
    if console_output:
        print(report)

    # Lets fill the entire cube with random numbers.
    # WARNING. The next statement is dangerous in high dimensional space
    # and/or data models with many members.
    # For this tiny database it creates already 3 * 12 * 4 * 6 * 2 = 3,456 cells.
    addresses = itertools.product(("2021", "2022", "2023"),
                                  ("Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
                                  ("North", "South", "West", "East"),
                                  ("trucks", "motorcycles", "coupe", "sedan", "sports", "van"),
                                  ("Sales", "Cost", "Profit", "Profit in %")
                                  )
    for address in addresses:
        cube.set(address, float(randrange(5, 100)))

    # Lets print the same report again
    if console_output:
        report.title = "The same report as before, but now the cube is filled with random data."
        report.refresh()
        print(report)

    # ...finally, let's dump ALL data to the console
    if console_output:
        print(f"\n{'-' * 100}\nCACHING - Comparison of report execution times with Caching Off and On\n{'-' * 100}")
        print(f"...let's run a larger report (without printing it). Caching is Off...")
    report_definition = {"title": "All data cells available in the Tiny data model...",
                         "columns": [{"dimension": "months"}],
                         "rows": [{"dimension": "years"}, {"dimension": "regions"}, {"dimension": "products"},
                                  {"dimension": "measures"}]}
    cube.reset_counters()
    start = time.time()
    report = Slice(cube, report_definition)

    if console_output:
        duration = time.time() - start
        cells = report.grid_rows_count * report.grid_cols_count
        # print(report)
        print(f"Report with {report.grid_rows_count:,} rows x {report.grid_cols_count:,} columns ="
              f" {cells:,} cells executed in {duration:.3} sec. "
              f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
              f"thereof {cube.counter_cell_requests - cells:,} by rules."
              f"\n\t{cube.counter_rule_requests:,} rules executed"
              f"\n\t{cube.counter_aggregations:,} cell aggregations calculated")

    if console_output:
        print(f"\n...again, the same report, now with Caching On, but cold=empty cache...")
    cube.reset_counters()
    start = time.time()
    cube.caching = True
    report.refresh()  # warm the cache...
    if console_output:
        duration = time.time() - start
        cells = report.grid_rows_count * report.grid_cols_count
        # print(report)
        print(f"Report with {report.grid_rows_count:,} rows x {report.grid_cols_count:,} columns ="
              f" {cells:,} cells executed in {duration:.3} sec. "
              f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
              f"thereof {cube.counter_cell_requests - cells:,} by rules."
              f"\n\t{cube.counter_rule_requests:,} rules executed"
              f"\n\t{cube.counter_aggregations:,} cell aggregations calculated")

    if console_output:
        print(f"\n...finally the same report, with Caching On and warm cache...")
    cube.reset_counters()
    start = time.time()
    report.refresh()
    if console_output:
        duration = time.time() - start
        cells = report.grid_rows_count * report.grid_cols_count
        # print(report)
        print(f"Report with {report.grid_rows_count:,} rows x {report.grid_cols_count:,} columns ="
              f" {cells:,} cells executed in {duration:.3} sec. "
              f"\n\t{cube.counter_cell_requests:,} individual cell requests, "
              f"thereof {cube.counter_cell_requests - cells:,} by rules."
              f"\n\t{cube.counter_rule_requests:,} rules executed"
              f"\n\t{cube.counter_aggregations:,} cell aggregations calculated")

    if console_output:
        print(f"\nRecommendation: Leave Caching On, whenever possible!")
        print(f"\t- Caching is anyhow activated by default.'")
        print(f"\t- The more aggregations and rules you have, the more you will benefit from caching.'")
        print(f"\t- Caching On and Off will return the same result, if all your rules are non-volatile.'")
        print(f"\t- Switch off caching only if you have rules are 'volatile'.'")


def play_advanced_business_logic(database: Database = load_tiny()):
    """ Demonstrates the implementation of advanced business logic in TinyOlap.
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
    # 2. Lets create a CellContext and see how it basically works
    c = cube.cell("2022", "Jan", "North", "trucks", "Sales")

    # Cursors behave (more or less) like float values,
    # ...but on direct assignment you need to be a bit careful:
    a = c.value  # as 'a = c' would only copy the reference to the CellContext object,
    # so we need to explicitly ask for .value
    a = float(c)  # ...would be an alternative approach to ask for the numeric value of 'c'
    a = c.numeric_value  # ...or this, in order to be sure to strictly get the numerical value.
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
    d = cube.cell("2022", "Feb", "North", "trucks", "Sales")
    # ...or you can just 'shift' your cursor TEMPORARILY to another cell idx_address, by defining what should change.
    # This will NOT change the cursor from 'Jan' to 'Feb', it will just return the value for 'Feb' and will then
    # forget about that.
    d = c["Feb"]
    # Another advantage as this approach using indexing/slicing is the fact that you can
    # directly write back to the database using the same syntax.
    c["Feb"] = d * 2.0

    # RECOMMENDATION: Even if you want to access 'Jan'(what is defined by the cursor itself),
    #                 it is good practice to ALWAYS use slicers, even is you don need to.
    #                 This greatly improves the readability and consistency of your code.
    # Both of the following statements are identical:
    q1 = c + c["Feb"] + c["Mar"]  # Who knows what 'c' is about?
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
    # But wait...   ALARM !!!! WARNING !!!! ALARM !!!! WARNING !!!!
    # Here we might run into a problem: while 'sports' is a unique member key over all dimensions
    # of the cube, the member 'Total' is not. 'Total' is defined for two dimensions, for 'products'
    # and 'regions' dimension.
    # WARNING: You have no guarantee and control on what dimension the cursor will actually modify.

    # But the solution to this problem is very easy, you just need to explicitly hand in the dimension name...
    #   cursor[cube_name:member_name]
    # BRAVO !!! Now your save, at least almost...
    sport_cars_in_percent = c["sports"] / c["products:Total"] * 100.0

    # *************************************************************************
    # 4. You can process many cells at once usisng the Area object
    # Instead of a single cell you access a range of cells, defined by a
    # multidimensional area. These areas only and always reflect the base-level
    # cells of a cube (aggregations do not exists in the cube). By this you can
    # easily do mass manipulation of data. Let's create an Area for 'Sales' '2022':
    data: Area = cube.area("Sales", "2022")
    # The above statement defines an area over ALL months, products and regions,
    # but for the 'measure' dimension only for 'Sales' and for the years only '2022'

    # Areas are super useful do delete data, meaning clearing an 'area of data' in a cube.
    # e.g. when you accidentally imported wrong data into a cube and need to delete it.
    data.clear()

    # Now that the data are is empty, let's add 2 values in the cube that fall into the Area.
    cube["2022", "Jan", "North", "trucks", "Sales"] = 45.0
    cube["2022", "Feb", "North", "sedan", "Sales"] = 67.0

    # Now you can get a list of ALL EXISTING records.
    # Each record contains the idx_address of each cell and its value as a list.
    records = list(data.records())
    # record and value can be seperated from each other easily as shown in the loop below
    for record in data.records():
        address = record[:-1]
        value = record[-1]
        # Such records can be used for whatever purpose, but especially
        # to instantly write bike values back to the cube.
        cube.set(address, 2.0 * value / (3.0 - 1.0))


    # But, such loops can also be done more elegantly with 1 line of code only.
    data *= 2.0  # ALL EXISTING values in the Area get multiplied by 2.0

    # You can also set all values in the area to a specific value.
    data.set_value(1.0)  # set ALL values (REALLY ALL VALUES) in the area to 1.0
    # So, the above ``set_value()``statement should be handled with care on larger data models,
    # as it enumerates the entire data space. 100 x 100 x 100 x 100 members over 4 dimensions
    # already end up incl 100.000.000 that will be written - much too much for TinyOlap.

    # And finally you have the same modifiers as with CellContext objects.
    # This is a very powerful and essential feature of TinyOlap.
    # The following statement copies all 'sales' data from 2022 to 2023,
    # before copying, the target area will be cleared.()
    # todo: implementation not yet ready. Go Bro, go ....
    # data["2023"] = data["2022"] * 2

    # *************************************************************************
    # 5. Let's get down to business.
    # When you'll build a lot of business logic, often with dedicated functions
    # or classes (e.g. for calculation an amortization or a forecast using ML,
    # or to read/write data from a web service, a database or an ERP system),
    # THEN the above 'manual' approach of doing calculations might get complex.
    #
    # The best way is to further encapsulate and reuse your business logic.
    # One solution is to define lambda functions like this...

    sport_cars_in_percent = lambda x: x["products:sports"] / x["products:Total"] * 100.0
    # Now you can reuse this function for whatever cursor you throw in:
    kpi = sport_cars_in_percent(c)


def main():
    play_tiny()
    play_advanced_business_logic()


if __name__ == "__main__":
    main()
