#!/usr/bin/env python3
"""Verify the loopback fixture serves the distinct static artifacts."""

from __future__ import annotations

from pathlib import Path
import unittest
from urllib.request import urlopen

from serve_fixture import LoopbackFixture


EXPECTED = {
    "working": ("candidate-2", "data-ui-mode=\"working\"", "Move piece"),
    "broken": ("candidate-2", "data-ui-mode=\"broken\"", "Move piece"),
    "stale": ("candidate-1", "data-ui-mode=\"working\"", "Move piece"),
    "login": ("candidate-2", "data-ui-mode=\"login\"", "Login required"),
}


class LoopbackFixtureTests(unittest.TestCase):
    def test_each_case_serves_its_distinct_artifact_on_loopback(self) -> None:
        for case, expected in EXPECTED.items():
            with self.subTest(case=case), LoopbackFixture(case) as fixture:
                with urlopen(fixture.url, timeout=2) as response:
                    body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                for marker in expected:
                    self.assertIn(marker, body)

    def test_local_candidate_is_newer_than_stale_served_artifact(self) -> None:
        local = (
            Path(__file__).resolve().parent
            / "local-candidate"
            / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn('data-candidate="candidate-2"', local)
        with LoopbackFixture("stale") as fixture:
            with urlopen(fixture.url, timeout=2) as response:
                stale = response.read().decode("utf-8")
        self.assertIn('data-candidate="candidate-1"', stale)


if __name__ == "__main__":
    unittest.main(verbosity=2)
