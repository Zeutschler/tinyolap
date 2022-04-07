import json
import time
import unittest
from tinyolap.case_insensitive_dict import *


class Dict(unittest.TestCase):
    def setUp(self):
        self.Dict = CaseInsensitiveDict
        self.d1 = self.Dict()
        self.d2 = self.Dict()
        self.d1['a'] = 1
        self.d1['B'] = 2
        self.d2['A'] = 1
        self.d2['b'] = 2

    def test_contains(self):
        self.assertIn('B', self.d1)
        d = self.Dict({'a': 1, 'B': 2})
        self.assertIn('b', d)

    def test_init(self):
        d = self.Dict()
        self.assertFalse(d)
        d = self.Dict({'a': 1, 'B': 2})
        self.assertTrue(d)

    def test_items(self):
        self.assertDictEqual(self.d1, self.d2)
        self.assertEqual(
            [v for v in self.d1.items()],
            [v for v in self.d2.items()])

    # def test_json_dumps(self):
    #     s = json.dumps(self.d1)
    #     self.assertIn('a', s)
    #     self.assertIn('B', s)

    def test_keys(self):
        self.assertEqual(self.d1.keys(), self.d2.keys())

    def test_values(self):
        self.assertEqual(
            [v for v in self.d1.values()],
            [v for v in self.d2.values()])