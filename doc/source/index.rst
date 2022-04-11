.. attention::
   TinyOlap is under active development and therefore subject of change.

   Please refer :ref:`feature backlog <backlog>` for a high-level status overview of the development process.

...back to `tinyolap.com <https://tinyolap.com>`_

=================
TinyOlap
=================

TinyOlap is a light-weight [1]_ in-process [2]_ multi-dimensional [3]_ in-memory [4]_ **OLAP database**
written in plain Python. TinyOlap follows the **model-driven approach** which is
suitable for many real world use cases, especially in the area of planning, budgeting, forecasting,
simulation, analysis and reporting.

.. [1] TinyOlap is standard Python, the core library has just a very few external dependencies.
       You can spin up a new database in milliseconds by code,
       or you can open an existing database with just 1 line of code. Using the included API (based on the genius
       `FastAPI <https://fastapi.tiangolo.com>`_, love it...︎) you can build web or remote applications using TinyOlap.

.. [2] TinyOlap is a simple library and running in your Python process, there is no external server.
       If you use the TinyOlap API then TinyOlap turns into a web server on its own.

.. [3] TinyOlap allows you to create low- to high-dimensional data space, depending on the problem you want to solve.
       Then you can read and write data from that space and execute multi-dimensional calculations.
       Aggregation along hierarchies over all dimensions is build-in.
       For advanced calculation you can write a `rule <rules>`_, just in plain Python.
       This is very suitable for many real world (business) and abstract problems.

.. [4] TinyOlap is an in-memory database with (optional) persistence to an SQLite database.
       Why optional? If you want to use TinyOlap just as a path-through calculation engine -
       what makes totally sense for certain use cases - then persistence might not be required.



Use Cases For TinyOlap
----------------------
TinyOlap is suitable for a huge variety of use cases, where aggregation and calculation
in multidimensional data space is required or makes sense. Actually, most business problems
are multi-dimensional by nature:

    If you for instance sell **1.** products to **2.** customers over certain **3.** channels over **4.** time,
    then you already have a **4-dimensional business problem** on which TinyOlap will perfectly support you.

Some use cases where TinyOlap will shine:

- TinyOlap is perfect for prototyping, testing and small to medium size use cases in enterprise
  performance management, as in the areas of finance, controlling, sales, marketing, human resource,
  supply chain and others.

- TinyOlap is when useful, when you have data containing certain attributes - the attributes will make
  up your dimensions in multi-dimensional space - and you need to do aggregations (or counting) or
  calculations over these attributes. e.g. to provide statistics for user requests, process incoming
  sensor data or statistics over the the clubs and players of a basketball or football league.

- TinyOlap can be also used as intelligent data processing engine, where a lot of business logic needs
  to be applied. e.g. for any kind mathematical or financial data processing, incl. advanced stuff
  like legal consolidation or portfolio optimization.

- For research and educational purposes in computer and business science, as well other disciplines.
  Building multi-dimensional data models is great for students to learn abstract thinking and simple coding.
  TinyOlap was actually build to support a research project in the area of analytics and AI, where we feed
  neuronal networks with thousands of TinyOlap databases for training purposes.

For such use cases, TinyOlap is much more intuitive and simpler to use than, e.g., a relational database
and building your business logic in SQL the hard way. Another nice side effect, TinyOlap is in comparison
most often much faster on many small queries compared to relational databases.

There is even :ref:`one thing that makes TinyOlap really unique<what_makes_tinyolap_unique>`
in the database space...

But whatever you intend to do with TinyOlap, please keep in mind, that TinyOlap is just interpreted Python code.
That means, although Tinyolap is perfect for evaluation and testing and small to mid-size use cases,
**TinyOlap is neither intended nor recommend to be used for any large scale production purposes**.
If you want to experience how well or not well TinyOlap behaves on larger data volumes, then please try
the 'huge' sample database and maybe even increase the ``numbers_of_records`` at the top of file 'huge.py'.
For larger data volumes, say > 5m records you need to test, if TinyOlap still meets you performance requirements.

TinyOlap is provided AS-IS and without any warranty, please refer the :ref:`provided license <license>`
for further details.


The Basic Idea Of TinyOlap
--------------------------
TinyOlap is following the **model-driven database approach**. The basic idea of this approach is, to explicitly define
a multi-dimensional data space that describes your business problem as a first step. Such data spaces consist of
:ref:`dimensions <dimensions>` and :ref:`cubes <cubes>`. Cubes represent multi-dimensional tables,
made up by a set of dimensions which define the axis of their multi-dimensional space. Dimensions are
flat list or hierarchies of :ref:`members <members>`.

To access data in a cube, members from each dimension of the cube are combined to build a :ref:`cell address <cells>`.
With these addresses you can access the individual cells of the cube for read and write purposes.
At all, TinyOlap is a **cell-oriented MOLAP database**, and although SQL is rudimentarily supported
(MDX is not yet supported), the most fun and efficient way is work with Python code.
So you will predominately define and manipulate :ref:`cells <cells>` and so called :ref:`data areas <areas>`.


How To Setup A Simple Database
------------------------------
Let's try to build a data model to support the quarterly business planning process of a well-known owner
of electric car manufacturing company. So, here's how Elon Musk is doing his business planning - allegedly!

.. code:: python

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

.. code:: python

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

To learn more on how to build :ref:`databases<databases>`, :ref:`dimensions <dimensions>`
and :ref:`cubes <cubes>` and all the cool and advanced feature of TinyOlap, please continue
with the :ref:`getting started guide<getting_started>`.



Motivation For TinyOlap
-----------------------
TinyOlap has started as **a by-product of a research project in the area of artificial intelligence**
we're currently working on. We needed a light-weight, free, fast, code-based MOLAP database for small to medium
sized data models. And as there was no such database available, I simply decided to build one.
Python was chosen as most of the research project (data science stuff) is also implemented in Python.

**TinyOlap is also a reminiscence and homage to the early days of OLAP databases**, where great products like
Applix TM/1 (now IBM) or MIS Alea (now Infor) or Jedox enabled business users to build expressive data models with
dimension, cubes and complex business logic in just a few minutes our hours. Unfortunately, these products
have grown up to complex and expensive client-server technologies, all striving for the ultimate
performance on mass data processing and high number of concurrent users to generate their revenue stream.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on local, client-side planning,
budgeting, calculations and analysis for research, educational, evaluation and testing purposes using Python.

.. _what_makes_tinyolap_unique:

What Makes TinyOlap Unique?
---------------------------
Because TinyOlap is written in plan Python, really **anything can happen through code**.
Although this might not seem to be a big thing, it actually is:
If you want to build business logic in professional OLAP databases like IBM TM/1, Jedox Palo or SAP HANA or
even in full blown CPM solution like SAP SAC, Tagetik or Anaplan, you need to rely on and use their *build-in
proprietary modelling and rules languages*. Although these build-in languages are most often super powerful
and fast, they are often hard to learn and even harder to master and often fail to support really complex
use cases. By using plain Python code, you are free and open to do whatever you want to do: the
**Plain Spotter Database** example database, which can be found in the TinyOlap samples folder, is a
funny (likely useless) example of some crazy things can do with TinyOlap.

With TinyOlap you can define your business logic directly in Python. This opens up unmatched opportunities
to perform even the most complex computations and integrate whatever service or capability into your
TinyOlap database. Integrate `weather data from Accuweather <https://github.com/bieniu/accuweather>`_ ,
no problem. Use Facebook's very elegant `forecasting library 'Prophet' <https://facebook.github.io/prophet/>`_,
no problem. **Your imagination is the limit**, you can even blend or integrate real time data steams into your
TinyOlap cubes.

How TinyOlap Internally Works?
------------------------------
TinyOlap uses plain Python objects like lists, tuples, sets and dictionaries to implement
all the multi-dimensional magic. I also tested implementations using Pandas dataframes,
NumPy arrays and also a true ROLAP implementation using in-memory SQLite.

Interestingly, the usage of the build-in Python objects clearly outperforms all the other approaches,
e.g. 10x to 50x faster than SQLite for most real world uses cases.

But there is much room for improvements, e.g. compressed bitmap indexes, like the genius
`Roaring Bitmaps <https://roaringbitmap.org>`_ are not yet used, but could potentially help
to minimize the memory footprint and maximize performance of TinyOlap.

.. _about_performance:

TinyOlap Performance - What To Expect?
--------------------------------------
Calculations and aggregations in TinyOlap are executed ***on-the-fly*** and in-memory.
Any change to the database is instantly reflected in subsequent cell requests and queries.
This is perfect for planning and manual data entry purposes (a web frontend is already in the making),
where users constantly enter and change values and instantly need feedback on the impact.

Our initial requirement was that TinyOlap provides sub-second response time for most queries
and also supports (more or less) instant *dimensional modelling* -
e.g., adding new or removing members of dimensions or add or replace new calculations. TinyOlap delivers that.

**Surprisingly, performance-wise TinyOlap is actually not bad at all**, at least for being written in plain Python.
For smaller use cases (< 100k records) TinyOlap might even outperform solutions like SAP HANA, TM/1 or
Jedox. Not because TinyOlap is the faster database by any means - these professional products are actually
magnitudes faster on calculations and aggregations - but as client-server solutions they have to
heavily deal with `marshalling <https://en.wikipedia.org/wiki/Marshalling_(computer_science)>`_
(sending data from the server to the client over the network or over process boundaries) what TinyOlap,
as a a simple in-process solution, does not need to care about. By this, you can consistently
execute up to 100k individual cell read requests per second against an 8-dimensional cube and expect
an average aggregation- and calculation-throughput of up to 1m cells on a M1 Mac, without
caching.

Finally perfromance very much depends on the use case. You'll need to try.
Some facts (M1 Macbook Air, no caching):

* 1M records will require ∼1GB RAM (I need to admit, 1k per record is not that efficient)
* ∼100k records/sec when doing data imports
* ∼2.5M aggregations/sec (8-dim cube) for a mixed workload of base level and aggregated cells
* ∼25T cell-queries/sec (*with caching on and warm cache you can expect ∼150T cell-queries/sec.*)

You see, **the build in caching greatly improves the user experience**. In read mostly scenarios - like reporting -
TinyOlap can get even super fast. When the cache has warmed up, most values are returned from a very fast Python
dictionary lookup.

.. note:: That said, TinyOlap should not be mistaken as a database for serious high performance
           business purposes - TinyOlap is written plain Python, not in C.

**TinyOlap should be fun and fast** for data models with up to a 1m records. But if your data
model contains extensive calculations, e.g. if your trying to calculate a 4-dimensional Mandelbrot set
with TinyOlap (what is possible) you might get disappointed. That said, TinyOlap is not intended to be
used for any kind of large scale mass data processing or analysis, and also not for production purposes.
Use professional products instead. TinyOlap is perfect for research, education, evaluation, testing
and small to medium use case purposes.

Writing values back to TinyOlap cubes is also acceptable fast and most often up to 100k records per second
when in full in-memory mode (on my M1 Macbook Air). When writing to disk (for that you need to set
``in-memory = False`` or simply skip the in-memory argument when you create a database) this value will drop
down to 20k records per second or less. This is due to the fact, that the records needs to be stored
in an SQLite database, which TinyOlap uses as file storage backend.

TinyOlap Limitations
--------------------
As of today, TinyOlap is built upon a relational database SQLite
(see `https://www.sqlite.org <https://www.sqlite.org>`_) for persistence.
This implies that TinyOlap is subject to certain limitations, for instance:

- SQLite is not a client-server database, so TinyOlap is not one.
  Saying that, TinyOlap in server-mode should serve a team of up to 10 users
  just fine.
- TinyOlap is not intended for mass data processing. Although also more than
  1 million records will work fine, it can get a bit too slow for your use.
  case. That said, 1 million records is already huge amount of data a planning
  & reporting purposes.

Another limitation is the fact that multi-threading and multi-processing is not
(yet) provided. This is due to the fact that multi-threading even slows down the
database and multi-processing would require a truly distributed database, what
TinyOlap is neither pretending, nor wants to be. TinyOlap is a lightweight
in-process MOLAP database for coders. Enjoy...

Table of Contents
==================

.. toctree::
   :maxdepth: 2

   getting_started
   samples

   server
   databases
   cubes
   dimensions
   members
   rules
   cells
   areas
   sqlquery

   license
   support
   backlog



Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`

