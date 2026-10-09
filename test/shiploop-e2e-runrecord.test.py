#!/usr/bin/env python3
"""No-model checks for test/shiploop_e2e/runrecord.py: which hosts launched a run, read from its launch records.

A run folder holds ``invocation.json`` (the first launch) and one ``invocation-resume-<host>-<seconds>.json`` per later
launch.  A regrade starts no host but writes a resume record too (``versions.regraded``), so it is not a launch.  The
fixtures are the shapes of the saved 2026-10-08 round runs, reduced to the keys the reader looks at.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))


def write(out: Path, name: str, host: str, regraded: bool = False) -> None:
    record = {"case": "custom", "host": host, "versions": {"source": "checkout", **({"regraded": True} if regraded else {})}}
    (out / name).write_text(json.dumps(record))


class RunRecordTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name)

    def test_a_run_started_once_names_its_one_host(self):
        import runrecord
        write(self.out, "invocation.json", "grok")
        self.assertEqual(runrecord.hosts_used(self.out), ["grok"])

    def test_a_run_finished_by_another_host_names_both_in_launch_order(self):
        # r2-battleship-grok-none: Grok started it, Claude finished it, then Grok was resumed again.
        import runrecord
        write(self.out, "invocation.json", "grok")
        write(self.out, "invocation-resume-claude-1791508003.json", "claude")
        write(self.out, "invocation-resume-grok-1791509021.json", "grok")
        self.assertEqual(runrecord.hosts_used(self.out), ["grok", "claude"])
        self.assertTrue(runrecord.mixed_host(self.out))

    def test_a_regrade_started_no_host_so_it_adds_none(self):
        import runrecord
        write(self.out, "invocation.json", "grok")
        write(self.out, "invocation-resume-claude-1791600000.json", "claude", regraded=True)
        self.assertEqual(runrecord.hosts_used(self.out), ["grok"])
        self.assertFalse(runrecord.mixed_host(self.out))

    def test_a_folder_with_no_launch_record_names_no_host(self):
        import runrecord
        self.assertEqual(runrecord.hosts_used(self.out), [])
        self.assertFalse(runrecord.mixed_host(self.out))

    def test_an_unreadable_record_is_skipped_and_the_rest_still_count(self):
        import runrecord
        write(self.out, "invocation.json", "claude")
        (self.out / "invocation-resume-grok-1.json").write_text("{not json")
        self.assertEqual(runrecord.hosts_used(self.out), ["claude"])

    def test_launches_come_first_launch_first_whatever_the_file_system_order(self):
        import runrecord
        write(self.out, "invocation-resume-grok-1791509021.json", "grok")
        write(self.out, "invocation-resume-claude-1791508003.json", "claude")
        write(self.out, "invocation.json", "grok")
        names = [name for name, _record in runrecord.launches(self.out)]
        self.assertEqual(names, ["invocation.json", "invocation-resume-claude-1791508003.json",
                                 "invocation-resume-grok-1791509021.json"])


if __name__ == "__main__":
    unittest.main()
