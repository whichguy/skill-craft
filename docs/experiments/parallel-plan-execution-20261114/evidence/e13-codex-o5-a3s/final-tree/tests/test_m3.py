import unittest

from pkg.m3 import merge_intervals


class MergeIntervalsTests(unittest.TestCase):
    def test_typical(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]),
                         [[1, 6], [8, 10], [15, 18]])

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_shared_endpoint(self):
        self.assertEqual(merge_intervals([[4, 5], [1, 4]]), [[1, 5]])

    def test_adjacent_integer_intervals_stay_separate(self):
        self.assertEqual(merge_intervals([[3, 4], [1, 2]]), [[1, 2], [3, 4]])

    def test_nested_duplicates_and_points(self):
        self.assertEqual(merge_intervals([[2, 2], [0, 5], [0, 5], [1, 3]]), [[0, 5]])

    def test_negative_chain(self):
        self.assertEqual(merge_intervals([[-2, 1], [-8, -5], [-5, -2]]), [[-8, 1]])

    def test_input_and_output_are_independent(self):
        original = [[8, 10], [1, 3], [2, 6]]
        result = merge_intervals(original)
        self.assertEqual(original, [[8, 10], [1, 3], [2, 6]])
        result[-1][0] = 99
        self.assertEqual(original, [[8, 10], [1, 3], [2, 6]])


if __name__ == '__main__':
    unittest.main()
