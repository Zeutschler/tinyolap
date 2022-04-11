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


def elons_random_number(low: float = 1000.0, high: float = 2000.0):
    return random.uniform(low, high)


def play_tesla(console_output: bool = True):
    # define your data space
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
    # add your custom business logic
    cube.register_rule(deviation)
    cube.register_rule(deviation_percent)

    # Add some 'Plan' data
    cube["Plan", "2021", "Q1", "North", "Model S"] = 400.0  # write to a single cell
    cube["Plan", "2021", "Q1", "North", "Model X"] = 200.0  # write to a single cell
    # The Elon Musk way of planning - what a lazy boy ;-)
    # The next statement will address all EXISTING 'Plan' data for all years, periods, regions
    # and products to the 500.0. Currently, there are only two values in the cube: 400.0 and 200.0.
    cube["Plan"] = 500.0
    if cube["Plan", "2021", "Q1", "North", "Model S"] != 500.00:
        raise ValueError("TinyOlap is cheating...")
    # The 'True' argument in the following statement will force writing the number 500.0
    # to REALLY ALL years, periods, regions and products by enumerating the entire data space in one shot.
    cube["Plan"].set_value(500.0, True)  # this will write 3 x 4 x 4 x 4 = 192 values to the cube
    cube["Plan", "2023"] = cube["Plan", "2022"] * 1.50  # Elon is skyrocketing, 50% more for 2023

    # Add some 'Actual' data
    cube["Actual"].set_value(elons_random_number)  # really? Elon is going for a shortcut here.

    # Let's check Elon"s performance. 'dev_percent' is calculated by the rule 'deviation_percent()'
    dev_percent = cube["Deviation %", "2023", "Year", "Total",  "Total"]
    if console_output:
        print(f"Elon's performance in 2023 is {dev_percent:.2%}. Congrats!")


if __name__ == "__main__":
    print(f"\nTinyOlap, as fast as a Tesla! 10x planning in just {timeit.timeit(lambda: play_tesla(), number=10):.4} sec.")
