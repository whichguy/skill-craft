"""Literal acceptance examples from SPEC.md; expected RED is intentional."""

import unittest

from slug import slugify
from test_support import suite


@suite("focused")
class SlugContract(unittest.TestCase):
    @suite("focused", "smoke")
    def test_ascii_letters_become_lowercase(self):
        # TC-01: all ASCII letters, mixed case, and the shortest valid title.
        for title, expected in (
            ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"),
            ("abcdefghijklmnopqrstuvwxyz", "abcdefghijklmnopqrstuvwxyz"),
            ("mIxEd", "mixed"),
            ("A", "a"),
        ):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    @suite("focused", "smoke")
    def test_digits_remain(self):
        # TC-02: leading zeroes are significant; digits are not separators.
        for title, expected in (
            ("0123456789", "0123456789"),
            ("0", "0"),
            ("A01B9", "a01b9"),
        ):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_separator_runs_collapse(self):
        # TC-03: each run collapses independently, including existing hyphens.
        for title, expected in (
            ("Alpha   Beta", "alpha-beta"),
            ("Alpha---Beta", "alpha-beta"),
            ("Alpha_beta.gamma/delta", "alpha-beta-gamma-delta"),
            ("A \t\r\n B", "a-b"),
            ("A--_!  B??C", "a-b-c"),
            ("A\x00\x1f\x7fB", "a-b"),
            ("already-slugged-123", "already-slugged-123"),
        ):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_boundary_separators_are_removed(self):
        # TC-04: trim separators at either boundary, including punctuation.
        for title, expected in (
            ("---Alpha", "alpha"),
            ("Alpha!!!", "alpha"),
            (" !_Alpha Beta_! ", "alpha-beta"),
            ("\t Alpha \n", "alpha"),
            ("--0--", "0"),
        ):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_non_ascii_characters_are_separators(self):
        # TC-05: non-ASCII letters/digits are separators, not transliterations.
        for title, expected in (
            ("caf\u00e9", "caf"),
            ("A\u00e9\u4e2dB", "a-b"),
            ("A\uff11\uff12\u0663B", "a-b"),
            ("A\U0001f642B", "a-b"),
            ("\u00e9A\u00e9", "a"),
            ("A\u212aB", "a-b"),
        ):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)

    def test_rejects_strings_without_ascii_alphanumerics(self):
        # TC-06: validation also applies after all separators are removed.
        for title in ("", " \t\r\n", "---", "_!?/.", "\x00", "\u00e9\u4e2d\U0001f642", "\uff11\uff12\u0663", "\u212a"):
            with self.subTest(title=title):
                with self.assertRaises(ValueError):
                    slugify(title)

    @suite("focused", "smoke")
    def test_rejects_non_strings(self):
        # TC-07: reject values rather than coercing them to titles.
        for title in (None, False, 0, 1.5, b"Hello", [], {}, object()):
            with self.subTest(type=type(title).__name__):
                with self.assertRaises(ValueError):
                    slugify(title)
