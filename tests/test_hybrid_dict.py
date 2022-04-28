from unittest import TestCase

from tinyolap.utilities.hybrid_dict import HybridDict


class Test(TestCase):
    """Tests all available samples, except the web_demo (for errors / fatal failure only)."""

    def setUp(self) -> None:
        pass

    def test_hybrid_dict_int(self):
        # Our 'generic case in-sensitive, strongly typed, hybrid dictionary/list',
        # extensively used for object collections

        hd = HybridDict[int]([1, 2, 3])
        self.assertEqual(hd[0], 1)
        self.assertEqual(hd["1"], 1)
        self.assertEqual(hd["1"] + hd["2"], 3)
        self.assertEqual(len(hd), 3)
        self.assertEqual(list(reversed(hd)), [3, 2, 1])
        self.assertEqual(hd.count(1), 1)

        s = 0
        for v in hd:
            s += v
        self.assertEqual(s, sum(hd))

    def test_hybrid_dict_str(self):
        hd = HybridDict[str](["A", "b", "C"])  # please note the lower case 'b'
        self.assertEqual(hd[0], "A")
        self.assertEqual(hd["A"], "A")
        self.assertEqual(hd["c"], "C")
        self.assertEqual(hd["B"], "b")
        self.assertEqual(hd["A"] + hd["B"], "Ab")
        self.assertEqual(len(hd), 3)
        self.assertEqual(list(reversed(hd)), ["C", "b", "A"])
        self.assertEqual(hd.count("b"), 1)

        s = ""
        for v in hd:
            s += v
        self.assertEqual(s, "AbC")

    def test_hybrid_dict_set_operations(self):
        list_a = [1, 2, 3]
        list_b = [3, 4, 5]
        a = HybridDict[int](list_a)
        b = HybridDict[int](list_b)
        ab = a + b

        self.assertEqual(list(ab), [1, 2, 3, 3, 4, 5])
        self.assertEqual(list(ab.distinct()), [1, 2, 3, 4, 5])
        self.assertEqual(list(a.append(7)), [1, 2, 3, 7])
        self.assertEqual(list(a.intersect(b)), [3])
        self.assertEqual(list(a.union(b)), [1, 2, 3, 4, 5, 7])
        self.assertEqual(list(ab.filter("2")), [2])

    def test_hybrid_dict_sources(self):
        source = object()
        different_source = object()

        list_a = [1, 2, 3]
        list_b = [3, 4, 5]
        a = HybridDict[int](list_a, source)
        b = HybridDict[int](list_b, source)
        c = HybridDict[int](list_b, different_source)

        ab = a + b

        self.assertEqual(list(ab.filter("2")), [2])

        with self.assertRaises(BaseException):
            ac = a + c
        with self.assertRaises(BaseException):
            ca = c + a
