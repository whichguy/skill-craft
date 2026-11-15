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

    def test_single_interval(self):
        self.assertEqual(merge_intervals([[7, 9]]), [[7, 9]])

    def test_nested_interval(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 6]]), [[1, 10]])

    def test_unsorted_input(self):
        self.assertEqual(
            merge_intervals([[15, 18], [8, 10], [2, 6], [1, 3]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_input_not_modified(self):
        original = [[5, 7], [1, 3], [2, 4]]
        snapshot = [iv[:] for iv in original]
        merge_intervals(original)
        self.assertEqual(original, snapshot)

    def test_negative_and_zero(self):
        self.assertEqual(
            merge_intervals([[-5, -1], [-1, 0], [2, 3]]),
            [[-5, 0], [2, 3]],
        )

    def test_all_merge_into_one(self):
        self.assertEqual(merge_intervals([[1, 2], [2, 3], [3, 4]]), [[1, 4]])

    def test_identical_intervals(self):
        self.assertEqual(merge_intervals([[3, 5], [3, 5], [3, 5]]), [[3, 5]])

    def test_point_intervals(self):
        self.assertEqual(
            merge_intervals([[1, 1], [3, 3], [1, 2]]),
            [[1, 2], [3, 3]],
        )


if __name__ == "__main__":
    unittest.main()
