import unittest

from lines import clean_lines


class CleanLinesTests(unittest.TestCase):
    def test_strips_discards_blanks_and_preserves_duplicates(self):
        self.assertEqual(clean_lines(" a \n \n b\n a "), ["a", "b", "a"])

    def test_uses_splitlines_for_multiple_line_endings(self):
        self.assertEqual(clean_lines(" one\r\ntwo\r three\v\tfour "), ["one", "two", "three", "four"])

    def test_empty_and_whitespace_only_text_are_empty(self):
        self.assertEqual(clean_lines(""), [])
        self.assertEqual(clean_lines(" \n\t\r\n "), [])

    def test_non_strings_raise_type_error(self):
        for value in (None, 1, ["line"]):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    clean_lines(value)


if __name__ == "__main__":
    unittest.main()
