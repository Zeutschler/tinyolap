# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
# http://hilite.me

import random
import timeit
from tinyolap.cell import Cell
from tinyolap.decorators import rule
from tinyolap.database import Database


@rule("sales", ["Deviation"])
def deviation(c: Cell):
    return c["Actual"] - c["Plan"]


@rule("sales", ["Deviation %"])
def deviation_percent(c: Cell):
    if c["Plan"]:  # prevent potential division by zero
        return c["Deviation"] / c["Plan"]
    return None


def elons_random_numbers(low: float = 1000.0, high: float = 2000.0):
    return random.uniform(low, high)


def play_tesla(console_output: bool = True) -> Database:
    # define the sales planning and reporting dataspace for Tesla
    db = Database("tesla")
    cube = db.add_cube("sales", [
        db.add_dimension("datatypes").edit().add_member(
            ["Actual", "Plan", "Deviation", "Deviation %"]).commit(),
        db.add_dimension("years").edit().add_member(
            ["2021", "2022", "2023"]).commit(),
        db.add_dimension("periods").edit().add_member(
            "Year", ["Q1", "Q2", "Q3", "Q4"]).commit(),
        db.add_dimension("regions").edit().add_member(
            "Total", ["North", "South", "West", "East"]).commit(),
        db.add_dimension("products").edit().add_member(
            "Total", ["Model S", "Model 3", "Model X", "Model Y"]).commit()
    ])
    db.dimensions["datatypes"].member_set_format("Deviation", "{:+,.0f}")
    db.dimensions["datatypes"].member_set_format("Deviation %", "{:+.2%}")

    # Add some custom business logic (implementation, see functions above)
    cube.register_rule(deviation)
    cube.register_rule(deviation_percent)

    # Adding single values for 'Plan' data
    cube["Plan", "2021", "Q1", "North", "Model S"] = 400.0  # write to a single cell
    cube["Plan", "2021", "Q1", "North", "Model X"] = 200.0  # write to a single cell

    # Now, the Elon Musk way of planning - what a lazy boy ;-)
    # The next statement will address <<<ALL EXISTING DATA>>> over all years, periods,
    # regions and products, and set all existing values to 500.0. Currently, there are
    # only 2 values 400.0 and 200.0 in the cube, so just these will be changed.
    cube["Plan"] = 500.0
    # Let's see if this has worked properly...
    if cube["Plan", "2021", "Q1", "North", "Model S"] != 500.00:
        raise ValueError("TinyOlap is a fake...")

    # Elon is even lazier than expected...
    # The 'True' arg in the following statement will force writing the number 500.0
    # to <<<REALLY ALL>>> years, periods, regions and products combinations at once.
    cube["Plan"].set_value(500.0, True)  # 3 x 4 x 4 x 4 = all 192 values := 500.0
    # For 2023 Elon is planning to skyrocket: 50% more for 2023
    cube["Plan", "2023"] = cube["Plan", "2022"] * 1.50

    # Add some 'Actual' data
    # Attention! Elon probably wants to take a shortcut here.
    # He simply hands in a Python function to generate some 'Actual' data.
    cube["Actual"].set_value(elons_random_numbers, True)

    # Where done! Our first TinyOlap database is ready to use.

    # Finally let's check Elon's business performance.
    dev_percent = cube["Deviation %", "2023", "Year", "Total",  "Total"]
    if console_output:
        print(f"Elon's 2023 performance is {dev_percent:+.2%} growth. "
              f"Congratulations, Elon!")

    return db


if __name__ == "__main__":
    print(f"\nTinyOlap, nearly as fast as a Tesla! 10x business planning "
          f"in just {timeit.timeit(lambda: play_tesla(), number=10):.4} sec.")
