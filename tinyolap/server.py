# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import os

from tinyolap.case_insensitive_dict import CaseInsensitiveDict
from tinyolap.database import Database


class Server:
    """
    Represents a TinyOlap server instance serving one or more databases.
    Only needed when multiple databases need to be served through a single object.
    """

    class Settings:
        version = "0.1"

    UNDEFINED = "undefined"
    DB_FILE_EXT = ".db"
    DB_DEFAULT_FOLDER = "db"

    def __init__(self):
        self._databases: CaseInsensitiveDict[str, Database] = CaseInsensitiveDict()
        self.__initialize()

    def reinitialize(self):
        """Re-initializes the server. This forces all allocated resources to be released."""
        self.__initialize()

    def __initialize(self):
        """Initializes the server for first use."""
        self._databases = CaseInsensitiveDict()
        files = self.get_existing_database_files()
        for file in files:
            database = Database(file)
            self._databases[database.name] = database

    # region database access via indexing/slicing
    def __getitem__(self, args):
        if type(args) is str:
            dbs = [db.name for db in self._databases.values()]
            if args in self._databases:
                return self._databases[args]
            raise KeyError(f"A database named '{args}' is not registered on the server.")
        raise KeyError(f"Invalid database name '{str(args)}'.")

    def __delitem__(self, args):
        self.deletes_database(args[0])
    # endregion

    def open_database(self, database_file: str):
        """
        Opens an existing database.

        Parameters
        ----------
        database_file : str
            A full qualified path to database file.
        """
        database = Database(database_file)
        if not database.open(database_file):
            return False
        if database.name in self._databases:
            raise KeyError(f"Method 'open_database()' failed. "
                                    f"A database named '{database.name}' already exists.")
        self._databases[database.name] = database
        return True

    def create_database(self, name: str, in_memory: bool = True, overwrite_existing: bool = False):
        """
        Creates a new database. If parameter ``in_memory``is set to ``True``,
        no database file will be created. For that case, all changes made to the database
        and data entered or imported will be lost after your application has shut down.

        If parameter ``in_memory``is set to ``False`` (the default settings), then a
        database file will be created in the folder 'db' aside your script root.
        If a database with the same name already exists, then the old database file will
        be renamed and a new database file will be created. Renaming simply appends a
        timestamp.

        .. danger::
           If parameter ``in_memory``is set to ``True`` and parameter ``overwrite_existing``
           is also set to ``True`` then an any existing database file will be deleted/overwritten.

        :param overwrite_existing: Identifies that an already existing database file with the
        same name will be overwritten.
        :param name: The name of the database to be created.
        Special characters are not supported for database names.
        :param in_memory: Defines if the database should operate in-memory only,
        without persistence (all data will be lost after your application will shut down)
        or, if set to ``False``, with an SQLite file storage_provider.
        """
        if not name in self._databases:
            database = Database(name, in_memory)
            self._databases[database.name] = database
            return database
        else:
            raise KeyError(f"A database named '{name}' is already registed in the server.")

    def add_database(self, database: Database) -> Database:
        """
        Adds a database to the server
        :param database: The database to be added.
        """
        if not database.name in self._databases:
            self._databases[database.name] = database
            return database
        else:
            raise KeyError(f"A database named '{database.name}' is already registed in the server.")

    def deletes_database(self, name: str):
        """Deletes a database from the filesystem. Handle with care."""
        return NotImplemented

    @staticmethod
    def get_database_folder():
        return os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            Server.DB_DEFAULT_FOLDER)

    @staticmethod
    def get_database_filename(name: str):
        return os.path.join(Server.get_database_folder(), name + Server.DB_FILE_EXT)

    @staticmethod
    def get_existing_database_files():
        files = []
        database_directory = Server.get_database_folder()
        if not os.path.exists(database_directory):
            os.mkdir(database_directory)
            return files
        for file in os.listdir(database_directory):
            if file.lower().endswith(Server.DB_FILE_EXT):
                files.append(os.path.join(database_directory, file))
        return files

    # region functions
    def _register(self, func, database: str, cube: str, pattern: list[str]):
        if database not in self._databases:
            raise KeyError(f"Database '{database}' not found.")
        if cube not in self._databases[database].cubes:
            raise KeyError(f"Cube '{cube}' of database '{database}' not found.")
        self._databases[database].cubes[cube]._register(func, pattern)
    # endregion
