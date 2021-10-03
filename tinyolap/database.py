import os
from pathlib import Path
from typing import Tuple, Dict
from collections.abc import Iterable

import utils
from case_insensitive_dict import CaseInsensitiveDict
from tinyolap.custom_exceptions import *
from cube import Cube
from dimension import Dimension
from backend import Backend

class Database:
    MIN_DIMS = 1
    MAX_DIMS = 32  # This value can be changed. For the given purpose (planning), 32 is already too much.
    # max. 2000 columns and that dimensions and measure share the same space.
    # Note: 32 dimensions is already huge for model-driven OLAP databases.
    MAX_MEASURES = 1024  # Value can be changed: max. measures = (2000 - MAX_DIMS)

    def __init__(self, name: str = None, in_memory: bool = False):
        """
        Creates a new database or, if a database file with the same name already exists, opens an existing database.

        The opening of an existing database will restore the state of the database either before the
        last call of the ``.close()`` method or before the Database object was released the last time.

        If a database file exists for the given database name and parameter `ìn-memory``wil be set to ``True`,
        then the existing database file will not be opened, changed or overwritten.

        :param name: Name of the database. Only alphanumeric characters and underscore are supported for database names
        (no whitespaces or special characters).

        :param in_memory: Identifies if the database should run in memory only (no persistence) or should persist
        all changes to disk. If `ìn-memory``wil be set to ``True`, then a potentially existing database file for the
        given database name will not be opened, changed or overwritten. To save a database running in in memory mode,
        use the ``save()``method of the database object.
        """
        if name != utils.to_valid_key(name):
            raise InvalidKeyException(f"'{name}' is not a valid database name. "
                                      f"alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")

        # self.dimensions: Dict[str, Dimension] = {}
        # self.cubes: Dict[str, Cube] = {}
        self.dimensions: CaseInsensitiveDict[str, Dimension] = CaseInsensitiveDict()
        self.cubes: CaseInsensitiveDict[str, Cube] = CaseInsensitiveDict()
        self.name: str = name
        self._in_memory = in_memory
        self._backend = Backend(name, self._in_memory)
        self._database_file = self._backend.file_path
        self.__load()
        self._caching = True
        self.file_path = self._backend.file_path

    # region Properties
    @property
    def in_memory(self) -> bool:
        """Identifies if the database is in-memory mode. Please note that the in-memory
        property can not be changed after the initialization of a database object."""
        return self._caching

    @property
    def caching(self) -> bool:
        """Identifies if caching is activated for the database.
        By default, caching is activated for all cubes.
        Individual cubes might have a different caching setting."""
        return self._caching

    @caching.setter
    def caching(self, value: bool):
        """Identifies if caching is activated for the database.
        By default, caching is activated for all cubes.
        Changing this value will overwrite all individual cube settings."""
        self._caching = value
        for cube in self.cubes:
            cube.caching = value

    # endregion

    # region Database related methods
    def close(self):
        """Closes the database."""
        self._backend.close()

    def delete(self, delete_log_file_too=True):
        """Deletes the database file, if such exists and the database is already closed.
        The ``delete()`` command will be ignored if a database is in in-memory mode.
        :param delete_log_file_too: If set to ``True``, also the database log file will be deleted, if such exits.
            Default value is ``True``. Log files are not available if ``in_memory`` has been set to ``True`` on
            database initialization.
        """
        if self._in_memory:
            return

        try:
            if not self._backend.conn:
                if Path(self.file_path).exists():
                    os.remove(self.file_path)
                if Path(self.file_path + ".log").exists():
                    os.remove(self.file_path + ".log")
            else:
                raise DatabaseFileException("Failed to delete database file. Database connection is still open.")
        except OSError as err:
            raise DatabaseFileException(f"Failed to delete database file. {str(err)}")

        if delete_log_file_too:
            if not self._backend.delete_log_file():
                raise DatabaseFileException(f"Failed to delete database log file.")

    # endregion

    # region Dimension related methods
    def add_dimension(self, name: str, description: str = None) -> Dimension:
        """Adds a new dimension to the database.
        :param name: Name of the dimension to be added.
        :param description:
        :return Dimension: The added dimension.
        :raises InvalidDimensionNameException: If the dimension name is invalid.
        :raises DuplicateDimensionException: If a dimension with the same name already exists.
        """
        if not utils.is_valid_db_object_name(name):
            raise InvalidKeyException(f"'{name}' is not a valid dimension name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if name in self.dimensions:
            raise DuplicateKeyException(f"Failed to add dimension. A dimension named '{name}' already exists.")
        dimension = Dimension.create(self._backend, name, description=description)
        dimension.backend = self._backend
        dimension.database = self
        self._backend.dimension_update(dimension, dimension.to_json())
        self.dimensions[name] = dimension
        return dimension

    def dimension_remove(self, dimension):
        """Removes a dimension from the database.
        :param dimension:
        :param name: The dimension or the name of the dimension to be removed.
        :raises KeyNotFoundException: If the dimension not exists.
        """
        if type(dimension) is str:
            name = dimension
        else:
            name = dimension._name
        if name not in self.dimensions:
            raise KeyNotFoundException(f"A dimension named '{name}' does not exist.")

        uses = [cube.name for cube in self.cubes.values() if len([name in [dim.name for dim in cube.dimensions]])]
        if uses:
            raise DimensionInUseException(f"Dimension '{name}' is in use by cubes ({', '.join(uses)}) "
                                          f"and therefore can not be removed. Remove cubes first.")

        # todo: Check if the dimension can be removed safely (not in use by any cubes)

        self._backend.dimension_remove(self.dimensions[name])
        del self.dimensions[name]

    def dimension_exists(self, name: str):
        """Checks if dimension exists.
        :param name: Name of the dimension to be checked.
        :returns bool: True if the dimension exists, False otherwise."""
        return name in self.dimensions

    # endregion

    # region Cube related methods
    def add_cube(self, name: str, dimensions: list, measures=None):
        # validate cube name
        if not utils.is_valid_db_object_name(name):
            raise CubeCreationException(f"Invalid cube name '{name}'. Cube names must contain "
                                        f"lower case alphanumeric characters only, no blanks or special characters.")
        if name in self.cubes:
            raise DuplicateKeyException(f"A cube named '{name}' already exists.")

        # validate dimensions
        if not dimensions:
            raise CubeCreationException("List of dimensions to create cube is empty or undefined.")
        if len(dimensions) > self.MAX_DIMS:
            raise CubeCreationException(f"Too many dimensions ({len(dimensions)}). "
                                        f"Maximum number dimensions per cube is {self.MAX_DIMS}.")
        dims = []
        for dimension in dimensions:
            if type(dimension) is str:
                if dimension not in self.dimensions:
                    raise CubeCreationException(f"A dimension named '{str(dimension)}' is not defined in "
                                                f"database '{self.name}'.")
                dims.append(self.dimensions[dimension])
            elif type(dimension) is Dimension:
                if dimension.name not in self.dimensions:
                    raise CubeCreationException(f"Dimension '{str(dimension.name)}' is not defined in "
                                                f"database '{self.name}'.")
                dim = self.dimensions[dimension.name]
                if dim is not dimension:
                    raise CubeCreationException(f"Dimension '{str(dimension.name)}' is not the same dimension "
                                                f"as the one defined in database '{self.name}'. You can only use "
                                                f"dimensions from within a database to add cubes.")

                dims.append(dimension)
            else:
                raise CubeCreationException(f"Unsupported dimension type '{str(dimension)}'.")
        # validate measures
        if measures:
            if type(measures) is str:
                if not utils.is_valid_member_name(measures):
                    raise CubeCreationException(f"Measure name '{str(measures)}' is not a valid measure name. "
                                                f"Please refer the documentation for further details.")
            elif isinstance(measures, Iterable):
                for m in measures:
                    if not utils.is_valid_member_name(m):
                        raise CubeCreationException(f"Measure name '{str(m)}' is not a valid measure name. "
                                                    f"Please refer the documentation for further details.")
        # create and return the cube
        cube = Cube.create(self._backend, name, dims, measures)
        cube.caching = self.caching
        self.cubes[name] = cube
        return cube

    def set(self, cube: str, address: Tuple[str], measure: str, value: float):
        """Writes a value to the database for the given cube, address and measure."""
        return self.cubes[cube].set(address, measure, value)

    def get(self, cube: str, address: Tuple[str], measure: str):
        """Returns a value from the database for a given cube, address and measure.
                If no records exist for a given valid address, then 0.0 will be returned."""
        return self.cubes[cube].get(address, measure)

    # endregion

    # region internal functions
    def __load(self):
        """Initialize objects from database."""
        if self._in_memory:
            return
        dims = self._backend.meta_dim()
        for dim in dims:
            name = dim[0]
            dimension = self.add_dimension(name)
            json_string = dim[1]
            dimension.from_json(json_string)

    def _remove_members(self, dimension, members):
        """Remove data for obsolete (deleted) members over all cubes.
        Formulas containing that member will get invalidated."""

        # broadcast to all cubes...
        for cube in self.cubes.values():
            cube._remove_members(dimension, members)

    def _flush_cache(self):
        """Flushes all caches of all cubes"""
        for cube in self.cubes.values():
            cube._cache = {}

    # endregion
