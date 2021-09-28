.. attention::
   TinyOlap is still under active development. Everything might be subject of change.

==========================
TinyOlap Developer's Guide
==========================

TinyOlap is a super-light-weight multi-dimensional in-memory OLAP database (often called a
`MOLAP <https://en.wikipedia.org/wiki/Online_analytical_processing#Multidimensional_OLAP_(MOLAP)>`_
Database) written in plain Python. TinyOlap follows the :ref:`model-driven approach <model_driven>`
which is very suitable for use cases such as planning, budgeting, simulation and reporting.

Basic Usage
-----------

The basic idea of the *model-driven* approach is to explicitly define the multi-dimensional data space
that describes a certain business problem or problem domain. Data space consist of
:ref:`dimensions <dimensions>` and :ref:`cubes <cubes>`. The cubes constitute the actual data space and
a set of dimensions defines the multi-dimensional axis of that data space. Dimensions are flat or
hierarchical lists of :ref:`members <members>`. Then, members from each dimension of a cube can be combined
to build a :ref:`cell address <cells>`, which is then used to access individual cells of the cube for read and write.
At all, TinyOlap is a cell-oriented database, query languages like SQL or MDX are not (yet) supported.

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

Use Cases for TinyOlap
---------------------------

TinyOlap is highly suitable for research and educational purposes in computer science as well as in business studies.
I actually use TinyOlap for teaching my master class students in "Business Analytics" at the HSD University for
Applied Science in Düsseldorf (Germany). Although Tinyolap might be helpful for evaluation and experimental purposes
for professional use cases, it is neither intended nor recommend to be used for any kind of production purposes,
especially not for larger data volumes > 1m records. TinyOlap is provided AS-IS and without any warranty, please
refer the :ref:`provided MIT license <license>` for further details.

Some Background Information
---------------------------
TinyOlap has started as a by-product of a research project I'm currently working on. I needed a light-weight
and free and fast MOLAP database, and as there was none available, I decided to build one. Python was chosen
as most of the research project (data science stuff) is also implemented in Python.

TinyOlap uses plain Python collection objects like lists, tuples, sets and especially dictionaries to implement
all the multi-dimensional magic. I tested also implementations using Pandas dataframes, NumPy arrays and also a
ROLAP implementation using in-memory SQLite. Interestingly, the usage of the build-in Python objects clearly
outperforms all the other approaches I tested (e.g. 10x to 50x faster that SQLite for real world uses cases).
And thanks to Pythons super powerful list comprehension feature it was also quite easy to implement.

TinyOlap is also a reminiscence and homage to the early days of OLAP databases, where great products like
Applix TM/1 (now IBM) or MIS Alea (nor infor) enabled business users to build expressive data models with
dimension, cubes and complex business logic in just a few minutes our hours. Unfortunately, these products
have grown up to complex and very expensive client-server database technologies, all striving for the ultimate
performance on mass data processing and high number of concurrent users.

In contrast, TinyOlap is intended to stay **free, simple and focussed** on local, client-side planning,
budgeting, calculations and analysis purposes using Python.

.. about_performance::

Some Words About Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
All calculations in TinyOlap are executed *on-the-fly* and in-memory, no aggregations needed to be recalculated
or updated. Any change to the database is instantly reflected in subsequent queries. This is perfect for planning
and manual data entry purposes (a web frontend is already in the making). In addition TinyOlap provides some
(optional) trivial, but effective built-in caching capabilities that further improve performance. TinyOlap
provides sub-second response for most queries - most often even in the range of a few milliseconds - and
supports instant *dimensional modelling* - e.g., adding new members to dimensions or adding new calculations.

Surprisingly, performance-wise TinyOlap is not that bad all for being written in plain Python.
For smaller use cases (< 100k records) TinyOlap might even outperform solutions like SAP HANA, TM/1 or
Jedox - not because TinyOlap is faster by any means - these professional products are actually by
magnitudes faster on calculations and aggregations - but as client-server solutions they have to
heavily deal with `marshalling https://en.wikipedia.org/wiki/Marshalling_(computer_science))`
(sending data from the server to the client over the network) what TinyOlap, as a a simple in-process
solution, does not need to care about. By this, you can consistently execute 100k cell read requests per second
against an 8-dimensional cube and expect an average aggregation- and calculation-throughput of roughly 1.5m cells
on a M1 Macbook Air, without caching. Caching greatly improves the user experience.

Thta said, TinyOlap should also be **fun and fast** with most data models with up to a 1m records.
But if your data model contains extensive calculations, e.g. if your trying to calculate a 4-dimensional
Mandelbrot set with TinyOlap you might get disappointed. That said, TinyOlap is not intended to be used for
any kind of mass data processing or analysis, and also not for production purposes. Use professional products instead
TinyOlap is perfect for evaluations, testing and education purposes.

Writing values back to TinyOlap cubes is also acceptable fast and most often at 100k records per second when in full
in-memory mode (on a M1 Macbook Air). When writing to disk (for that you need to set ``in-memory = False`` or skip the
in-memory argument when you create a database) this value will drops down to 20k records per second or less.
This is due to the fact, that the records needs to be stored in an SQLite database, which TinyOlap uses as file
storage backend. If your computer still has a mechanical HDD this value might even drop dramatically down to just
2k records per seconds.

Limitations
^^^^^^^^^^^
As of today, TinyOlap is built upon the relational database SQLite
(https://www.sqlite.org). This implies that TinyOlap is subject to certain
limitations, for instance:

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

Table of Contents
==================

.. toctree::
   :maxdepth: 3

   setup
   usage
   model_driven
   best_practise
   databases
   cubes
   dimensions
   formulas
   server
   license


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
