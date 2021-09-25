import os
from pathlib import Path
import sqlite3
from typing import List, Set, Tuple, Dict

import util
from backend import Backend
from cube import Cube
from dimension import Dimension
from exceptions import DuplicateKeyException, KeyNotFoundException, InvalidKeyException


class Database:
    def __init__(self, name: str):
        if name != util.to_valid_key(name):
            raise InvalidKeyException(f"'{name}' is not a valid database name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        self.dimensions: Dict[str, Dimension] = {}
        self.cubes: Dict[str, Cube] = {}
        self.name: str = name
        self.backend = Backend(name)
        self.database_file = self.backend.file_path
        self.__load()
        self.file_path = self.backend.file_path

    def close(self):
        """Closes the database."""
        self.backend.close()

    def remove(self):
        """Removes the database file if (1) it exists and (2) if the database is closed (not anymore in use)."""
        if self.backend.conn:
            if Path(self.file_path).exists():
                os.remove(self.file_path)
            if Path(self.file_path + ".log").exists():
                os.remove(self.file_path + ".log")

    def dimension_add(self, name: str):
        """Adds a dimension to the database.
        :param name: Name of the dimension to be added.
        :return Dimension: The added dimension.
        :raises InvalidDimensionNameException: If the dimension name is invalid.
        :raises DuplicateDimensionException: If a dimension with the same name already exists.
        """
        if name != util.to_valid_key(name):
            raise InvalidKeyException(f"'{name}' is not a valid dimension name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if name in self.dimensions:
            raise DuplicateKeyException(f"Failed to add dimension. A dimension named '{name}' already exists.")
        dimension = Dimension(name)
        dimension.backend = self.backend
        dimension.database = self
        self.backend.dimension_update(dimension, dimension.to_json())
        self.dimensions[name] = dimension
        return dimension

    def dimension_remove(self, dimension):
        """Removes a dimension from the database.
        :param name: The dimension or the name of the dimension to be removed.
        :raises KeyNotFoundException: If the dimension not exists.
        """
        if type(dimension) is str:
            name = dimension
        else:
            name = dimension.name
        if name not in self.dimensions:
            raise KeyNotFoundException(f"A dimension named '{name}' does not exist.")

        # todo: Check if the dimension can be removed safely (not in use by any cubes)

        self.backend.dimension_remove(self.dimensions[name])
        del self.dimensions[name]

    def dimension_exists(self, name: str):
        """Checks if dimension exists.
        :param name: Name of the dimension to be checked.
        :returns bool: True if the dimension exists, False otherwise."""
        return name in self.dimensions

    def cube_add(self, name:str, dimensions:list, mesaures = None):
        pass

    def set(self, cube: str, address: Tuple[str], measure: str, value: float):
        """Writes a value to the database for the given cube, address and measure."""
        return False

    def get(self, cube: str, address: Tuple[str], measure: str):
        """Returns a value from the database for a given cube, address and measure.
                If no records exist for the given address, then 0.0 will be returned."""
        return False

    def __load(self):
        """Initialize objects from database."""
        dims = self.backend.meta_dim()
        for dim in dims:
            name = dim[0]
            dimension = self.dimension_add(name)
            json_string = dim[1]
            dimension.from_json(json_string)

    def __remove_members(self,dimension, members):
        """Remove data for obsolete (deleted) members over all cubes.
        Formulas containing that member will get invalidated."""

        #todo: Invalidate rules containing obsolete members.

        pass