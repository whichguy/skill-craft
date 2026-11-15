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

    def test_adjacent_without_overlap(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_and_duplicate(self):
        self.assertEqual(merge_intervals([[2, 3], [1, 8], [1, 8], [4, 6]]), [[1, 8]])

    def test_negative_and_single_points(self):
        self.assertEqual(merge_intervals([[0, 0], [-3, -1], [-1, -1], [2, 2]]),
                         [[-3, -1], [0, 0], [2, 2]])

    def test_input_and_result_independence(self):
        original = [[8, 10], [1, 3], [2, 6]]
        result = merge_intervals(original)
        self.assertEqual(original, [[8, 10], [1, 3], [2, 6]])
        result[1][1] = 99
        self.assertEqual(original, [[8, 10], [1, 3], [2, 6]])


if __name__ == '__main__':
    unittest.main()
