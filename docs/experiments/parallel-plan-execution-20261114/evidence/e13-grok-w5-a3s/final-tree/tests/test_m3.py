import copy
import unittest

from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_example_overlap_and_disjoint(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_touching_merges_adjacent_does_not(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_does_not_modify_input(self):
        original = [[1, 3], [2, 6], [8, 10]]
        snapshot = copy.deepcopy(original)
        result = merge_intervals(original)
        self.assertEqual(original, snapshot)
        self.assertIsNot(result, original)
        original[0][0] = 99
        original.append([20, 21])
        self.assertEqual(result, [[1, 6], [8, 10]])

    def test_unsorted_and_contained(self):
        self.assertEqual(
            merge_intervals([[15, 18], [8, 10], [2, 6], [1, 3]]),
            [[1, 6], [8, 10], [15, 18]],
        )
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 5]]), [[1, 10]])

    def test_single_and_identical(self):
        self.assertEqual(merge_intervals([[7, 9]]), [[7, 9]])
        self.assertEqual(merge_intervals([[1, 2], [1, 2]]), [[1, 2]])

    def test_point_intervals_and_negatives(self):
        self.assertEqual(merge_intervals([[1, 1], [1, 2]]), [[1, 2]])
        self.assertEqual(merge_intervals([[1, 1], [2, 2]]), [[1, 1], [2, 2]])
        self.assertEqual(merge_intervals([[-5, -1], [-2, 3], [10, 12]]), [[-5, 3], [10, 12]])


if __name__ == "__main__":
    unittest.main()
