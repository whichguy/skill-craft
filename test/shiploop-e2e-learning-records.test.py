"""No-model checks of the closed loop's parts (docs/shiploop-e2e-closed-loop-plan-2026-10-30.md, stage 2): learning
records, predictions, the A/A spread and the purpose check."""
from __future__ import annotations

import inspect
import itertools
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import learning_records as lr
import prediction
import purpose_check
import review
import spread

FLOORS = ["accuracy", "fidelity"]


def card(case="hello", tokens=1_000_000, ok=True, refusals=2, comparable=True):
    return {"case": case, "floors": {"accuracy": "pass" if ok else "fail", "fidelity": "pass"},
            "validity": {"correctness": {"valid": True}, "attribution": {"valid": comparable}, "timing": {"valid": False}},
            "efficiency": {"tokens": tokens, "turns": 200, "refusals": refusals, "totals_lower_bound": False}}


class LedgerCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.ledger = self.temp / "learning-records.jsonl"

    def open_record(self, title="a lesson", **fields):
        record = lr.new_id()
        lr.append("opened", record, self.ledger, title=title, anchor={"clause_id": "S-14", "relationship": "supports"},
                  materiality=fields.pop("materiality", "material"), confidence=fields.pop("confidence", "medium"),
                  target=fields.pop("target", "shiploop"), files=["skills/shiploop/scripts/x.py"],
                  proposal="say so in the packet", **fields)
        return record


    def assert_owner_decisions_respected(self, path):
        """Catch conflicting branch histories without changing how old events fold."""
        events = sorted(lr.rows(path), key=lambda event: (event["at"], event["event_id"]))
        latest_decision = {row["record"]: index for index, row in enumerate(events)
                           if row["event"] in ("owner", "reopened")}
        held = {}
        for index, row in enumerate(events):
            record, event = row["record"], row["event"]
            if index < latest_decision.get(record, -1):
                continue
            if event == "owner":
                if row.get("outcome") == "accept":
                    held.pop(record, None)
                else:
                    held[record] = row["event_id"]
            elif event == "reopened":
                held.pop(record, None)
            elif event in ("admitted", "predicted"):
                self.assertNotIn(record, held, f"{record}: {event} after owner hold; record an explicit resolution")


class LearningRecordsTest(LedgerCase):
    def test_events_fold_into_one_status_per_record(self):
        record = self.open_record()
        self.assertEqual(lr.current(self.ledger)[record]["status"], "open")
        lr.append("admitted", record, self.ledger)
        lr.append("predicted", record, self.ledger, prediction={"record": record}, candidate="abc")
        self.assertEqual(lr.current(self.ledger)[record]["status"], "in_candidate")
        lr.append("decided", record, self.ledger, decision="DROP")
        lr.append("verdict", record, self.ledger, verdict="refuted", outcome="refuted", reason="tokens rose",
                  reopen_when="new evidence")
        state = lr.current(self.ledger)[record]
        self.assertEqual((state["status"], state["decision"], state["verdict"]), ("refuted", "DROP", "refuted"))
        lr.append("reopened", record, self.ledger, reason="it recurred")
        self.assertEqual(lr.current(self.ledger)[record]["status"], "admitted")

    def test_a_union_merge_of_two_branches_folds_whatever_the_line_order(self):
        record = self.open_record()
        lr.append("admitted", record, self.ledger)
        lr.append("deferred", record, self.ledger, reason="n = 1", reopen_when="it recurs")
        lines = self.ledger.read_text().splitlines()
        self.ledger.write_text("\n".join(reversed(lines)) + "\n")
        self.assertEqual(lr.current(self.ledger)[record]["status"], "deferred")

    def test_a_broken_line_is_an_error_naming_it(self):
        self.open_record()
        with self.ledger.open("a") as handle:
            handle.write('{"event": "opened"\n')
        with self.assertRaisesRegex(ValueError, "line 2"):
            lr.rows(self.ledger)

    def test_rows_refuse_unknown_events_and_reserved_fields(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            lr.append("promoted", lr.new_id(), self.ledger)
        with self.assertRaisesRegex(ValueError, "malformed"):
            lr.append("opened", "LR-1", self.ledger)
        with self.assertRaisesRegex(ValueError, "may not set"):
            lr.append("opened", lr.new_id(), self.ledger, at="2020-01-01")

    def test_the_reviewer_view_shows_live_then_settled_and_is_capped(self):
        live = self.open_record("live lesson")
        settled = self.open_record("settled lesson")
        lr.append("deferred", settled, self.ledger, reason="n = 1", reopen_when="it recurs")
        view = lr.reviewer_view(self.ledger)
        self.assertLess(view.index(live), view.index(settled))
        self.assertIn("n = 1", view)
        for n in range(40):
            self.open_record(f"lesson {n} " + "x" * 120)
        capped = lr.reviewer_view(self.ledger, max_chars=1500)
        self.assertLessEqual(len(capped), 1500 + 80)
        self.assertRegex(capped, r"\d+ more lines not shown")

    def test_the_improver_view_carries_no_evidence(self):
        record = self.open_record(source={"run": "/runs/x", "exposure": "development"})
        lr.append("opened", record, self.ledger, title="a lesson", source={"run": "/runs/y", "evidence": "held-out detail"})
        view = lr.improver_view(record, self.ledger)
        self.assertEqual(set(view), {"record", "title", "anchor", "files", "proposal", "next_experiment"})
        self.assertNotIn("held-out", json.dumps(view))
        self.assertEqual(lr.current(self.ledger)[record]["seen"], 2)

    def test_select_takes_an_admitted_material_shiploop_record_never_a_confirmation_one(self):
        low = self.open_record("low", confidence="low")
        high = self.open_record("high", confidence="high")
        exposed = self.open_record("exposed", confidence="high", source={"exposure": "confirmation"})
        harness = self.open_record("harness", confidence="high", target="harness")
        minor = self.open_record("minor", confidence="high", materiality="minor")
        self.assertIsNone(lr.select(self.ledger))
        for record in (low, high, exposed, harness, minor):
            lr.append("admitted", record, self.ledger)
        self.assertEqual(lr.select(self.ledger), high)
        lr.append("predicted", high, self.ledger)
        self.assertEqual(lr.select(self.ledger), low)

    def test_select_for_a_cycle_takes_only_a_record_that_cycle_can_measure_and_has_not_seen(self):
        """A cycle measures its exposing case and keeps its generality case unseen: a record found on a hosted case it
        will not run, or with evidence from its generality case, is not its record."""
        hosted = self.open_record("hosted", confidence="high",
                                  source={"case": "gym-membership-salesforce", "exposure": "development"})
        seeded = self.open_record("seeded", confidence="low", source={"learnings": "Wave A", "commit": "008feae"})
        ours = self.open_record("ours", confidence="medium", source={"case": "user-listing", "exposure": "development"})
        both = self.open_record("both", confidence="high", source={"case": "user-listing", "exposure": "development"})
        lr.append("opened", both, self.ledger, source={"case": "csv-report", "exposure": "development"})
        for record in (hosted, seeded, ours, both):
            lr.append("admitted", record, self.ledger)
        self.assertEqual(lr.select(self.ledger), hosted, "without a cycle's cases the rule is as it was: the oldest of the highest")
        self.assertEqual(lr.select(self.ledger, "user-listing", "csv-report"), ours,
                         "not the hosted record, and not the one with evidence from the unseen generality case")
        self.assertEqual(lr.select(self.ledger, "user-listing", None), both)
        lr.append("predicted", ours, self.ledger)
        lr.append("predicted", both, self.ledger)
        self.assertEqual(lr.select(self.ledger, "user-listing", "csv-report"), seeded,
                         "a seeded record names no case, so any cycle may take it")
        lr.append("predicted", seeded, self.ledger)
        self.assertIsNone(lr.select(self.ledger, "user-listing", "csv-report"))
        self.assertEqual(lr.select(self.ledger, "gym-membership-salesforce", None), hosted)

    def test_select_offers_a_seeded_record_whose_materiality_reads_high_and_never_a_minor_one(self):
        """The seeded LR-20261030-5dce01 says materiality high where reviewers and the judge say material or minor. It was
        admitted by the owner and verified, and a re-find reopens it; select compared the field to the exact string material,
        so a re-found, re-admitted record could never be taken by a cycle, with no error."""
        seeded = lr.new_id()
        self.raw_row(seeded, "opened", title="seeded", materiality="high", confidence="high", target="shiploop")
        lr.append("admitted", seeded, self.ledger)
        minor = self.open_record("minor", materiality="minor")
        lr.append("admitted", minor, self.ledger)
        self.assertEqual(lr.select(self.ledger), seeded)
        lr.append("predicted", seeded, self.ledger, prediction={"record": seeded}, candidate="abc")
        self.assertIsNone(lr.select(self.ledger), "a minor record is still never taken")
        checked_in = lr.current()["LR-20261030-5dce01"]
        self.assertEqual(checked_in["materiality"], "high", "the one real row this is about")

    def test_a_material_sighting_makes_a_record_that_was_opened_minor_material_and_a_minor_one_never_lowers_it(self):
        """The restore pilot's record was opened minor (a pilot, never to be taken by a loop). A later review that found a
        clear defect in a build and set same_as to it was judged material, but the fold kept the first row's minor, so the
        record could be admitted and still never selected. A record is as material as its most material sighting."""
        pilot = self.open_record("opened minor", materiality="minor")
        lr.append("admitted", pilot, self.ledger)
        self.assertIsNone(lr.select(self.ledger))
        lr.append("opened", pilot, self.ledger, materiality="material", source={"case": "hello", "exposure": "development"})
        self.assertEqual(lr.current(self.ledger)[pilot]["materiality"], "material")
        self.assertEqual(lr.select(self.ledger), pilot)
        lr.append("opened", pilot, self.ledger, materiality="minor", source={"case": "hello", "exposure": "development"})
        self.assertEqual(lr.current(self.ledger)[pilot]["materiality"], "material", "a later minor sighting does not lower it")
        self.assertEqual(lr.select(self.ledger), pilot)

    def test_ingest_routes_findings_and_attaches_a_recurrence(self):
        known = self.open_record("known")
        finding = {"id": "D1", "title": "again", "materiality": "material", "confidence": "high", "target": "shiploop",
                   "files": [], "proposal": "p", "next_experiment": "n", "mission_anchor": {"clause_id": "S-6"}}
        routes = {"implementation": [dict(finding, same_as=known)],
                  "owner_challenges": [dict(finding, id="D2", same_as="LR-20990101-abcdef")],
                  "harness": [dict(finding, id="D3", target="harness")]}
        opened = lr.ingest({}, routes, {"run": "/runs/r", "exposure": "development"}, self.ledger)
        states = lr.current(self.ledger)
        self.assertEqual(opened[0], known)
        self.assertEqual((states[known]["status"], states[known]["seen"]), ("admitted", 2))
        self.assertEqual(states[opened[1]]["status"], "owner")
        self.assertEqual(states[opened[2]]["status"], "deferred")
        rows = [row for row in lr.rows(self.ledger) if row["record"] == opened[1] and row["event"] == "opened"]
        self.assertEqual(rows[0]["same_as_unknown"], "LR-20990101-abcdef")

    def refound(self, record, route):
        finding = {"id": "D9", "title": "again", "materiality": "material", "confidence": "high", "target": "shiploop",
                   "files": [], "proposal": "p", "next_experiment": "n", "mission_anchor": {"clause_id": "S-6"},
                   "same_as": record}
        return lr.ingest({}, {route: [finding]}, {"run": "/runs/again", "exposure": "development"}, self.ledger)

    def test_a_refound_record_the_owner_holds_stays_with_the_owner_until_the_owner_decides(self):
        """Stage 5's second launch opened a record and routed it to the owner. A later exploration that re-finds it and
        whose judge says implementation must add its evidence, not take the record out of the owner's hands."""
        held = self.open_record("held")
        lr.append("owner", held, self.ledger, reason="material challenge routed to the owner or an investigation")
        self.assertEqual(self.refound(held, "implementation"), [held])
        state = lr.current(self.ledger)[held]
        self.assertEqual((state["status"], state["seen"]), ("owner", 2), "the evidence is kept and the owner's hold is not lost")
        self.assertEqual(len(state["sources"]), 1, "the re-find's source is on the record")
        self.assertIsNone(lr.select(self.ledger), "a record the owner holds is never offered to a cycle")
        lr.append("owner", held, self.ledger, outcome="accept", owner_decision="qualify it")
        self.assertEqual(lr.current(self.ledger)[held]["status"], "admitted")
        self.assertEqual(lr.select(self.ledger), held, "the owner's accept is what makes it selectable")

    def test_a_refound_record_in_a_candidate_stays_in_it_whatever_the_route(self):
        for route in ("implementation", "owner_challenges", "harness"):
            with self.subTest(route=route):
                record = self.open_record(f"in flight {route}")
                lr.append("admitted", record, self.ledger)
                lr.append("predicted", record, self.ledger, prediction={"record": record}, candidate="abc")
                self.refound(record, route)
                state = lr.current(self.ledger)[record]
                self.assertEqual((state["status"], state["seen"], state["candidate"]), ("in_candidate", 2, "abc"))

    def test_a_refound_open_record_is_still_admitted_and_an_admitted_one_can_still_go_to_the_owner(self):
        open_record = self.open_record("open")
        self.refound(open_record, "implementation")
        self.assertEqual(lr.current(self.ledger)[open_record]["status"], "admitted")
        admitted = self.open_record("admitted")
        lr.append("admitted", admitted, self.ledger)
        self.refound(admitted, "owner_challenges")
        self.assertEqual(lr.current(self.ledger)[admitted]["status"], "owner",
                         "a new challenge to an admitted record is the owner's to answer")

    def test_rediscovery_preserves_owner_disposition_and_keeps_new_evidence(self):
        for outcome, route in itertools.product((None, "reject"), ("implementation", "owner_challenges", "harness")):
            with self.subTest(outcome=outcome, route=route):
                ledger = self.temp / f"{outcome}-{route}.jsonl"
                record = lr.new_id()
                lr.append("opened", record, ledger, title="held lesson", materiality="material", target="shiploop")
                lr.append("admitted", record, ledger)
                lr.append("owner", record, ledger, outcome=outcome, reason="keep the owner's reason",
                          owner_decision="investigate first")
                before = ledger.read_bytes()
                ids = lr.ingest({}, {route: [{"id": "D1", "same_as": record, "routing": "investigate"}]},
                                {"run": "/runs/new", "exposure": "development"}, ledger)
                state = lr.current(ledger)[record]
                self.assertEqual(ids, [record])
                reopened_for_owner = outcome == "reject" and route == "owner_challenges"
                self.assertEqual(state["status"], "rejected" if outcome == "reject" and not reopened_for_owner else "owner")
                if not reopened_for_owner:
                    self.assertEqual(state["reason"], "keep the owner's reason")
                    self.assertEqual(state["owner_decision"], "investigate first")
                    self.assertEqual(state["sources"][-1]["held"], "rejected" if outcome == "reject" else "owner")
                    self.assertEqual(state["sources"][-1]["routing"], "investigate")
                    self.assertEqual(len(lr.rows(ledger)), 4, "only the new observation is appended")
                self.assertEqual(state["seen"], 2)
                self.assertEqual(state["sources"][-1]["route"], route)
                self.assertEqual(state["sources"][-1]["run"], "/runs/new")
                self.assertTrue(ledger.read_bytes().startswith(before))
                self.assertIsNone(lr.select(ledger), "owner disposition must exclude it without an exposure filter")

    def test_checked_in_history_guard_detects_stale_branch_admission_and_prediction(self):
        for event in ("admitted", "predicted"):
            with self.subTest(event=event):
                record = self.open_record()
                lr.append("owner", record, self.ledger, outcome="reject")
                lr.append(event, record, self.ledger)
                # A union merge may place the later event first; event time governs the check.
                self.ledger.write_text("\n".join(reversed(self.ledger.read_text().splitlines())) + "\n")
                with self.assertRaisesRegex(AssertionError, record):
                    self.assert_owner_decisions_respected(self.ledger)
                self.ledger.unlink()
        for release in ("accept", "reopened"):
            with self.subTest(release=release):
                record = self.open_record()
                lr.append("owner", record, self.ledger)
                lr.append("owner" if release == "accept" else "reopened", record, self.ledger, outcome="accept")
                lr.append("admitted", record, self.ledger)
                lr.append("predicted", record, self.ledger)
                self.assert_owner_decisions_respected(self.ledger)

    def test_history_guard_allows_a_later_explicit_resolution_without_erasing_the_conflict(self):
        for resolution in ("accept", "owner", "reopened"):
            with self.subTest(resolution=resolution):
                ledger = self.temp / f"resolved-{resolution}.jsonl"
                record = lr.new_id()
                lr.append("opened", record, ledger)
                lr.append("owner", record, ledger, outcome="reject")
                lr.append("admitted", record, ledger, reason="conflicting branch")
                before = ledger.read_bytes()
                lr.append("reopened" if resolution == "reopened" else "owner", record, ledger,
                          outcome="accept" if resolution == "accept" else None, reason="explicit resolution")
                self.assert_owner_decisions_respected(ledger)
                self.assertTrue(ledger.read_bytes().startswith(before))
                if resolution == "owner":
                    lr.append("predicted", record, ledger)
                    with self.assertRaisesRegex(AssertionError, record):
                        self.assert_owner_decisions_respected(ledger)

    def test_a_same_batch_owner_referral_survives_a_later_automatic_route(self):
        record = self.open_record()
        finding = {"same_as": record}
        lr.ingest({}, {"owner_challenges": [finding], "harness": [finding]},
                  {"exposure": "confirmation"}, self.ledger)
        state = lr.current(self.ledger)[record]
        self.assertEqual((state["status"], state["seen"], state["exposure"]), ("owner", 3, "confirmation"))
        self.assertEqual([source["route"] for source in state["sources"]], ["owner_challenges", "harness"])

    def test_ordinary_reopening_and_explicit_owner_acceptance_still_allow_admission(self):
        for disposition in ("deferred", "refuted", "verified", "accepted", "reopened"):
            with self.subTest(disposition=disposition):
                record = self.open_record(disposition)
                lr.append("admitted", record, self.ledger)
                if disposition == "deferred":
                    lr.append("deferred", record, self.ledger, reason="ordinary deferral")
                elif disposition in ("refuted", "verified"):
                    lr.append("verdict", record, self.ledger, outcome=disposition)
                else:
                    lr.append("owner", record, self.ledger, outcome="reject")
                    if disposition == "accepted":
                        lr.append("owner", record, self.ledger, outcome="accept")
                    else:
                        lr.append("reopened", record, self.ledger, reason="explicit reopening")
                lr.ingest({}, {"implementation": [{"same_as": record}]}, {}, self.ledger)
                self.assertEqual(lr.current(self.ledger)[record]["status"], "admitted")

    SETTLED_BY = {
        "verified": lambda self, record: lr.append("verdict", record, self.ledger, verdict="confirmed", outcome="verified",
                                                   reason="promoted", reopen_when="the effect is lost"),
        "refuted": lambda self, record: lr.append("verdict", record, self.ledger, verdict="refuted", outcome="refuted",
                                                  reason="tokens rose", reopen_when="new evidence that the measure can move"),
        "no_effect": lambda self, record: lr.append("verdict", record, self.ledger, verdict="no_effect", outcome="no_effect",
                                                    reason="inside the tolerance", reopen_when="a larger effect is predicted"),
        "unexplained_gain": lambda self, record: lr.append("verdict", record, self.ledger, verdict="unexplained",
                                                           outcome="unexplained_gain", reason="a gain nobody predicted"),
        "deferred": lambda self, record: lr.append("deferred", record, self.ledger, reason="n = 1",
                                                   reopen_when="the pause recurs on any case or model"),
        "rejected": lambda self, record: lr.append("owner", record, self.ledger, outcome="reject", reason="not this"),
    }

    def settled(self, status, title=None):
        """A record that has been admitted, then settled the way the fold reaches `status`."""
        record = self.open_record(title or status)
        lr.append("admitted", record, self.ledger)
        self.SETTLED_BY[status](self, record)
        self.assertEqual(lr.current(self.ledger)[record]["status"], status)
        return record

    def test_a_harness_sighting_never_moves_a_settled_record_or_rewrites_its_reason(self):
        """A harness finding is a measurement defect for a separate evaluator experiment, not a claim about the record's
        fix. Following its route used to append `deferred` with ingest's own text: a verified, refuted or unexplained record
        became deferred, and a deferred one lost its reason and reopening condition to the default."""
        for status in self.SETTLED_BY:
            with self.subTest(status=status):
                self.ledger = self.temp / f"harness-{status}.jsonl"
                record = self.settled(status)
                before = lr.current(self.ledger)[record]
                rows_before = len(lr.rows(self.ledger))
                self.assertEqual(self.refound(record, "harness"), [record])
                state = lr.current(self.ledger)[record]
                self.assertEqual((state["status"], state["seen"]), (status, 2))
                self.assertEqual((state["reason"], state["reopen_when"]), (before["reason"], before["reopen_when"]))
                self.assertEqual(len(lr.rows(self.ledger)), rows_before + 1, "only the observation is appended")
                self.assertEqual((state["sources"][-1]["held"], state["sources"][-1]["route"]), (status, "harness"))
                self.assertIsNone(lr.select(self.ledger))

    def test_a_settled_record_can_still_be_taken_to_the_owner_by_a_sighting(self):
        """What a sighting may do to a settled record is ask: an owner-routed one moves it to the owner, who decides.
        It adopts nothing. This is what 916a2c2b did for a rejected record, applied to the other settled statuses."""
        for status in self.SETTLED_BY:
            with self.subTest(status=status):
                self.ledger = self.temp / f"ask-{status}.jsonl"
                record = self.settled(status)
                self.assertEqual(self.refound(record, "owner_challenges"), [record])
                state = lr.current(self.ledger)[record]
                self.assertEqual((state["status"], state["seen"]), ("owner", 2))
                self.assertNotIn("held", state["sources"][-1])
                self.assertIsNone(lr.select(self.ledger))

    def test_unmarked_historical_route_events_keep_their_existing_meaning(self):
        record = self.open_record()
        lr.append("owner", record, self.ledger, outcome="reject")
        lr.append("admitted", record, self.ledger, reason="historical or explicit event")
        self.assertEqual(lr.current(self.ledger)[record]["status"], "admitted")

    def test_the_checked_in_ledger_folds_and_the_harness_alone_may_write_it(self):
        import boundary
        states = lr.current()
        self.assertTrue(states)
        self.assert_owner_decisions_respected(lr.LEDGER)
        self.assertFalse(boundary.candidate_path("test/shiploop_e2e/learning-records.jsonl"))
        evaluator = {path.name for path in boundary.evaluator_files(ROOT / "test" / "shiploop_e2e")}
        self.assertNotIn("learning-records.jsonl", evaluator)
        attributes = subprocess.run(["git", "-C", str(ROOT), "check-attr", "merge",
                                     "test/shiploop_e2e/learning-records.jsonl"], capture_output=True, text=True,
                                    check=True).stdout
        self.assertIn("merge: union", attributes)


    def test_a_verdict_that_defers_a_record_takes_effect(self):
        record = self.open_record()
        lr.append("admitted", record, self.ledger)
        lr.append("predicted", record, self.ledger, prediction={"record": record}, candidate="abc")
        lr.append("decided", record, self.ledger, decision="DROP")
        lr.append("verdict", record, self.ledger, verdict="confirmed", outcome="deferred", reason="regressed a case",
                  reopen_when="a candidate keeps the effect without it", calibration="stated, not measured")
        state = lr.current(self.ledger)[record]
        self.assertEqual(state["status"], "deferred")
        self.assertEqual(state["calibration"], "stated, not measured")

    def test_unicode_line_separators_in_a_title_do_not_break_the_ledger(self):
        title = "a\u2028title\u2029with\u0085separators"
        record = self.open_record(title)
        self.assertEqual(lr.current(self.ledger)[record]["title"], title)
        self.assertIn(title, lr.reviewer_view(self.ledger))

    def test_an_empty_same_as_is_no_claim_and_a_bad_one_is_named(self):
        finding = {"id": "D1", "title": "t", "potential_impact": "i", "next_experiment": "n", "proposal": "p",
                   "evidence": [{"reference": "r", "observation": "o", "interpretation": "i"}],
                   "mission_anchor": {"clause_id": "S-14", "relationship": "supports", "challenge": None},
                   "materiality": "material", "confidence": "high", "alternatives": [], "target": "shiploop",
                   "files": ["skills/shiploop/scripts/x.py"], "implementation_eligible": True,
                   "proposed_disposition": "implement"}
        self.assertEqual(review._discovery_problems({**finding, "same_as": ""}, 0), [])
        self.assertEqual(review._discovery_problems({**finding, "same_as": None}, 0), [])
        self.assertEqual(review._discovery_problems({**finding, "same_as": "LR-20261030-abcdef"}, 0), [])
        self.assertIn("same_as", " ".join(review._discovery_problems({**finding, "same_as": "none"}, 0)))

    # Materiality vocabulary. review.py accepts `material` or `minor` and nothing else, and select() takes `material` (and,
    # for the one seeded row, `high`), so an admitted record carrying any other word is never offered and nothing says so.
    LEGACY = "LR-20261030-5dce01"

    def raw_row(self, record, event, at="2020-01-01T00:00:00.000000Z", **fields):
        """A row as an older append() could write it, which the current one may refuse."""
        row = {"contract": lr.CONTRACT, "event_id": f"{at}-{event[:3]}000", "at": at, "record": record, "event": event, **fields}
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def test_append_refuses_a_materiality_that_select_could_never_read(self):
        for value in ("high", "low", "critical", "Material", "material ", "", None, 3, ["material"]):
            with self.subTest(value=value):
                record = lr.new_id()
                with self.assertRaisesRegex(ValueError, "materiality"):
                    lr.append("opened", record, self.ledger, title="t", materiality=value)
                self.assertFalse(self.ledger.exists() and self.ledger.read_text(), "a refused row is not written")
        for value in ("material", "minor"):
            with self.subTest(value=value):
                lr.append("opened", lr.new_id(), self.ledger, title="t", materiality=value)
        lr.append("opened", lr.new_id(), self.ledger, source={"run": "/runs/y"})
        self.assertEqual(len(lr.rows(self.ledger)), 3, "a sighting that makes no claim about materiality is not refused")

    def test_the_checked_in_ledger_has_one_unreadable_materiality_and_it_is_the_named_one(self):
        """A history check, as for owner decisions: a union merge from a branch that predates the check in append() can
        bring in a word the vocabulary does not have. This fails then, instead of a record being skipped without a sound.
        The one row that says "high" (LR-20261030-5dce01, event_id 2026-10-31T05:14:11.983143Z-5f757d) is the exception
        select() reads (MATERIAL); it is not edited, the ledger being append-only."""
        odd = {(row["record"], row["materiality"]) for row in lr.rows(lr.LEDGER)
               if row["event"] == "opened" and "materiality" in row and row["materiality"] not in lr.MATERIALITY}
        self.assertEqual(odd, {(self.LEGACY, "high")})
        self.assertIn("high", lr.MATERIAL, "select reads the one unreadable word the ledger holds")

    def test_ingest_refuses_an_unreadable_materiality_before_it_writes_anything(self):
        good = {"id": "D1", "title": "fine", "materiality": "material", "confidence": "high", "target": "shiploop"}
        bad = {"id": "D2", "title": "odd", "materiality": "high", "confidence": "high", "target": "harness"}
        for route in ("implementation", "owner_challenges", "harness"):
            with self.subTest(route=route):
                ledger = self.temp / f"bad-{route}.jsonl"
                # The good finding goes on the route ingest handles first, or last when the bad one is on the first.
                good_route = "harness" if route == "implementation" else "implementation"
                with self.assertRaisesRegex(ValueError, "D2.*materiality"):
                    lr.ingest({}, {good_route: [good], route: [bad]}, {"run": "/runs/r"}, ledger)
                self.assertFalse(ledger.exists() and ledger.read_text(), "a half-recorded batch is not left behind")

    def test_a_sighting_with_no_materiality_writes_none_rather_than_a_null(self):
        known = self.open_record("known")
        lr.ingest({}, {"owner_challenges": [{"same_as": known}]}, {"run": "/runs/r"}, self.ledger)
        sighting = [row for row in lr.rows(self.ledger) if row["event"] == "opened"][-1]
        self.assertNotIn("materiality", sighting)
        self.assertEqual(lr.current(self.ledger)[known]["materiality"], "material", "the first claim stands")




class PredictionTest(unittest.TestCase):
    REG = {"cases": {"hello": {"role": "regression"}, "csv-report": {"role": "regression"}}, "tolerance": 0.10,
           "quality_tolerance": 0.0, "floors": FLOORS}

    def good(self, **change):
        return {"contract": "prediction/1", "record": "LR-20261030-abcdef", "anchor": "S-7",
                "because": "a shorter packet head costs fewer tokens",
                "effects": [{"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.15}],
                "guards": [{"case": "*", "measure": "accuracy", "direction": "not_down"}], **change}

    def test_a_prediction_needs_a_direction_and_an_effect_the_epoch_can_resolve(self):
        prediction.validate(self.good(), self.REG)
        for broken, why in ((self.good(effects=[]), "no worse"),
                            (self.good(effects=[{"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.05}]),
                             "below the registered tolerance"),
                            (self.good(effects=[{"case": "chess", "measure": "tokens", "direction": "down", "at_least": 0.2}]),
                             "not a registered case"),
                            (self.good(effects=[{"case": "hello", "measure": "tokens", "direction": "same", "at_least": 0.2}]),
                             "up or down"),
                            (self.good(effects=[{"case": "hello", "measure": "vibes", "direction": "up", "at_least": 0.2}]),
                             "dotted scorecard path"),
                            (self.good(record="LR-1"), "learning-record id"),
                            (self.good(extra=1), "unknown prediction keys")):
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                prediction.validate(broken, self.REG)

    def test_a_floor_or_a_diagnostic_effect_is_not_held_to_the_efficiency_tolerance(self):
        prediction.validate(self.good(effects=[
            {"case": "hello", "measure": "accuracy", "direction": "up", "at_least": 0.05},
            {"case": "hello", "measure": "efficiency.refusals", "direction": "down", "at_least": 0.05}]), self.REG)

    def test_verdicts_follow_the_measured_change(self):
        control = [card(tokens=1_000_000) for _ in range(3)]
        for tokens, expected in ((800_000, "confirmed"), (1_150_000, "refuted"), (950_000, "no_effect")):
            candidate = [card(tokens=tokens) for _ in range(3)]
            judged = prediction.verdict(self.good(guards=[]), self.REG, control, candidate)
            self.assertEqual(judged["verdict"], expected, tokens)
        unknown = prediction.verdict(self.good(guards=[]), self.REG, control, [card(comparable=False)] * 3)
        self.assertEqual(unknown["verdict"], "unknown")

    def test_a_broken_guard_refutes_a_confirmed_effect(self):
        control = [card(case=c) for c in ("hello", "csv-report") for _ in range(3)]
        candidate = [card(tokens=700_000) for _ in range(3)] + [card(case="csv-report", ok=False) for _ in range(3)]
        judged = prediction.verdict(self.good(), self.REG, control, candidate)
        self.assertEqual(judged["effects"][0]["verdict"], "confirmed")
        self.assertEqual([g["held"] for g in judged["guards"]], [False, True])
        self.assertEqual(judged["verdict"], "refuted")

    def test_a_diagnostic_from_zero_counts_the_control_as_one(self):
        self.assertEqual(prediction.change("efficiency.refusals", 0, 3), 3.0)
        self.assertAlmostEqual(prediction.change("accuracy", 1.0, 2 / 3), -1 / 3)

    def test_the_record_outcome_reads_the_decision_and_the_verdict_together(self):
        cases = {("PROMOTE", "confirmed"): "verified", ("PROMOTE", "no_effect"): "unexplained_gain",
                 ("DROP", "refuted"): "refuted", ("DROP", "no_effect"): "no_effect", ("DROP", "confirmed"): "deferred",
                 ("UNDECIDED", "unknown"): "admitted"}
        for (decision, found), expected in cases.items():
            with self.subTest(decision=decision, found=found):
                self.assertEqual(prediction.outcome(decision, {"verdict": found}, ["why"])["outcome"], expected)


    def test_a_malformed_case_or_amount_is_a_refusal_not_a_crash(self):
        effect = {"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.2}
        for broken, why in ((self.good(effects=[{**effect, "case": ["hello", "csv-report"]}]), "registered case"),
                            (self.good(effects=[{**effect, "case": {"a": 1}}]), "registered case"),
                            (self.good(effects=[{**effect, "at_least": 10 ** 400}]), "positive number"),
                            (self.good(guards=[{"case": ["hello"], "measure": "accuracy", "direction": "not_down"}]),
                             "neither")):
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                prediction.validate(broken, self.REG)

    def test_an_unknown_guard_leaves_the_prediction_unjudged_and_an_unjudged_drop_is_not_a_settled_no_effect(self):
        control = [card(tokens=1_000_000) for _ in range(3)]
        candidate = [card(tokens=700_000) for _ in range(3)]
        for one in candidate:
            one["efficiency"].pop("refusals")
        guard = [{"case": "hello", "measure": "efficiency.refusals", "direction": "not_up"}]
        judged = prediction.verdict(self.good(guards=guard), self.REG, control, candidate)
        self.assertEqual(judged["effects"][0]["verdict"], "confirmed")
        self.assertIsNone(judged["guards"][0]["held"])
        self.assertEqual(judged["verdict"], "unknown")
        after = prediction.outcome("DROP", {"verdict": "unknown"}, ["no success to divide by"])
        self.assertEqual(after["outcome"], "deferred")
        self.assertIn("could not be judged", after["reason"])



class SpreadTest(unittest.TestCase):
    def test_a_tight_build_allows_a_small_tolerance_and_a_loose_one_does_not(self):
        tight = [card(tokens=1_000_000 + n * 10_000) for n in range(8)]
        loose = [card(tokens=t) for t in (600_000, 1_400_000, 900_000, 1_100_000, 700_000, 1_300_000, 1_000_000, 800_000)]
        report = {"tight": spread.case_spread(tight, FLOORS, 3, 5000), "loose": spread.case_spread(loose, FLOORS, 3, 5000)}
        self.assertEqual(report["tight"]["splits"], 560)
        self.assertEqual(report["tight"]["false_decision"]["tokens"]["0.05"], 0.0)
        self.assertGreater(report["loose"]["false_decision"]["tokens"]["0.10"], 0.5)
        recommended = spread.recommend(report, "tokens", 3)
        self.assertEqual(recommended["by_case"], {"tight": 0.05, "loose": 0.4})
        self.assertEqual(recommended["tolerance"], 0.4)

    def test_failures_give_a_false_drop_risk_and_quality_splits_never_reach_efficiency(self):
        cards = [card() for _ in range(6)] + [card(ok=False) for _ in range(2)]
        report = spread.case_spread(cards, FLOORS, 3, 5000)
        self.assertEqual((report["failures"], report["failure_rate"]), (2, 0.25))
        self.assertAlmostEqual(report["false_drop_risk"], 1 - 0.75 ** 3, places=4)
        self.assertGreater(report["quality_split_differs"], 0)

    def test_too_few_attempts_say_so_and_recommend_nothing(self):
        report = {"hello": spread.case_spread([card() for _ in range(4)], FLOORS, 3, 5000)}
        self.assertIn("cannot make two arms", report["hello"]["why"])
        self.assertIsNone(spread.recommend(report, "tokens", 3)["tolerance"])

    def test_the_scoring_digest_moves_with_a_case_entry_but_not_with_other_cases(self):
        catalog = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
        first = spread.scoring_digest({"hello": catalog["hello"]})
        self.assertEqual(first, spread.scoring_digest({"hello": dict(catalog["hello"])}))
        changed = spread.scoring_digest({"hello": {**catalog["hello"], "prompt": "something else"}})
        self.assertNotEqual(first["sha256"], changed["sha256"])


    def test_splits_whose_quality_differs_never_reach_the_efficiency_comparison(self):
        cards = [card() for _ in range(6)] + [card(ok=False) for _ in range(2)]
        report = spread.case_spread(cards, FLOORS, 3, 5000)
        differing = round(report["quality_split_differs"] * report["splits"])
        self.assertGreater(differing, 0)
        self.assertEqual(report["false_decision"]["tokens"]["compared"], report["splits"] - differing)

    def test_the_scoring_digest_follows_the_modules_the_scorer_imports_and_ignores_unrelated_ones(self):
        with tempfile.TemporaryDirectory() as temp:
            harness = Path(temp)
            for name in spread.SCORING_MODULES:
                (harness / name).write_text("")
            (harness / "scorecard.py").write_text("import helper\n")
            (harness / "helper.py").write_text("from deeper import thing\n")
            (harness / "deeper.py").write_text("thing = 1\n")
            (harness / "unrelated.py").write_text("y = 1\n")
            (harness / "checks").mkdir()
            before = spread.scoring_digest({}, harness)["sha256"]
            (harness / "unrelated.py").write_text("y = 2\n")
            self.assertEqual(spread.scoring_digest({}, harness)["sha256"], before, "an unrelated module moved it")
            (harness / "deeper.py").write_text("thing = 2\n")
            self.assertNotEqual(spread.scoring_digest({}, harness)["sha256"], before, "an imported module did not")



    def test_a_large_sample_is_drawn_without_listing_every_split(self):
        produced = []
        real = itertools.combinations

        def counting(*args):
            for item in real(*args):
                produced.append(1)
                yield item
        with mock.patch.object(spread.itertools, "combinations", counting):
            splits = spread._splits(24, 3, 500)  # 2.7 million ways to deal 24 attempts; listing them took 378 MB
        self.assertEqual(len(splits), 500)
        self.assertEqual(len(set(splits)), 500, "a split was drawn twice")
        self.assertTrue(all(len(left) == 3 == len(right) and not set(left) & set(right) for left, right in splits))
        self.assertLess(len(produced), 100_000, "the whole space was enumerated")

    def test_a_small_space_is_still_listed_in_full(self):
        self.assertEqual(len(spread._splits(8, 3, 5000)), 560)


class PurposeCheckTest(unittest.TestCase):
    RECORD = "LR-20261030-aaaaaa"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.write("skills/shiploop/scripts/a.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, path, text, trailers=(RECORD,)):
        self.write(path, text)
        self.git("add", "-A")
        self.git("commit", "-qm", "change\n\n" + "\n".join(f"Learning-Record: {t}" for t in trailers))
        return self.git("rev-parse", "HEAD").strip()

    def check(self, head, files=("skills/shiploop/scripts/a.py",)):
        return purpose_check.script_check(self.repo, self.base, head, self.RECORD, list(files))

    def test_a_generic_change_with_one_record_passes(self):
        head = self.commit("skills/shiploop/scripts/a.py", "x = 1\n# run the type checkers first\n")
        result = self.check(head)
        self.assertTrue(result["passed"], result["problems"])
        self.assertEqual(purpose_check.decide(result, None)["result"], "passed")

    def test_a_probe_word_rejects_before_any_run(self):
        head = self.commit("skills/shiploop/scripts/a.py", "x = 1\n# sink the whole battleship\n")
        result = self.check(head)
        self.assertFalse(result["passed"])
        self.assertEqual(result["probe_hits"][0]["case"], "battleship")
        self.assertEqual(purpose_check.decide(result, None)["result"], "rejected")

    def test_the_developer_guide_is_exempt(self):
        head = self.commit("skills/shiploop/README.md", "A recorded run built a battleship game.\n")
        self.assertTrue(self.check(head, ["skills/shiploop/README.md"])["passed"])

    def test_one_record_and_only_the_candidates_files(self):
        none = self.commit("skills/shiploop/scripts/a.py", "x = 2\n", trailers=())
        self.assertIn("exactly one Learning-Record", self.check(none)["problems"][0])
        self.git("reset", "-q", "--hard", self.base)
        two = self.commit("skills/shiploop/scripts/a.py", "x = 3\n", trailers=(self.RECORD, "LR-20261030-bbbbbb"))
        self.assertFalse(self.check(two)["passed"])
        self.git("reset", "-q", "--hard", self.base)
        outside = self.commit("test/shiploop_e2e/run.py", "graded = True\n")
        self.assertIn("outside the candidate", " ".join(self.check(outside)["problems"]))
        self.git("reset", "-q", "--hard", self.base)
        extra = self.commit("skills/shiploop/scripts/b.py", "y = 1\n")
        result = self.check(extra)
        self.assertTrue(result["passed"])
        self.assertEqual(result["extra_files"], ["skills/shiploop/scripts/b.py"])

    def test_the_review_decides_and_an_unusable_review_rejects(self):
        passed = {"passed": True, "problems": []}
        self.assertEqual(purpose_check.decide(passed, {"validity": {"status": "valid"}, "verdict": "aligned",
                                                  "prediction_follows": True})["result"],
                         "passed")
        retry = purpose_check.decide(passed, {"validity": {"status": "valid"}, "verdict": "extra", "summary": "s",
                                              "files": [{"path": "b.py", "serves": "no", "why": "a rename"}]})
        self.assertEqual((retry["result"], retry["reasons"][1]), ("retry", "b.py: a rename"))
        self.assertEqual(purpose_check.decide(passed, {"validity": {"status": "valid"}, "verdict": "misaligned"})["result"],
                         "rejected")
        self.assertEqual(purpose_check.decide(passed, {"validity": {"status": "invalid", "reason": "timeout"}})["result"],
                         "rejected")

    def test_the_review_is_given_the_anchor_clause_and_never_the_run(self):
        text = purpose_check.review_prompt({"record": self.RECORD, "title": "t"}, purpose_check.clause_text("S-13"),
                                           None, "diff --git a/x b/x")
        self.assertIn("**S-13 Everything is generic.**", text)
        # The review can only see what review_prompt is given: the record, its clause, the prediction and the diff.
        self.assertEqual(list(inspect.signature(purpose_check.review_prompt).parameters),
                         ["record", "anchor", "prediction", "diff"])
        self.assertIn("not in SPEC.md", purpose_check.clause_text("S-99"))

    def test_every_case_has_terms_and_none_matches_the_engine_except_the_tracked_hits(self):
        terms = purpose_check.load_terms()
        catalog = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
        self.assertEqual(set(terms["terms"]), set(catalog))
        known = {(row["path"], row["case"]) for row in terms["known"]}
        records = lr.current()
        for row in terms["known"]:
            self.assertIn(row["record"], records)
        found = set()
        for path in (ROOT / "skills" / "shiploop").rglob("*"):
            relative = path.relative_to(ROOT).as_posix()
            if not path.is_file() or "__pycache__" in path.parts or relative in terms["exempt"]:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for case, patterns in terms["terms"].items():
                if any(pattern.search(text) for pattern in patterns):
                    found.add((relative, case))
        self.assertEqual(found, known)
        self.assertFalse(any(re.fullmatch(r"\\bcheckers\??\\b", p.pattern) for p in terms["terms"]["checkers"]))


    def test_a_probe_word_cannot_hide_behind_a_diff_header_lookalike(self):
        head = self.commit("skills/shiploop/scripts/a.py",
                           "x = 1\n++ b/skills/shiploop/README.md\nsink the battleship\n")
        self.assertEqual([hit["case"] for hit in self.check(head)["probe_hits"]][:1], ["battleship"])

    def test_a_probe_word_is_found_whatever_prefix_the_users_git_config_asks_for(self):
        self.git("config", "diff.noprefix", "true")
        head = self.commit("skills/shiploop/scripts/a.py", "x = 1\n# the battleship\n")
        self.assertTrue(self.check(head)["probe_hits"])

    def test_a_file_with_a_non_ascii_name_is_not_mistaken_for_one_outside_the_candidate(self):
        path = "skills/shiploop/references/caf\u00e9.md"
        head = self.commit(path, "a reference\n")
        result = self.check(head, [path])
        self.assertTrue(result["passed"], result["problems"])
        self.assertEqual(result["changed"], [path])

    def test_a_rename_out_of_the_harness_is_seen_as_a_deletion_there(self):
        self.write("test/shiploop_e2e/checks/oracle.py", "def check():\n    return True\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "a check the candidate may not touch")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.git("mv", "test/shiploop_e2e/checks/oracle.py", "skills/shiploop/scripts/oracle_copy.py")
        self.git("commit", "-qm", "move\n\nLearning-Record: " + self.RECORD)
        result = self.check(self.git("rev-parse", "HEAD").strip(), ["skills/shiploop/scripts/oracle_copy.py"])
        self.assertFalse(result["passed"])
        self.assertIn("test/shiploop_e2e/checks/oracle.py", " ".join(result["problems"]))

    def test_generic_words_are_not_probe_terms(self):
        for line in ("# the sampling temperature of a model", "# a sunk cost", "# print hello, world in the example",
                     "# the fleet of workers"):
            with self.subTest(line=line):
                self.assertFalse(purpose_check.probe_hits([("skills/shiploop/scripts/a.py", line)],
                                                          purpose_check.load_terms()))

    def test_an_aligned_review_must_also_say_the_prediction_follows(self):
        passed = {"passed": True, "problems": []}
        for follows, expected in ((False, "rejected"), (None, "rejected"), (True, "passed")):
            reviewed = {"validity": {"status": "valid"}, "verdict": "aligned", "summary": "s",
                        "prediction_note": "any change would meet it"}
            if follows is not None:
                reviewed["prediction_follows"] = follows
            with self.subTest(prediction_follows=follows):
                decided = purpose_check.decide(passed, reviewed)
                self.assertEqual(decided["result"], expected)
        self.assertIn("any change would meet it", " ".join(purpose_check.decide(passed, {
            "validity": {"status": "valid"}, "verdict": "aligned", "prediction_follows": False,
            "prediction_note": "any change would meet it"})["reasons"]))


if __name__ == "__main__":
    unittest.main()
