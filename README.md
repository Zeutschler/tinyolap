![TinyOlap logo](/doc/source/_logos/cube16.png)  TinyOlap is still under active development and not 
yet available on [PyPi.org](https://pypi.org).
# TinyOlap 

TinyOlap is a light-weight, client-side, model-driven, cell-oriented, multi-dimensional OLAP 
database for **planning, budgeting, reporting, analysis and many other purposes**. 
Although this sounds very complicated, TinyOlap is actually very easy to use and should 
be suitable for all levels of Python and database skills. Enjoy...

## Getting started
**To get started**, please visit the **TinyOlap documentation** at [https://tinyolap.com](https://tinyolap.com)

Or, for the curious, just clone this repo and check our introduction sample [/samples/tiny.py](https://github.com/Zeutschler/tinyolap/blob/main/samples/tiny.py).

## How To Set up A Simple Database
Let's see how you can build a TinyOlap data model, e.g., to support the quarterly business planning process of a well-known car manufacturer.

    from tinyolap.database import Database

    # setup a new TinyOlap database
    db = Database("tesla")

    # create some dimensions 
    data_type = db.dimension_add("datatype")
                .member_add(["Actual", "Plan", "Act vs. Pl"])
    years = db.dimension_add("years")
                .member_add(["2021", "2022", "2023", "2024", "2025"])
    periods = db.dimension_add("periods")
                .member_add("Year", ["Q1", "Q2", "Q3", "Q4"])
    regions = db.dimension_add("regions")
                .member_add("Total", ["North", "South", "West", "East"])
    products = db.dimension_add("products")
                .member_add("Total", ["Model S", "Model 3", "Model X", "Model Y"])

    # create a cube
    cube = db.cube_add("sales", [data_type, years, periods, regions, products])

Now that our 5-dimensional database is setup, we can start to write data to and read data from the cube.
TinyOlap uses slicing syntax ``[dim1, dim2, ..., dimN]`` for simple but elegant cell access. PLease be aware,
that the order of the dimension members in the slicer really matters.

    # write some values to the cube
    cube["Actual", "2021", "Q1", "North", "Model S"] = 1000.0
    cube["Actual", "2021", "Q2", "West", "Model S"] = 500.0
    cube["Actual", "2021", "Q3", "West", "Model 3"] = 20.0

    # read some values
    v = cube["Actual", "2021", "Q1", "North", "Model S"]  # returns 1000.0
    v = cube["Actual", "2025", "Q1", "East", "Model X"]   # returns 0.0
    v = cube["Actual", "2021", "Year", "West", "Total"]   # returns 1500.0, an aggregated number
    v = cube["Actual", "2021", "Year", "Total", "Total"]  # returns 1520.0, an aggregated number

To dive deeper, please visit the **TinyOlap documentation** at [https://tinyolap.com](https://tinyolap.com)

## Why Building An In-Memory Database In Plain Python? 
TinyOlap started as a by-product of a research project - we simply needed a super-light-weight MOLAP database 
to feed thousands of databases into a neuronal network for training it on how to do proper business planning. 
But there was no database that met our requirements, so I build one: **TinyOlap**

TinyOlap is also a reminiscence and homage to the early days of OLAP databases, where great products like 
Applix TM/1 or MIS Alea enabled business users to build expressive data models with dimension, cubes and complex 
business logic in just a few minutes our hours. Unfortunately, these products have grown up to complex and 
expensive client-server database technologies, all striving for the ultimate performance on mass data 
processing and high number of concurrent users - there is no small and cheap MOLAP database anymore.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on 
client-side planning, budgeting, calculations and analysis purposes. TinyOlap provides sub-second 
response for most queries (see limitations below) and supports instant 
*dimensional modelling* - e.g., adding new members to dimensions or adding new calculations.
