# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

class CaseInsensitiveDict(dict):
    """
    A simple case insensitive dictionary.
    """

    class Key(str):
        def __init__(self, key):
            str.__init__(key)

        def __hash__(self):
            return hash(self.lower())

        def __eq__(self, other):
            return self.lower() == other.lower()

    def __init__(self, data=None):
        super(CaseInsensitiveDict, self).__init__()
        if not data:
            data = {}
        else:
            if isinstance(data, dict):
                for key, val in data.items():
                    self[key] = val
            else:
                for key, val in data:
                    self[key] = val

    def __contains__(self, key):
        key = self.Key(key)
        result = super(CaseInsensitiveDict, self).__contains__(key)
        return result

    def __setitem__(self, key, value):
        key = self.Key(key)
        super(CaseInsensitiveDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        key = self.Key(key)
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def __delitem__(self, key):
        key = self.Key(key)
        return super(CaseInsensitiveDict, self).__delitem__(key)
