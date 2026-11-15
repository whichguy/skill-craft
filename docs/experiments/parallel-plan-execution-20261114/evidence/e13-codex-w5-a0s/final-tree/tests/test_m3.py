import unittest
from pkg.m3 import merge_intervals


class MergeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]), [[1, 6], [8, 10], [15, 18]])

    def test_touching(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_disjoint(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_and_duplicates(self):
        self.assertEqual(merge_intervals([[2, 3], [1, 8], [1, 8], [4, 5]]), [[1, 8]])

    def test_negative_and_points(self):
        self.assertEqual(merge_intervals([[0, 0], [-3, -1], [-1, 0], [2, 2]]), [[-3, 0], [2, 2]])

    def test_no_mutation_or_aliasing(self):
        original = [[5, 7], [1, 3], [2, 4]]
        result = merge_intervals(original)
        self.assertEqual(original, [[5, 7], [1, 3], [2, 4]])
        self.assertEqual(result, [[1, 4], [5, 7]])
        result[1][1] = 99
        self.assertEqual(original, [[5, 7], [1, 3], [2, 4]])

    def test_single(self):
        self.assertEqual(merge_intervals([[4, 4]]), [[4, 4]])
