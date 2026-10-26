import unittest
def run_own(cls):
    names = [n for n in cls.__dict__ if n.startswith("test")]
    suite = unittest.TestSuite(cls(n) for n in names)
    unittest.TextTestRunner(verbosity=1).run(suite)
