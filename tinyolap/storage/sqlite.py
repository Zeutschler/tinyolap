# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import datetime
from abc import ABC, abstractmethod
import logging
import os
import string
import sqlite3
from collections.abc import Iterable
from os import path
from pathlib import Path
from timeit import default_timer as timer
import tinyolap.utils
from tinyolap.storage.storageprovider import StorageProvider
from tinyolap.exceptions import *
from tinyolap.encryption import Encryptor, NotAnEncryptor


class SqliteStorage(StorageProvider):
    """SQLite 3 storage provider. Default for persistence in TinyOlap."""

    LOG_PREFIX = " SqliteStorage - "

    # file related names
    DB_DEFAULT_FOLDER_NAME = "db"
    DB_EXTENSION = ".tinyolap.db"
    LOG_EXTENSION = ".tinyolap.log"
    LOG_LEVEL = logging.INFO

    # database object names
    META_TABLE_META = "tinyolap_meta"
    META_TABLE_CUBES = "tinyolap_cubes"
    META_TABLE_DIMENSIONS = "tinyolap_dimensions"
    META_TABLE_FIELDS = [("key", "TEXT PRIMARY KEY"), ("config", "TEXT")]

    HISTORY_TABLE = "tinyolap_history"
    HISTORY_TABLE_FIELDS = [("timestamp", "TEXT"), ("user", "TEXT"), ("action", "TEXT"), ("data", "TEXT")]

    DATA_TABLE_PREFIX = "tinyolap_data_"

    def __init__(self, name: str, database_folder: str = None, enable_logging: bool = True,
                 logger: logging.Logger = None, encryptor: Encryptor = None):
        self.name = name.strip()
        self.database_folder = database_folder
        self.logging = enable_logging
        self.logger = logger
        self.log_file = None
        if self.logging and not self.logger:
            self._initialize_logger()
        if encryptor is None:
            encryptor = NotAnEncryptor()
        self.encryptor = encryptor
        self.file_name = None
        self.folder = None
        self.file_path = None
        self.is_open = False
        self.conn: sqlite3.Connection = None
        self.cursor: sqlite3.Cursor = None

    # region basic database handling - open , close, delete, ...
    @property
    def connected(self) -> bool:
        """
        Identifies if the storage provider is connected or open.
        :return: ``True`` if the storage provider is connected, ``False`` otherwise.
        """
        return self.is_open

    @property
    def uri(self) -> str:
        """
        Returns or sets the uri (uniform resource identifier) of the current database.
        :return: The uri of the database.
        """
        if not self.file_path:
            file_exists, folder, self.file_path, self.file_name = self._evaluate_path(self.name)
            if file_exists:
                return self.file_path.as_uri()
        return self.file_path.as_uri()

    @uri.setter
    def uri(self, value: str):
        """
        Returns or sets the uri (uniform resource identifier) of the current database.
        :return: The uri of the database.
        """
        file_exists, self.folder, self.file_path, self.file_name = self._evaluate_path(value)

    def open(self, **kwargs) -> bool:
        """
        Opens the database. If the database does not exist, a new database file will be created.
        :param kwargs:
        :return: Returns ``True``if the database has been opened successfully.
        :raises DatabaseBackendException: Raised when the opening of / connecting to the database file failed.
        """
        if kwargs:
            file_name = kwargs["file_name"]
            if file_name:
                self.name = file_name

        file_exists, self.folder, self.file_path, self.file_name = self._evaluate_path(self.name)
        self.log_file = str(self.file_path) + self.LOG_EXTENSION
        self._initialize_logger()

        self.close()
        try:
            if self.logging:
                self.logger.info(f"{self.LOG_PREFIX}Opening database '{str(self.file_path)}'")
                # self.logger.handlers[0].flush()
            self.conn: sqlite3.Connection = sqlite3.connect(self.file_path)
            self.cursor: sqlite3.Cursor = self.conn.cursor()

            self._prepare_database()
            self.is_open = True
        except sqlite3.Error as err:
            msg = f"{self.LOG_PREFIX}Failed to open database '{self.file_path}'. SQLite exception: {str(err)}"
            if self.logging:
                self.logger.error(msg)
            raise DatabaseBackendException(msg)
        except Exception as err:
            msg = f"{self.LOG_PREFIX}Failed to open database '{self.file_path}'. {str(err)}"
            if self.logging:
                self.logger.error(msg)
            raise DatabaseBackendException(msg)
        return True

    def close(self) -> bool:
        """
        Closes the database.
        :return: ``True`` if the database was successfully closed
            or was already closed, ``False``otherwise.
        """
        if self.is_open:
            if self.logging and self.logger:
                self.logger.info(f"{self.LOG_PREFIX}Closing database '{self.file_path}'.")
                # self.logger.handlers[0].flush()
            if self.conn or self.is_open:
                try:
                    self._commit()
                    self.conn.close()
                except sqlite3.Error as err:
                    msg = f"{self.LOG_PREFIX}Failed to close database '{self.file_path}'. SQLite exception: {str(err)}"
                    if self.logging:
                        self.logger.error(msg)
                        # self.logger.handlers[0].flush()
                    raise DatabaseBackendException(msg)
                except Exception as err:
                    msg = f"{self.LOG_PREFIX}Failed to close database '{self.file_path}'. {str(err)}"
                    if self.logging:
                        self.logger.error(msg)
                        # self.logger.handlers[0].flush()
                    raise DatabaseBackendException(msg)

        self.is_open = False
        return True

    def exists(self) -> bool:
        """
        Checks if a database with the given name exists.
        :return: ``True`` if the database file exists, ``False``otherwise.
        """
        file_exists, folder, file_path, file_name = self._evaluate_path(self.name)
        return file_exists

    def delete(self) -> bool:
        """
        Deletes the database file and the database log file, if such exist.
        :return: True if the database file and the database log file was deleted successfully
        or if both do not exist.
        """
        file_exists, folder, file_path, file_name = self._evaluate_path(self.name)
        try:
            if self.is_open:
                self.close()
            if path.exists(file_path):
                if self.logging and self.logger:
                    self.logger.info(f"{self.LOG_PREFIX}Deleting database file '{self.file_path}'.")
                    # self.logger.handlers[0].flush()
                os.remove(file_path)
            self.delete_log()
            return True
        except OSError as err:
            if self.logging:
                self.logger.error(f"{self.LOG_PREFIX}Failed to delete database file '{self.file_path}'. {str(err)}")
                # self.logger.handlers[0].flush()
            return False

    def delete_log(self) -> bool:
        """
        Deletes the database log file, if such exists.
        :return: True if the log file was deleted successfully or if the log file not exist.
        """
        file_exists, folder, file_path, file_name = self._evaluate_path(self.name)
        self.log_file = str(file_path) + self.LOG_EXTENSION
        try:
            if path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except OSError:
            return False

    # endregion

    # region History related methods
    def add_to_history(self, time_stamp: datetime.datetime, user: str, action: str, data: str):
        """
        Add an event to the database history.
        :param time_stamp: Timestamp of the event
        :param user: The name of the user that initiated the event.
        :param action: The name of action executed through the event.
        :param data: The data related to the event. Defines what and how to undo or redo the event.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def add_many_to_history(self, records: list[tuple[datetime.datetime, str, str, str]]):
        """
        Add multiple events to the database history.
        :param records: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str)
        """
        # todo: implementation missing
        raise NotImplementedError()

    def clear_history(self):
        """
        Clears the entire history.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def delete_history_earlier_than(self, time_stamp: datetime.datetime):
        """
        Deletes all events from the history earlier than a specific timestamp.
        :param time_stamp: The timestamp to apply.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def delete_history_later_than(self, time_stamp: datetime.datetime):
        """
        Deletes all events from the history later than a specific timestamp.
        :param time_stamp: The timestamp to apply.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def delete_history_by_rowid(self, rowid):
        """
        Deletes events from the history by their rowid. Argument ``rowids`` can either be a single
        int value or an iterable of int.
        :param rowid: Either a single int value, or an iterable of int.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def get_history_from_time_window(self, from_time_stamp: datetime.datetime = datetime.datetime.min,
                                     to_time_stamp: datetime.datetime = datetime.datetime.max) \
            -> list[tuple[datetime.datetime, str, str, str, int]]:
        """
        Returns the history records for a given time window.
        :param from_time_stamp: Begin of the time window.
        :param to_time_stamp: End of the time window.
        :return: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str, rowid:int)
        sorted in ascending order by the timestamp.
        """
        # todo: implementation missing
        raise NotImplementedError()

    def get_history(self, count: int = 1) -> list[tuple[datetime.datetime, str, str, str, int]]:
        """
        Returns the a certain number of records from the history.
        :param count: Number of records to be returned.
        :return: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str, rowid:int)
        sorted in ascending order by the timestamp.
        """
        a = f"SELECT * FROM ContentMaster WHERE ContentAddedByUserID = '%@' ORDER BY rowid DESC LIMIT {count}"
        # todo: implementation missing
        raise NotImplementedError()

    def count_history(self):
        """
        Returns the number of records in the history.
        """
        # todo: implementation missing
        raise NotImplementedError()

    # endregion

    # region Cell (data record) related methods
    def set_record(self, cube_name, address: str, data: str = None, instant_commit: bool = True) -> bool:
        """
        Add, updates or deletes a record related to a specific address and cube.
        To delete data, set argument ``data`` to ``None``.
        :param cube_name: Name of the targeted cube.
        :param address: The address of the cube cell as a string.
          Recommendation: use *str(idx_address:tuple[int])* to generate address from int cell address tuples.
        :param data: The data to be set as a string. The json format should be applied, or any string.
        :param instant_commit: If set to ``True``, then the change is instantly committed to the underlying database.
        :return: ``True`` if successful.
        """
        # todo: add encryption

        table = self.DATA_TABLE_PREFIX + cube_name
        if not data:
            sql = f"DELETE FROM {table} WHERE address = '{address}';"
            self._execute(sql)
        else:
            sql = f"INSERT INTO {table}(address, data) VALUES(?,?) " \
                  f"ON CONFLICT(address) DO UPDATE SET data=EXCLUDED.data;"
            if self.encryptor:
                data = self.encryptor.encrypt(data)
            self._execute(sql, (address, data))
        if instant_commit:
            self._commit()
        return True

    def set_records(self, cube_name, records: list[tuple[str, str]], instant_commit: bool = True) -> bool:
        """
        Add, updates or deletes a record related to a specific address and cube.
        To delete data, set argument ``data`` to ``None``.
        :param cube_name: Name of the targeted cube.
        :param records: A list of (address, data) tuples to be set for the specific cube.
        :param instant_commit: If set to ``True``, then the change is instantly committed to the underlying database.
        :return: ``True`` if successful.
        """
        # todo: add encryption

        table = self.DATA_TABLE_PREFIX + cube_name
        # separate records that should be deleted and upserted.
        del_records = [(address,) for address, data in records if not data]
        if del_records:
            sql = f"DELETE FROM {table} WHERE address = '?';"
            self._execute(sql, del_records)
            if self.encryptor:
                upsert_records = [(address, self.encryptor.encrypt(data)) for address, data in records if data]
            else:
                upsert_records = [(address, data) for address, data in records if data]
        else:
            upsert_records = records

        if upsert_records:
            sql = f"INSERT INTO {table}(address, data) VALUES(?,?) " \
                  f"ON CONFLICT(address) DO UPDATE SET data=EXCLUDED.data;"
            self._execute(sql, upsert_records)

        if instant_commit:
            self._commit()
        return True

    def get_record(self, cube_name: str, address: str):
        """
        Returns data from a cubes data table.
        :param cube_name: Name of the cube to get data from.
        :param address: The requested address.
        :return: The data stored for the given address.
           If the address does not exist, ``None`` will be returned.
        """
        # todo: add encryption

        table = self.DATA_TABLE_PREFIX + cube_name
        sql = f"SELECT data FROM {table} WHERE address = '{address}';"
        records = self._fetchall(sql)
        if records:
            if self.encryptor:
                return self.encryptor.decrypt(records[0][0])
            else:
                return records[0][0]
        return None

    def get_records(self, cube_name: str):
        """
        Returns all records from a cubes data table.
        :param cube_name: Name of the cube to get data from.
        :return: All records of the cube.
        """
        # todo: add encryption

        table = self.DATA_TABLE_PREFIX + cube_name
        sql = f"SELECT * FROM {table};"
        records = self._fetchall(sql)
        if records:
            return records
        return None

    # endregion

    # region meta data related methods
    def add_meta(self, key: str, json: str):
        """
        Adds or updates a meta configuration.
        :param key: The name of the meta item.
        :param json: The configuration of the meta item in json format.
        """
        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Adding or updating meta configuration for key: '{key}'.")
            # self.logger.handlers[0].flush()

        key = self.encryptor.encrypt(key)
        json = self.encryptor.encrypt(json)

        data = (key, json)
        sql = f"INSERT INTO {self.META_TABLE_META} (key, config)" \
              f"VALUES(?, ?)  " \
              f"ON CONFLICT(key) DO UPDATE SET config = EXCLUDED.config;"
        self._execute(sql, data)
        self._commit()

    def get_meta(self, key: str) -> str:
        """
        Returns the configuration of a meta item in json format.
        :return: A json string.
        """
        key = self.encryptor.encrypt(key)

        result = self._fetchall(f"SELECT config FROM {self.META_TABLE_META} WHERE key = '{key}'")
        if result:
            value = str(result[0][0])
            value = self.encryptor.decrypt(value)
            return value
        return None

    # endregion

    # region Cube related methods
    def get_cubes(self) -> list[tuple[str, str]]:
        """
        Returns a list of all cubes and their configuration (in json format)
        available in the database.
        :return: A list of tuples of type (cube_name:str, json:str).
        """
        # todo: add encryption

        result = self._fetchall(f"SELECT * FROM {self.META_TABLE_CUBES}")
        return result

    def get_cube_names(self) -> list[str]:
        """
        Returns a list of all cubes names available in the database.
        :return: List of cube names.
        """
        # todo: add encryption

        names = []
        result = self._fetchall(f"SELECT key FROM {self.META_TABLE_CUBES}")
        for row in result:
            names.append(row[0])
        return names

    def count_cubes(self):
        """
        Returns the number of cubes defined in the database.
        :return: The number of cubes defined for the database.
        """
        return self._fetchall(f"SELECT COUNT(*) FROM {self.META_TABLE_CUBES}")[0][0]

    def add_cube(self, cube_name: str, json: str) -> bool:
        """
        Adds or updates a cube configuration.
        :param dimensions_count: Number of the dimension in the cube.
          If set to -1, then no data table will be created.
        :param cube_name: The name of the cube.
        :param json: The configuration of the cube in json format.
        :return: ``True`` if successful,``False`` otherwise.
        """
        # todo: add encryption

        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Adding or updating configuration for cube '{cube_name}'.")
            # self.logger.handlers[0].flush()
        # add cube to meta table
        data = (cube_name, json)
        sql = f"INSERT INTO {self.META_TABLE_CUBES} (key, config)" \
              f"VALUES(?, ?)  " \
              f"ON CONFLICT(key) DO UPDATE SET config=EXCLUDED.config;"
        self._execute(sql, data)

        # create cube data table
        table_name = self.DATA_TABLE_PREFIX + cube_name
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} " \
              f"(address TEXT PRIMARY KEY, data TEXT" \
              f") WITHOUT ROWID;"
        self._execute(sql)

        self._commit()
        return True

    def remove_cube(self, cube_name: str):
        """
        Removes a cube from the database.
        :param cube_name: Name of the cube to be removed.
        """
        # todo: add encryption

        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Removing configuration and data tables for cube '{cube_name}'.")
            # self.logger.handlers[0].flush()
        table_name = self.DATA_TABLE_PREFIX + cube_name
        self._execute(f"DROP TABLE IF EXISTS {table_name};")
        self._execute(f"DELETE FROM {self.META_TABLE_CUBES} WHERE key = '{cube_name}';")
        self._commit()

    def clear_cube(self, cube_name: str) -> True:
        """
        Clears (deletes) all records from a cubes data table.
        :param cube_name: The name of the cube to be cleared.
        :return:
        """
        table_name = self.DATA_TABLE_PREFIX + cube_name
        if self._table_exists(table_name):
            self._execute(f"DELETE FROM {table_name};")
            self._commit()
        return True

    def count_cube_records(self, cube_name: str) -> int:
        """
        Returns the number of records contained in cube table.
        :return: The number of records in cube table.
        """
        # todo: add encryption

        table_name = self.DATA_TABLE_PREFIX + cube_name
        return self._fetchall(f"SELECT COUNT(*) FROM {table_name}")[0][0]

    # endregion

    # region Dimension related methods
    def get_dimensions(self) -> list[tuple[str, str]]:
        """
        Returns a list of all dimensions and their configuration (in json format)
        available in the database.
        :return: A list of tuples of type (cube_name:str, json:str).
        """
        # todo: add encryption

        result = self._fetchall(f"SELECT * FROM {self.META_TABLE_DIMENSIONS}")
        if result:
            return result
        return []

    def get_dimension_names(self) -> list[str]:
        """
        Returns a list of all dimension names available in the database.
        :return: List of database names.
        """
        # todo: add encryption

        names = []
        result = self._fetchall(f"SELECT key FROM {self.META_TABLE_DIMENSIONS}")
        for row in result:
            names.append(row[0])
        return names

    def count_dimensions(self):
        """
        Returns the number of dimensions defined in the database.
        :return: The number of dimension defined for the database.
        """
        # todo: add encryption

        return self._fetchall(f"SELECT COUNT(*) FROM {self.META_TABLE_DIMENSIONS}")[0][0]

    def add_dimension(self, dimension_name: str, json: str) -> bool:
        """
        Adds or updates a dimension configuration.
        :param dimension_name: The name of the dimension.
        :param json: The configuration of the dimension in json format.
        :return: ``True`` if successful,``False`` otherwise.
        """
        # todo: add encryption

        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Adding or updating configuration for dimension '{dimension_name}'.")
            # self.logger.handlers[0].flush()
        data = (dimension_name, json)
        sql = f"INSERT INTO {self.META_TABLE_DIMENSIONS} (key, config)" \
              f"VALUES(?, ?)  " \
              f"ON CONFLICT(key) DO UPDATE SET config = EXCLUDED.config;"
        self._execute(sql, data)
        self._commit()

    def remove_dimension(self, dimension_name: str):
        """
        Removes a dimension from the database.
        :param dimension_name: Name of the dimension to be removed.
        """
        # todo: add encryption

        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Removing configuration for dimension '{dimension_name}'.")
            # self.logger.handlers[0].flush()
        sql = f"DELETE FROM {self.META_TABLE_DIMENSIONS} WHERE key = '{dimension_name}';"
        self._execute(sql)
        self._commit()

    # endregion

    # region database related internal methods
    def _commit(self, optimize=False) -> True:
        """
        Commits all accumulated changes to the database. Optionally, the database can be optimized (compacted).
        :param optimize: if set to ``True``, the database will be optimized and compacted.
        :return: ``True`` if the commit and the optimization was successful.
        :raises DatabaseBackendException: Raised when the commit or (optional) optimization of the database failed.
        """
        if optimize:
            try:
                if self.logging:
                    self.logger.info(f"{self.LOG_PREFIX}Optimizing database (PRAGMA vacuum; PRAGMA optimize;).")
                    # self.logger.handlers[0].flush()
                self._execute('PRAGMA vacuum;')
                self._execute('PRAGMA optimize;')
            except sqlite3.Error as err:
                msg = f"{self.LOG_PREFIX}Failed to optimize database. SQLite exception: {str(err)}"
                if self.logging:
                    self.logger.error(msg)
                    # self.logger.handlers[0].flush()
                raise DatabaseBackendException(msg)
            except Exception as err:
                msg = f"{self.LOG_PREFIX}Failed to optimize database. {str(err)}"
                if self.logging:
                    self.logger.error(msg)
                    # self.logger.handlers[0].flush()
                raise DatabaseBackendException(msg)

        try:
            if self.conn and self.is_open:
                self.conn.commit()
            return True
        except sqlite3.Error as err:
            msg = f"{self.LOG_PREFIX}Failed to commit database. SQLite exception: {str(err)}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            raise DatabaseBackendException(msg)
        except Exception as err:
            msg = f"{self.LOG_PREFIX}Failed to commit database. {str(err)}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            raise DatabaseBackendException(msg)

    def _prepare_database(self) -> bool:
        """
        Validates and prepares a database to be used as a TinyOlap storage_provider
        by adding some meta tables.
        :return: ``True`` if the database was successfully prepared, ``False`` otherwise.
        :raises DatabaseBackendException: Raised when the preparation of the database failed.
        """

        # Check if meta tables already exist - then it's (most likely) a valid TinyOlap database.
        if not (self._table_exists(self.META_TABLE_CUBES) and self._table_exists(self.META_TABLE_DIMENSIONS)):
            # ...not yet a TinyOlap database, let's configure it.
            if self.logging:
                self.logger.info(f"{self.LOG_PREFIX}Prepare (new) database for initial use by adding meta tables.")
                # self.logger.handlers[0].flush()

            try:
                # do some configuration for optimized performance
                self._execute('PRAGMA temp_store=MEMORY;')
                self._execute('PRAGMA journal_mode=MEMORY;')
                self._commit()

                # add meta tables
                metas = [self.META_TABLE_META, self.META_TABLE_CUBES, self.META_TABLE_DIMENSIONS]
                for meta in metas:
                    if not self._table_exists(meta):
                        self._add_table(meta, self.META_TABLE_FIELDS)
                        self.add_meta("provider", "tinyolap")
                    if not self._table_exists(meta):  # ensure the table has been created.
                        if self.logging:
                            self.logger.info(f"{self.LOG_PREFIX}Failed to prepare database for use with TinyOlap.")
                        raise DatabaseBackendException("Failed to add meta tables to database.")

                # add and prepare history table
                if not self._table_exists(self.HISTORY_TABLE):
                    self._add_table(self.HISTORY_TABLE, self.HISTORY_TABLE_FIELDS)
                    self._execute(f"CREATE INDEX IF NOT EXISTS {self.HISTORY_TABLE}_timestamp_index "
                                  f"ON {self.HISTORY_TABLE}(timestamp);")
                    self._execute(f"CREATE INDEX IF NOT EXISTS {self.HISTORY_TABLE}_user_index "
                                  f"ON {self.HISTORY_TABLE}(user);")

            except sqlite3.Error as err:
                msg = f"{self.LOG_PREFIX}Failed to prepare database for use with TinyOlap. SQLite exception: {str(err)}"
                if self.logging:
                    self.logger.error(msg)
                    # self.logger.handlers[0].flush()
                raise DatabaseBackendException(msg)
            except Exception as err:
                msg = f"{self.LOG_PREFIX}Failed to prepare database for use with TinyOlap. {str(err)}"
                if self.logging:
                    self.logger.error(msg)
                    # self.logger.handlers[0].flush()
                raise DatabaseBackendException(msg)

        else:
            # check if data can be decrypted properly.
            provider = self.get_meta("provider")  # this should return 'tinyolap'
            if provider != "tinyolap":
                raise EncryptionException(f"Failed to open database. Invalid username or password.")

        return True

    def _add_table(self, table_name: str, fields: list[tuple[str, str]], index_sql: str = None):
        """
        Adds a new table to the database. If the table already exists,
        then the table will be dropped and recreated.
        :param table_name: Name of the table to be created.
        :param fields: A list of tuples containing field name and type
        """
        if self.logging:
            self.logger.info(f"{self.LOG_PREFIX}Adding or replacing table '{table_name}' to database.")
            # self.logger.handlers[0].flush()
        sql = f"DROP TABLE IF EXISTS {table_name};"
        self._execute(sql)
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([str(f[0]) + ' ' + str(f[1]) for f in fields])} );"
        self._execute(sql)
        self._commit()
        if index_sql:
            self._execute(index_sql)
            self._commit()
        return True

    def _table_exists(self, table_name) -> bool:
        """
        Evaluates if a table exists in the database.
        :param table_name: Name of the table to be evaluated.
        :return: ``True`` if the table exists, ``False`` otherwise.
        :raises DatabaseBackendException: Raised when the execution of the existence check failed.
        """
        if not self.cursor:
            self.cursor = self.conn.cursor()
        sql = f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        try:
            return self.cursor.execute(sql).fetchone()[0] == 1
        except (sqlite3.Error, Exception) as err:
            msg = f"{self.LOG_PREFIX}Failed to check existence of table {table_name} in database. {str(err)}"
            if self.logging:
                self.logger.error(msg)
            raise DatabaseBackendException(msg)

    def _get_tables(self):
        """
        Returns the list of all tables available in the database.
        :return: A resultset containing the tables of the database.
        """
        return self._fetchall(f"SELECT name, sql FROM sqlite_master WHERE type='table';")

    def _execute(self, sql: str, data=None) -> bool:
        """
        Executes an SQL statement without returning a result or resultset.
        Intended to be used for DDL statements.
        :param sql: The SQL statement to be executed.
        :param data: (optional) data to be handed in.
        :return: ``True`` is successful, ``False`` otherwise.
        """
        duration = 0.0
        if self.logging and self.LOG_LEVEL == logging.DEBUG:
            duration = timer()

        try:
            if not self.cursor:
                self.cursor = self.conn.cursor()
            if data:
                if type(data) is list:
                    result = self.cursor.executemany(sql, data)
                else:
                    result = self.cursor.execute(sql, data)
            else:
                result = self.cursor.execute(sql)

        except (sqlite3.Error, Exception) as err:
            msg = f"{self.LOG_PREFIX}Failed to execute SQL statement. {str(err)} SQL := {sql}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            raise DatabaseBackendException(msg)

        if self.logging and self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.debug(f"{self.LOG_PREFIX}SQL statement successfully executed in {duration:.6f}s: {sql}")
        return True

    def _execute_transaction(self, sql: list[str]) -> bool:
        """
        Executes a list of SQL statements within a single transaction (rollback on failure).
        :param sql: A list of SQL statement to be executed.
        :return: ``True`` is successful, ``False`` otherwise.
        """
        duration = 0.0
        if self.logging and self.LOG_LEVEL == logging.DEBUG:
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
        except (sqlite3.Error, Exception) as err:
            msg = f"{self.LOG_PREFIX}Failed to execute transaction containing {len(sql)} statements." \
                  f" {str(err)} Failed SQL := {current_statement}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            self.cursor.execute("rollback")
            raise DatabaseBackendException(msg)

        if self.logging and self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.debug(f"{self.LOG_PREFIX}SQL transaction executed in {duration:.6f}s: {sql}")
        return True

    def _fetchall(self, sql: str):
        """
        Executes an SQL statement and returns all records as the resultset.
        :param sql: The SQL statement to be executed.
        :return: The resultset of the query.
        """
        duration = 0.0
        if self.LOG_LEVEL == logging.DEBUG:
            duration = timer()

        try:
            if not self.cursor:
                self.cursor = self.conn.cursor()
            result = self.cursor.execute(sql).fetchall()
        except (sqlite3.Error, Exception) as err:
            msg = f"{self.LOG_PREFIX}Failed to execute SQL statement and fecth results. {str(err)} SQL := {sql}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            raise DatabaseBackendException(msg)

        if self.logging and self.LOG_LEVEL == logging.DEBUG:
            duration = timer() - duration
            self.logger.error(f"{self.LOG_PREFIX}SQL fetchall executed in {duration:.6f}s: {sql}")

        return result

    # endregion

    # region file handling & naming
    def _evaluate_path(self, name: str) -> tuple[bool, str, Path, str]:
        """
        Tries to evaluate a valid file path from a given name or file path.
        :param name: The name or file path to be evaluated.
        :return: A tuple of type (exists:bool, folder:str, path_to_file:str, file_name:str).
          The *exists* flag identifies if a file for the given name already exists.
        """
        # check if the name is a file path and maybe already exists
        file = Path(name)
        exists = file.exists() & file.is_file()
        if exists:
            file_path = file.absolute()
            file_name = file.name
            folder = file.parent.absolute()
            return bool(exists), str(folder), file_path, file_name

        # ...file does not exist, setup a valid file apth from the predefined or default file path.
        file_name = name
        if not file_name.endswith(self.DB_EXTENSION):
            file_name += self.DB_EXTENSION

        if not self.database_folder:  # use default database location
            folder = os.path.join(os.getcwd(), self.DB_DEFAULT_FOLDER_NAME)
        else:
            folder = self.database_folder

        # Ensure the database folder exists, if not create it.
        try:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                if self.logging:
                    self.logger.error(f"Database folder '{folder}' has been created.")
                    # self.logger.handlers[0].flush()
        except OSError as err:
            msg = f"Failed to create database folder '{folder}'. {str(err)}"
            if self.logging:
                self.logger.error(msg)
                # self.logger.handlers[0].flush()
            raise DatabaseBackendException(msg)

        # Assemble database file name
        file_path = os.path.join(folder, file_name)
        file = Path(file_path)
        exists = file.exists() & file.is_file()
        file_path = file.absolute()
        folder = file.parent.absolute()
        file_name = file.name
        return bool(exists), str(folder), file_path, file_name

    def _to_save_name(self, name: str) -> str:
        """
        Converts a string to a valid filename.
        :param name: The name to be converted.
        :return: A valid file_name, without special characters.
        """
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        valid_name = ''.join(c for c in name if c in valid_chars)
        return valid_name.replace(' ', '_')

    def _initialize_logger(self):
        """Initializes the logger, if required."""
        if self.logger:  # an existing logger was already handed in
            return
        if not self.logging:  # enable_logging not required.
            return

        self.logger = logging.getLogger("tinyolap.storage_provider.sqlite")

        if not self.log_file:
            file_exists, self.folder, self.file_path, self.file_name = self._evaluate_path(self.name)
            self.log_file = str(self.file_path) + self.LOG_EXTENSION

        handler = logging.FileHandler(self.log_file, mode='w')
        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(self.LOG_LEVEL)

        # self.logger = enable_logging.getLogger("TinOlap.SqliteStorage")
        # handler = enable_logging.FileHandler(self.log_file, mode='w')
        # handler.setLevel(self.LOG_LEVEL)
        # formatter = enable_logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        # handler.setFormatter(formatter)
        # self.logger.addHandler(handler)

    # endregion
