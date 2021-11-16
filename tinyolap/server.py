import os
from typing import Dict
import functools

from custom_errors import DuplicateKeyError
from database import Database


# def singleton(cls):
#     """Make a class a Singleton class (only one instance)"""
#     @functools.wraps(cls)
#     def wrapper_singleton(*args, **kwargs):
#         if not wrapper_singleton.instance:
#             wrapper_singleton.instance = cls(*args, **kwargs)
#         return wrapper_singleton.instance
#     wrapper_singleton.instance = None
#     return wrapper_singleton
# @singleton
class Server:
    """
    Represents a TinyOlap server instance serving one or more databases.
    """

    UNDEFINED = "undefined"
    DB_FILE_EXT = ".db"
    DB_DEFAULT_FOLDER = "db"

    def __init__(self):
        self.databases: Dict[str, Database] = {}
        self.__initialize()

    def reinitialize(self):
        """Re-initializes the server. This forces all allocated resources to be released."""
        self.__initialize()

    def __initialize(self):
        """Initializes the server for first use."""
        self.databases.clear()  # initiates the garbage collection
        files = self.get_existing_database_files()
        for file in files:
            database = Database(file)
            self.databases[database.name] = database


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
        if database.name in self.databases:
            raise DuplicateKeyError(f"Method 'open_database()' failed. "
                                    f"A database named '{database.name}' already exists.")
        self.databases[database.name] = database
        return True

    def create_database(self, name: str, in_memory: bool =True):
        """
        Creates a new database in the default database folder.

        Parameters
        ----------
        name : str
            The name of the database. Special characters are not supported for databse names.
        """
        if not name in self.databases:
            database = Database(name, in_memory)
            self.databases[database.name] = database
            return database
        else:
            raise KeyError(f"Database '{name}' already exists.")


    def delete_database(self):
        """Deletes a database from the filesystem. Handle with care."""
        raise NotImplementedError

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
        if database not in self.databases:
            raise KeyError(f"Database '{database}' not found.")
        if cube not in self.databases[database].cubes:
            raise KeyError(f"Cube '{cube}' of database '{database}' not found.")
        self.databases[database].cubes[cube]._register(func, pattern)

    # endregion
