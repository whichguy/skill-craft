import unittest


class BrokenFixture(unittest.TestCase):
    def setUp(self):
        self.fail("synthetic test-fixture assertion")

    def test_behavior(self):
        self.assertTrue(True)
