api_description = """
TinyOlap REST API

## Purpose

The TinyOlap REST API enables the hosting of a single or multiple TinyOlap databases.
The API provides remote client access to various (not all) TinyOlap database capabilities:

* Access to the **catalogs** of a TinyOlap database to investigate the the structure of a database (_not yet implemented_).
* **Read and write** cells, data areas and attributes from TinyOlap cubes and dimensions (_not yet implemented_).
* **Batch operations** to import data to and retrieve data from TinyOalp databases (_not implemented_).
* **Modelling** of the database structure. Adding, removing and editing of dimensions, cubes, member, rules etc. (_not yet implemented_).
* **User and Authorization Management** (_not implemented_).
"""

tags_metadata = [
    {
        "name": "databases",
        "description": "Provides information about databases, includes the database catalogs.",
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