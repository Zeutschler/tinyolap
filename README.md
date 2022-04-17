![TinyOlap logo](/doc/source/_logos/cube16.png)  TinyOlap is under active development. Visit [tinyolap.com](https://tinyolap.com) 

# TinyOlap 

TinyOlap is an open-source, multi-dimensional, in-memory, **model-first OLAP engine** written in plain Python. 
As an in-process Python library, it empowers developers to build lightweight solutions for planning, 
forecasting, simulation, analytics and many other numerical problems.

TinyOlap is also quite handy as a smart alternative to Pandas DataFrames when your data is multi-dimensional, 
requires hierarchical aggregations or complex calculations.

TinyOlap aims to honour and mimic commercial products like IBM TM/1, Jedox PALO or Infor d/EPM. If their 
scalability and performance is not required, or their technical complexity or cost is not reasonable for 
your purpose, then TinyOlap might be for you.

## Getting started
To get started, please download the [TinyOlap cheat sheet (pdf)](https://tinyolap.com/tinyolap_cheatsheet.pdf)
and check the various provided samples 
at [/samples/](https://github.com/Zeutschler/tinyolap/blob/main/samples).or visit [tinyolap.com](https://tinyolap.com) . 

If you want to use the TinyOlap package only, without the samples, then you can install TinyOlap using pip:

    pip install tinyolap

## How To Set up a Database
Let's try to build a data model to support the quarterly business planning process of a well-known owner 
of electric car manufacturing company. So, here's how Elon Musk is doing his business planning - allegedly!

    from tinyolap.cell import Cell
    from tinyolap.decorators import rule
    from tinyolap.database import Database
    from tinyolap.slice import Slice
    
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
    
    # Purpose: Support Elon Musk on his business planning & reporting for Tesla
    def play_tesla(console_output: bool = True):
        # 1st - define an appropriate 5-dimensional cube (the data space)
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
        # 2nd - (if required) add custom business logic, so called 'rules'.
        #       Register the 2 rules that have been implemented above. Take a look.
        cube.register_rule(deviation)
        cube.register_rule(deviation_percent)

        # 3rd - (optional) some beautifying, set number formats
        db.dimensions["datatypes"].member_set_format("Deviation", "{:+,.0f}")
        db.dimensions["datatypes"].member_set_format("Deviation %", "{:+.2%}")

Now that our 5-dimensional database is setup, we can start to write and read data from the cube.
TinyOlap uses slicing syntax ``[dim1, dim2, ..., dimN]`` for simple but elegant cell access. 

        # 4th - to write data to the cubes, just define and address and assign a value
        cube["Plan", "2021", "Q1", "North", "Model S"] = 400.0  # write a single value
        cube["Plan", "2021", "Q1", "North", "Model X"] = 200.0  # write a single value
    
        # 5th - TinyOlap's strength is manipulating larger areas of data
        cube["Plan"] = 500.0  # set the existing value 400.0 and 200.0 to 500.0
        cube["Plan"].set_value(500.0, True)  # 3 x 4 x 4 x 4 = set all 192 values to 500.0
        cube["Plan", "2023"] = cube["Plan", "2022"] * 1.50  # Easily data manipulation
    
        # Let's hand in a Python function to generate the 'Actual' data.
        cube["Actual"].set_value(elons_random_numbers, True) # 3 x 4 x 4 x 4 = set 192 values
    
        # 6th - some minimal reporting
        print(Slice(cube, {"title": "Tesla - Sales 2023 by region and products",
                           "header": [{"dimension": "years", "member": "2023"},
                                      {"dimension": "periods", "member": "Year"}],
                           "columns": [{"dimension": "datatypes"}],
                           "rows": [{"dimension": "products"}]
                           }))

Here's a screenshot of the Tesla database in action. To try this on your own, simply run 
the [/samples/tesla_web_demo.py](https://github.com/Zeutschler/tinyolap/blob/main/samples/tesla_web_demo.py) script.

![Tesla Screenshot](https://github.com/Zeutschler/tinyolap/blob/main/doc/source/_logos/tesla_screenshot.png?raw=true)

To dive deeper, please visit the **TinyOlap website and documentation** at [https://tinyolap.com](https://tinyolap.com)
or the provided samples.

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
response for most queries and supports instant *dimensional modelling* - e.g., adding new members to dimensions or adding new calculations. Finally, the implementation of business logic in Python offers endless possibilities that are
missing in the domain-specific languages of most commercial products.