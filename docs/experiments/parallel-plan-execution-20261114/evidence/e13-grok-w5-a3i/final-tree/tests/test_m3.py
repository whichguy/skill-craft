import copy
import unittest

from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_typical_example(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_touching_endpoints_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_and_contained(self):
        self.assertEqual(
            merge_intervals([[8, 10], [1, 10], [2, 3], [15, 18]]),
            [[1, 10], [15, 18]],
        )

    def test_single_and_point_intervals(self):
        self.assertEqual(merge_intervals([[5, 5]]), [[5, 5]])
        self.assertEqual(
            merge_intervals([[5, 5], [5, 5], [6, 6], [4, 5]]),
            [[4, 5], [6, 6]],
        )

    def test_negatives_and_chain(self):
        self.assertEqual(
            merge_intervals([[-4, -1], [-1, 2], [10, 12], [-10, -8]]),
            [[-10, -8], [-4, 2], [10, 12]],
        )

    def test_input_not_modified(self):
        original = [[2, 6], [1, 3], [8, 10]]
        snapshot = copy.deepcopy(original)
        result = merge_intervals(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(result, [[1, 6], [8, 10]])
        result[0][1] = 99
        self.assertEqual(original, snapshot)


if __name__ == "__main__":
    unittest.main()
