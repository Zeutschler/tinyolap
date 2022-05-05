# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations
import re
import string
import os
from tinyolap.config import Config
from tinyolap.exceptions import *

import fnmatch
from itertools import chain
from typing import List, TypeVar, Generic
from collections.abc import Sequence
from packaging.version import parse as parse_version


MEMBER_NAME_CHARS = set(string.ascii_letters + string.digits + '.-_/#+-*:,;|{}()"')
DB_OBJECT_NAME_CHARS = set(string.ascii_letters + string.digits + '_-')


def is_version_compatible(version: str) -> bool:
    """Checks if a specific TinyOlap version number is compatible with the current version of the TinyOlap library.
    Especially relevant for file and database format upwards and downwards compatibility."""
    minimal_version = parse_version(Config.LOWEST_COMPATIBLE_VERSION)
    current_version = parse_version(Config.VERSION)
    version = parse_version(version)
    return (version >= minimal_version) and (version <= current_version)


def check_content_type_and_version(content_type: str, version: str, expected_content_type: str):
    """Ensures that the content type and the version for deserialization matches the requirements."""
    if content_type != expected_content_type:
        raise TinyOlapSerializationError(f"Unexpected content type. "
                                         f"'{expected_content_type}' expected, but "
                                         f"'{content_type}' was found.")
    if not is_version_compatible(version):
        raise TinyOlapSerializationError(f"Incompatible version '{version}' detected. "
                                         f"Lowest compatible version is '{Config.LOWEST_COMPATIBLE_VERSION}',"
                                         f"highest compatible version is '{Config.VERSION}' (current).")


def is_valid_member_name(name: str):
    """Checks if a given name is valid (only contains characters by MEMBER_NAME_CHARS)."""
    return set(name) <= MEMBER_NAME_CHARS


def is_valid_db_object_name(name: str):
    """Checks if a given name is valid (only contains characters by DB_OBJECT_NAME_CHARS)."""
    return set(name) <= DB_OBJECT_NAME_CHARS


def to_valid_key(s: str):
    """Converts a string key to a valid TinyOlap object name."""
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def dict_keys_to_int(dictionary: dict):
    """Converts all string address in a dictionary containing numbers into integer address.
    Note: This is not a general solutions and sufficient for a special purpose."""
    converted = {}
    for k, v in dictionary.items():
        new_k = k
        if type(k) is str:
            if str(k).isdigit():
                new_k = int(k)
        if type(v) is dict:
            new_v = dict_keys_to_int(v)
        # elif not isinstance(v, str) and isinstance(v, collections.abc.Sequence):
        else:
            new_v = v
        converted[new_k] = new_v
    return converted


def get_path(folder: str = "db", create_path: bool = True):
    """
    Returns the path to a folder relative to the current working directory.
    :param folder: Name of the folder.
    :param create_path: Flag if the folder should be created if it does not exist.
    :return: The path of the folder.
    """
    folder = os.path.normpath(folder)
    directory = os.path.join(os.getcwd(), folder)
    if create_path:
        if not os.path.exists(directory):
            os.makedirs(directory)
    return directory


def get_file_path(file_name: str, folder: str = "db", create_path: bool = True):
    """
    Returns the path to a file and folder relative to the current working directory.
    :param file_name: Name of the file (incl. extensions).
    :param folder: Name of the folder.
    :param create_path: Flag if the folder should be created if it does not exist.
    :return: The path of the file.
    """
    file_folder = get_path(folder, create_path)
    return os.path.join(file_folder, file_name)





