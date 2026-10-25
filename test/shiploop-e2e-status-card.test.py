#!/usr/bin/env python3
"""test/shiploop_e2e/status_card.py: the owner's status card renders a JSON model and nothing else, no model needed."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import status_card  # noqa: E402

MODEL = {
    "plan": [{"step": "R0 harness", "state": "done"}, {"step": "R1 K3", "state": "running", "note": "4 of 12"},
             {"step": "K2, K4", "state": "waiting", "note": "if arms separate"}, {"step": "Report", "state": "later"}],
    "progress": {"done": 2, "total": 6, "unit": "samples", "running": 1, "stamp": "18:36", "eta": "20:27"},
    "columns": ["T control", "C gate"],
    "rows": [{"name": "K1 chess engine", "sub": "band 3+ steps", "cells": [
        {"slots": [{"state": "below", "label": "2", "tip": "2 steps"}, {"state": "running", "label": "11m"},
                   {"state": "pending"}], "summary": "mean 0.00"},
        {"slots": [{"state": "pass", "label": "6"}, {"state": "error", "label": "err", "tip": "no step plan"},
                   {"state": "bogus"}], "summary": "mean 1.00", "verdict": "supports"}]}],
    "legend": {"pass": "scored 1", "note": "number = steps planned"}}


class StatusCard(unittest.TestCase):
    def test_each_slot_state_draws_its_own_mark_and_an_error_is_never_a_pass(self):
        found = status_card.render(MODEL)
        self.assertEqual(found.count('<i class="f"></i>'), 1)
        self.assertEqual(found.count('<i class="o"></i>'), 2)  # the below slot and its legend mark
        self.assertEqual(found.count('<i class="e"></i>'), 1)
        self.assertEqual(found.count('title="pending"'), 1)
        self.assertEqual(found.count('title="bogus"'), 1)  # an unknown state is drawn as pending
        self.assertIn('title="no step plan"', found)
        self.assertIn('<b class="ok">supports</b>', found)

    def test_the_plan_strip_gives_every_state_an_icon_and_an_unknown_one_reads_pending(self):
        found = status_card.render(MODEL)
        for icon in ("ti-check", "ti-loader-2", "ti-hourglass", "ti-circle-dashed"):
            self.assertIn(icon, found)
        self.assertIn('<span class="ch pending"><i class="ti ti-circle-dashed" aria-hidden="true"></i>Report', found)
        self.assertIn("R1 K3 · 4 of 12", found)

    def test_the_progress_line_and_legend_come_from_the_model(self):
        found = status_card.render(MODEL)
        self.assertIn("2 of 6 samples", found)
        self.assertIn("ETA about 20:27", found)
        self.assertIn("width:33%", found)
        self.assertIn("scored 1", found)
        self.assertIn("number = steps planned", found)
        self.assertIn('<h2 class="sr-only">Status at 18:36: 2 of 6 samples finished, 1 running.</h2>', found)

    def test_text_is_escaped_and_only_rows_are_required(self):
        found = status_card.render({"rows": [{"name": "<b>x</b>", "cells": [{"slots": [{"state": "pass", "tip": '"a"'}]}]}]})
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", found)
        self.assertIn('title="&quot;a&quot;"', found)
        self.assertNotIn('class="pl"', found)

    def test_the_cli_reads_a_model_file_or_stdin(self):
        script = ROOT / "test" / "shiploop_e2e" / "status_card.py"
        done = subprocess.run([sys.executable, "-B", str(script)], input=json.dumps(MODEL), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 of 6", done.stdout)


if __name__ == "__main__":
    unittest.main()
