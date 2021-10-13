.. _backlog:

===============
Feature Backlog
===============

TinyOlap is work in progress. This is a **high-level** overview of the core features and overall development status.

*Last Updated 13. October 2021*

-----------------

1. Available Feature
--------------------

- **Cubes** - Cubes define multidimensional space and store and process the actual data.

  - **Values** - Cubes are intended to be used for numerical data (floats), but can
    store any Python data or object type. Persistence is limited by the capabilities
    provided through `pickling and unpickling <https://docs.python.org/3/library/pickle.html>`_
    of Python objects.

-----------------

- **Dimensions** - Dimensions define the axis of a cube. They main contain a list or
  hierarchy of members. Hierarchies defined the aggregation logic of cubes.

  - **Members** - String keys to access data. by defining a multidimensional address of
    all dimensions of a cube.

  - **Member Alias** - (1...N) Alias keys to access members. Helpful to provide access to
    members via multiple keys, e.g. a business keys and technical keys. Useful for data importing.

  - **Subsets** - (1...N) Lists of members. Useful for display or calculation purposes.

  - **Attributes** - (1...N) Attributes per member

-----------------

- **Cells** - Cells are python objects that provide easy access to cube cells.
  Most importantly they can be used in Python calculations and mainly behave as floats.

- **Area** - Areas of data from a cube to define an orthogonal subspace. Useful for
  any kind of mass data manipulations (delete, copy etc.), provide basic arithmetic
  opertaions.

-----------------

- **Rules** - Rules add custom business or program logic to cubes. Rules are plain Python
  functions or methods and most often evaluate numeric expressions from data in cubes.
  Rules need to be registered for a cube. There are different flavors of rule

  1. **All level rules** - Get executed for cell requests on aggregated and base level cells.

  2. **Base level rules** - Get executed for cell requests on base level cells only.

  3. **Aggregation level rules** - Get executed for cell requests on aggregated cells only.

-----------------

- **Slice** - Minimal implementation of a report layout for console output.

-----------------

- **Samples Databases** - Samples to showcase how to build real world TinyOlap databases.

  - **Tiny Database** - A very small (tiny) database build 100% by code showcasing most the
    of TinyOlap capabilities.

  - **Tutor Database** - A small to medium sized OLAP data model for sales data. Based on a
    historic set of CSV and custom files from 1994. Shipped with MIS Alea at that time.

-----------------

2. Under Development
--------------------

- **Web API** - A web API server, utilizing FastAPI, to serve TinyOlap databases.

- **Web Frontend** - A minimalistic web frontend on top of the Web API. Providing capabilities
  to browse (slice and dice) and manually enter data

-----------------

- **Cubes** - Additional Cube features.

  - **Rules** - Additional rules variants.

    - **Roll-Up rules** - Overwrite the actual base level values of a cube and will get aggregated.

    - **Push rules** - Get executed when data is entered or imported into a cube.

-----------------

3. Backlog
----------

- **Cubes** - Additional Cube features.

  - **Splashing** - The capability to enter data on aggregated cells to automatically break
    them down to the bases level cells of a cube.

-----------------

- **Data Importers** - Capabilities to easily import data from files and other source like
    Pandas data fames.

  - **Auto Importer** - Generate a database or cube from a file, incl. setup of dimensions
    and data import.

  - **Pandas Importer** - Generate a database or cube from one or more
    `Pandas <https://pandas.pydata.org>`_ data frames.

-----------------

- **Console GUI** - A simple console gui for interaction with databases and cubes.

-----------------

- **Samples Databases** - More samples.

  - **Integrated Planning Database** - A template for integrated planning purposes
    with sales, hr, production, P&L, balance sheet and cash flow. Including currency
    conversion and auto forecasting using ML.

  - **Plane-Spotter Database** A near real-time database (both contents and structure)
    based on open source flight radar data.

  - **Personal Expense Tracker Database** A simple data model to track and manage
    monthly spend.

-----------------

- **CI/CD** - Automated CI/CD pipeline to publish to `tinyolap.com <https://www.tinyolap.com>`_.

-----------------

- **Promotion** - To inform others about TiynOlap.

  - **One-Pager** - A short document explaining the main features of TinyOlap.

  - **Slide Deck** - An introduction to TinyOlap.

  - **Cheat Sheet** - A cheat sheet for TinyOlap developers.

  - **Blog post** - Introduction to TinyOlap post, for medium etc.

  - **Video** - Introduction video to TinyOlap.

  - **Homepage** - A nice homepage.

-----------------

4. Future Ideas
--------------

- **Port to JavaScript** - It should be possible to port TinyOlap to Javascript to run a database
  directly in the browser as a client side application. Performance should be comparable to
  the current Python implementation.

-----------------

- **Public Data Model Repository** - A community driven directory of data models for various purposes.
  Either to provide data models to others or data. Either as code and files (preferrable) or as
  prebuild TinyOlap databases, with data or without.
