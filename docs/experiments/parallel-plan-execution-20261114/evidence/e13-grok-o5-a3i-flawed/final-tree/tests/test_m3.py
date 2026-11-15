import unittest

from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_typical_partial_overlap(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_touching_endpoints_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_single_interval(self):
        self.assertEqual(merge_intervals([[7, 9]]), [[7, 9]])

    def test_unsorted_input(self):
        self.assertEqual(
            merge_intervals([[15, 18], [8, 10], [2, 6], [1, 3]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_nested_and_contained(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 5]]), [[1, 10]])

    def test_does_not_modify_input(self):
        original = [[2, 6], [1, 3], [8, 10]]
        snapshot = [iv[:] for iv in original]
        merge_intervals(original)
        self.assertEqual(original, snapshot)

    def test_point_intervals(self):
        self.assertEqual(merge_intervals([[5, 5], [5, 5], [6, 6]]), [[5, 5], [6, 6]])

    def test_negatives_and_zero(self):
        self.assertEqual(
            merge_intervals([[-5, -1], [-1, 0], [2, 3]]),
            [[-5, 0], [2, 3]],
        )

    def test_chain_of_overlaps(self):
        self.assertEqual(
            merge_intervals([[1, 2], [2, 3], [3, 4], [10, 12]]),
            [[1, 4], [10, 12]],
        )


if __name__ == "__main__":
    unittest.main()
