# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import annotations
from itertools import chain

_RaiseKeyError = object() # singleton for no-default behavior

class CaseInsensitiveDict(dict):
    # dicts take a mapping or iterable as their optional first argument
    __slots__ = ()  # no __dict__ - that would be redundant

    @staticmethod  # because this doesn't make sense as a global function.
    def _process_args(mapping=(), **kwargs):
        if hasattr(mapping, 'items'):
            mapping = getattr(mapping, 'items')()
        return ((k.lower(), v) for k, v in chain(mapping, getattr(kwargs, 'items')()))

    def __init__(self, mapping=(), **kwargs):
        super(CaseInsensitiveDict, self).__init__(self._process_args(mapping, **kwargs))

    def __getitem__(self, k):
        return super(CaseInsensitiveDict, self).__getitem__(k.lower())
    def lookup(self, k):
        return super(CaseInsensitiveDict, self).get(k.lower())
    def lookuptry(self, k):
        try:
            return super(CaseInsensitiveDict, self).__getitem__(k.lower())
        except:
            return None

    def __setitem__(self, k, v):
        return super(CaseInsensitiveDict, self).__setitem__(k.lower(), v)

    def __delitem__(self, k):
        return super(CaseInsensitiveDict, self).__delitem__(k.lower())

    def get(self, k, default=None):
        return super(CaseInsensitiveDict, self).get(k.lower(), default)

    def setdefault(self, k, default=None):
        return super(CaseInsensitiveDict, self).setdefault(k.lower(), default)

    def pop(self, k, v=_RaiseKeyError):
        if v is _RaiseKeyError:
            return super(CaseInsensitiveDict, self).pop(k.lower())
        return super(CaseInsensitiveDict, self).pop(k.lower(), v)

    def update(self, mapping=(), **kwargs):
        super(CaseInsensitiveDict, self).update(self._process_args(mapping, **kwargs))

    def __contains__(self, k):
        return super(CaseInsensitiveDict, self).__contains__(k.lower())

    def copy(self):  # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)

    def populate(self, dictionary: dict) -> CaseInsensitiveDict:
        for k, v in dictionary.items():
            self[k] = v
        return self

    @classmethod
    def fromkeys(cls, keys, v=None):
        return super(CaseInsensitiveDict, cls).fromkeys((k.lower() for k in keys), v)

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, super(CaseInsensitiveDict, self).__repr__())