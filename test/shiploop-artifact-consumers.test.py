#!/usr/bin/env python3
"""Producer-to-reader closure checks for selected ShipLoop artifact families.

The package catalog documents every family.  This suite deliberately executes
the new or changed routes whose consumer cannot be inferred from a filename:
baseline cold context, outer-work callbacks/read receipts, archive diagnostics,
the derived delivery view, and transactional recovery.  Established families
keep their focused suites named by the catalog instead of duplicating a full
action-walk here.
"""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_artifact_matrix_action_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()

import shiploop_artifacts as artifacts  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_report import render_report  # noqa: E402


class ArtifactConsumerMatrixTests(ACTION.ShipLoopActionWalkFixture):
    """Exercise only routes that need an explicit producer/reader boundary."""

    def context_text(self, section: str, **selectors: str) -> str:
        offset = 0
        digest = ""
        chunks: list[str] = []
        while True:
            args = ["context", "--section", section, "--offset", str(offset), "--limit", "8000"]
            for key, value in selectors.items():
                args.extend(("--" + key.replace("_", "-"), value))
            if digest:
                args.extend(("--digest", digest))
            output = self.cli(*args).stdout
            header, body = output.split("\n", 1)
            match = re.fullmatch(
                rf"Context {re.escape(section)}; digest ([0-9a-f]{{64}}); characters (\d+):(\d+)/(\d+)",
                header,
            )
            self.assertIsNotNone(match, output)
            assert match is not None
            page_digest, start, end, total = match.groups()
            self.assertEqual(int(start), offset, output)
            self.assertEqual(page_digest, digest or page_digest, output)
            chunks.append(body[: int(end) - offset])
            offset = int(end)
            digest = page_digest
            if offset == int(total):
                return "".join(chunks)

    def context_record(self, section: str, **selectors: str) -> dict:
        return store.loads(self.context_text(section, **selectors))

    def initialize_at_preflight(self) -> None:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--prompt",
            "Exercise artifact producer and consumer routes through durable Markdown.",
        )
        self.assertEqual(self.state()["stage"], "preflight")

    def outer_request(
        self, context: dict, *, entry_id: str, dedupe_key: str, target_stage: str
    ) -> dict:
        result = copy.deepcopy(context["append_template"])
        result.update(
            entry_id=entry_id,
            dedupe_key=dedupe_key,
            required_action="Record the named release decision before advancing the outer lifecycle.",
            target_stage=target_stage,
            target_alias="release-boundary",
            prerequisites=["The current candidate and its evidence are available."],
            expected_outcome="An authorized outer-stage decision is recorded with evidence.",
            evidence="The durable quality and candidate evidence are available to the responsible reviewer.",
            authority_limitations="This journal entry does not grant deployment or publication authority.",
            rationale="The inner action found work that only the outer lifecycle may resolve.",
        )
        return result

    def append_outer_work(self, payload: dict) -> None:
        self.cli(
            "journal",
            "--target",
            "outer",
            "--operation",
            "append",
            "--action",
            self.action_id(),
            "--result",
            self.record("outer-work", payload),
        )

    def test_catalog_has_a_closed_named_inventory_with_honest_conditional_route(self) -> None:
        catalog = artifacts.catalog()
        rows = catalog["families"]
        self.assertEqual(catalog["version"], 2)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        required = {
            "baseline",
            "observation-checkpoint",
            "outer-ledger",
            "outer-callback-receipt",
            "outer-read-receipt",
            "outer-evidence",
            "diagnostic-archives",
            "operational",
            "report",
        }
        by_id = {row["id"]: row for row in rows}
        self.assertTrue(required.issubset(by_id))
        fields = {
            "id",
            "pattern",
            "producer",
            "authority",
            "updater",
            "reader",
            "trigger",
            "content",
            "invalidation",
            "test",
            "coverage",
        }
        for row in rows:
            self.assertTrue(fields.issubset(row), row)
            self.assertTrue(all(isinstance(row[field], str) and row[field] for field in fields), row)
        observation = by_id["observation-checkpoint"]
        self.assertEqual(observation["coverage"], "runtime")
        self.assertIn("before parent completion", observation["trigger"])
        self.initialize_at_preflight()
        routed = self.context_record("artifacts")
        self.assertEqual(
            [row["id"] for row in routed["families"]],
            [row["id"] for row in rows],
        )

    def test_preflight_and_approach_are_real_producers_with_cold_context_readers(self) -> None:
        self.initialize_at_preflight()
        preflight = {
            "summary": "The fixture baseline contains a committed repository and local Python runtime.",
            "baseline": "committed-head",
        }
        packet, _ = self.complete(preflight, label="matrix-preflight")
        self.assertEqual(self.state()["stage"], "approach")
        self.assertIn("read baseline evidence via context --section: preflight", packet.stdout)
        self.assertEqual(self.context_record("preflight")["summary"], preflight["summary"])

        approach = {
            "summary": "The approach preserves the baseline and plans a bounded tested delivery sequence.",
            "body": "# Matrix approach\n\nPreserve the recorded baseline and use exact-output checks.\n",
        }
        self.converge_objective(approach, label="approach")
        self.assertEqual(self.state()["stage"], "survey")
        survey_packet = self.cli("next").stdout
        self.assertIn("context --section: preflight, approach", survey_packet)
        approach_text = self.context_text("approach")
        self.assertIn("Preserve the recorded baseline", approach_text)
        self.assertNotIn("Matrix approach", self.context_text("preflight"))

    def test_outer_work_ledger_callback_and_read_receipt_are_content_sensitive(self) -> None:
        self.initialize_at_preflight()
        initial = self.context_record("outer-work")
        self.assertEqual(initial["entries"], [])
        self.assertFalse((self.run_dir / "outer-work.md").exists())

        first = self.outer_request(
            initial,
            entry_id="OW-MATRIX-QUALITY",
            dedupe_key="matrix-quality-decision",
            target_stage="quality",
        )
        self.append_outer_work(first)
        request_path = self.run_dir / "journal-requests" / f"{first['request_id']}.md"
        self.assertTrue(request_path.is_file())

        diagnostic = self.context_record(
            "audit", kind="journal-requests", record=f"{first['request_id']}.md"
        )
        self.assertEqual(diagnostic["content"]["request"]["entry_id"], "OW-MATRIX-QUALITY")
        self.assertEqual(diagnostic["content"]["receipt"]["outcome"], "created")

        first_read = self.context_record("outer-work")
        self.assertEqual([row["id"] for row in first_read["entries"]], ["OW-MATRIX-QUALITY"])
        receipt_path = self.run_dir / "outer-work-reads" / f"{self.action_id()}.md"
        old_receipt = store.read_record(receipt_path)
        old_journal_hash = old_receipt["journal_sha256"]

        second = self.outer_request(
            first_read,
            entry_id="OW-MATRIX-PUBLISH",
            dedupe_key="matrix-publish-decision",
            target_stage="publish",
        )
        self.append_outer_work(second)
        self.assertNotEqual(self.state()["outer_work_sha256"], old_journal_hash)
        self.assertEqual(store.read_record(receipt_path)["journal_sha256"], old_journal_hash)

        current = self.context_record("outer-work")
        self.assertCountEqual(
            [row["id"] for row in current["entries"]],
            ["OW-MATRIX-PUBLISH", "OW-MATRIX-QUALITY"],
        )
        current_receipt = store.read_record(receipt_path)
        self.assertEqual(current_receipt["journal_sha256"], self.state()["outer_work_sha256"])
        self.assertNotEqual(current_receipt["digest"], old_receipt["digest"])

    def test_observation_receipt_callback_projects_unverified_knowledge_without_consuming_parent(self) -> None:
        self.initialize_at_preflight()
        parent_action = self.action_id()
        ticket = self.context_record("observation")["ticket"]
        result = {
            "summary": "Record a discovered later-stage condition without claiming verification.",
            "knowledge_revision": ticket["expected_knowledge_revision"],
            "learnings": "The observation remains explicitly unverified until a later check.",
            "discoveries": [
                {
                    "id": "matrix-observation",
                    "domain": "environment",
                    "observation": "The later release decision needs a recorded outer-stage owner.",
                    "evidence": "bounded matrix observation",
                    "scope": ["all"],
                    "disposition": "informational",
                    "rationale": "The observation informs future preparation without changing the current baseline.",
                    "revalidate": "Verify the owner and decision before outer publication.",
                }
            ],
        }
        result_path = self.record("matrix-observation", result)
        self.cli("done", "--action", ticket["action"], "--result", result_path)

        state = self.state()
        self.assertEqual(state["action"]["id"], parent_action)
        self.assertEqual(state["stage"], "preflight")
        receipt_path = self.run_dir / "observations" / f"{ticket['action']}.md"
        receipt = store.read_record(receipt_path)
        self.assertEqual(receipt["parent_action"], parent_action)
        self.assertEqual(receipt["route"]["kind"], "informational")
        self.assertEqual(
            state["observation_receipts"][ticket["action"]],
            protocol.digest(receipt),
        )

        current = self.context_record("knowledge")
        self.assertEqual(current["entries"][0]["source"]["kind"], "unverified-observation")
        self.assertEqual(current["entries"][0]["source"]["verification"], "not-run")
        diagnostic = self.context_record(
            "audit", kind="knowledge-history", record=f"{ticket['action']}.md"
        )
        content = diagnostic["content"]
        self.assertEqual(content["source"]["kind"], "unverified-observation")
        self.assertEqual(content["source"]["verification"], "not-run")
        self.assertEqual(content["ledger"]["entries"][0]["id"], "matrix-observation")
        before_replay = (self.run_dir / "state.md").read_bytes()
        self.cli("done", "--action", ticket["action"], "--result", result_path)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before_replay)
        self.assertFalse((self.run_dir / "results" / f"{parent_action}.md").exists())

    def test_delivery_report_and_operational_recovery_consume_changed_source_content(self) -> None:
        report_dir = self.root / "report-fixture"
        report_dir.mkdir()
        store.write_record(report_dir / "state.md", {"phase": "halted", "stage": "halted"}, "ShipLoop state")
        store.write_record(
            report_dir / "delivery.md",
            {"summary": "Initial staged release evidence", "verification": "first read-back"},
            "ShipLoop delivery evidence",
        )
        first_html, first_meta = render_report(report_dir)
        store.write_record(
            report_dir / "delivery.md",
            {"summary": "Revised staged release evidence", "verification": "second read-back"},
            "ShipLoop delivery evidence",
        )
        second_html, second_meta = render_report(report_dir)
        self.assertIn("delivery.md", first_meta["sources"])
        self.assertIn("Initial staged release evidence", first_html)
        self.assertIn("Revised staged release evidence", second_html)
        self.assertNotEqual(first_meta["source_digest"], second_meta["source_digest"])

        operational_root = self.root / "operational-fixture"
        operational_root.mkdir()

        def crash_after_first_target(phase: str, index: int) -> None:
            if phase == "after-target" and index == 1:
                raise RuntimeError("intentional matrix interruption")

        with self.assertRaisesRegex(RuntimeError, "intentional matrix interruption"):
            store.transaction(
                operational_root,
                {"first.md": "first\n", "second.md": "second\n"},
                fault=crash_after_first_target,
            )
        self.assertTrue((operational_root / "transaction.md").is_file())
        self.assertTrue(store.recover(operational_root))
        self.assertEqual((operational_root / "first.md").read_text(), "first\n")
        self.assertEqual((operational_root / "second.md").read_text(), "second\n")
        self.assertFalse((operational_root / "transaction.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
