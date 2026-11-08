import unittest

class Control(unittest.TestCase):
    def helper(self):
        self.assertEqual(1, 2)

    @unittest.expectedFailure
    def test_behavior(self):
        self.assertEqual(1, 2)
