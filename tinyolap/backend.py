import sqlite3
import os
from os import path
from pathlib import Path
import logging
from timeit import default_timer as timer
from collections.abc import Iterable
from tinyolap.custom_exceptions import *

# noinspection SqlNoDataSourceInspection
class Backend:
    """SQLite storage backend"""
    META_TABLE_CUB = "meta_cub"
    META_TABLE_DIM = "meta_dim"
    META_TABLE_FIELDS = [("key", "TEXT PRIMARY KEY"), ("config", "TEXT")]
    CUB_PREFIX = "cub_"
    DB_FOLDER_NAME = "db"
    DB_EXTENSION = ".db"

    LOG_EXTENSION = ".log"
    LOG_LEVEL = logging.INFO

    def __init__(self, database_name: str, in_memory: bool = False):
        self.conn: sqlite3.Connection = None
        self.cursor: sqlite3.Cursor = None
        self._in_memory: bool = in_memory
        self.database_name: str = database_name
        self.is_open = False
        if self._in_memory:
            self.file_name, self.file_folder, self.file_path = "", "", ""
            self.log_file = ""
        else:
            self.file_name, self.file_folder, self.file_path = self.__generate_path_from_database_name(self.database_name)
            self.log_file = os.path.join(self.file_folder, self.file_name + self.LOG_EXTENSION)
            self.__setup_logger()
            self.logger.info(f"Database backend initialization started.")
            self.open(self.file_path)
            self.logger.info(f"Database backend initialization finished.")


    def __setup_logger(self):
        if self._in_memory:
            return
        self.logger = logging.getLogger("backend")
        handler = logging.FileHandler(self.log_file, mode='w')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(self.LOG_LEVEL)

    def delete_log_file(self):
        """Deletes the database log file."""
        try:
            if path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except OSError:
            return False

    def delete(self):
        """Closes an open database and deletes the database file."""
        if self._in_memory:
            return
        try:
            self.close()
            if path.exists(self.file_path):
                os.remove(self.file_path)
            self.logger.info(f"Database file '{self.file_path}' has been deleted.")
            return True
        except OSError as err:
            self.logger.error(f"Failed to delete database file '{self.file_path}'. {str(err)}")
            return False

    def open(self, file_path: str) -> bool:
        if self._in_memory:
            return True
        """
        Opens a database. If the database does not exist, a new database will be created.
        """
        if self.conn and (self.file_path.lower() != file_path.lower()):
            self.close()
            self.logger.info(f"Database connection to file '{self.file_path}' closed.")

        self.file_path = file_path
        self.file_folder, self.file_name = os.path.split(file_path)

        try:
            database_already_existed = Path(self.file_path).exists()
            self.conn = sqlite3.connect(self.file_path)
            self.cursor = self.conn.cursor()
            self.is_open = True
            if database_already_existed:
                self.logger.info(f"Open database file '{file_path}'.")
                return self.__validate_db()
            else:  # new database
                self.logger.info(f"Created new database file '{file_path}'.")
                self.__configure_db()
                self.__initialize_db()
                return True
        except sqlite3.Error as err:
            self.logger.error(f"Failed to open database '{file_path}'. {str(err)}")
            raise FatalException()
            return False
        except Exception as err:
            self.logger.error(f"Failed to open database '{file_path}'. {str(err)}")
            raise FatalException()
            return False

    def close(self):
        if self._in_memory:
            return
        """Closes the database."""
        if self.logger:
            self.logger.info(f"Closing database '{self.database_name}'.")
            self.logger.handlers[0].flush()
        if self.conn:
            self.commit()
            self.conn.close()
        self.is_open = False
        return True

    def commit(self, optimize=False):
        if self._in_memory:
            return
        """Commits all accumulated changes to the database."""
        if optimize:
            self.__execute('PRAGMA vacuum;')
            self.__execute('PRAGMA optimize;')
        if self.conn:
            self.conn.commit()

    def cube_get(self, cube_name, address, measure) -> float:
        """Returns a single measure from a cube fact table.
        If the address does not exist, value 0.0 will be returned.
        Arguments 'address' and 'measure' are index values of typ <int>."""
        if not isinstance(measure, Iterable):
            measure = [measure]
        fields_clause = ', '.join(['m'+ str(m) for m in measure])
        sql = f"SELECT {fields_clause} FROM {Backend.CUB_PREFIX + cube_name} " \
              f"WHERE {' AND '.join(['d' + str(i + 1) + '=' + str(d) for i, d in enumerate(address)])};"
        # records = self.cursor.execute(sql).fetchall()
        records = self.__fetchall(sql)
        if records:
            return records[0][0]
        return 0.0

    def cube_get_range(self, cube_name, member_lists: list[list[int]], measures, aggregate: bool =True) -> list:
        """Executes a range query on the cube fact table """
        if not isinstance(measures, Iterable):
            measures = [measures]
        member_list_text = []
        for i, ml in enumerate(member_lists):
            member_list_text.append(f"d{i + 1} in ({','.join([str(m) for m in ml])})")
        where_clause = ' AND '.join([m for m in member_list_text])
        if aggregate:
            fields_clause = ', '.join(['SUM(m'+ str(m) + ')' for m in measures])
        else:
            fields_clause = ', '.join(['m'+ str(m) for m in measures])
        sql = f"SELECT {fields_clause} " \
              f"FROM {Backend.CUB_PREFIX + cube_name} " \
              f"WHERE ({where_clause});"
        return self.__fetchall(sql)

    def cube_get_many(self, cube_name, address: list[int], measures: list[int]) -> list:
        """Returns multiple measures (given by a list of measure indexes) from a cube fact table.
        If the address does not exist, a list of 0.0 values will be returned.
        Arguments 'address' and 'measures' represent index values of typ list[int]."""
        sql = f"SELECT m{', '.join(['m' + str(m) for m in measures])} " \
              f"FROM {Backend.CUB_PREFIX + cube_name} " \
              f"WHERE {' AND '.join(['d' + str(i + 1) + '=' + str(d) for i, d in enumerate(address)])};"
        rs = self.__fetchall(sql)
        if rs:
            return [float(v) for v in rs[0]]
        return [0.0 for _ in measures]

    def cube_set(self, cube_name, address: list[int], measure: int, value, instant_commit: bool = True):
        """Sets single measure value into a cube fact table.
        Note: This method executes an 'upsert' on a cube fact tables."""
        table = Backend.CUB_PREFIX + cube_name
        if value is None:
            where_statement = ' AND '.join([('d' + str(i + 1) + '=' + str(d))for i, d in enumerate(address)])
            sql = f"DELETE FROM {table} WHERE {where_statement};"
        else:
            dim_col_list = ', '.join(['d' + str(i + 1) for i, d in enumerate(address)])
            measure_col = f"m{measure[0]}"
            sql = f"INSERT INTO {table}({dim_col_list}, {measure_col})" \
                  f"VALUES({', '.join([str(d) for d in address])}, {value}) " \
                  f"ON CONFLICT({dim_col_list}) " \
                  f"DO UPDATE SET {measure_col}=EXCLUDED.{measure_col};"
        self.__execute(sql)
        if instant_commit:
            self.commit()
        return True

    def cube_set_many(self, cube_name, address, measures, values):
        """Sets multiple value for multiple measures in a cube table.
        This method executes an upsert (insert or update) on cube tables.
        Arguments 'address' and 'measures' are index values of typ <int>."""
        table = Backend.CUB_PREFIX + cube_name
        dim_col_list = ', '.join(['d' + str(i + 1) for i, d in enumerate(address)])
        dim_member_list = ', '.join([str(d) for d in address])
        value_list = ', '.join([str(v) for v in values])
        measure_col_list = ', '.join(['m' + str(m) for m in measures])
        measure_col_set_list = ', '.join([f"{'m' + str(m)}=EXCLUDED.{'m' + str(m)}" for m in measures])
        sql = f"INSERT INTO {table}({dim_col_list}, {measure_col_list})" \
              f"VALUES({dim_member_list}, {value_list}) " \
              f"ON CONFLICT({dim_col_list}) " \
              f"DO UPDATE SET {measure_col_set_list};"
        self.__execute(sql)

    def add_cube(self, cube_name, dimensions, measures):
        """Initializes the database with all required meta tables."""
        if self._in_memory:
            return
        table_name = Backend.CUB_PREFIX + cube_name
        dim_col_list = ', '.join(['d' + str(i + 1) + ' int' for i, d in enumerate(dimensions)])
        dim_col_pk_list = ', '.join(['d' + str(i + 1) for i, d in enumerate(dimensions)])
        measure_list = ', '.join(['m' + str(m) + ' real' for m in measures])
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} (" \
              f"{dim_col_list}, {measure_list}, " \
              f"PRIMARY KEY ({dim_col_pk_list})) WITHOUT ROWID;"
        self.__execute(sql)
        self.logger.info(f"New cube '{cube_name}' added: {sql}")
        return table_name

    def cube_remove(self, cube_name):
        table = Backend.CUB_PREFIX + cube_name
        sql = f"DROP TABLE IF EXISTS {table};"
        self.__execute(sql)
        self.logger.info(f"Cube '{cube_name}' removed: {sql}")

    def __initialize_db(self):
        """Initializes a new and empty database by adding several meta tables."""
        self.logger.info(f"Initialization of new database started.")
        self.__add_table(self.META_TABLE_CUB, self.META_TABLE_FIELDS)
        self.__add_table(self.META_TABLE_DIM, self.META_TABLE_FIELDS)
        if not self.__table_exists(self.META_TABLE_DIM):
            self.logger.error(f"Failed to add meta tables.")
            raise FatalException("Failed to add meta tables to database.")
        self.logger.info(f"Initialization of new database finished.")


    def __add_table(self, table_name, fields: list[tuple]):
        sql = f"DROP TABLE IF EXISTS {table_name};"
        self.__execute(sql)
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([str(f[0]) + ' ' + str(f[1]) for f in fields])} );"
        self.__execute(sql)
        self.commit()
        self.logger.info(f"New database table '{table_name}' added. {sql}")

    def __generate_add_table_statement(self, table_name, fields: list[tuple]):
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({','.join([str(f[0]) + ' ' + str(f[1]) for f in fields])} );"

    def __validate_db(self) -> bool:
        """Checks that the database is equipped with all required meta tables."""
        if not self.__table_exists(self.META_TABLE_CUB):
            self.__initialize_db()
        return True

    def __configure_db(self):
        """Configures a new SQLite database for optimized performance."""
        self.__execute('PRAGMA temp_store=MEMORY;')
        self.__execute('PRAGMA journal_mode=MEMORY;')
        # self.__execute('PRAGMA synchronous=normal;')
        # self.__execute('PRAGMA mmap_size = 30000000000;')
        self.commit()

    def __get_all_db_tables(self):
        return self.__fetchall(f"SELECT name, sql FROM sqlite_master WHERE type='table';")

    def __table_exists(self, table_name):
        # get the count of tables with the name
        if not self.cursor:
            self.cursor = self.conn.cursor()
        sql = f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        try:
            return self.cursor.execute(sql).fetchone()[0] == 1
        except sqlite3.Error as err:
            raise FatalException()

    def __execute(self, sql: str, data=None):
        """Executes an SQL query without returning a result or resultset."""
        duration = 0.0
        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer()

        try:
            if not self.cursor:
                self.cursor = self.conn.cursor()
            if data:
                self.cursor.execute(sql, data)
            else:
                self.cursor.execute(sql)
        except sqlite3.Error as err:
            self.logger.error(f"SQLite error on '.execute(sql)'. {str(err)} SQL := {sql}")
        except Exception as err:
            self.logger.error(f"Unexpected error on '.execute(sql)'.{str(err)} SQL := {sql}")

        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.debug(f"SQL statement executed in {duration:.6f}s: {sql}")

    def __execute_transaction(self, sql: list[str]):
        """Executes a list of SQL statements within a single transaction with rollback on failure."""
        duration = 0.0
        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer()

        current_statement = ""
        if not self.cursor:
            self.cursor = self.conn.cursor()
        try:
            # clear current dim table
            self.cursor.execute("begin")
            for statement in sql:
                current_statement = statement
                self.cursor.execute(statement)
            self.cursor.execute("commit")
        except sqlite3.Error as err:
            self.logger.error(f"SQLite error  on '.execute_transaction(sql)'. {str(err)} SQL := {current_statement}")
            self.cursor.execute("rollback")
            return False
        except Exception as err:
            self.logger.error(f"Unexpected error on '.execute_transaction()'.{str(err)} SQL := {current_statement}")
            return False

        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.debug(f"SQL transaction executed in {duration:.6f}s: {sql}")
        return True

    def __fetchall(self, sql: str):
        """Executes an SQL query statement and returns all records as the resultset."""
        duration = 0.0
        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer()

        if not self.cursor:
            self.cursor = self.conn.cursor()
        result = self.cursor.execute(sql).fetchall()

        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.error(f"SQL fetchall executed in {duration:.6f}s: {sql}")

        return result

    def __generate_path_from_database_name(self, database_name: str):
        if self._in_memory:
            return None, None, None
        file_name = database_name + self.DB_EXTENSION
        file_folder = os.path.join(os.getcwd(), self.DB_FOLDER_NAME)
        if not path.isdir(file_folder):
            os.mkdir(file_folder)
        file_path = os.path.join(file_folder, file_name)
        return file_name, file_folder, file_path

    def dimension_update(self, dimension, json):
        if self._in_memory:
            return
        """"""
        data = [dimension.name, json]
        sql = f"INSERT INTO {self.META_TABLE_DIM} (key, config)" \
              f"VALUES(?, ?)  " \
              f"ON CONFLICT(key) DO UPDATE SET config = excluded.config;"
        self.__execute(sql, data)
        self.commit()
        self.logger.info(f"Configuration of dimension '{dimension.name}' added or updated in meta table.")

    def dimension_remove(self, dimension):
        if self._in_memory:
            return
        """Deletes all tables related to a dimension."""
        self.__execute(f"DELETE FROM {self.META_TABLE_DIM} WHERE key = '{dimension.name}';")
        self.logger.info(f"Dimension '{dimension.name}' removed from meta table.")

    def meta_dim(self):
        """Returns all dimension meta data."""
        return self.__fetchall(f"SELECT * FROM {self.META_TABLE_DIM}")

    def dimensions_count(self):
        """Returns the number of dimensions defined in the database."""
        return self.__fetchall(f"SELECT COUNT(*) FROM {self.META_TABLE_DIM}")[0]