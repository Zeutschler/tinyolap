# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import itertools
import math
import random
import time
from art import *

import tinyolap.cell
from tinyolap.area import Area
from tinyolap.cell import Cell
from tinyolap.decorators import rule
from tinyolap.database import Database
from tinyolap.cube import Cube
from tinyolap.rules import RuleScope, RuleInjectionStrategy
from tinyolap.slice import Slice
from random import randrange


def create_rules_database(console_output: bool = False) -> Database:
    """Creates a database to test and showcase TinyOlap rules capabilities."""
    db = Database("rules", in_memory=True)
    db.caching = False

    # Dimension - Years
    years = db.add_dimension("years")
    years.edit()
    years.add_many("2021")
    years.add_many("2022")
    years.add_many("2023")
    years.add_many("All years", ["2021", "2022", "2023"])
    years.commit()

    # Dimension - Months
    months = db.add_dimension("months")
    months.edit()
    months.add_many(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    months.add_many(["Q1", "Q2", "Q3", "Q4"],
                        [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                           ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    months.add_many("Year", ("Q1", "Q2", "Q3", "Q4"))
    months.commit()
    months.add_subset("summer", ("Jun", "Jul", "Aug", "Sep"))

    # Dimension - Regions
    regions = db.add_dimension("regions")
    regions.edit()
    regions.add_many("Total", ("North", "South", "West", "East"))
    regions.commit()
    regions.add_attribute("manager", str)
    for a in zip(regions.members, ("Peter Parker", "Ingmar Ice", "Carlo Carulli",
                                           "Heinz Erhardt", "Pyotr Tchaikovsky")):
        regions.set_attribute("manager", a[0], a[1])
    regions.add_attribute("lc", str)
    for member, currency in zip(regions.members, ["USD", "EUR", "USD", "EUR", "USD"]):
        regions.set_attribute("lc", member, currency)


    # Dimension - Products
    products = db.add_dimension("products")
    products.edit()
    products.add_many("Total", ["cars", "trucks", "motorcycles"])
    products.add_many("cars", ["coupe", "sedan", "sports", "van"])
    products.add_many("best sellers", ["sports", "motorcycles"])
    products.commit()
    products.add_attribute("price", float)
    for member in products.leaf_members:
        products.set_attribute("price", member, 100.0)

    # Dimension - Measures
    measures = db.add_dimension("measures")
    measures.edit()
    measures.add_many(["Price", "Quantity", "Sales", "Cost", "Profit", "Profit in %"])
    measures.add_many("Profit", ["Sales", "Cost"], [1.0, -1.0])
    measures.commit()
    measures.member_set_format("Profit in %", "{:.2%}")  # e.g. 0.8640239 >>> 86.40%

    # Dimension - Reporting Currency
    currency = db.add_dimension("currency")
    currency.edit()
    currency.add_many(["GC", "LC"])
    currency.commit()

    # Dimension - Currency Codes
    currcodes = db.add_dimension("currcode")
    currcodes.edit()
    currcodes.add_many(["EUR", "USD"])
    currcodes.commit()

    # Cube - Sales
    sales = db.add_cube("sales", [years, months, regions, products, currency, measures])
    exrates = db.add_cube("exrates", [years, months, currcodes])

    # Rules registration
    sales.register_rule(rule_profit_in_percent)
    sales.register_rule(push_rule_sales_to_cost)
    sales.register_rule(rule_lc_to_gc)

    # Populate Sales Cube
    for address in itertools.product(["2021", "2022", "2023"],
            ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            ["North", "South", "West", "East"],
            ["trucks", "motorcycles", "coupe", "sedan", "sports", "van"],
            ["LC"], ["Quantity", "Sales"]):
        sales[address] = 100.0
    # Populate exrates Cube
    for address in itertools.product(["2021", "2022", "2023"],
            ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
        exrates[address + ("EUR", )] = 1.0
        exrates[address + ("USD", )] = 0.95

    return db


@rule("sales", ["measures:Profit in %"], scope=RuleScope.ALL_LEVELS)
def rule_profit_in_percent(c: tinyolap.cell.Cell):
    """Rule to calculate the Profit in %."""
    sales = c["Sales"]
    if sales:
        return c["Profit"] / sales
    return None


@rule("sales", trigger=["currency:GC"], feeder=["currency:LC"],  scope=RuleScope.BASE_LEVEL)
def rule_lc_to_gc(c: tinyolap.cell.Cell):
    """Rule to calculate the Profit in %."""
    value = c["currency:LC"]
    if value:
        currcode = c.member("regions").attribute("lc")
        exrate = c.db["exrates", c.member("years"), c.member("months"), currcode]
        return value * exrate
    return value


@rule("sales", ["Sales"], scope=RuleScope.ON_ENTRY)
def push_rule_sales_to_cost(c: tinyolap.cell.Cell):
    """Rule to set the cost as 75% of sales."""
    if c.value:
        c["Cost"] = c * 0.75
    else:
        c["Cost"] = None


def main():
    db = create_rules_database()
    sales: Cube = db.cubes["sales"]
    view = sales.views.create(name="test", definition={
                "title": "Test ON_ENTRY Rules -> 'Cost' = 'Sales * 0.75",
                "filters": {"dimensions": ["years", "months" ]},
                "columns": {"dimensions": ["currency","measures"]},
                "rows": {"dimensions": ["regions", "products"]}
                })
    print(view.to_console_output())



if __name__ == "__main__":
    main()
