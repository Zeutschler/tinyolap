import os
import sqlite3
import weakref
from typing import List, Set, Tuple, Dict
from errorhandling import Errors


class DatabaseSerializer():
    """Serializer for TinyOlap Databases"""
    TO_PREFIX = "to_"

    def __init__(self, database, database_filename: str = None):
        self.database = weakref.ref(database) if database else None
        self.database_filename = database_filename
        self.con = sqlite3.connect(self.database_filename)

    def __open_or_create(self) -> bool:
        if os.path.isfile(self.name):
            self.database_file = self.name
            if self.open(self.database_file):
                return True
        elif self.create(self.name):
            return True
        return False

    def create(self, name: str) -> bool:
        """
        Creates a new database.

        Attributes
        ----------
        name : str
            Name of the database to be created. Alphanumeric characters supported only.
        """
        name = name.lower().strip()
        if any(not c.isalnum() for c in name) | (not name):  # check for valid database name
            Errors.add(f"Method 'Database.create()' failed. '{name}' is not a valid database name. Alphanumeric characters supported only.")
            return False
        self.name = name
        self.database_file = self.server.get_database_filename(name)
        self.serializer = DatabaseSerializer(self.database_file, name)
        if self.serializer.initialize():
            return self
        return None


    def open(self, database_file: str) -> bool:
        """
        Opens an existing database.

        Attributes
        ----------
        database_file : str
            Full qualified path to a database file.
        """
        if not os.path.isfile(database_file):
            Errors.add(f"Method 'Database.open()' failed. The database file '{database_file}' does not a exist.")
            return False
        self.database_file = database_file
        self.name = os.path.splitext(os.path.basename(self.database_file))[0]
        self.serializer = DatabaseSerializer(self.database_file)
        return self.serializer.initialize()


    def get_all_tables(self):
        cursor = self.con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = []
        for table in cursor.fetchall():
            tables.append(table[0])
        return tables

    def initialize(self):
        tables = self.get_all_tables()
        if not tables: # new or empty database
            self.create_metamodel()
        else:
            print(tables)
        return True

    def create_metamodel(self, instant_commit: bool = True):
        cursor = self.con.cursor()
        cursor.execute(f"CREATE TABLE to_meta (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute(f"INSERT INTO to_meta VALUES ('name','{self.name}')")

        cursor.execute("CREATE TABLE to_cubes (key TEXT PRIMARY KEY, description TEXT, fact_table TEXT)")
        cursor.execute("CREATE TABLE to_dimensions (key TEXT PRIMARY KEY, description TEXT, dimension_table TEXT)")
        cursor.execute("CREATE TABLE to_table_dimensions (table_key TEXT, dim_key TEXT, ordinal INTEGER)")
        if instant_commit:
            self.con.commit()

    def clear(self):
        """Clears the database. All TinyOlap data-model specific tables will deleted, meta tables will be cleared."""
        cursor = self.con.cursor()
        tables = list(cursor.execute(
            "SELECT name FROM sqlite_master WHERE table_name LIKE 'to_%' AND type IN ('view', 'table', 'index', 'trigger')"))
        cursor.executescript(';'.join(["drop table if exists %s" % t for t in tables]))
        cursor.executescript('VACUUM;')
        self.con.commit()
        self.create_metamodel()

    def create_dim_member_table(self, dim_name: str, attributes: List):
        pass

    def create_dim_aggregation_table(self, dim_name: str, aggregation_tuples: List[Tuple[int, int, float]],
                                     instant_commit: bool = True):
        cursor = self.con.cursor()
        table_name = "to_dim_agg_" + dim_name
        cursor.execute(f"CREATE TABLE {table_name} (parent INTEGER, member INTEGER, weight NUMERIC DEFAULT 1.0)")
        cursor.executemany(f"INSERT INTO  {table_name} (parent, member, weight) values (?,?, ?)", aggregation_tuples)
        if instant_commit:
            self.con.commit()
