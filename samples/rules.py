# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import itertools
import tinyolap.cell
from tinyolap.cube import Cube
from tinyolap.database import Database
from tinyolap.decorators import rule
from tinyolap.rules import RuleScope


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
    # months.add_subset("summer", ("Jun", "Jul", "Aug", "Sep"))
    months.subsets.add_static_subset("summer", ("Jun", "Jul", "Aug", "Sep"))

    # Dimension - Regions
    regions = db.add_dimension("regions")
    regions.edit()
    regions.add_many("Total", ("North", "South", "West", "East"))
    regions.commit()
    regions.add_attribute("manager", str)
    for member, manager in zip(regions.members, ("Peter Parker", "Ingmar Ice", "Carlo Carulli",
                                   "Heinz Erhardt", "Pyotr Tchaikovsky")):
        # regions.set_attribute("manager", a[0], a[1])
        regions.attributes["manager"][member] = manager
    regions.add_attribute("lc", str)
    for member, currency in zip(regions.members, ["USD", "EUR", "USD", "EUR", "USD"]):
        # regions.set_attribute("lc", member, currency)
        regions.attributes["lc"][member] = currency

    # Dimension - Products
    products = db.add_dimension("products")
    products.edit()
    products.add_many("Total", ["cars", "trucks", "motorcycles"])
    products.add_many("cars", ["coupe", "sedan", "sports", "van"])
    products.add_many("best sellers", ["sports", "motorcycles"])
    products.commit()
    products.attributes.add("price", float)
    for member in products.leaf_members:
        products.attributes.set("price", member, 100.0)

    # Dimension - Measures
    measures = db.add_dimension("measures")
    measures.edit()
    measures.add_many(["Price", "Quantity", "Sales", "Cost", "Profit", "Profit in %"])
    measures.add_many("Profit", ["Sales", "Cost"], [1.0, -1.0])
    measures.commit()
    # measures.member_set_format("Profit in %", "{:.2%}")  # e.g. 0.8640239 >>> 86.40%
    measures.members["Profit in %"].format = "{:.2%}"  # e.g. 0.8640239 >>> 86.40%

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
        exrates[address + ("EUR",)] = 1.0
        exrates[address + ("USD",)] = 0.95

    return db


@rule("sales", ["measures:Profit in %"], scope=RuleScope.ALL_LEVELS)
def rule_profit_in_percent(c: tinyolap.cell.Cell):
    """Rule to calculate the Profit in %."""
    sales = c["measures:Sales"]
    if sales:
        return c["measures:Profit"] / sales
    return None


@rule("sales", trigger=["currency:GC"], feeder=["currency:LC"], scope=RuleScope.BASE_LEVEL)
def rule_lc_to_gc(c: tinyolap.cell.Cell):
    """
    Base level rule to calculate a value in global currency ('GC') from local currency ('LC').
    This requires to first read the value in local currency, then read the currency code for the
    current region from and attribute, then look up the exchange rate from the exchange rate cube
    named ('exrates') and finally multiply the value with the exchange rate to get the requested
    value in GC.
    """
    value = c["currency:LC"]  # read the value in local currency
    if value:
        currcode = c.member("regions").attribute("lc")  # read the currency code for the current region
        exrate = c.db["exrates", c.member("years"), c.member("months"), currcode]  # look up exchange rate
        return value * exrate  # evaluate and return GC value
    return value


@rule("sales", ["measures:Sales"], scope=RuleScope.ON_ENTRY)
def push_rule_sales_to_cost(c: tinyolap.cell.Cell, value):
    """Rule to set the cost as 75% of sales."""
    if c.value:
        c["measures:Cost"] = c * 0.75
    else:
        c["measures:Cost"] = None


@rule("sales", ["measures:Sales", "currency:LC"], scope=RuleScope.COMMAND, command=["increase by*"])
def command_rule_price_increase(c: tinyolap.cell.Cell, command):
    """Rule to increase a value by a certain value or percentage."""
    command = str(command).lower()
    if command.startswith("increase by"):
        command = command[(len("increase by")):].strip()
        is_percentage = command.endswith("%")
        if is_percentage:
            value_text = command[:-1].strip()
        else:
            value_text = command
        if value_text.isdecimal():
            value = float(value_text)
        else:
            value = None

        if value:
            if is_percentage:
                c["measures:Sales"] = c * (1 + value/100)
            else:
                c["measures:Sales"] = c + value


def main():
    db = create_rules_database()
    sales: Cube = db.cubes["sales"]
    view = sales.views.create(name="test", definition={
        "title": "Test ON_ENTRY Rules -> 'Cost' = 'Sales * 0.75",
        "filters": {"dimensions": [{"dimension": "years", "members": "All years"},
                                   {"dimension": "months", "members": "Year"}]},
        "columns": {"dimensions": ["currency", "measures"]},
        "rows": {"dimensions": ["regions", "products"]}
    })
    print(view.to_console_output())


if __name__ == "__main__":
    main()
