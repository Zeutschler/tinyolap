# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import random
from tinyolap.cell import Cell
from tinyolap.decorators import rule
from tinyolap.database import Database
from tinyolap.view import View


@rule(cube="sales", trigger=["Delta %"])
def delta_percent(c: Cell):
    if c.Plan:  # prevent potential division by zero
        return c.Delta / c.Plan
    return None


def elons_random_numbers(low: float = 1000.0, high: float = 2000.0):
    return random.uniform(low, high)


# Purpose: Support Elon Musk on his business planning & reporting for Tesla
def tesla_business_planning(console_output: bool = True):
    # 1st - define an appropriate 5-dimensional cube (the data space)
    db = Database("rubi")

    dim_months = db.add_dimension("months")
    dim_months.edit()
    dim_months.add_many(["Jan", "Feb", "Mar", "Apr", "Mai", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    dim_months.add_many(["Q1", "Q2", "Q3", "Q4"],
                        [("Jan", "Feb", "Mar"), ("Apr", "Mai", "Jun"),
                         ("Jul", "Aug", "Sep"), ("Oct", "Nov", "Dec")])
    dim_months.add_many("Year", ("Q1", "Q2", "Q3", "Q4"))
    dim_months.commit()

    datatypes = db.add_dimension("datatypes").edit()\
        .add_many(["Actual", "Plan"])\
        .add_many("Delta", ["Actual", "Plan"], [1.0, -1.0])\
        .add_many("Delta %").commit()


    cube = db.add_cube("sales", [
        db.add_dimension("datatypes").edit()
                       .add_many(["Actual", "Plan"])
                       .add_many("Delta", ["Actual", "Plan"], [1.0, -1.0])
                       .add_many("Delta %")
                       .commit(),
        db.add_dimension("years").edit().add_many(
            ["2021", "2022", "2023"]).commit(),
        db.add_dimension("periods").edit().add_many(
            "Year", ["Q1", "Q2", "Q3", "Q4"]).commit(),
        db.add_dimension("regions").edit().add_many(
            "Total", ["North", "South", "West", "East"]).commit(),
        db.add_dimension("products").edit().add_many(
            "Total", ["Model S", "Model 3", "Model X", "Model Y"]).commit()
    ])
    # 2nd - (if required) add custom business logic, so called 'rules'.
    #       Register the rule that has been implemented above. Take a look.
    cube.register_rule(delta_percent)

    # 3rd - (optional) some beautifying, set number formats
    db.dimensions["datatypes"].members["Delta"].format = "{:+,.0f}"
    db.dimensions["datatypes"].members["Delta %"].format = "{:+.2%}"

    # 4th - to write data to the cubes, just define and address and assign a value
    cube["Plan", "2021", "Q1", "North", "Model S"] = 400.0  # write a single value
    cube["Plan", "2021", "Q1", "North", "Model X"] = 200.0  # write a single value

    # 5th - TinyOlap's strength is manipulating larger areas of data
    # That's the Elon Musk way of planning - what a lazy boy ;-)
    # The next statement will address <<<ALL EXISTING DATA>>> over all years, periods,
    # regions and products, and set all existing values to 500.0. Currently, there are
    # only 2 values 400.0 and 200.0 in the cube, so just these will be changed.
    cube["Plan"] = 500.0
    # Let's see if this has worked properly...
    if cube["Plan", "2021", "Q1", "North", "Model S"] != 500.00:
        raise ValueError("TinyOlap is cheating...")
    # Elon might be lazier than expected...
    # The 'True' arg in the following statement will force writing the number 500.0
    # to <<<REALLY ALL>>> years, periods, regions and products combinations at once.
    cube["Plan"].set_value(500.0, True)  # 3 x 4 x 4 x 4 = all 192 values := 500.0
    # For 2023 Elon is planning to skyrocket: 50% more for 2023
    cube["Plan", "2023"] = cube["Plan", "2022"] * 1.50

    # Now it's time for 'Actual' data
    # What??? Elon probably wants to take a shortcut here...
    # He simply hands in a Python function to generate all the 'Actual' data.
    cube["Actual"].set_value(elons_random_numbers, True)
    # Where already done! Our first TinyOlap database is ready to use.

    # 6th - reading data and simple reporting
    view = View(cube).refresh()
    if console_output:
        # let's create a minimal default report and dump it to the console
        print(view.to_console_output())

        # finally, let's congratulate Elon
        dev_percent = cube["Delta %", "2023", "Year", "Total", "Total"]
        print(f"\nTesla's is {dev_percent:+.2%} above 'Plan' for 2023. "
              f"Congratulations, Elon!")

    return db


if __name__ == "__main__":
    tesla_business_planning()
