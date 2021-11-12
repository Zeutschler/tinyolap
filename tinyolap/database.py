# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections.abc import Iterable
from copy import deepcopy
from typing import Tuple

import tinyolap.utils
from storage.sqlite import SqliteStorage
from storage.storageprovider import StorageProvider
from tinyolap.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.cube import Cube
from tinyolap.custom_errors import *
from tinyolap.dimension import Dimension
from tinyolap.history import History


class Database:
    """
    Databases are the root objects that should be use to create **TinyOlap** data model or database.
    The Database object provides methods to create :ref:`dimensions <dimensions>` and :ref:`cubes <cubes>`.
    """
    MIN_DIMS = 1
    MAX_DIMS = 32  # This value can be changed. For the given purpose (planning), 32 is already too much.
    # max. 2000 columns and that dimensions and measure share the same space.
    # Note: 32 dimensions is already huge for model-driven OLAP _databases.
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
        if name != tinyolap.utils.to_valid_key(name):
            raise InvalidKeyException(f"'{name}' is not a valid database name. "
                                      f"alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        self.dimensions: CaseInsensitiveDict[str, Dimension] = CaseInsensitiveDict()
        self.cubes: CaseInsensitiveDict[str, Cube] = CaseInsensitiveDict()
        self._history: History = History(self)
        self._name: str = name
        self._in_memory = in_memory
        if in_memory:
            self._storage_provider: StorageProvider = None
        else:
            self._storage_provider: StorageProvider = SqliteStorage(self._name)
            self._storage_provider.open()
        self._load()
        self._caching = True

    # region Properties
    @property
    def in_memory(self) -> bool:
        """
        Identifies if the database is in-memory mode. Please note that the in-memory
        property can not be changed after the initialization of a database object.

        :return: Returns ``True`` if the database is in-memory mode, ``False`` otherwise.
        """
        return self._in_memory

    @property
    def history(self) -> History:
        """Returns the history of the database."""
        return self._history

    @property
    def name(self) -> str:
        """Returns the name of the database."""
        return self._name

    @property
    def uri(self) -> str:
        """Returns the uri of the database."""
        if self._storage_provider:
            return self._storage_provider.uri
        return None

    @property
    def file_path(self) -> str:
        """Returns the file path of the database."""
        if self._storage_provider:
            file = self._storage_provider.uri
            if file.startswith("file://"):
                file = file[7:]
            return file
        return None

    @property
    def caching(self) -> bool:
        """
        Identifies if caching is activated for the database.
        By default, caching is activated for all :ref:`cubes <cubes>`.
        The caching setting for individual cubes can be overwritten.

        .. note::
            It is highly recommended, especially for larger data models containing
            a lot of data maybe even essential, to always set caching to ``True```
            what anyhow is the default value. Caching greatly improves the user
            experience by caching values for **aggregated cells** from cubes.

            Please be aware that the cache needs to be warmed up on first use.
            For future versions of **TinyOlap** it is planned to also persist the
            cube cache to enable faster initial cell access.

        :return: Returns ``True`` if caching is activated for the database, ``False`` otherwise.
        """
        return self._caching

    @caching.setter
    def caching(self, value: bool):
        """
        Identifies if caching is activated for the database.
        By default, caching is activated for all :ref:`cubes <cubes>`.
        The caching setting for individual cubes can be overwritten.

        .. note::
            It is highly recommended, especially for larger data models containing
            a lot of data maybe even essential, to always set caching to ``True```
            what anyhow is the default value. Caching greatly improves the user
            experience by caching values for **aggregated cells** from cubes.

            Please be aware that the cache needs to be warmed up on first use.
            For future versions of **TinyOlap** it is planned to also persist the
            cube cache to enable faster initial cell access.

        :param value: Set value to ``True`` to activate caching, ``False`` to deactivate caching.
        """
        self._caching = value
        for cube in self.cubes.values():
            cube.caching = value

    # endregion

    # region Database related methods
    def rename(self, new_name: str):
        """Renames the database.
        :param new_name: New name for the database.
        :raise KeyError: Raised if the key is invalid.
        """
        if new_name != tinyolap.utils.to_valid_key(new_name):
            raise KeyError(f"'{new_name}' is not a valid database name. "
                           f"alphanumeric characters and underscore supported only, "
                           f"no whitespaces, no special characters.")
        self._name: str = new_name

    def clone(self):
        """Creates a clone (copy) of the database."""
        return deepcopy(self)

    def open(self, file_name: str):
        """
        Opens a database from a file.
        :param file_name: The database file path to be opened.
        """
        self._storage_provider.open()
        # todo: Implement a dedicated serializes/deserializer to initialize a database

    def close(self):
        """
        Closes the database. If in-memory mode is off ``in_memory == False`` ,
        then all pending changes to the database file will be committed and
        the connection to the underlying database will be be closed.

        The ``close()`` command has no effect if the database is in-memory mode
        ``in_memory == True``.
        """
        if self._storage_provider:
            self._storage_provider.close()

    def delete(self):
        """
        Deletes the database file and log file, if such exists. If the database is
        open, it will be closed beforehand. You should handle this method with care.
        The ``delete()`` command has no effect if the database is in in-memory mode
        ``in_memory == True``.
        """
        if self._storage_provider:
            self._storage_provider.close()
            self._storage_provider.delete()

    def export(self, name: str, overwrite_if_exists: bool = False):
        """
        Exports the database to a new database file. This method is useful e.g.
        for creating backups and especially to persist databases that run in
        in-memory mode.

        .. note::
            When **TinyOlap** is used for data processing purposes, rather than
            as for planning or other data-entry focussed tasks, it is a clever
            idea to spin up the database first in in-memory mode, do all your
            processing and then persists the result using the ``export(...)``
            method. This approach is presumably much faster than constantly
            writing to the database file.

        :param name: Either a simple name or a fully qualified file path. If
           the name does not represent a path, then the databse file will be
           created in the default location '/db' or whatever is specified in
           the config file for ``database_folder``.
        :param overwrite_if_exists: Defines if an already existing file should
           be overwritten or not. If set to ``False`` and the file already exist,
           an FileExistsError will be raised.
        :return:
        """
        if name.lower() == self.name.lower():
            raise DatabaseBackendException(f"Failed to export database '{self.name}'. "
                                           f"You cannot export a database under it's current name.")

        exporter: StorageProvider = SqliteStorage(name)
        if exporter.exists():
            if not overwrite_if_exists:
                raise FileExistsError(f"Failed to export database '{self.name}'. "
                                      f"The database file '{exporter.uri}' already exists.")
            else:
                exporter.delete()

        # Export the database
        exporter.open()
        for dimension in self.dimensions.values():
            exporter.add_dimension(dimension.name, dimension.to_json())
        for cube in self.cubes.values():
            exporter.add_cube(cube.name, cube.to_json())
            exporter.set_records(cube.name, cube._get_records())
        exporter.close()

    # endregion

    # region CellContext access via indexing
    def __getitem__(self, item):
        cube = self.cubes[item[0]]
        return cube.get(item[1:])

    def __setitem__(self, item, value):
        cube = self.cubes[item[0]]
        cube.set(item[1:], value)

    def __delitem__(self, item):
        cube = self.cubes[item[0]]
        cube.set(item[1:], None)

    # endregion

    # region Dimension related methods
    def add_dimension(self, name: str, description: str = None) -> Dimension:
        """Adds a new :ref:`dimension <dimensions>` to the database.

        :param name: Name of the dimension to be added.
        :param description: Description for the dimension.
        :return Dimension: The newly added dimension.
        :raises InvalidDimensionNameException: If the dimension name is invalid.
        :raises DuplicateDimensionException: If a dimension with the same name already exists.
        """
        if not tinyolap.utils.is_valid_db_object_name(name):
            raise InvalidKeyException(f"'{name}' is not a valid dimension name. "
                                      f"Lower case alphanumeric characters and underscore supported only, "
                                      f"no whitespaces, no special characters.")
        if name in self.dimensions:
            raise DuplicateKeyException(f"Failed to add dimension. A dimension named '{name}' already exists.")
        dimension = Dimension._create(self._storage_provider, name, description=description)
        dimension.database = self
        self.dimensions[name] = dimension
        return dimension

    def dimension_remove(self, dimension):
        """Removes a :ref:´dimension <dimensions>´ from the database.

        :param dimension: Name of the dimension, or the :ref:`dimension <dimensions>´ object to be removed.
        :raises KeyNotFoundError: If the dimension not exists.
        """
        if type(dimension) is str:
            name = dimension
        else:
            name = dimension._name
        if name not in self.dimensions:
            raise KeyNotFoundError(f"A dimension named '{name}' does not exist.")

        uses = [cube.name for cube in self.cubes.values() if len([name in [dim.name for dim in cube._dimensions]])]
        if uses:
            raise DimensionInUseException(f"Dimension '{name}' is in use by cubes ({', '.join(uses)}) "
                                          f"and therefore can not be removed. Remove cubes first.")

        if self._storage_provider and self._storage_provider.connected:
            self._storage_provider.remove_dimension(name)

        del self.dimensions[name]

    def dimension_exists(self, name: str):
        """Checks if a dimension exists.

        :param name: Name of the dimension to be checked.
        :returns bool: Returns ``True`` if the dimension exists, ``False`` otherwise."""
        return name in self.dimensions

    # endregion

    # region Cube related methods
    def add_cube(self, name: str, dimensions: list, measures=None, description: str = None):
        """
        Creates a new :ref:´cube<cubes>´ and adds it to the database.


        :param name: Name of the cube to be created.
        :param dimensions: A list of either names of existing dimensions of the database or
        :ref:`dimension <dimensions>` objects contained in the database.
        :param measures: (optional) a measure name or a list of measures names for the cube.
        If argument 'measures' is not defined, that a default measure named 'value' will be created.
        :param description: (optional) description for the cube.
        :return: The added cube object.
        :raises CubeCreationException: Raised if the creation of the cubed failed due to one
        of the following reasons:

        * The cube name is not invalid. Cube have to consist of lower case alphanumeric characters
            or underscore only, blanks or special characters are not allowed.

        * The list of dimensions is empty, contains dimension names or objects not associated with
          the cube, or the number of dimensions exceeds the upper limit of dimensions supported
          for cube creation.

          .. note::
             The default upper limit for cube creation is 32 dimensions, but this limit can be
             adjusted at any time by changing the value for ``MAX_DIMS`` in the source file
             'database.py'.

        :raises DuplicateKeyException: Raised if the cube already exists.")
        """

        # validate cube name
        if not tinyolap.utils.is_valid_db_object_name(name):
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
                if not tinyolap.utils.is_valid_member_name(measures):
                    raise CubeCreationException(f"Measure name '{str(measures)}' is not a valid measure name. "
                                                f"Please refer the documentation for further details.")
            elif isinstance(measures, Iterable):
                for m in measures:
                    if not tinyolap.utils.is_valid_member_name(m):
                        raise CubeCreationException(f"Measure name '{str(m)}' is not a valid measure name. "
                                                    f"Please refer the documentation for further details.")
        # create and return the cube
        cube = Cube.create(self._storage_provider, name, dims, measures, description)
        cube.caching = self.caching
        self.cubes[name] = cube
        return cube

    def cube_exists(self, name: str):
        """Checks if a cube exists.

        :param name: Name of the cube to be checked.
        :returns bool: Returns ``True`` if the cube exists, ``False`` otherwise."""
        return name in self.cubes

    def set(self, cube: str, address: Tuple[str], value: float):
        """
        Writes a value to the database for the given cube, idx_address and measure.
        Write back is supported for base level cells only.

        .. note:: Although TinyOlap is intended to be used for numerical data mainly,
            any Python data type or object reference can be written to a database.
            Persistence is only provided/guarantied for build-in base data types.
            If you want to serialized/deserialized custom objects through cube cells,
            then write/read json and do serialization and deserialization by yourself.

        :param cube: Name of the cube to write to.
        :param address: Address of the cube cell to write to.
        :param value: The value to be written to the database.
        """
        self.cubes[cube].set(address, value)

    def get(self, cube: str, address: Tuple[str], measure: str):
        """Returns a value from the database for a given cube, idx_address and measure.
                If no records exist for a given valid idx_address, then 0.0 will be returned."""
        return self.cubes[cube].get(address, measure)

    # endregion

    # region internal functions
    def _load(self):
        """Initialize database from storage storage_provider."""

        if self._storage_provider:
            if not self._storage_provider.exists():
                return
            if not self._storage_provider.connected:
                self._storage_provider.open()

            # initialize dimensions
            data = self._storage_provider.get_dimensions()
            for dim_tuple in data:
                dim_name, dim_json = dim_tuple
                dimension = self.add_dimension(dim_name)
                dimension.from_json(dim_json)

            # initialize cubes
            # todo: implementation missing

            # import data
            # todo: implementation missing

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
