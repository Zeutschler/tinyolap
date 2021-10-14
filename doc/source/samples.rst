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

**Usage:** Open and/or start the script *...tinyolap/samples/tiny.py*

Purpose of the Tiny data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Tiny** data model is a very small and simple demo database created with Python code.
It's contains just very small 5 dimensions and 1 cube that reflects some **sales** data.
The intended use is to showcase the basic operations to create a TiynOlap database by code.
And also how to create and print a simple report to the console.

The data model contains 5 dimensions for years, months, products, regions and some sales
figures.

----------------
2. Huge
----------------

**Usage:** Open and/or start the script *...tinyolap/samples/huge.py*

Purpose of the Huge data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Huge** data model is - in contrast - larger demo database (at least for TinyOlap),
created by some lines of Python code. It shows how TinyOlap behaves on larger data sets.
You can play around with the parameters ``numbers_of_records``  (default = 1,000,000),
``numbers_of_dimensions`` (default = 8) and ``members_per_dimension (default = 100) to
check how the database behaves and perform.

As a rule of thumb, TinyOlap databases consume ±1.5kb per record.

.. warning::
   Please be aware that your RAM is limited. **Don't overdo it!** Python will crash when
   your running out of memory.

----------------
3. Plane Spotter
----------------

**Usage:** Open and/or start the script *...tinyolap/samples/planespotter.py*

Purpose of the Plane Spotter data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Plane Spotter** data model is kind of a gimmick and creates a data model containing
real-time flight data from the great `OpenSky online network <https://opensky-network.org>`_.

The data model show cases how you can update the structure and content of database in
more or less real time. Although the aquisition of the flight data will need some
seconds, the update and import of the data model only takes a few milliseconds.

The demo runs in an endless loop for 10 minutes with 5 second wait time between calls.
So, you need to kill the stop/process when your getting bored...

-----------------
4. Tutor Database
-----------------

**Usage:** Open and/or start the script *...tinyolap/samples/tutor.py*

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
by Infor and currently called **Infor d/EPM v12**, if I'm not mistaken.

The Tutor database is in german language, but it should be understandable for everyone.
The TXT files in the folder *tutor* are the original files ship with the database on a
3½-inch disk at around 1995, they are single-byte **latin-1** encoded (ISO 8859-1).

