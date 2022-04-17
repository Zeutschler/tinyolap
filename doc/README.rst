TinyOlap
=======

**TinyOlap** is a minimal in-process in-memory multi-dimensional database with numerical aggregations
and calculations in mind. First a multi-dimensional data model needs to be defined, consisting of
cubes, dimensions, members, hierarchies etc. Afterwards additional calculation logic can be added
through arbitrary Python code. Data access is cell-based or range-based. A minimal support for SQL
in also provided. All calculations will be executed on the fly. Optionally, persistence is provided
through SQLite.

TinyOlap is a byproduct of a research project, intended to mimic the behavior and
capabilities of real-world MOLAP databases (e.g. IBM TM/1, SAP HANA or Jedox PALO) but with a super
minimal footprint. TinyOlap is best suited for interactive planning, forecasting, simulation and
general multidimensional numerical problems.

thanks