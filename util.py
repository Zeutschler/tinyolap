import re
from collections.abc import Iterable
import collections

def to_valid_key(s: str):
    s = str(s).strip().lower().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def dict_keys_to_int(dictionary: dict):
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

