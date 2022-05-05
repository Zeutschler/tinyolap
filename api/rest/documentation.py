api_description = """
TinyOlap REST API

## Purpose

The TinyOlap REST API provides read/write access to the data in TinyOlap databases.

The API provides remote client access to the various (not all) TinyOlap database 
components like cubes, dimensions and members.

* Access to the **catalogs** of a TinyOlap database to investigate the the structure of a database (_not yet implemented_).
* **Read and write** cells, data areas and attributes from TinyOlap cubes and dimensions (_not yet implemented_).
* **Batch operations** to import data to and retrieve data from TinyOlap databases (_not implemented_).
* **Modelling** of the database structure. Adding, removing and editing of dimensions, cubes, member, rules etc. (_not yet implemented_).
* **User and Authorization Management** (_not yet implemented_).
"""

tags_metadata = [
    {
        "name": "databases",
        "description": "Provides information about databases, includes the database catalogs. "
                       ""
                       "Please note that database management and configuration, like adding, remove, backup "
                       "of databases, is not (yet) supported by the API.",
    },
    {
        "name": "cells",
        "description": "Read/write access to cube cells.",
        "externalDocs": {
            "description": "External documentation for 'cells'",
            "url": "https://tinyolap.com/docs/cells.html",
        },
    },
]