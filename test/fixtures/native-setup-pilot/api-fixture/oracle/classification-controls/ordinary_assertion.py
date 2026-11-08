import unittest

class Control(unittest.TestCase):
    def helper(self):
        self.assertEqual(1, 2)

    def test_behavior(self):
        self.assertEqual(1, 2)
