import unittest


class RuntimeFailure(unittest.TestCase):
    def test_not_an_assertion(self):
        raise RuntimeError("synthetic test-method error")
