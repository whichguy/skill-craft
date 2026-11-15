import unittest

from pkg.m3 import merge_intervals


class MergeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_touching(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_disjoint(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_duplicates(self):
        self.assertEqual(merge_intervals([[2, 3], [1, 9], [1, 9]]), [[1, 9]])

    def test_negative_and_point(self):
        self.assertEqual(merge_intervals([[0, 0], [-5, -2], [-2, 0]]), [[-5, 0]])

    def test_input_unchanged_and_output_independent(self):
        source = [[5, 6], [1, 3], [2, 4]]
        result = merge_intervals(source)
        self.assertEqual(source, [[5, 6], [1, 3], [2, 4]])
        self.assertEqual(result, [[1, 4], [5, 6]])
        result[1][1] = 99
        self.assertEqual(source, [[5, 6], [1, 3], [2, 4]])
