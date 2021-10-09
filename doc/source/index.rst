.. attention::
   TinyOlap is under active development. Code and API is subject of change.

=================
Developer's Guide
=================

TinyOlap is a super-light-weight multi-dimensional **in-memory OLAP database** (often called a
`MOLAP <https://en.wikipedia.org/wiki/Online_analytical_processing#Multidimensional_OLAP_(MOLAP)>`_
Database) written in plain Python. TinyOlap follows the :ref:`model-driven approach <model_driven>`
which is very suitable for business use cases such as planning, budgeting, forecasting, simulation
and reporting. And there is :ref:`one thing that makes TinyOlap stunning and unique<what_makes_tinyolap_unique>`.

Use cases for TinyOlap
---------------------------
TinyOlap is highly suitable for research and educational purposes in computer and business science, as well
as in other disciplines. In addition TinyOlap is **perfect for prototyping and testing** in professional use cases,
e.g., in business area like finance, controlling, sales, marketing and supply chain management.

Although Tinyolap might be helpful for evaluation, testing and experimental purposes, **TinyOlap is neither intended
nor recommend to be used for production purposes**. TinyOlap is provided AS-IS and without any warranty,
please refer the :ref:`provided MIT license <license>` for further details.

Basic Usage
-----------
The basic idea of the **model-driven approach** is to explicitly define the multi-dimensional data space
that describes a certain business problem or whatever multi-dimensional problem domain. Data space consist of
:ref:`dimensions <dimensions>` and :ref:`cubes <cubes>`. Cubes represent the multi-dimensional data space, made up
by a set of dimensions whihc define the axis of the multi-dimensional data space. Dimensions are flat list or
hierarchies of :ref:`members <members>`.

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

Use cases for TinyOlap
---------------------------
TinyOlap is highly suitable for research and educational purposes in computer science as well as in business
studies and other disciplines.

I actually use TinyOlap also for teaching my students at the HSD University for Applied Science in
Düsseldorf (Germany). Although Tinyolap might be helpful for evaluation, testing and experimental purposes
for professional use cases, it is neither intended nor recommend to be used for any kind of production purposes,
especially not for larger data volumes, say > 5m records. TinyOlap is provided AS-IS and without any warranty,
please refer the :ref:`provided MIT license <license>` for further details.

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
Applix TM/1 (now IBM) or MIS Alea (nor infor) enabled business users to build expressive data models with
dimension, cubes and complex business logic in just a few minutes our hours. Unfortunately, these products
have grown up to complex and very expensive client-server database technologies, all striving for the ultimate
performance on mass data processing and high number of concurrent users.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on local, client-side planning,
budgeting, calculations and analysis for research, educational, evaluation and testing purposes using Python.

.. _what_makes_tinyolap_unique:

What makes TinyOlap unique?
---------------------------
Aside of being written in Python, the very cool thing about TinyOlap is that really **anything happens by code**.
You want to build business logic in professional OLAP databases like TM/1, Palo or SAP HANA or even in full
blown CPM solution like SAP SAC, Tagetik or Anaplan you need to rely on their build-in proprietary modelling
and rules languages. Although these build-in languages are most often super powerful and fast, they are hard to
learn and even harder to master and often fail to support really complex use cases.

With TinyOlap you build your business logic directly in Python. This opens up unmatched opportunities
to perform even the most complex computations and integrate whatever service or capability into your
TinyOlap database you like. Integrate `weather data from Accuweather<https://github.com/bieniu/accuweather>` ,
no problem. Use Facebook's very elegant `forecasting library 'Prophet'<https://facebook.github.io/prophet/>`,
no problem. **Your imagination is the limit**, you can even blend or integrate real time data steams into your
TinyOlap cubes. Or take a look at the (upcoming, funny and useless) **Mandelbox** example in the TinyOlap
samples folder, to get inspired.

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
heavily deal with `marshalling <https://en.wikipedia.org/wiki/Marshalling_(computer_science)>`
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
(see `https://www.sqlite.org<https://www.sqlite.org>') for persistence.
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

   setup
   usage
   model_driven
   best_practise
   samples
   databases
   cubes
   dimensions
   rules
   server
   license


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
