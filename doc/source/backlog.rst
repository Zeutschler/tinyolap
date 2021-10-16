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

  - **MemberContext Alias** - (1...N) Alias keys to access members. Helpful to provide access to
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

-----------------

- **SQLite Backend** - Stores data model and data to a file.
  Rework required: Simplified, faster and more compact persistence.

  .. note::
        Current persistence is much to complex (and slow) due to true multi-dimensional storage.
        Should be replace by fixed column layout, encapsulating complexity through json objects.
        This would also greatly help to provide simple string based encryption.

-----------------

- **Cubes** - Additional Cube features.

  - **Rules** - Additional rules variants.

    - **Roll-Up rules** - Overwrite the actual base level values of a cube and will get aggregated.

    - **Push rules** - Get executed when data is entered or imported into a cube.

    - **Command rules** - Get executed when explicitly called (by code only), also require a cell context.

-----------------

3. Backlog
----------

- **Web Frontend** - A beautiful, minimalistic but innovative web frontend on top of the Web API.
  Providing capabilities to navigate (slice and dice), analyse and enter data. Mobile first.

  .. attention::
    This is undoubtedly the most important component for the overall **success of TinyOlap**.

  - **Grid** - A minimalistic, visually reduced grid with alternatively fixed (browser-style)
    or unfixed (report style) row and column axis.

  - **Cursor** - A cell cursor, as in Excel, either by finger/mouse or keyboard, supporting
    instant editing (start typing to edit).

  - **CellContext Swiping** - The selected cell should have a small *gripper* attached (left or right).
    By taking and swiping or dragging the gripper up, down, left and right individual menus should
    appear that contain *drag targets* to invoke certain functionality. e.g.

    - **delete** the cell value(s)

    - **fix** the value to prohibit changes on splashing etc.

    - **analyze** the cell, e.g. like PowerSearch in DeltaMiner

  - **Dimension Editing** - Renaming, adding and removing members.


-----------------

- **Cubes** - Additional Cube features.

  - **Cube/CellContext Comments** - A minimalistic discussion thread over cubes and cells,
    enabling users to discuss and exchange information. Maybe with attachments.

  - **Splashing** - The capability to enter values on aggregated cells to automatically
    process the break down to the bases level cells of a cube.

    - **Distribution** - Enter value on oe modify aggregated measure, evenly distribute values.

    - **Copy** - Copy from one member or multi-member-context to another.

    - **Delete** - Delete values and data areas.

    - **Fill** - Fill all cells with the same value.

    - **Command Rules** - Command rules are custom rules that get executed when a
      predefined keyword is entered by a user for a given cell content. Such rules
      need to specify the optional 'command' argument in the rules decorator.

      If entered in cells, commands must start with special character, e.g. '#'.

      .. code:: python

            @rule(cube:"sales", pattern:"Profit", command:"Double")
            def rule_profit(c: tinyolap.cell.CellContext):
                # 'profit' is defined as 'sales' - 'cost'
                c["Sales"] *= 2
                c["Cost"] *= 2

            # Command to 'double the profit', only available on cells addressing the member 'Profit'.
            c.Execute("Double")         # explicit call
            c["Profit"] = "#Double"     # implicit call by setting a value

    - **Build-In Command Rules** - There should be also a list of build-in commands
      to execute generic action or data processing tasks to data. e.g.:

      - **'Bookmark' Command** - Creates a named or unnamed bookmark for time travel.

      .. code:: python

            # Set a global bookmark for time travel. Both calls are identical.
            c.Execute("Bookmark", "Planning 2023", "Start of planning session 2023")
            database.trimetravel.add_bookmark("Planning 2023", "Start of planning session 2023")

    - **Forecast** - Extrapolates a series of values.

      .. code:: python

            # forecasts a single value based on 'actual' data for a given cell context
            # based on series derived from the subsequent members of the dimensions 'years' and 'months'
            c.forecast(["years", "months"], "data_type:actual")

  - **Time Maschine** - Ability to travel back and forth over changes made to the data base
    in regards of structure and data. Only available for persistent databases.

  - **Log** - Log all user information and changes to the database, mainly to enable time travel.

  - **Custom aggregations** - Aside of aggregations along the member hierarchies, this will
    enable the following aggregations individually and in combination:

    - **Subset Aggregations** - Aggregations based member subsets.

      .. code:: python

            # aggregate all member of the subset 'new cars' of dimension 'cars'
            total_of_new_cars = c["cars:new cars"]     # specific
            total_of_new_cars = c["new cars"]          # will work, if no conflicts occur

    - **Attribute Aggregations** - Aggregations based on member attribute values.

      .. code:: python

            # aggregate all member of dimension 'cars' that have attribute 'color' == 'blue'
            total_of_blue_cars = c["cars:color:blue"]   # specific
            total_of_blue_cars = c["color:blue"]        # will work, if no conflicts occur
            total_of_blue_cars = c["blue"]              # will work, if no conflicts occur

    - **Multi-MemberContext Aggregations** - Aggregations based on a list of members.

      .. code:: python

            # aggregate the members 'sports' and 'sedan' of dimension 'cars'
            sports_and_sedan_cars = c["cars:sports, sedan"]  # specific
            sports_and_sedan_cars = c["sports, sedan"]       # will work, if no conflicts occur

            # aggregate all member of dimension 'cars' that have attribute 'color' == 'blue' or 'red'
            red_n_blue_cars = c["cars:color:blue, red"]  # specific
            red_n_blue_cars = c["color:blue, red"]       # will work, if no conflicts occur
            red_n_blue_cars = c["blue, red"]             # will work, if no conflicts occur

    - **Wildcard Aggregations** - Aggregations based on wildcard search (not regular expressions).

      .. code:: python

            # aggregate all member of the 'cars' dimension starting with 's'.
            total_of_new_cars = c["cars:s*"]  # specific, would return (sedan, sports)
            total_of_new_cars = c["s*"]       # will probably NOT work due to ambiguities over multiple dimensions

  - **Fixing** - The ability to fix and protect cells from being changed, e.g. when splashing
    or deleting values.

-----------------

- **Security and Authorization** - To enable encryption and multi-user management.

  - **User Management** - The main idea is to know *who has done what and when* to enable
    collaboration and process data in the context or related to a user.

    There should be a *user* and *user group* concept. Rights are assigned to groups,
    users are assigned to groups. We need to further think about this...

  - **Encryption** - Secure encryption requires a single encryption key and therefore
    enycrypted database can only opened or started with the 'admin' account.

    .. attention::
       As SQLite does not support encryption and authorization out of the box we need
       to encrypt the content of the database by ourselves. As most data ist store
       in json, this should not be a (very) big thing.

  - **Default Behavior** - When a new database is created (by code), the default user
    is always 'admin' and no explicit login is required. For existing databases, without
    encryption and authorization enabled, also no explicit login should be required.

  - **Authorization** - Users should be restricted to read (see), write or modify certain
    cubes and members in dimensions. Authorization should be managed by dedicated cubes (like
    in MIS Alea).

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
