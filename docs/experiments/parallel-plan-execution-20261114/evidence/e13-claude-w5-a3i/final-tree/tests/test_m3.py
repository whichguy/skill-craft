import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_touching_endpoints_merge(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_input(self):
        self.assertEqual(merge_intervals([[8, 10], [1, 3], [2, 6]]),
                         [[1, 6], [8, 10]])

    def test_contained_interval(self):
        self.assertEqual(merge_intervals([[1, 10], [2, 3], [4, 5]]), [[1, 10]])

    def test_single_point_and_single_interval(self):
        self.assertEqual(merge_intervals([[5, 5]]), [[5, 5]])
        self.assertEqual(merge_intervals([[5, 5], [5, 5]]), [[5, 5]])

    def test_input_not_modified(self):
        data = [[5, 7], [1, 3], [2, 4]]
        merge_intervals(data)
        self.assertEqual(data, [[5, 7], [1, 3], [2, 4]])

    def test_result_does_not_alias_input(self):
        data = [[1, 2]]
        out = merge_intervals(data)
        out[0][1] = 99
        self.assertEqual(data, [[1, 2]])

    def test_negative_numbers(self):
        self.assertEqual(merge_intervals([[-5, -1], [-1, 2], [4, 6]]),
                         [[-5, 2], [4, 6]])


if __name__ == "__main__":
    unittest.main()
