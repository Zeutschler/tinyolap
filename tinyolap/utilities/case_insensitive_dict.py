from __future__ import annotations
from itertools import chain

_RaiseKeyError = object()  # singleton for no-default behavior


class CaseInsensitiveDict_explicit:

    @staticmethod  # because this doesn't make sense as a global function.
    def _process_args(mapping=(), **kwargs):
        if hasattr(mapping, 'items'):
            mapping = getattr(mapping, 'items')()
        return ((k.lower(), v) for k, v in chain(mapping, getattr(kwargs, 'items')()))

    def __init__(self, mapping=(), **kwargs):
        self.dict = dict()

    def __getitem__(self, k):
        return self.dict[str(k).lower()]

    def lookup(self, k):
        return self.dict[str(k).lower()]

    def try_lookup(self, k):
        try:
            return self.dict[str(k).lower()]
        except:
            return None

    def __setitem__(self, k, v):
        self.dict[str(k).lower()] = v

    def __delitem__(self, k):
        del(self.dict[str(k).lower()])

    def get(self, k, default=None):
        return self.dict.get(str(k).lower(), default)

    def setdefault(self, k, default=None):
        return self.dict.setdefault(str(k).lower(), default)

    def pop(self, k, v=_RaiseKeyError):
        if v is _RaiseKeyError:
            return self.dict.pop(str(k).lower())
        return self.dict.pop(str(k).lower(), v)

    def update(self, mapping=(), **kwargs):
        self.dict.update(self._process_args(mapping, **kwargs))

    def __contains__(self, k):
        return self.dict.__contains__(str(k).lower())

    def copy(self):  # don't delegate w/ super - dict.copy() -> dict :(
        return self.dict.copy()

    def populate(self, dictionary: dict) -> CaseInsensitiveDict:
        for k, v in dictionary.items():
            self[k] = v
        return self

    @classmethod
    def fromkeys(cls, keys, v=None):
        return CaseInsensitiveDict.fromkeys((str(k).lower() for k in keys), v)

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, self.dict.__repr__())



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
        return super(CaseInsensitiveDict, self).__getitem__(str(k).lower())

    def lookup(self, k):
        return super(CaseInsensitiveDict, self).get(k.lower())

    def try_lookup(self, k):
        try:
            return super(CaseInsensitiveDict, self).__getitem__(str(k).lower())
        except:
            return None

    def __setitem__(self, k, v):
        return super(CaseInsensitiveDict, self).__setitem__(str(k).lower(), v)

    def __delitem__(self, k):
        return super(CaseInsensitiveDict, self).__delitem__(str(k).lower())

    def get(self, k, default=None):
        return super(CaseInsensitiveDict, self).get(str(k).lower(), default)

    def setdefault(self, k, default=None):
        return super(CaseInsensitiveDict, self).setdefault(str(k).lower(), default)

    def pop(self, k, v=_RaiseKeyError):
        if v is _RaiseKeyError:
            return super(CaseInsensitiveDict, self).pop(str(k).lower())
        return super(CaseInsensitiveDict, self).pop(str(k).lower(), v)

    def update(self, mapping=(), **kwargs):
        super(CaseInsensitiveDict, self).update(self._process_args(mapping, **kwargs))

    def __contains__(self, k):
        return super(CaseInsensitiveDict, self).__contains__(str(k).lower())

    def copy(self):  # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)

    def populate(self, dictionary: dict) -> CaseInsensitiveDict:
        for k, v in dictionary.items():
            self[k] = v
        return self

    @classmethod
    def fromkeys(cls, keys, v=None):
        return super(CaseInsensitiveDict, cls).fromkeys((str(k).lower() for k in keys), v)

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, super(CaseInsensitiveDict, self).__repr__())
