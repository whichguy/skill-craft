import unittest

class Control(unittest.TestCase):
    def helper(self):
        self.assertEqual(1, 2)

    def test_behavior(self):
        with self.subTest(value=1):
            raise RuntimeError("fixture failure")
