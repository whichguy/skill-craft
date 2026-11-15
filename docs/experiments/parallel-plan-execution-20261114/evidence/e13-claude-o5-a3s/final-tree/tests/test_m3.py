import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTest(unittest.TestCase):
    def test_typical(self):
        self.assertEqual(
            merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
            [[1, 6], [8, 10], [15, 18]],
        )

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_touching_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_not_merged(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_input(self):
        self.assertEqual(merge_intervals([[8, 10], [1, 3], [2, 6]]), [[1, 6], [8, 10]])

    def test_contained(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 5]]), [[1, 10]])

    def test_single_point(self):
        self.assertEqual(merge_intervals([[5, 5], [5, 5]]), [[5, 5]])

    def test_input_not_modified(self):
        data = [[5, 7], [1, 6]]
        merge_intervals(data)
        self.assertEqual(data, [[5, 7], [1, 6]])

    def test_result_independent_of_input(self):
        data = [[1, 2]]
        out = merge_intervals(data)
        out[0][1] = 99
        self.assertEqual(data, [[1, 2]])

    def test_negative_numbers(self):
        self.assertEqual(merge_intervals([[-5, -1], [-2, 3]]), [[-5, 3]])


if __name__ == "__main__":
    unittest.main()
