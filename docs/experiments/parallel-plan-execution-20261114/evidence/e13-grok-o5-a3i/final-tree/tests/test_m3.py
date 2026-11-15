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

    def test_touching_endpoints_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_and_contained(self):
        self.assertEqual(
            merge_intervals([[10, 12], [1, 5], [2, 3], [6, 8]]),
            [[1, 5], [6, 8], [10, 12]],
        )

    def test_input_not_modified(self):
        original = [[2, 6], [1, 3], [8, 10]]
        snapshot = [pair[:] for pair in original]
        merge_intervals(original)
        self.assertEqual(original, snapshot)

    def test_single_interval_and_identical(self):
        self.assertEqual(merge_intervals([[7, 9]]), [[7, 9]])
        self.assertEqual(merge_intervals([[0, 1], [0, 1]]), [[0, 1]])

    def test_chain_and_negatives(self):
        self.assertEqual(
            merge_intervals([[-4, -1], [-1, 2], [5, 5], [2, 3]]),
            [[-4, 3], [5, 5]],
        )


if __name__ == "__main__":
    unittest.main()
