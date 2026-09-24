#!/usr/bin/env python3
"""Contract tests for stopped selected-ephemeral Improve settlement."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
IMPROVE = ROOT / "skills" / "improve" / "SKILL.md"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


class StoppedStandaloneImproveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-stopped-improve-")
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.state = {"run_id": "run01", "repo": str(self.workspace)}
        self.skill = bridge.resolve_skill(str(IMPROVE))
        self.seed_result = {
            "outcome": "done",
            "summary": "Provisional plan is awaiting Improve.",
            "evidence_refs": ["provisional-plan.md"],
            "work_items": [{"id": "DRAFT", "title": "Unreviewed plan item"}],
        }
        self.binding = bridge.binding(
            self.state, "plan-test", "plan", self.seed_result, self.skill,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def start(self, *, marker: str | None = None) -> tuple[dict[str, object], str]:
        contract = {
            "workspace": str(self.workspace),
            "work": "Review the provisional plan and retain any reconciliation evidence.",
            "exit_condition": "Two qualifying trivial reviews and current evidence establish completion.",
            "repeat_condition": "Continue while an authorized improvement or evidence gap remains.",
            "required_trivial_reviews": 2,
            "context": {
                "request": "Improve this ShipLoop plan.\n" + (
                    marker if marker is not None else self.binding["contract_marker"]
                ),
                "scope": "Only the provisional plan and listed planning evidence files.",
                "authority": "Do not commit, merge, push, or broaden the parent scope.",
                "environment": "Python is available for local planning checks.",
                "resources": [{
                    "purpose": "selected Improve card",
                    "locator": self.skill["skill_card"],
                }],
            },
        }
        completed = subprocess.run(
            [sys.executable, "-B", self.skill["runtime_cli"], "start"],
            input=json.dumps(contract), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout), completed.stdout

    def done(self, packet: dict[str, object], report: dict[str, str]) -> tuple[dict[str, object], str]:
        argv = packet["done_argv"]
        self.assertIsInstance(argv, list)
        completed = subprocess.run(
            argv, input=json.dumps(report), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout), completed.stdout

    def stopped(
        self, *, marker: str | None = None, classification: str = "unresolved",
        exit_assessment: str = "unknown", continuation: str = "cancelled",
    ) -> tuple[dict[str, object], str]:
        packet, _raw = self.start(marker=marker)
        terminal, raw = self.done(packet, {
            "classification": classification,
            "exit_assessment": exit_assessment,
            "continuation_assessment": continuation,
            "evidence": "The selected target needs upstream reconciliation before plan acceptance.",
            "handoff": (
                "The provisional plan is incomplete; retain its target, evidence and unresolved "
                "premise for the parent reconciliation route."
            ),
        })
        self.assertEqual(terminal["status"], "stopped")
        self.assertFalse(Path(terminal["state_file"]).exists())
        return terminal, raw

    def completed(self) -> tuple[dict[str, object], str]:
        packet, _raw = self.start()
        for index in range(2):
            packet, raw = self.done(packet, {
                "classification": "trivial",
                "exit_assessment": "satisfied" if index == 1 else "unsatisfied",
                "continuation_assessment": "allowed",
                "evidence": f"qualifying review {index + 1} found no material issue",
                "handoff": "No material findings; retain the current planning scope and evidence.",
            })
        self.assertEqual(packet["status"], "complete")
        return packet, raw

    def save_packet(self, raw: str, binding: dict[str, object] | None = None) -> Path:
        path = bridge.receipt_path(self.binding if binding is None else binding)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
        return path

    def write_evidence(self, name: str = "observations.md") -> Path:
        path = self.workspace / name
        path.write_text("Observed planning evidence.\n", encoding="utf-8")
        return path

    def receipt(self, evidence: Path) -> dict[str, object]:
        return {
            "summary": "A plan premise is unresolved and requires upstream reconciliation.",
            "target": "research",
            "evidence_refs": [str(evidence)],
        }

    def test_real_stopped_packet_archives_exact_incomplete_record(self) -> None:
        packet, raw = self.stopped()
        evidence = self.write_evidence()
        self.save_packet(raw)
        submitted = self.receipt(evidence)

        record, writes = bridge.settle_incomplete(self.binding, submitted)

        self.assertEqual(record["runtime_phase"], "stopped")
        self.assertEqual(record["binding_id"], "run01/plan-test")
        self.assertEqual(record["action_id"], "plan-test")
        self.assertEqual(record["stage"], "plan")
        self.assertEqual(record["seed_result"], self.seed_result)
        self.assertEqual(record["submission"], submitted)
        self.assertEqual(record["receipt"], {
            "summary": submitted["summary"],
            "target": "research",
            "evidence_refs": ["observations.md"],
        })
        self.assertNotIn("review_refs", record["receipt"])
        self.assertNotIn("check_refs", record["receipt"])
        self.assertEqual(writes["improve/plan-test/terminal.json"], raw)
        self.assertEqual(
            record["identities"]["terminal_packet_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )
        archive = record["evidence"][0]
        self.assertEqual(archive["source"], "observations.md")
        self.assertEqual(writes[archive["archive"]], evidence.read_text(encoding="utf-8"))
        self.assertEqual(
            writes["improve/plan-test/receipt.md"],
            store.dumps(record, "ShipLoop standalone Improve receipt"),
        )
        self.assertIn("collect or cancel", record["stale_check_note"])
        self.assertIsNone(packet["next_argv"])
        self.assertIsNone(packet["done_argv"])
        self.assertIsNone(packet["report_schema"])
        self.assertEqual((record, writes), bridge.settle_incomplete(self.binding, submitted))

    def test_evidence_snapshot_keeps_archive_and_identity_equal_after_mutation(self) -> None:
        _packet, raw = self.stopped()
        evidence = self.write_evidence()
        self.save_packet(raw)
        submitted = self.receipt(evidence)
        original_read = bridge._read_workspace
        reads = {"evidence": 0}

        def read_then_mutate(workspace: Path, relative: Path, label: str) -> bytes:
            value = original_read(workspace, relative, label)
            if label == "incomplete Improve receipt evidence":
                reads["evidence"] += 1
                if reads["evidence"] == 1:
                    evidence.write_text("mutated after snapshot\n", encoding="utf-8")
            return value

        with mock.patch.object(bridge, "_read_workspace", side_effect=read_then_mutate):
            record, writes = bridge.settle_incomplete(self.binding, submitted)

        archive = record["evidence"][0]
        archived = writes[archive["archive"]]
        self.assertEqual(reads["evidence"], 1)
        self.assertEqual(archived, "Observed planning evidence.\n")
        self.assertEqual(evidence.read_text(encoding="utf-8"), "mutated after snapshot\n")
        self.assertEqual(archive["sha256"], hashlib.sha256(archived.encode("utf-8")).hexdigest())
        self.assertEqual(record["identities"]["evidence_sha256"][archive["source"]], archive["sha256"])

    def test_rejects_malformed_active_complete_and_missing_packets(self) -> None:
        evidence = self.write_evidence()
        submitted = self.receipt(evidence)

        active, active_raw = self.start()
        self.addCleanup(Path(active["state_file"]).unlink, missing_ok=True)
        self.save_packet(active_raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not stopped"):
            bridge.settle_incomplete(self.binding, submitted)

        stopped, stopped_raw = self.stopped()
        malformed = copy.deepcopy(stopped)
        malformed.pop("last_report")
        self.save_packet(json.dumps(malformed))
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "unsupported schema"):
            bridge.settle_incomplete(self.binding, submitted)

        complete, complete_raw = self.completed()
        self.save_packet(complete_raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not stopped"):
            bridge.settle_incomplete(self.binding, submitted)
        self.assertFalse(Path(complete["state_file"]).exists())

        path = bridge.receipt_path(self.binding)
        path.unlink()
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "unavailable"):
            bridge.settle_incomplete(self.binding, submitted)

    def test_rejects_foreign_binding_live_state_and_non_cancelled_stop(self) -> None:
        evidence = self.write_evidence()
        submitted = self.receipt(evidence)

        _foreign, foreign_raw = self.stopped(
            marker="ShipLoop standalone Improve binding: foreign/action",
        )
        self.save_packet(foreign_raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not bound"):
            bridge.settle_incomplete(self.binding, submitted)

        live, live_raw = self.stopped()
        state_path = Path(live["state_file"])
        state_path.write_text("still live", encoding="utf-8")
        self.addCleanup(state_path.unlink, missing_ok=True)
        self.save_packet(live_raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "remains present"):
            bridge.settle_incomplete(self.binding, submitted)

        _blocked, blocked_raw = self.stopped(continuation="blocked")
        self.save_packet(blocked_raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not cancelled"):
            bridge.settle_incomplete(self.binding, submitted)

    def test_rejects_linked_or_noncanonical_receipt_evidence_paths(self) -> None:
        packet, raw = self.stopped()
        evidence = self.write_evidence()
        submitted = self.receipt(evidence)
        packet_path = self.save_packet(raw)
        copied = self.workspace / "copied-packet.json"
        copied.write_text(raw, encoding="utf-8")
        packet_path.unlink()
        packet_path.symlink_to(copied)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "cannot be a symlink"):
            bridge.settle_incomplete(self.binding, submitted)

        packet_path.unlink()
        self.save_packet(raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "must be distinct"):
            bridge.settle_incomplete(self.binding, {
                **submitted,
                "evidence_refs": [str(evidence), str(evidence)],
            })
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        linked = self.workspace / "linked.md"
        linked.symlink_to(outside)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "cannot be a symlink"):
            bridge.settle_incomplete(self.binding, self.receipt(linked))

        hard_link = self.workspace / "hard-link.md"
        os.link(evidence, hard_link)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "single-link"):
            bridge.settle_incomplete(self.binding, self.receipt(hard_link))

        with self.assertRaisesRegex(bridge.StandaloneImproveError, "absolute local path"):
            bridge.settle_incomplete(self.binding, {
                **submitted,
                "evidence_refs": ["observations.md"],
            })
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "escapes its expected root"):
            bridge.settle_incomplete(self.binding, self.receipt(outside))
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "unsupported or missing"):
            bridge.settle_incomplete(self.binding, {**submitted, "review_refs": []})

        self.assertEqual(packet["status"], "stopped")

    def test_complete_remains_unavailable_for_a_stopped_packet(self) -> None:
        _packet, raw = self.stopped()
        self.save_packet(raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not complete"):
            bridge.complete(self.binding, {
                "summary": "Success must not be synthesized from a stopped child.",
                "review_refs": [],
                "check_refs": [],
            })

    def test_rejects_nonplan_and_durable_legacy_bindings(self) -> None:
        evidence = self.write_evidence()
        submitted = self.receipt(evidence)
        _packet, raw = self.stopped()
        self.save_packet(raw)
        nonplan = bridge.binding(self.state, "plan-test", "research", {}, self.skill)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "bound plan Improve child"):
            bridge.settle_incomplete(nonplan, submitted)

        root = self.workspace / "legacy-improve"
        runtime = root / "runtime" / "until-loop"
        scripts = runtime / "scripts"
        scripts.mkdir(parents=True)
        (root / "SKILL.md").write_text(
            "---\nname: improve\n---\nUse the bundled until-loop adapter.\n", encoding="utf-8",
        )
        (runtime / "ADAPTER.md").write_text(
            "---\nname: until-loop\n---\nUse the durable v2 adapter.\n", encoding="utf-8",
        )
        (scripts / "until-loop").write_text("#!/bin/sh\n", encoding="utf-8")
        with self.assertRaisesRegex(
            bridge.StandaloneImproveError,
            "durable Until Loop runtimes are no longer supported; select the current Improve card",
        ):
            bridge.resolve_skill(str(root / "SKILL.md"))
        # A saved binding that names a durable CLI is refused, not settled.
        stale = copy.deepcopy(self.binding)
        stale["skill"]["runtime_cli"] = str(scripts / "until-loop")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "differs from selected card"):
            bridge.settle_incomplete(stale, submitted)

    def test_saved_durable_improve_runtime_is_a_retired_run(self) -> None:
        # The Improve card is fixed at init, so a saved run bound to a durable
        # runtime is refused on every verb with the fresh-run route, not with
        # the init-only "select the current Improve card" advice.
        durable = copy.deepcopy(self.binding)
        durable["skill"]["runtime_cli"] = str(self.workspace / "runtime" / "scripts" / "until-loop")
        saved = {"navigator_protocol_version": 4, "active_improve": durable}
        reason = navigator.retired_run_reason(saved)
        self.assertEqual(reason, navigator.DURABLE_IMPROVE_REASON)
        self.assertIn(navigator.FRESH_RUN_HINT, reason)
        self.assertNotIn("select the current Improve card", reason)
        with self.assertRaisesRegex(navigator.NavigatorError, "retired durable Until Loop runtime"):
            navigator.validate(saved)
        current = {"navigator_protocol_version": 4, "active_improve": copy.deepcopy(self.binding)}
        self.assertIsNone(navigator.retired_run_reason(current))


if __name__ == "__main__":
    unittest.main()
