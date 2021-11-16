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

Purpose of the Tiny data model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The **Tiny** data model is a very small and simple demo database created with Python code.
It's contains just very small 5 dimensions and 1 cube that reflects some **sales** data.
The intended use is to showcase the basic operations to create a TiynOlap database by code.
And also how to create and print a simple report to the console.

The data model contains 5 dimensions for years, months, products, regions and some sales
figures.

-----------------
2. Tutor Database
-----------------

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


.. autoclass:: samples.tutor.Tutor
    :members:

.. autoclass:: tinyolap.samples.tutor.Tutor
    :members:

.. automodule:: samples.tutor
    :members:

.. automodule:: tutor
    :members:
