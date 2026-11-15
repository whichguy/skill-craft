import unittest

from pkg.m3 import merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_typical_overlap(self):
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

    def test_single_interval(self):
        self.assertEqual(merge_intervals([[7, 9]]), [[7, 9]])

    def test_does_not_mutate_input(self):
        src = [[2, 3], [1, 5]]
        out = merge_intervals(src)
        self.assertEqual(out, [[1, 5]])
        self.assertEqual(src, [[2, 3], [1, 5]])

    def test_contained_interval(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 5]]), [[1, 10]])


if __name__ == "__main__":
    unittest.main()
