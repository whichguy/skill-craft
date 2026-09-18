import unittest
from slug import slugify
from test_support import suite

@suite("focused", "smoke")
class SlugStarter(unittest.TestCase):
    def test_simple_words(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
