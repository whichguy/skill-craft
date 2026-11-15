import unittest

from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_example_overlap_and_gaps(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_touching_endpoints_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_and_contained(self):
        self.assertEqual(
            merge_intervals([[10, 12], [1, 4], [2, 3], [5, 8]]),
            [[1, 4], [5, 8], [10, 12]],
        )

    def test_input_not_modified(self):
        original = [[2, 6], [1, 3], [8, 10]]
        snapshot = [pair[:] for pair in original]
        merge_intervals(original)
        self.assertEqual(original, snapshot)

    def test_single_and_point_intervals(self):
        self.assertEqual(merge_intervals([[7, 7]]), [[7, 7]])
        self.assertEqual(merge_intervals([[5, 5], [5, 5], [5, 6]]), [[5, 6]])

    def test_chain_and_negatives(self):
        self.assertEqual(
            merge_intervals([[-4, -1], [-1, 2], [2, 3], [10, 10]]),
            [[-4, 3], [10, 10]],
        )


if __name__ == "__main__":
    unittest.main()
