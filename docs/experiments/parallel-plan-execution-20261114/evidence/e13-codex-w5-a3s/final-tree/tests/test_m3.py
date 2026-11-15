import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_shared_endpoint(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_duplicates_and_points(self):
        self.assertEqual(merge_intervals([[2, 2], [1, 5], [1, 5], [3, 4]]), [[1, 5]])

    def test_negative_chain(self):
        self.assertEqual(merge_intervals([[0, 2], [-4, -1], [-1, 0]]), [[-4, 2]])

    def test_new_list_without_input_mutation(self):
        intervals = [[8, 10], [1, 3], [2, 6]]
        result = merge_intervals(intervals)
        self.assertEqual(intervals, [[8, 10], [1, 3], [2, 6]])
        result[1][0] = 99
        self.assertEqual(intervals, [[8, 10], [1, 3], [2, 6]])

    def test_single_point(self):
        self.assertEqual(merge_intervals([[7, 7]]), [[7, 7]])


if __name__ == '__main__':
    unittest.main()
