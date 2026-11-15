import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_typical_overlaps(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_touching_endpoints(self):
        self.assertEqual(merge_intervals([[4, 5], [1, 4]]), [[1, 5]])

    def test_adjacent_integer_intervals_remain_separate(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_duplicate_and_point_intervals(self):
        self.assertEqual(merge_intervals([[2, 2], [1, 8], [1, 8], [3, 5]]), [[1, 8]])

    def test_negative_and_transitive_overlap(self):
        self.assertEqual(merge_intervals([[0, 2], [-5, -2], [-2, 0]]), [[-5, 2]])

    def test_input_unchanged_and_output_independent(self):
        intervals = [[8, 9], [1, 3], [2, 5]]
        result = merge_intervals(intervals)
        self.assertEqual(intervals, [[8, 9], [1, 3], [2, 5]])
        result[0][0] = -10
        result[-1][1] = 100
        self.assertEqual(intervals, [[8, 9], [1, 3], [2, 5]])

    def test_single_point(self):
        self.assertEqual(merge_intervals([[7, 7]]), [[7, 7]])
