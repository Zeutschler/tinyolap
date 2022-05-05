# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import datetime
import bisect
from enum import IntEnum

from tinyolap.commands import *


class HistoryMode(IntEnum):
    OFF = 0
    SESSION = 1
    PERSIST = 2


# class TimeMachineCommandEnum(Enum):
#     UNDEFINED = 0
#     SET = 1
#     ADD_DIM = 10
#     DEL_DIM = 11
#     ALTER_DIM = 12
#     ADD_CUBE = 50
#     DEL_CUBE = 51


class HistoryPartition:
    """Represents a partition of a History log.
    The HistoryLog is segmented into partitions to support log persistence over multiple usage sessions
    of a database, e.g. over multiple days, weeks, months or years. Only the last relevant partitions should
    be loaded into memory (by default)."""

    def __init__(self):
        self._log: list[Command] = []
        self._log_ts: list[datetime] = []
        self._first: datetime = datetime.datetime.now()
        self._last: datetime = self._first
        self._cursor: int = 0

    @property
    def first(self) -> datetime:
        return self._first

    @property
    def last(self) -> datetime:
        return self._last

    @property
    def cursor(self) -> int:
        """Returns the actual cursor of the partition. If the History is not is use,
        the cursor points to the end of the partition, otherwise to the entry next to be
        undone. If all entries of the partition are already undone, then cursor will
        return -1."""
        return self._cursor

    def reset(self):
        """Resets the cursor of the partition."""
        self._cursor = len(self._log) - 1

    def get_and_move_previous(self):
        """
        Returns the log entry at the current cursor position and moves the cursor to the previous log entry.
        :return: A tuple containing 1st a boolean indicating if the cursor is already at the first position,
                 2nd the timestamp of the log entry, 3rd the data of the log entry.
        """
        if self._cursor < 0:
            raise IndexError("Cursor is already at the begin.")
        self._cursor -= 1
        return self._cursor > 0, self._log_ts[self._cursor + 1], self._log[self._cursor + 1]

    def get_and_move_next(self):
        """
        Returns the log entry at the current cursor position and moves the cursor to the next log entry.
        :return: A tuple containing 1st a boolean indicating if the cursor is already at the end of the log,
                 2nd the timestamp of the log entry, 3rd the data of the log entry.
        """
        if self._cursor >= len(self._log):
            raise IndexError("Cursor is already at the end.")
        self._cursor += 1
        return self._cursor >= len(self._log), self._log_ts[self._cursor - 1], self._log[self._cursor - 1]

    def __len__(self):
        return len(self._log)

    def any(self, from_timestamp: datetime = datetime.datetime.min,
            to_timestamp: datetime = datetime.datetime.max):
        """Evaluates if any log entries exists that falls into a given time frame.

        :param from_timestamp: Form timestamp. The earliest timestamp to consider.
        :param to_timestamp: To timestamp. The latest timestamp to consider.
        :return: ``True``, if at least one log entry exists, ``False`` otherwise.
        """
        return self.count(from_timestamp, to_timestamp) > 0

    def count(self, from_timestamp: datetime = datetime.datetime.min,
              to_timestamp: datetime = datetime.datetime.max):
        """Evaluates the number of log entries that fall into a given time frame.

        :param from_timestamp: Form timestamp. The earliest timestamp to consider.
        :param to_timestamp: To timestamp. The latest timestamp to consider.
        :return: The number of log entries within the given timeframe.
        """
        if to_timestamp < self._first or from_timestamp > self._last:
            return 0
        if from_timestamp <= self._first and to_timestamp >= self._last:
            return len(self._log)

        first = bisect.bisect_left(self._log_ts, from_timestamp)
        last = bisect.bisect_right(self._log_ts, to_timestamp, lo=first)
        return last - first

    def append(self, command: Command):
        """
        Appends data to the log partition.
        :param command: The command to be added to the log.
        """
        if len(self._log) == 0:
            self._first = command.timestamp
            self._last = self._first
        else:
            self._last = command.timestamp
        self._log_ts.append(self._last)
        self._log.append(command)

    def clear(self, from_timestamp: datetime = datetime.datetime.min,
              to_timestamp: datetime = datetime.datetime.max):
        """
        Clears the log. If none of the optional parameters ``from_timestamp`` and ``to_timestamp`` will defined,
        then the entire log will be cleared. Otherwise only the log entries of the given timeframe will be deleted.
        :param from_timestamp: Form timestamp. The earliest timestamp to consider.
        :param to_timestamp: To timestamp. The latest timestamp to consider.
        """
        if to_timestamp < self._first or from_timestamp > self._last:
            return  # nothing to delete

        if from_timestamp <= self._first and to_timestamp >= self._last:
            # delete all
            self._log = []
            self._log_ts = []
            self._first: datetime = datetime.datetime.now()
            self._last: datetime = self._first
            return

        # delete specific entries from time frame.
        first = bisect.bisect_left(self._log_ts, from_timestamp)
        last = bisect.bisect_right(self._log_ts, to_timestamp, lo=first)
        self._log = self._log[:first] + self._log[last:]
        self._log_ts = self._log_ts[:first] + self._log_ts[last:]

    def pop(self):
        """Removes and returns the last entry from the partition."""
        raise NotImplementedError()

    def peek(self):
        """Returns the last entry from the partition without removing it."""
        raise NotImplementedError()

    def __getitem__(self, item) -> (datetime, Command):
        if item is int:
            return self._log_ts[item], self._log[item]
        raise KeyError("Int index expected.")


class HistoryCursor:
    def __init__(self, log: HistoryLog):
        self._log = log
        self._partition: int = len(log._partitions) - 1
        self._index: int = len(log._partitions[-1]) - 1
        self._first = datetime.datetime.min
        self._last = self._first

    def __len__(self):
        return len(self._log)

    @property
    def length(self) -> int:
        """Returns the length of the history log."""
        return len(self._log)

    @property
    def earliest_timestamp(self) -> datetime:
        """
        Returns the first timestamp available in the history.
        If the history is empty, the current date-time will be returned.
        """
        if len(self._log._partitions[0]):
            timestamp = self._log._partitions[0]._log_ts[0]
        else:
            timestamp = datetime.datetime.now()
        return timestamp

    @property
    def latest_timestamp(self) -> datetime:
        """
        Returns the latest timestamp available in the history.
        If the history is empty, the current date-time will be returned.
        """
        last_partition = len(self._log._partitions) - 1
        if last_partition >= 0:
            len_last_partition = len(self._log._partitions[last_partition]._log_ts)
            if len_last_partition == 0:
                if last_partition == 0:
                    timestamp = datetime.datetime.now()
                else:
                    partition = last_partition - 1
                    timestamp = self._log._partitions[last_partition]._log_ts[-1]
            else:
                timestamp = self._log._partitions[last_partition]._log_ts[-1]
        else:
            timestamp = datetime.datetime.now()
        return timestamp


class HistoryLog:
    """A log to support the time machine capabilities for TinyOlap databases."""

    def __init__(self):
        self._partition_max_size: int = 100_000  # the max. size of a partition, in number of records
        self._partitions: list[HistoryPartition] = [HistoryPartition()]
        self._current_partition: int = 0
        self._cursor_partition: int = 0
        self._cursor = HistoryCursor(self)

    @property
    def first(self) -> datetime:
        """Returns the first timestamp contained in the HistoryLog."""
        return self._partitions[0].first

    @property
    def last(self) -> datetime:
        """Returns the last timestamp contained in the HistoryLog."""
        return self._partitions[self._current_partition].last

    def __len__(self):
        return sum([len(partition) for partition in self._partitions])

    def clear(self):
        """Clears the time machine log."""
        self._partitions: list[HistoryPartition] = [HistoryPartition()]
        self._current_partition: int = 0

    def is_empty(self) -> bool:
        return len(self) == 0

    def append(self, data):
        self._partitions[self._current_partition].append(data)

    def get_and_move_previous(self):
        """
        Returns the log entry at the current cursor position and moves the cursor to the previous log entry.
        :return: A tuple containing 1st a boolean indicating if the cursor is already at the first position,
                 2nd the timestamp of the log entry, 3rd the data of the log entry.
        """
        if self._cursor_partition < 0:
            raise IndexError("Cursor is already at the begin.")
        has_previous, timestamp, data = self._partitions[self._cursor_partition].get_and_move_previous()
        if not has_previous:
            self._cursor_partition -= 1
        return self._cursor_partition >= 0, timestamp, data

    def get_and_move_next(self):
        """
        Returns the log entry at the current cursor position and moves the cursor to the next log entry.
        :return: A tuple containing 1st a boolean indicating if the cursor is already at the end of the log,
                 2nd the timestamp of the log entry, 3rd the data of the log entry.
        """
        if self._cursor_partition > len(self._partitions):
            raise IndexError("Cursor is already at the end.")
        has_next, timestamp, data = self._partitions[self._cursor_partition].get_and_move_next()
        if not has_next:
            self._cursor_partition += 1
        return self._cursor_partition <= len(self._partitions), timestamp, data

    def reset(self):
        """Resets the cursor for the log."""
        for partition in self._partitions:
            partition.reset()
        self._cursor_partition = len(self._partitions) - 1

    def entries(self, reverse: bool = True):
        """Return the entries of the log, implemented as an iterator. Calling this method will reset the cursor.

        :param reverse: If set to ``True``(the default value), then the log will be iterated in reverse order,
                        meaning latest entries first.
        :return: The entries from the log.
        """
        self.reset()
        while self._cursor_partition >= 0:
            has_previous, timestamp, data = self._partitions[self._cursor_partition].get_and_move_previous()
            if not has_previous:
                self._cursor_partition -= 1
            yield self._cursor_partition >= 0, timestamp, data


class History:
    def __init__(self, database):
        self._database = database
        self._log = HistoryLog()
        self._cursor = HistoryCursor(self._log)
        self._mode = HistoryMode.OFF

    @property
    def mode(self) -> HistoryMode:
        """Returns the time machine mode."""
        return self._mode

    @mode.setter
    def mode(self, value: HistoryMode):
        """Sets the time machine mode."""
        self._mode = value

    @property
    def is_enabled(self):
        return not self._mode == HistoryMode.OFF

    def append(self, command: Command):
        """
        Appends a command to the history.
        :param command: The command to append.
        """
        if self._mode is HistoryMode.OFF:
            return

        self._log.append(command)

    def append_cube_set(self, cube: str, address, value_before, value_after):
        """
        Appends a cube cell value change to the the History log.
        :param cube: The cube of the cell to be added.
        :param address: address of the cell to be added
        :param value_before: The previous value of the cell.
        :param value_after: The new value of the cell.
        """
        if self._mode is HistoryMode.OFF:
            return

        idx_address = self._database.cubes[cube]._address_to_idx_address(address)
        cmd = CubeSetCommand(cube, idx_address, value_before, value_after)
        self._log.append(cmd)

    def undo_to(self, timestamp: datetime.datetime = datetime.datetime.min):
        """
        Undo all executed commands up to a certain point in time. If the timestamp
        is higher then the last timestamp available in the history log, then no undo will be executed.
        If the timestamp is earlier than the first timestamp available in the history log,
        then the entire history log will be undone.

        :param timestamp: The point in time up to when the executed commands should be undone.
        :return: True if the undo was processed successfully. False otherwise.
        """
        pass

    def redo_to(self, timestamp: datetime.datetime = datetime.datetime.max):
        """
        Redo all undone executed commands up to a certain point in time. If the timestamp
        is earlier then the current cursor position within the history log (state of undo's),
        then no redo will be executed.
        If the timestamp is higher than the last timestamp available in the history log,
        then all undo's will be redone.

        :param timestamp: The point in time up to when the executed commands should be redone.
        :return: True if the undo was processed successfully. False otherwise.
        """
        pass

    def undo(self, count: int = 1):
        """
        Undo a certain number of executed commands.
        If parameter ``count`` is set to -1 or to a number higher than the number of available
        commands in the history log, then all commands will be undone.

        :param count: Number of commands to be undone, default value is 1 undo. If parameter ``count`` is set to -1 or
        to a number higher than the number of available commands in the history log, then all commands will be undone.
        :return: ``True`` if the undo was processed successfully. ``False`` otherwise.
        """
        for has_prev, timestamp, command in self._log.entries():
            self._process(command)
            count -= 1
            if count == 0:
                break

    def redo(self, count: int = 1):
        """
        Redo a certain number of executed commands.
        If parameter ``count`` is set to -1 or to a number higher than the number of available
        commands in the history log, then all commands will be undone.

        :param count: Number of commands to be undone, default value is 1 redo. If parameter ``count`` is set to -1 or
        to a number higher than the number of available commands in the history log, then all commands will be undone.
        :return: ``True`` if the redo was processed successfully. ``False`` otherwise.
        """
        pass

    def cursor_position(self) -> int:
        """
        Returns the current position of the history log cursor. If the history is at the current state,
        meaning no commands have been undone, then 0 will be returned. Otherwise the number
        currently undone commands will be returned.
        """
        pass

    def cursor_timestamp(self) -> int:
        """
        Returns the current timestamp at the history log cursor. This is the timestamp of the
        next to be undone command. If all commands have already been undone,
        then ``datetime.datetime.min`` will be returned.
        """
        pass

    def _process(self, command: Command, undo: bool = True):
        if undo:
            command.undo(self._database)
        else:
            command.redo(self._database)
