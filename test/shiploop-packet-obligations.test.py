#!/usr/bin/env python3
"""The packet obligation ledger holds (ShipLoop efficiency plan G-LEDGER).

test/shiploop_e2e/packet_obligations.json names what every packet must carry and where; this suite renders the packets with
this checkout's navigator (no model, no project) and fails when a row no longer holds:

* the ledger is well formed, covers the seven obligations the plan names, and every anchor token is in the source file it names;
* every row holds in every packet of its kinds that its ``when`` condition selects: the dry-run walk of all 23 stages and the
  Improve parent packets, and the offline step slice, on both delegation routes, in the printed text or the packet file as the
  row says;
* each row notices a lost token (the mutation record: take any anchor of any row out of every packet and the check names it), so a
  green run is not a vacuous one.

A unit that moves an obligation changes its row in the same commit; a pin becomes a ledger token only after the obligation is
confirmed present here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test"))
import obligations  # noqa: E402
import shiploop_packet_view as packet_view  # noqa: E402

# The obligations the plan says hold at every stage, as ledger row ids (the narrative and the home commit are conditional rows).
PLAN_SEVEN = {"callback": "callback", "result shape": "result-shape", "Checked by": "checked-by", "RULES": "rules",
              "narrative": "narrative", "pause and recovery frame": "pause-recovery", "KNOWLEDGE commit and close": "home-commit"}


class LedgerShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = obligations.load()

    def test_the_ledger_covers_the_seven_obligations_the_plan_names(self) -> None:
        ids = {row["id"] for row in self.ledger["obligations"]}
        for name, row_id in PLAN_SEVEN.items():
            with self.subTest(obligation=name):
                self.assertIn(row_id, ids)

    def test_a_row_names_its_surface_kinds_and_anchors(self) -> None:
        for row in self.ledger["obligations"]:
            with self.subTest(row=row["id"]):
                self.assertIn(row["surface"], obligations.SURFACES)
                self.assertTrue(set(row["kinds"]) <= set(obligations.KINDS) and row["kinds"])
                self.assertTrue(row["obligation"].strip())
                for anchor in row["anchors"]:
                    self.assertTrue(anchor["any"])

    def test_every_anchor_token_is_in_the_source_file_it_names(self) -> None:
        self.assertEqual(obligations.source_violations(self.ledger), [])

    def test_a_token_that_is_not_in_its_source_is_reported(self) -> None:
        bad = json.loads(json.dumps(self.ledger))
        bad["obligations"][0]["anchors"][0]["any"] = ["a sentence no ShipLoop source contains"]
        self.assertEqual([v["id"] for v in obligations.source_violations(bad)], [bad["obligations"][0]["id"]])

    def test_a_malformed_ledger_is_refused(self) -> None:
        cases = {
            "schema": lambda d: d.update(schema="shiploop-packet-obligations/v0"),
            "duplicate id": lambda d: d["obligations"].append(dict(d["obligations"][0])),
            "surface": lambda d: d["obligations"][0].update(surface="tail"),
            "no anchors": lambda d: d["obligations"][0].update(anchors=[]),
            "source": lambda d: d["obligations"][0]["anchors"][0].update(source="skills/shiploop/scripts/not_a_file.py"),
        }
        for name, break_it in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                broken = json.loads(json.dumps(self.ledger))
                break_it(broken)
                path = Path(temp) / "ledger.json"
                path.write_text(json.dumps(broken))
                with self.assertRaises((ValueError, KeyError)):
                    obligations.load(path)


class LedgerHoldsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = obligations.load()
        cls.packets = obligations.all_packets()

    def test_every_row_holds_in_every_packet_it_covers(self) -> None:
        self.assertEqual(obligations.check(self.ledger, self.packets), [])

    def test_every_outcome_a_packet_tells_the_model_to_report_is_one_its_stage_accepts(self) -> None:
        """The route behind the result-shape row (test-economy review, 2026-10-17, row 5; memory
        test-the-route-not-the-wording): a packet that tells the model to report an outcome its stage's gate does not take
        sends it to a refusal.  Derived from the stage table over every producer packet of the walk on both routes, so a
        reworded duty or a new stage is checked without a new pin; the refusals' own exits are submitted through the gate
        in shiploop-test-loop."""
        named = 0
        for packet in self.packets:
            if packet["kind"] != "producer":
                continue
            with self.subTest(packet=packet["where"]):
                self.assertEqual(packet_view.unaccepted_outcomes(packet["stage"], packet["file"]), [])
                named += len(packet_view.named_outcomes(packet["file"]))
        self.assertGreaterEqual(named, 40, "the extraction found the instructions it checks (62 on 2026-10-17)")

    def test_the_walk_covers_all_23_stages_and_the_improve_parent_on_both_routes(self) -> None:
        import shiploop_stage_spec as stage_spec
        for route in obligations.ROUTES:
            walked = [p for p in self.packets if p["where"].startswith(f"dry-run {route} ")]
            stages = {p["stage"] for p in walked if p["kind"] == "producer"}
            with self.subTest(route=route):
                self.assertEqual(stages, set(stage_spec.STAGES))
                self.assertEqual(len(stages), 23)  # 24 until verify retired (design T §9.1 2b-4c)
                self.assertTrue(any(p["kind"] == "improve" for p in walked))
            sliced = [p for p in self.packets if p["where"].startswith(f"slice node-fix-bug {route} ")]
            self.assertTrue({"step-plan", "implement", "test", "document", "carry-forward"} <= {p["stage"] for p in sliced})

    def test_no_row_is_vacuous(self) -> None:
        """Each row applies to packets, and the conditional rows to many (the narrative at most stages, the loop at the looped ones)."""
        applies = {}
        for row in self.ledger["obligations"]:
            condition = row.get("when", {}).get("file_has")
            applies[row["id"]] = sum(1 for p in self.packets if p["kind"] in row["kinds"] and (not condition or condition in p["file"]))
        self.assertTrue(all(count > 0 for count in applies.values()), applies)
        self.assertGreaterEqual(applies["narrative"], 40)
        # Decision 20 (owner 2026-10-18): only the test stage still prints the argument ("Exit when ALL of these
        # hold"), so "until-loop" now applies to far fewer packets; "until-loop-no-argument" covers every other
        # looped stage, which used to be "until-loop"'s whole count.
        self.assertGreaterEqual(applies["until-loop"], 2)
        self.assertGreaterEqual(applies["until-loop-no-argument"], 20)
        self.assertGreaterEqual(applies["callback"], 60)

    def test_the_printed_text_of_a_long_stage_is_a_head_and_the_ledger_still_holds_in_it(self) -> None:
        """A stage whose packet passes PRINT_LIMIT prints a head; the head rows are checked there, not in the file."""
        limit = obligations._imports()[0].PRINT_LIMIT
        heads = [p for p in self.packets if p["kind"] == "producer" and len(p["file"]) > limit]
        self.assertGreaterEqual(len(heads), 8)
        for packet in heads:
            with self.subTest(packet=packet["where"]):
                self.assertTrue(packet["printed"].rstrip().endswith("=== end ShipLoop print ==="))


class LedgerNoticesTests(unittest.TestCase):
    """The mutation record: a green ledger proves nothing unless it goes red when a token goes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = obligations.load()
        cls.packets = obligations.all_packets()

    def test_taking_any_anchor_out_of_every_packet_is_named_by_its_row(self) -> None:
        for row in self.ledger["obligations"]:
            for index, anchor in enumerate(row["anchors"]):
                with self.subTest(row=row["id"], anchor=index):
                    found = obligations.check(self.ledger, self.packets, drop=tuple(anchor["any"]))
                    self.assertIn(row["id"], {v["id"] for v in found})

    def test_taking_a_token_out_of_one_stage_names_that_stage(self) -> None:
        target = next(p["where"] for p in self.packets if p["where"].startswith("dry-run inline ") and p["stage"] == "test")
        mutated = [dict(p, printed=p["printed"].replace("Checked by:", "")) if p["where"] == target else p for p in self.packets]
        found = obligations.check(self.ledger, mutated)
        self.assertEqual({(v["id"], v["where"]) for v in found}, {("checked-by", target)})

    def test_the_rows_a_checkout_loses_are_listed_once_each_in_ledger_order(self) -> None:
        self.assertEqual(obligations.lost(self.ledger, self.packets), [])
        mutated = [dict(p, printed=p["printed"].replace("Checked by:", "").replace("Goal:", "")) for p in self.packets]
        self.assertEqual(obligations.lost(self.ledger, mutated), ["goal-done-when", "checked-by"])

    def test_the_arm_checks_record_keeps_what_the_battery_wrote_and_adds_the_lost_rows(self) -> None:
        script = ROOT / "test" / "shiploop_e2e" / "obligations.py"
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "arm-checks.json").write_text(json.dumps({"spec_flipped": ["S-6"]}))
            done = subprocess.run([sys.executable, "-B", str(script), "--arm-checks", temp], capture_output=True, text=True, cwd=ROOT)
            record = json.loads((Path(temp) / "arm-checks.json").read_text())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(record, {"spec_flipped": ["S-6"], "obligations_lost": []})

    def test_the_command_line_exits_zero_on_this_checkout_and_non_zero_for_a_ledger_it_breaks(self) -> None:
        script = ROOT / "test" / "shiploop_e2e" / "obligations.py"
        ok = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        with tempfile.TemporaryDirectory() as temp:
            broken = json.loads(json.dumps(self.ledger))
            broken["obligations"][0]["anchors"].append({"any": ["a line no packet prints"], "source": "skills/shiploop/scripts/shiploop_navigator.py"})
            path = Path(temp) / "ledger.json"
            path.write_text(json.dumps(broken))
            bad = subprocess.run([sys.executable, "-B", str(script), "--ledger", str(path)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("callback", bad.stdout)


if __name__ == "__main__":
    unittest.main()
