"""Independent acceptance examples from SPEC.md; failures must remain visible."""

import string
import unittest

from slug import slugify
from test_support import suite


class SlugContract(unittest.TestCase):
    def test_tc02_ascii_letters_and_digits(self):
        self.assertEqual(
            slugify("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"),
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz0123456789",
        )

    def test_tc03_single_alphanumeric(self):
        for title, expected in (("A", "a"), ("z", "z"), ("0", "0"), ("9", "9")):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    @suite("focused", "smoke")
    def test_tc04_maximal_separator_runs(self):
        cases = (
            ("Hello   World", "hello-world"),
            ("Hello,,,World", "hello-world"),
            ("Hello---World", "hello-world"),
            ("Hello \t/_!\nWorld", "hello-world"),
            ("A..B___C / D", "a-b-c-d"),
            ("Release  2.0", "release-2-0"),
        )
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_tc05_each_ascii_separator(self):
        for separator in string.punctuation + string.whitespace + "\x00\x1f\x7f":
            with self.subTest(separator=repr(separator)):
                self.assertEqual(slugify("A" + separator + "B"), "a-b")

    @suite("focused")
    def test_tc06_remove_boundary_separators(self):
        cases = (
            ("---Hello", "hello"),
            ("Hello!!!", "hello"),
            (" /_Hello, World!!\t", "hello-world"),
            ("--7--", "7"),
            ("  Hello World  ", "hello-world"),
        )
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_tc07_non_ascii_characters_are_separators(self):
        cases = (
            ("caf\u00e9 noir", "caf-noir"),
            ("A\u4f60\u597d\U0001f680B", "a-b"),
            ("A\u0301B", "a-b"),
            ("A\u00a0\u2003B", "a-b"),
            ("a\u0661\uff12b", "a-b"),
            ("a\u212ab", "a-b"),
            ("x\u0130y", "x-y"),
            ("\u00e9Hello\u4f60", "hello"),
        )
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    @suite("focused", "smoke")
    def test_tc08_empty_or_whitespace_raises(self):
        for title in ("", " ", "\t\n\r\v\f", "\u00a0\u2003"):
            with self.subTest(title=title):
                with self.assertRaises(ValueError):
                    slugify(title)

    def test_tc09_no_ascii_alphanumeric_raises(self):
        for title in ("!!!", "---", " _/ ", "\x00", "\u00e9\u4f60\U0001f680", "\u0661\uff12", "\u212a\u0130"):
            with self.subTest(title=title):
                with self.assertRaises(ValueError):
                    slugify(title)

    @suite("smoke")
    def test_tc10_non_string_raises(self):
        for title in (None, 0, 42, 3.5, True, b"Hello", bytearray(b"Hello"), [], {}, ("Hello",), object()):
            with self.subTest(title=title):
                with self.assertRaises(ValueError):
                    slugify(title)
