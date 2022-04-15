![TinyOlap logo](/doc/source/_logos/cube16.png)  TinyOlap is under active development.

# TinyOlap 

TinyOlap is a light-weight, in-process, multi-dimensional, **model-first OLAP 
engine** for planning, budgeting, reporting, analysis and many other numerical purposes. 
Although this sounds very complicated, TinyOlap is actually very easy to use and should 
be suitable for all levels of Python and database skills.

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

TinyOlap is also quite handy as a smart alternative to Pandas DataFrames when your use case
is multi-dimensional data, requires hierarchical aggregations or complex calculations. 

## Getting started
**To get started**, download the [TinyOlap cheat sheet (pdf)](https://tinyolap.com/tinyolap_cheatsheet.pdf)
or visit [tinyolap.com](https://tinyolap.com) . 

If you want to use the TinyOlap package only, without the samples, then you can install TinyOlap using pip:

    pip install tinyolap

For the curious, just clone this repo and check our introduction sample [/samples/tiny.py](https://github.com/Zeutschler/tinyolap/blob/main/samples/tiny.py).

## How To Set up A Simple Database
Let's try to build a data model to support the quarterly business planning process of a well-known owner 
of electric car manufacturing company. So, here's how Elon Musk is doing his business planning - allegedly!

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

Now that our 5-dimensional database is setup, we can start to write data to and read data from the cube.
TinyOlap uses slicing syntax ``[dim1, dim2, ..., dimN]`` for simple but elegant cell access. 

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


To dive deeper, please visit the **TinyOlap website and documentation** at [https://tinyolap.com](https://tinyolap.com)

## Why Building An In-Memory Database In Plain Python? 
TinyOlap started as a by-product of a research project - we simply needed a super-light-weight MOLAP database 
to feed thousands of small- to medium-sized databases into a neuronal network for training it on how to do proper business planning. 
But, although we tested them all, there was no database that met our requirements, so we build one: **TinyOlap**

TinyOlap is also a reminiscence and homage to the early days of OLAP databases, where great products like 
Applix TM/1 or MIS Alea enabled business users to build expressive data models with dimension, cubes and complex 
business logic in just a few minutes our hours. Unfortunately, these products have grown up to complex and 
expensive client-server database technologies, all striving for the ultimate performance on mass data 
processing and high number of concurrent users - there is no light-weight and in-expensive MOLAP database anymore. 
Maybe, TinyOlap can bring back this light-weight experience, at least TinyOlap is free.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on 
client-side planning, budgeting, calculations and analysis purposes. TinyOlap provides sub-second 
response for most queries (see limitations below) and supports instant 
*dimensional modelling* - e.g., adding new members to dimensions or adding new calculations.
