.. attention::
   TinyOlap is under active development and therefore subject of change.

   Please refer :ref:`feature backlog <backlog>` for a high-level status overview.

=================
TinyOlap
=================

TinyOlap is a light-weight [1]_ in-process [2]_ multi-dimensional [3]_ in-memory [4]_ **OLAP database**
written in plain Python. TinyOlap follows the :ref:`model-driven approach <model_driven>` which is
suitable for many real world use cases, especially in the area of planning, budgeting, forecasting,
simulation, analysis and reporting.

.. [1] TinyOlap is standard Python, no external dependencies. You can spin up a database in milliseconds by code,
       or you can spin up an existing database using the included web api (based on the great
       `FastAPI <https://fastapi.tiangolo.com>`_, love it...︎) and build a web or remote application on top.

.. [2] TinyOlap is a simple library and running in your Python process, there is no external server.
       If you use the TinyOlap web api then TinyOlap turns into a web server on its own.

.. [3] TinyOlap allows you to create low- to high-dimensional data space, depending on the problem you want to solve.
       Then you can read and write data from that space and do multi-dimensional calculations. Aggregation is build-in.
       For advanced calculation you need to write a `rule <rules>`_, what is nothing else then a Python function.
       This is very suitable for many real world (business) and abstract problems.

.. [4] TinyOlap is an in-memory database with (optional) persistence to an SQLite database.
       Why optional? If you want to use TinyOlap just as a path-through calculation engine,
       what makes totally sense for certain use cases, then persistence might not be required.


Use cases for TinyOlap
----------------------
TinyOlap is suitable for a huge variety of use cases, where aggregation and calculation
in multidimensional data space is required or makes sense. Actually, most business problems
are multi-dimensional:

    If you for instance sell **1.** products to **2.** customers over certain **3.** channels over **4.** time,
    then you already have a **4-dimensional business problem** on which TinyOlap will perfectly support you.

Some use case where TinyOlap will shine:

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
  TinyOlap was actually build to support a research project in the area of AI.

For such use cases, TinyOlap is much more intuitive and simpler to use than, e.g., a relational database
and building your business logic in SQL the hard way. Another nice side effect, TinyOlap is in comparison
most often much faster on such queries than relational databases.

And there is also :ref:`one thing that makes TinyOlap really unique<what_makes_tinyolap_unique>`
in the database space...

But whatever you do, please keep in mind, that TinyOlap is just interpreted Python code. Meaning, although
Tinyolap is perfect for evaluation and testing and small to mid-size use cases, **TinyOlap is neither
intended nor recommend to be used for any large scale production purposes**. If you want to experience
how well or not well TinyOlap behaves on larger data volumes, then please try the 'huge' sample database
and set the increase the ``numbers_of_records`` at the top of file 'huge.py'. For larger data volumes,
say > 5m records you need to test, if TinyOlap still meets you performance requirements.

TinyOlap is provided AS-IS and without any warranty, please refer the :ref:`provided license <license>`
for further details.


Basic Usage
-----------
The basic idea of the **model-driven approach** is, to explicitly define the multi-dimensional
data space that describes a certain business problem as a first step. Data space consist of
:ref:`dimensions <dimensions>` and :ref:`cubes <cubes>`. Cubes represent the multi-dimensional data space,
made up by a set of dimensions whihc define the axis of the multi-dimensional data space. Dimensions are
flat list or hierarchies of :ref:`members <members>`.

To access a cube, members from each of the cube dimensions are combined
to build a :ref:`cell address <cells>`. With these addresses you can access the individual cells of the cube for
read and write purposes. At all, TinyOlap is a **cell-oriented MOLAP database**, query languages like SQL or
MDX are not (yet) supported. Any request requires a cell address.

Let's try to build a data model to support the quarterly business planning process of a well-known car manufacturer.

.. code:: python

    from tinyolap.database import Database

    # setup a new database
    db = Database("tesla")

    # define dimensions
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

.. code:: python

    # write some value to the cube
    cube["Actual", "2021", "Q1", "North", "Model S"] = 1000.0
    cube["Actual", "2021", "Q2", "West", "Model S"] = 500.0
    cube["Actual", "2021", "Q3", "West", "Model 3"] = 20.0

    # read values
    v = cube["Actual", "2021", "Q1", "North", "Model S"]  # returns 1000.0
    v = cube["Actual", "2025", "Q1", "East", "Model X"]   # returns 0.0
    v = cube["Actual", "2021", "Year", "West", "Total"]   # returns 1500.0
    v = cube["Actual", "2021", "Year", "Total", "Total"]  # returns 1520.0

To learn more on how to build :ref:`databases<databases>`, :ref:`dimensions <dimensions>`
and :ref:`cubes <cubes>` and all the cool and advanced feature of TinyOlap, please continue
with the :ref:`getting started guide<setup>`. Enjoy...



Why TinyOlap was implemented?
----------------------------
TinyOlap has started as **a by-product of a research project in the area of artificial intelligence**
I'm currently working on. I needed a light-weight, free, fast, code-based MOLAP database for small to medium
sized data models. And as there was no such database available, I simply needed to build one.
Python was chosen as most of the research project (data science stuff) is also implemented in Python.

And because Python is - to my own surprise - a very elegant and highly productive language for such purposes.
In the past, I have built comparable commercial database products using C and C#. Although these were by
orders of magnitudes faster, they were a pain to implement and the implementation took months to years.

**TinyOlap is also a reminiscence and homage to the early days of OLAP databases**, where great products like
Applix TM/1 (now IBM) or MIS Alea (now Infor) enabled business users to build expressive data models with
dimension, cubes and complex business logic in just a few minutes our hours. Unfortunately, these products
have grown up to complex and very expensive client-server database technologies, all striving for the ultimate
performance on mass data processing and high number of concurrent users.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on local, client-side planning,
budgeting, calculations and analysis for research, educational, evaluation and testing purposes using Python.

.. _what_makes_tinyolap_unique:

What makes TinyOlap unique?
---------------------------
Because TinyOlap is written in plan Python, really **anything happens by code**. Although this might not seem
to be a big thing, but is actually is:
If you want to build business logic in professional OLAP databases like IBM TM/1, Jedox Palo or SAP HANA or
even in full blown CPM solution like SAP SAC, Tagetik or Anaplan, you need to rely on and use their *build-in
proprietary modelling and rules languages*. Although these build-in languages are most often super powerful
and fast, they are often hard to learn and even harder to master and often fail to support really complex
use cases. By using plain Python code, you are free and open to do whatever you want: the (upcoming)
**Plain Spotter Database** example database, which can be found in the TinyOlap samples folder, is a
funny (and useless) example of what you can do with TinyOlap.

With TinyOlap you build your business logic directly in Python. This opens up unmatched opportunities
to perform even the most complex computations and integrate whatever service or capability into your
TinyOlap database you like. Integrate `weather data from Accuweather <https://github.com/bieniu/accuweather>`_ ,
no problem. Use Facebook's very elegant `forecasting library 'Prophet' <https://facebook.github.io/prophet/>`_,
no problem. **Your imagination is the limit**, you can even blend or integrate real time data steams into your
TinyOlap cubes.

How TinyOlap internally works?
-----------------------------
TinyOlap uses plain Python objects like lists, tuples, sets and dictionaries to implement
all the multi-dimensional magic. I tested also implementations using Pandas dataframes,
NumPy arrays and also a true ROLAP implementation using in-memory SQLite.

Interestingly, the usage of the build-in Python objects clearly outperforms all the other approaches I
tested (e.g. 10x to 50x faster that SQLite for real world uses cases). And thanks to Pythons
super powerful list comprehension feature it was also quite easy to implement.

.. _about_performance:

TinyOlap performance - What to expect?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
All calculations and aggregations in TinyOlap are executed *on-the-fly* and in-memory.
Any change to the database is instantly reflected in subsequent cell requests and queries.
This is perfect for planning and manual data entry purposes (a web frontend is already in the making).

In addition TinyOlap provides some (optional) trivial, but effective built-in caching capabilities
that further improve performance. TinyOlap provides sub-second response for most queries - most often
even in the range of a few milliseconds - and supports (more or less) instant *dimensional modelling* -
e.g., adding new members to dimensions new calculations.

**Surprisingly, performance-wise TinyOlap is not that bad all**, at least for being written in plain Python.
For smaller use cases (< 100k records) TinyOlap might even outperform solutions like SAP HANA, TM/1 or
Jedox. Not because TinyOlap is the faster database by any means - these professional products are actually
magnitudes faster on calculations and aggregations - but as client-server solutions they have to
heavily deal with `marshalling <https://en.wikipedia.org/wiki/Marshalling_(computer_science)>`_
(sending data from the server to the client over the network or over process boundaries) what TinyOlap,
as a a simple in-process solution, does not need to care about. By this, you can consistently
execute up to 100k individual cell read requests per second against an 8-dimensional cube and expect
an average aggregation- and calculation-throughput of roughly 1m cells on a M1 Macbook Air, without
caching. In addition, **the build in caching greatly improves the user experience**.

.. note:: That said, TinyOlap should not be mistaken as a database for serious high performance
business purposes - TinyOlap is written plain Python, not in C.

**TinyOlap should be fun and fast** with most data models with up to a 1m records. But if your data
model contains extensive calculations, e.g. if your trying to calculate a 4-dimensional Mandelbrot set
with TinyOlap you might get disappointed. That said, TinyOlap is not intended to be used for any kind
of large scale mass data processing or analysis, and also not for production purposes. Use professional
products instead. TinyOlap is perfect for research, education, evaluation and testing purposes.

Writing values back to TinyOlap cubes is also acceptable fast and most often at 100k records per second
when in full in-memory mode (on a M1 Macbook Air). When writing to disk (for that you need to set
``in-memory = False`` or skip the in-memory argument when you create a database) this value will drops
down to 20k records per second or less. This is due to the fact, that the records needs to be stored
in an SQLite database, which TinyOlap uses as file storage backend. If your computer still has a mechanical
HDD this value might even drop dramatically down to just 2k records per seconds.

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
- The calculations capabilities of TinyOlap are sufficient for most
  planning uses cases. But still - especially when comapre to products like
  TM/1 - they maybe not sufficient for advanced use cases.

Another limitation is the fact that multi-threading and multi-processing is not
(yet) provided. This is due to the fact that multi-threading even slows down the
database and multi-processing would require a truly distributed database, what
TinyOlap is neither pretending, nor wants to be. TinyOlap is a lightweight
in-process MOLAP database for coders.

Table of Contents
==================

.. toctree::
   :maxdepth: 2

   backlog
   setup
   usage
   support
   model_driven
   best_practise
   samples
   databases
   cubes
   dimensions
   cells
   members
   areas
   rules
   sqlquery
   server
   license
   lowcode


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
