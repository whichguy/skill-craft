#!/usr/bin/env python3
"""Focused contract tests for immutable ShipLoop chain-ledger events."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
MODULE_PATH = SCRIPTS / "shiploop_chain_ledger.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "shiploop_chain_ledger_under_test", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
ledger = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ledger
SPEC.loader.exec_module(ledger)

import shiploop_store as store


RECORDED = "2026-09-18T12:00:00Z"
OCCURRED_EARLY = "2026-09-18T11:00:00Z"
OCCURRED_LATE = "2026-09-18T13:00:00Z"


class ShipLoopChainLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-chain-ledger-")
        self.addCleanup(self.temp.cleanup)
        # macOS /var is a system symlink, so use the physical fixture path.
        self.root = Path(self.temp.name).resolve()
        self.ledger_dir = self.root / "chain"

    def append(
        self,
        event_id: str,
        *,
        kind: str = "bridge-intent",
        data: dict | None = None,
        occurred_at: str | None = None,
        recorded_at: str | None = RECORDED,
    ) -> dict:
        return ledger.append_event(
            self.ledger_dir,
            event_id,
            kind,
            {} if data is None else data,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
        )

    def render(self, event: dict) -> str:
        return store.dumps(event, title=f"ShipLoop chain event {event['seq']}")

    def test_cold_read_and_append_use_canonical_markdown(self) -> None:
        self.assertEqual(ledger.read_events(self.ledger_dir), [])

        row = self.append(
            "intent-1",
            data={"action": "bridge", "attempt": 1},
            occurred_at=OCCURRED_EARLY,
        )
        event = row["event"]
        path = Path(row["path"])

        self.assertEqual(path.name, "00000001-intent-1.md")
        self.assertEqual(event["schema"], ledger.EVENT_SCHEMA)
        self.assertEqual(event["seq"], 1)
        self.assertEqual(event["previous_sha256"], None)
        self.assertEqual(event["recorded_at"], RECORDED)
        self.assertEqual(event["occurred_at"], OCCURRED_EARLY)
        self.assertEqual(path.read_text(encoding="utf-8"), self.render(event))
        self.assertEqual(
            row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
        )
        self.assertEqual(ledger.read_events(self.ledger_dir), [row])

    def test_idempotent_replay_preserves_original_bytes_and_conflicts_fail(self) -> None:
        first = self.append(
            "receipt-1",
            kind="bridge-receipt",
            data={"status": "accepted"},
            occurred_at=OCCURRED_EARLY,
            recorded_at=None,
        )
        path = Path(first["path"])
        before = path.read_bytes()

        replay = self.append(
            "receipt-1",
            kind="bridge-receipt",
            data={"status": "accepted"},
            occurred_at=OCCURRED_EARLY,
            recorded_at=None,
        )
        self.assertEqual(replay, first)
        self.assertEqual(path.read_bytes(), before)

        with self.assertRaises(ledger.LedgerError):
            self.append(
                "receipt-1",
                kind="bridge-receipt",
                data={"status": "changed"},
                occurred_at=OCCURRED_EARLY,
            )
        with self.assertRaises(ledger.LedgerError):
            self.append(
                "receipt-1",
                kind="other-kind",
                data={"status": "accepted"},
                occurred_at=OCCURRED_EARLY,
            )
        with self.assertRaises(ledger.LedgerError):
            self.append(
                "receipt-1",
                kind="bridge-receipt",
                data={"status": "accepted"},
                occurred_at=OCCURRED_LATE,
            )
        with self.assertRaises(ledger.LedgerError):
            self.append(
                "receipt-1",
                kind="bridge-receipt",
                data={"status": "accepted"},
                occurred_at=OCCURRED_EARLY,
                recorded_at=RECORDED,
            )

    def test_corruption_gap_and_duplicate_ids_fail_closed(self) -> None:
        first = self.append("first", data={"value": 1})
        self.append("second", data={"value": 2})
        first_path = Path(first["path"])
        corrupted = dict(first["event"])
        corrupted["data"] = {"value": "changed"}
        first_path.write_text(self.render(corrupted), encoding="utf-8")
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)

        gap = self.root / "gap"
        gap.mkdir()
        gap_event = {
            "schema": ledger.EVENT_SCHEMA,
            "seq": 3,
            "event_id": "third",
            "kind": "bridge-intent",
            "recorded_at": RECORDED,
            "previous_sha256": None,
            "data": {},
        }
        (gap / "00000003-third.md").write_text(
            self.render(gap_event), encoding="utf-8"
        )
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(gap)

        duplicate = self.root / "duplicate"
        duplicate.mkdir()
        first_event = {
            "schema": ledger.EVENT_SCHEMA,
            "seq": 1,
            "event_id": "same-id",
            "kind": "bridge-intent",
            "recorded_at": RECORDED,
            "previous_sha256": None,
            "data": {"first": True},
        }
        first_duplicate_path = duplicate / "00000001-same-id.md"
        first_duplicate_path.write_text(self.render(first_event), encoding="utf-8")
        first_digest = hashlib.sha256(first_duplicate_path.read_bytes()).hexdigest()
        second_event = {
            "schema": ledger.EVENT_SCHEMA,
            "seq": 2,
            "event_id": "same-id",
            "kind": "bridge-receipt",
            "recorded_at": RECORDED,
            "previous_sha256": first_digest,
            "data": {"second": True},
        }
        (duplicate / "00000002-same-id.md").write_text(
            self.render(second_event), encoding="utf-8"
        )
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(duplicate)

    def test_symlinks_and_multi_link_entries_are_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        linked_directory = self.root / "linked-directory"
        linked_directory.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(linked_directory)

        row = self.append("safe-entry", data={"safe": True})
        path = Path(row["path"])
        alias = self.root / "external-hardlink.md"
        os.link(path, alias)
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)

        alias.unlink()
        path.unlink()
        sentinel = outside / "sentinel.md"
        sentinel.write_text("outside\n", encoding="utf-8")
        path.symlink_to(sentinel)
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)

    def test_timestamp_skew_and_ties_do_not_change_append_order(self) -> None:
        first = self.append(
            "later-occurrence",
            data={"order": "first"},
            occurred_at=OCCURRED_LATE,
        )
        second = self.append(
            "earlier-occurrence",
            data={"order": "second"},
            occurred_at=OCCURRED_EARLY,
        )
        third = self.append(
            "same-timestamps",
            data={"order": "third"},
            occurred_at=OCCURRED_EARLY,
        )
        rows = ledger.read_events(self.ledger_dir)

        self.assertEqual([row["event"]["seq"] for row in rows], [1, 2, 3])
        self.assertEqual(
            [row["event"]["event_id"] for row in rows],
            ["later-occurrence", "earlier-occurrence", "same-timestamps"],
        )
        self.assertEqual(
            [row["event"]["recorded_at"] for row in rows],
            [RECORDED, RECORDED, RECORDED],
        )
        self.assertEqual(
            [row["event"]["occurred_at"] for row in rows],
            [OCCURRED_LATE, OCCURRED_EARLY, OCCURRED_EARLY],
        )
        self.assertEqual(second["event"]["previous_sha256"], first["sha256"])
        self.assertEqual(third["event"]["previous_sha256"], second["sha256"])

    def test_only_own_regular_temporary_files_are_ignored(self) -> None:
        self.ledger_dir.mkdir()
        temporary = self.ledger_dir / ".shiploop-chain-ledger-crash.tmp"
        temporary.write_text("not published\n", encoding="utf-8")
        self.assertEqual(ledger.read_events(self.ledger_dir), [])
        self.append("after-temp")
        self.assertEqual(len(ledger.read_events(self.ledger_dir)), 1)

        temporary.unlink()
        temporary.symlink_to(self.root / "outside-temp")
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)

    def test_recovery_refuses_an_unmatched_private_hardlink(self) -> None:
        self.ledger_dir.mkdir()
        outside = self.root / "outside-hardlink.md"
        outside.write_text("outside\n", encoding="utf-8")
        temporary = self.ledger_dir / ".shiploop-chain-ledger-unmatched.tmp"
        os.link(outside, temporary)

        with self.assertRaises(ledger.LedgerError):
            ledger.recover_pending_temporary(self.ledger_dir)
        self.assertTrue(temporary.exists())
        self.assertTrue(outside.exists())
        self.assertEqual(os.stat(temporary).st_nlink, 2)

    def test_append_recovers_only_an_exact_pending_temporary_pair(self) -> None:
        first = self.append("before-recovery", data={"state": "first"})
        temporary = self.ledger_dir / ".shiploop-chain-ledger-pending.tmp"
        os.link(Path(first["path"]), temporary)
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)

        second = self.append("after-recovery", data={"state": "second"})
        rows = ledger.read_events(self.ledger_dir)
        self.assertEqual(
            [row["event"]["event_id"] for row in rows],
            ["before-recovery", "after-recovery"],
        )
        self.assertEqual(second["event"]["seq"], 2)
        self.assertFalse(temporary.exists())
        self.assertEqual(os.stat(Path(first["path"])).st_nlink, 1)

    def test_competing_processes_serialized_by_external_fcntl_lock(self) -> None:
        child = textwrap.dedent(
            f"""
            import fcntl
            import json
            from pathlib import Path
            import sys
            import time

            sys.path.insert(0, {str(SCRIPTS)!r})
            import shiploop_chain_ledger as ledger

            directory = Path(sys.argv[1])
            event_id = sys.argv[2]
            lock_path = directory.parent / ".caller.lock"
            with lock_path.open("a+b") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                if event_id == "process-a":
                    time.sleep(0.2)
                row = ledger.append_event(
                    directory,
                    event_id,
                    "bridge-receipt",
                    {{"worker": event_id}},
                    recorded_at="2026-09-18T12:00:00Z",
                )
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            print(json.dumps({{"event_id": row["event"]["event_id"], "seq": row["event"]["seq"]}}))
            """
        )
        first = subprocess.Popen(
            [sys.executable, "-B", "-c", child, str(self.ledger_dir), "process-a"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.05)
        second = subprocess.Popen(
            [sys.executable, "-B", "-c", child, str(self.ledger_dir), "process-b"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first_stdout, first_stderr = first.communicate(timeout=10)
        second_stdout, second_stderr = second.communicate(timeout=10)
        self.assertEqual(first.returncode, 0, first_stderr)
        self.assertEqual(second.returncode, 0, second_stderr)
        results = {json.loads(first_stdout)["event_id"], json.loads(second_stdout)["event_id"]}
        self.assertEqual(results, {"process-a", "process-b"})
        rows = ledger.read_events(self.ledger_dir)
        self.assertEqual([row["event"]["seq"] for row in rows], [1, 2])
        self.assertEqual(
            {row["event"]["event_id"] for row in rows},
            {"process-a", "process-b"},
        )

    @unittest.skipUnless(hasattr(signal, "SIGKILL"), "requires POSIX SIGKILL")
    def test_kill_after_hardlink_requires_bounded_temporary_recovery(self) -> None:
        child = textwrap.dedent(
            f"""
            import os
            from pathlib import Path
            import signal
            import sys

            sys.path.insert(0, {str(SCRIPTS)!r})
            import shiploop_chain_ledger as ledger

            original_unlink = ledger.os.unlink

            def kill_before_temp_unlink(path, *args, **kwargs):
                if Path(path).name.startswith(ledger._TEMP_PREFIX):
                    os.kill(os.getpid(), signal.SIGKILL)
                return original_unlink(path, *args, **kwargs)

            ledger.os.unlink = kill_before_temp_unlink
            ledger.append_event(
                Path(sys.argv[1]),
                "killed-entry",
                "bridge-intent",
                {{"kill": True}},
                recorded_at="2026-09-18T12:00:00Z",
            )
            """
        )
        process = subprocess.run(
            [sys.executable, "-B", "-c", child, str(self.ledger_dir)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
        self.assertTrue((self.ledger_dir / "00000001-killed-entry.md").exists())
        self.assertTrue(
            any(
                path.name.startswith(".shiploop-chain-ledger-")
                for path in self.ledger_dir.iterdir()
            )
        )
        with self.assertRaises(ledger.LedgerError):
            ledger.read_events(self.ledger_dir)
        self.assertTrue(ledger.recover_pending_temporary(self.ledger_dir))
        self.assertFalse(ledger.recover_pending_temporary(self.ledger_dir))
        rows = ledger.read_events(self.ledger_dir)
        self.assertEqual([row["event"]["event_id"] for row in rows], ["killed-entry"])
        self.assertEqual(
            os.stat(self.ledger_dir / "00000001-killed-entry.md").st_nlink, 1
        )
        self.assertFalse(
            any(
                path.name.startswith(".shiploop-chain-ledger-")
                for path in self.ledger_dir.iterdir()
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
