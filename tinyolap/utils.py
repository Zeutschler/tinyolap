import re
from collections.abc import Iterable
import collections
import string

MEMBER_NAME_CHARS = set(string.ascii_letters + string.digits + '.-_/#+-*:,;|{}()"')
DB_NAME_CHARS = set(string.ascii_lowercase + string.digits + '_')


def is_valid_member_name(name: str):
    """Checks if a given name is valid (only contains characters by MEMBER_NAME_CHARS)."""
    return set(name) <= MEMBER_NAME_CHARS


def is_valid_db_table_name(name: str):
    """Checks if a given name is valid (only contains characters by DB_NAME_CHARS)."""
    return (set(name) <= DB_NAME_CHARS) and (name.lower() == name)


def to_valid_key(s: str):
    s = str(s).strip().lower().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def dict_keys_to_int(dictionary: dict):
    """Converts all string keys in a dictionary containing numbers into integer keys.
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


class CaseInsensitiveDict(dict):
    class Key(str):
        def __init__(self, key):
            str.__init__(key)

        def __hash__(self):
            return hash(self.lower())

        def __eq__(self, other):
            return self.lower() == other.lower()

    def __init__(self, data=None):
        super(CaseInsensitiveDict, self).__init__()
        if data is None:
            data = {}
        for key, val in data.items():
            self[key] = val

    def __contains__(self, key):
        key = self.Key(key)
        return super(CaseInsensitiveDict, self).__contains__(key)

    def __setitem__(self, key, value):
        key = self.Key(key)
        super(CaseInsensitiveDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        key = self.Key(key)
        return super(CaseInsensitiveDict, self).__getitem__(key)
