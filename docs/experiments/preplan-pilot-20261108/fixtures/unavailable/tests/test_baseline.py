import unittest
from src import client

class Baseline(unittest.TestCase):
    def test_unconfigured_transport_is_explicit(self):
        with self.assertRaises(ConnectionError): client.apply("sandbox", [])

if __name__ == "__main__": unittest.main()
