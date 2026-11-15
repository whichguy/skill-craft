import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_shared_endpoint(self):
        self.assertEqual(merge_intervals([[4, 5], [1, 4]]), [[1, 5]])

    def test_adjacent_integer_points_stay_separate(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_and_duplicate(self):
        self.assertEqual(merge_intervals([[2, 3], [1, 10], [1, 10]]), [[1, 10]])

    def test_negative_and_zero_length(self):
        self.assertEqual(merge_intervals([[0, 0], [-3, -1], [-1, 0], [5, 5]]),
                         [[-3, 0], [5, 5]])

    def test_input_and_result_independent(self):
        intervals = [[8, 10], [2, 6], [1, 3]]
        original = [pair[:] for pair in intervals]
        result = merge_intervals(intervals)
        self.assertEqual(intervals, original)
        result[0][0] = 99
        self.assertEqual(intervals, original)


if __name__ == '__main__':
    unittest.main()
