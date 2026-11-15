import unittest
from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_typical(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_touching_endpoints(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_not_merged(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_and_input_untouched(self):
        src = [[8, 10], [1, 3], [2, 6]]
        copy = [pair[:] for pair in src]
        self.assertEqual(merge_intervals(src), [[1, 6], [8, 10]])
        self.assertEqual(src, copy)

    def test_single(self):
        self.assertEqual(merge_intervals([[5, 5]]), [[5, 5]])


if __name__ == "__main__":
    unittest.main()
