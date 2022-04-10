.. _samples:

=======
Samples
=======

TinyOlap comes with a few sample databases that are intended to explain the concept of TinyOlap,
and how you can build or import your own data models and databases. You will find the samples in
the **samples** folder.

----------------
1. Tiny Database
----------------

**Usage:** Open and/or run the script *...tinyolap/samples/tiny.py*

Purpose of the Tiny data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Tiny** data model is a very small and simple demo database created with Python code.
It's contains just very small 5 dimensions and 1 cube that reflects some **sales** data.
The intended use is to showcase the basic operations to create a TiynOlap database by code.
And also how to create and print a simple report to the console.

The data model contains 5 dimensions for years, months, products, regions and some sales
figures.

-----------------
2. Tesla Database
-----------------

**Usage:** Open and/or run the script *...tinyolap/samples/tesla.py*

Purpose of the Tesla data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Tesla** is the famous example that we use in the documentation and on the `TinyOlap website <https://tinyolap.com>`_ .
It show cases some corecapabilities of TinyOlap.

------------------------------
3. Financial Planning Database
------------------------------

.. attention::
   Under development. Coming soon.

**Usage:** Open and/or run the script *...tinyolap/samples/finance.py*

Purpose of the Finance data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Finance** data model is a simple, but real example for financial planning.
The data model is a great template for integrated financial planning for small to large companies.
It provides the following features, leveraging many of TinyOlap's capabilities:

- Sales plan by legal entities, sales-teams, products and regions based on price and quantity.

- HR plan covering employees some attributes and their salaries. Segmented by legal entities.

- Production plan covering planned quantities, raw material costs and capacities.

- Profit and Loss statement, integrating all other plans.

- User management and access rights, so, e.g., the sales guy can look into the salary data
  and only the finance guy can see certain cost figures and EBIT. And the boss can see
  anything but is not allowed to change data.

------------------------------
4. Huge (the opposite of tiny)
------------------------------

.. warning::
   Please be aware that your RAM is limited. **Don't overdo it!** Python will crash when
   your running out of memory.

**Usage:** Open and/or run the script *...tinyolap/samples/huge.py*

Purpose of the Huge data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The **Huge** data model is a already a larger database, at least for TinyOlap.
It shows how TinyOlap behaves on larger data sets.
You can play around with the parameters ``numbers_of_records``  (default = 1,000,000),
``numbers_of_dimensions`` (default = 8) and ``members_per_dimension (default = 100) to
check how the database behaves and perform.

As a rule of thumb, TinyOlap databases consume an average ±1.5kb per record (incl data model).

----------------
5. Plane Spotter
----------------

**Usage:** Open and/or run the script *...tinyolap/samples/planespotter.py*

Purpose of the Plane Spotter data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Plane Spotter** data model is kind of a gimmick and creates a data model containing
real-time flight data from the great `OpenSky online network <https://opensky-network.org>`_.

The data model show cases how you can update the structure and content of database in
more or less real time. Although the request for flight data will need some time (sometimes
seconds), the actual update and import of the data model only takes a few milliseconds.

-------------------------------
6. Tutor - A vintage data model
-------------------------------

**Usage:** Open and/or run the script *...tinyolap/samples/tutor.py*

Purpose of the Tutor data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **tutor** data model is a typical **sales planning and reporting** data model.
Although being very old and special (see *History* below) it nicely reflects how
business often was and still is structured.

The data model contains products (PRODUKTE), regions (REGIONEN), time dimensions (JAHRE, MONATE),
some value types (DATENART) with actual ('Ist') and plan figures, and finally a small
set of measures (WERTART) contain quantity ('Menge'), sales ('Umsatz'), cost
('variable Kosten') and a profit contribution ('DB1').

Tutor is the largest sample data model coming with TinyOlap. With exactly **135,443
records**, it's already reflects a somehow realistic data volume for the business
planning of a smaller to mid-sized company. Enjoy this ...

The special history of the Tutor database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **tutor** database is a piece of OLAP history, it's almost 30 years old, actually from
the pre-internet area. The Tutor database was shipped as the sample database of **MIS Alea**,
one of the first *true* MOLAP databases available. MIS Alea was developed by the MIS Group in
Darmstadt, Germany. Actutally MIS Alea was a clone of TM/1, which itself was developed
by `Manny Perez <https://cubewise.com/history/>`_ at Sinper Corp., USA. After several
company transitions, MIS Alea is still successful in the BI market and is now owned
by Infor and currently called **Infor d/EPM**, if I'm not already changed.

The Tutor database is in german language, but it should be understandable for everyone.
The TXT files in the folder *tutor* are the original files ship with the database on a
3½-inch disk at around 1995, they are single-byte **latin-1** encoded (ISO 8859-1).

-------------------------------
7. Tutor Web Demo
-------------------------------

**Usage:** Open and/or run the script *...tinyolap/samples/tutor_web_demo.py*

Purpose of the Tutor WEb Demo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **tutor web demo** simply spins up very rudimentary web service on top of
the Tutor data model described above.

The implementation is lousy (I'm not a frontend guy) and is intended to showcase
the slice feature of TinyOlap and to provide a nicer visual interface. All other samples
just create console output.

----------------------------------------
8. Tiny42 - TinyOlap parallel-processing
----------------------------------------

**Usage:** Open and/or run the script *...tinyolap/samples/tiny42.py*

Purpose of the Tiny42 data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This example show cases the cloning of databases and how to use multiprocessing
(not multi-threading) to process multiple databases in parallel. The example
works in-memory, in order to not flood you disk with database files.

We create 1x database template, create 42x independent clones and process *them* in
a distributed manner, whatever *them* might be, e.g., recipients, machines, locations
or departments). The clones get adapted (by adding some new members) and
filled with some data. When anything is recollected, we consolidate all the clones
into one single databases.

For illustration purposes we use an IoT sample for the *Tiny Marmalade Factory*,
where 42x marmalade machines create some senor data. Each machines return their
own machine and sensor ids.