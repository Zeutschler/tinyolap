# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from readerwriterlock import rwlock


class Lock:
    """
    Provides read-writer-locks with write-priority for TinyOlap databases.
    Note: TinyOlap supports multiple parallel reads but only single isolated writes or changes,
    so locks are essential for database consistency.
    """
    def __init__(self):
        self._locks = dict()

    def __getitem__(self, item) -> rwlock.RWLockWrite:
        """
        Returns a read-writer-lock for the requested item.
        If the item key does not exist, a new read-writer lock will be created and returned
        :param item:
        :return: the requested lock
        """
        lock = self._locks.setdefault(item)
        if lock:
            return lock
        # create a new lock
        lock = rwlock.RWLockWrite()
        self._locks[item] = lock
        return lock
