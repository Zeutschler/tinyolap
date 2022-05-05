from tinyolap.database import Database


def catalog(db: Database, full_catalog: bool = False):
    """
    Returns a database catalog.
    :param db: The database to create the catalog for.
    :param full_catalog: Flag is the full catalog or a shortened version should be returned.
    :return: A dict containing the catalog.
    """
    if not full_catalog:
        info = {"database":
                    {"id": db.name,
                     "description": db.description,
                     "in_memory": db.in_memory,
                     "caching": db.caching,
                     "cubes": [{"id": db.cubes[cube].name,
                           "caching": db.cubes[cube].caching,
                           "description": db.cubes[cube].description,
                           "dimensions": [dim.name for dim in db.cubes[cube].dimensions],
                           "cells_count": db.cubes[cube].cells_count,
                           } for cube in db.cubes],
                    "dimensions": [
                        {"id": db.dimensions[dim].name,
                        "description": db.dimensions[dim].description,
                        "members_count": len(db.dimensions[dim]),
                        } for dim in db.dimensions],
                    }}
    else:
        info = {"database":
                    {"id": db.name,
                     "description": db.description,
                     "in_memory": db.in_memory,
                     "caching": db.caching,
                     "cubes": [
                         {"id": db.cubes[cube].name,
                            "caching": db.cubes[cube].caching,
                            "description": db.cubes[cube].description,
                            "dimensions": [dim.name for dim in db.cubes[cube].dimensions],
                            "cells_count": db.cubes[cube].cells_count,
                            "rules_count": len(db.cubes[cube].rules),
                            } for cube in db.cubes],
                    "dimensions": [
                        {"id": db.dimensions[dim].name,
                        "description": db.dimensions[dim].description,
                        "members_count": len(db.dimensions[dim]),
                        "members": [{"id": member.name} for member in db.dimensions[dim].members],
                        "attributes": [{"id": attribute,
                                        "value_type": dim.attributes[attribute]} for attribute in db.dimensions[dim].attributes],
                        } for dim in db.dimensions],
                    }}
    return info
