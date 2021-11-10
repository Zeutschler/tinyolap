from enum import Enum
from abc import ABC, abstractmethod
import datetime


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    # region basic database handling - open , close, delete, ...
    @abstractmethod
    def open(self, **kwargs):
        """
        Opens the database. If the database does not exist, a new database file will be created.
        :param kwargs:
        :return: Returns ``True``if the database has been opened successfully.
        :raises DatabaseBackendException: Raised when the opening of / connecting to the database file failed.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Closes the database.
        :return: ``True`` if the database was successfully closed
            or was already closed, ``False``otherwise.
        """
        pass

    @abstractmethod
    def exists(self) -> bool:
        """
        Checks if a database with the given name exists.
        :return: ``True`` if the database file exists, ``False``otherwise.
        """
        pass

    @abstractmethod
    def delete(self):
        """
        Deletes the database file and the database log file, if such exist.
        :return: True if the database file and the database log file was deleted successfully
        or if both do not exist.
        """
        pass

    @abstractmethod
    def delete_log(self):
        """
        Deletes the database log file, if such exists.
        :return: True if the log file was deleted successfully or if the log file not exist.
        """
        pass
    # endregion

    # region History related methods
    @abstractmethod
    def add_to_history(self, time_stamp: datetime.datetime, user: str, action: str, data: str):
        """
        Add an event to the database history.
        :param time_stamp: Timestamp of the event
        :param user: The name of the user that initiated the event.
        :param action: The name of action executed through the event.
        :param data: The data related to the event. Defines what and how to undo or redo the event.
        """
        pass

    @abstractmethod
    def add_many_to_history(self, records: list[tuple[datetime.datetime, str, str, str]]):
        """
        Add multiple events to the database history.
        :param records: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str)
        """
        pass

    @abstractmethod
    def clear_history(self):
        """
        Clears the entire history.
        """
        pass

    @abstractmethod
    def delete_history_earlier_than(self, time_stamp: datetime.datetime):
        """
        Deletes all events from the history earlier than a specific timestamp.
        :param time_stamp: The timestamp to apply.
        """
        pass

    @abstractmethod
    def delete_history_later_than(self, time_stamp: datetime.datetime):
        """
        Deletes all events from the history later than a specific timestamp.
        :param time_stamp: The timestamp to apply.
        """
        pass

    @abstractmethod
    def delete_history_by_rowid(self, rowid):
        """
        Deletes events from the history by their rowid. Argument ``rowids`` can either be a single
        int value or an iterable of int.
        :param rowid: Either a single int value, or an iterable of int.
        """
        pass

    @abstractmethod
    def get_history_from_time_window(self, from_time_stamp: datetime.datetime = datetime.datetime.min,
                                     to_time_stamp: datetime.datetime = datetime.datetime.max)\
            -> list[tuple[datetime.datetime, str, str, str, int]]:
        """
        Returns the history records for a given time window.
        :param from_time_stamp: Begin of the time window.
        :param to_time_stamp: End of the time window.
        :return: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str, rowid:int)
        sorted in ascending order by the timestamp.
        """
        pass

    @abstractmethod
    def get_history(self, count: int = 1) -> list[tuple[datetime.datetime, str, str, str, int]]:
        """
        Returns the a certain number of records from the history.
        :param count: Number of records to be returned.
        :return: A list of tuples of format (time_stamp:datetime, user:str, action:str, data:str, rowid:int)
        sorted in ascending order by the timestamp.
        """
        pass

    @abstractmethod
    def count_history(self) -> int:
        """
        Returns the number of records in the history.
        """
        pass
    # endregion

    # region Cell (data record) related methods
    @abstractmethod
    def set_record(self, cube_name, address: str, data: str = None, instant_commit: bool = True):
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
        pass

    @abstractmethod
    def set_records(self, cube_name, records: list[tuple[str, str]], instant_commit: bool = True):
        """
        Add, updates or deletes a record related to a specific address and cube.
        To delete data, set argument ``data`` to ``None``.
        :param cube_name: Name of the targeted cube.
        :param records: A list of (address, data) tuples to be set for the specific cube.
        :param instant_commit: If set to ``True``, then the change is instantly committed to the underlying database.
        :return: ``True`` if successful.
        """
        pass

    @abstractmethod
    def get_record(self, cube_name: str, address: str) -> str:
        """
        Returns data from a cubes data table.
        :param cube_name: Name of the cube to get data from.
        :param address: The requested address.
        :return: The data stored for the given address.
           If the address does not exist, ``None`` will be returned.
        """
        pass
    # endregion

    # region Cube related methods
    @abstractmethod
    def get_cubes(self) -> list[tuple[str, str]]:
        """
        Returns a list of all cubes and their configuration (in json format)
        available in the database.
        :return: A list of tuples of type (cube_name:str, json:str).
        """
        pass

    @abstractmethod
    def get_cube_names(self) -> list[str]:
        """
        Returns a list of all cubes names available in the database.
        :return: List of cube names.
        """
        pass

    @abstractmethod
    def count_cubes(self) -> int:
        """
        Returns the number of cubes defined in the database.
        :return: The number of cubes defined for the database.
        """
        pass

    @abstractmethod
    def add_cube(self, cube_name: str, json: str):
        """
        Adds or updates a cube configuration.
        :param dimensions_count: Number of the dimension in the cube.
          If set to -1, then no data table will be created.
        :param cube_name: The name of the cube.
        :param json: The configuration of the cube in json format.
        :return: ``True`` if successful,``False`` otherwise.
        """
        pass

    @abstractmethod
    def remove_cube(self, cube_name: str):
        """
        Removes a cube from the database.
        :param cube_name: Name of the cube to be removed.
        """
        pass

    @abstractmethod
    def clear_cube(self, cube_name: str):
        """
        Clears (deletes) all records from a cubes data table.
        :param cube_name: The name of the cube to be cleared.
        :return:
        """
        pass

    @abstractmethod
    def count_cube_records(self, cube_name: str) -> int:
        """
        Returns the number of records contained in cube table.
        :return: The number of records in cube table.
        """
        pass
    # endregion

    # region Dimension related methods
    @abstractmethod
    def get_dimensions(self) -> list[tuple[str, str]]:
        """
        Returns a list of all dimensions and their configuration (in json format)
        available in the database.
        :return: A list of tuples of type (cube_name:str, json:str).
        """
        pass

    @abstractmethod
    def get_dimension_names(self) -> list[str]:
        """
        Returns a list of all dimension names available in the database.
        :return: List of dimension names.
        """
        pass

    @abstractmethod
    def count_dimensions(self) -> int:
        """
        Returns the number of dimensions defined in the database.
        :return: The number of dimension defined for the database.
        """
        pass

    @abstractmethod
    def add_dimension(self, dimension_name: str, json: str):
        """
        Adds or updates a dimension configuration.
        :param dimension_name: The name of the dimension.
        :param json: The configuration of the dimension in json format.
        :return: ``True`` if successful,``False`` otherwise.
        """
        pass

    @abstractmethod
    def remove_dimension(self, dimension_name: str):
        """
        Removes a dimension from the database.
        :param dimension_name: Name of the dimension to be removed.
        """
        pass
    # endregion




