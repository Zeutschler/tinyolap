# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import annotations
import datetime
import logging
import os
import sqlite3
import string
from os import path
from pathlib import Path

def evaluate_path(self, name: str) -> tuple[bool, str, Path, str]:
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
        raise TinyOlapFileError(msg)

    # Assemble database file name
    file_path = os.path.join(folder, file_name)
    file = Path(file_path)
    exists = file.exists() & file.is_file()
    file_path = file.absolute()
    folder = file.parent.absolute()
    file_name = file.name
    return bool(exists), str(folder), file_path, file_name

def to_save_name(self, name: str) -> str:
    """
    Converts a string to a valid filename.
    :param name: The name to be converted.
    :return: A valid file_name, without special characters.
    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    valid_name = ''.join(c for c in name if c in valid_chars)
    return valid_name.replace(' ', '_')