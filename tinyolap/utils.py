# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
import string

MEMBER_NAME_CHARS = set(string.ascii_letters + string.digits + '.-_/#+-*:,;|{}()"')
DB_OBJECT_NAME_CHARS = set(string.ascii_letters + string.digits + '_')

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

