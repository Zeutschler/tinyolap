.. _sqlquery:

=======================
SQL Support in TinyOlap
=======================

Currently TinyOlap only comes with very little support for SQL queries.
But although far from complete, the available SQL support is quite useful for many purposes.
Let's take a look at some SQL queries using the **tiny** sample database.

The **tiny** sample database ('*...tinyolap/samples/tiny.py*') contains a **Sales** cube which
consists of the following 5 dimensions, bases members and *aggregated* members:

-  **years**: 2021, 2022, 2023, *All years*

-  **months**: Jan, Feb, ..., Dec, *Q1*, ..., *Q4*, *Year*.
   In addition, the months dimension has a *member subset* called **summer** that contains the
   members Jun, Jul, Aug and Sep.

-  **regions**: *Total*, North, South, West, East.
   The regions dimension also has a *member attribute* called **manager** that contains the
   following attribute values:

   -  *Total* = "Peter Parker"
   -  North = "Ingmar Ice"
   -  South ="Carlo Carulli"
   -  West:=Heinz Erhardt"
   -  East="Pyotr Tchaikovsky"

-  **products**: *Total*, *cars*, coupe, sedan, sports, van, trucks, motorcycles, *best sellers*)

-  **measures**: Sales, Cost, Profit, Profit in %.
   Two of these measures are defined through rules:

   -  Profit := Sales - Cost

   -  Profit in % := Profit / Sales


Simple SQL queries
---------------------

The common structure for all SQL queries in **TinyOlap** is as follows:

    **SELECT** *[fields to be returned]* **FROM** *[cube]* **WHERE** *[filters to be applied]*

To return the value for a certain cell in the cube Sales, you need to define a member for each
of the cube dimensions: ::

    SELECT * FROM Sales WHERE '2021', 'Jan', 'North', 'motorcycles', 'Sales'

Although the order of the members in the above sample query is not important, to keep the order
helps to maintain the consistency over multiple queries. The query engine automatically
tries to resolve the members against all dimensions of the cube. You can also explicitly
define to dimension for each individual dimension. ::

    SELECT * FROM Sales WHERE
       years:'2021', months:'Jan', 'North',
       products:'motorcycles', measures:'Sales'

Although is some more code to write, it greatly supports the readability of your SQL statements and also
overcomes certain issue, e.g., as a member named **Total** exists in two dimensions (**regions** and **products**)
the following will fail: ::

    SELECT * FROM Sales WHERE
       '2021', 'Jan', 'Total', 'Total', 'Sales'

But this query would work just fine: ::

    SELECT * FROM Sales WHERE
       '2021', 'Jan', regions:'Total', products:'Total', 'Sales'


The query resultset
^^^^^^^^^^^^^^^^^^^
All of the above queries use the wildcard character ***** for the **SELECT** statement. This will
cause the query engine to return the member name for all dimension of the cube and the value of the cell
for all returned records as a Python list (rows) of lists (column values), e.g., like this:

+------+-----+-------+-------------+-------+--------+
| 2021 | Jan | North | motorcycles | Sales | 525.34 |
+------+-----+-------+-------------+-------+--------+

.. code:: python

    query = Query(db)
    query.execute("SELECT * FROM Sales WHERE '2021', 'Jan', 'North', 'motorcycles', 'Sales'")
    data = query.records

So, the ``data`` variable will actually contain something like this.

.. code:: python

    data = [['2021', 'Jan', 'North', 'motorcycles', 'Sales', 123.45]]

As you can see, the names of the name of columns are not contained in the returned ``record`` array.
This behaviour can be changed through the property ``query.include_column_names = True``.

.. code:: python

    query = Query(db, include_column_names=True)
    query.include_column_names = True  # alternative approach to include column names
    query.execute("SELECT * FROM Sales WHERE '2021', 'Jan', 'North', 'motorcycles', 'Sales'")
    data = query.records

+-------+--------+---------+-------------+----------+--------+
| years | months | regions | products    | measures | value  |
+=======+========+=========+=============+==========+========+
| 2021  | Jan    | North   | motorcycles | Sales    | 525.34 |
+-------+--------+---------+-------------+----------+--------+


Defining the fields to be returned
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As alternative to the wildcard character ***** for the **SELECT** statement, you can also specify
the columns that should be returned. As of to today only the member name for specific
dimensions and/or (if defined) the attribute value of a member from a specific dimension can be returned.
e.g., the following SQL statements requests the member names for the dimensions months and regions, but
also the manager attribute from the regions dimension. ::

    SELECT months, regions, regions.manager FROM Sales WHERE
       '2021', 'Jan', 'East', 'vans', 'Sales'

The resulting records would look something like this:

+--------+---------+-------------------+--------+
| months | regions | regions.manager   | value  |
+========+=========+===================+========+
| Jan    | East    | Pyotr Tchaikovsky | 525.34 |
+--------+---------+-------------------+--------+

Although not explicitly requested, the query engine automatically adds a **value** column to the
resultset containing the current cell value. But you can also specific **value** as an explicit
column name. The following statement shows an example. ::

    SELECT months, value, regions, regions.manager FROM Sales WHERE
       '2021', 'Jan', 'East', 'vans', 'Sales'

The resulting records would look something like this:

+--------+--------+---------+-------------------+
| months | value  | regions | regions.manager   |
+========+========+=========+===================+
| Jan    | 525.34 | East    | Pyotr Tchaikovsky |
+--------+--------+---------+-------------------+

Underdefined WHERE statements
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Although recommended, is not necessary to define a member for all dimensions of the cube in the WHERE statement.
For every dimension that is not defined, the query engine automatically determines the topmost members for each
dimension and adds these to the query. So the following statements are valid and return


More advanced SQL queries
----------------------------

**Usage:** Open and/or start the script *...tinyolap/samples/tiny.py*


.. autoclass:: tinyolap.query.Query
    :members:
    :noindex:
