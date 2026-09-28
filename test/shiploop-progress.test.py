#!/usr/bin/env python3
"""Real file-observer/CLI tests; no browser or model-process claims."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as navigator
import shiploop_progress as progress
import shiploop_store as store
from shiploop_chain_support import ChainFixture

CLI = SCRIPTS / "shiploop"


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-progress-runtime-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        self.run = self.base / "run"
        self.run.mkdir()
        (self.run / ".lock").touch()
        self.state = navigator.new_state(str(self.repo), "Add a progress view", improve_skill="")
        navigator.save(self.run, self.state)
        self.processes = []
        self.addCleanup(self.cleanup_observers)

    def cleanup_observers(self):
        if self.run.exists():
            progress.stop(self.run)
            deadline = time.monotonic() + 5
            while progress.running(self.run) and time.monotonic() < deadline:
                time.sleep(.05)
        for process in self.processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)

    def cli(self, *args, auto="off"):
        return subprocess.run([sys.executable, "-B", str(CLI), *args],
                              capture_output=True, text=True, timeout=15,
                              env={**os.environ, "SHIPLOOP_PROGRESS": auto,
                                   "PYTHONDONTWRITEBYTECODE": "1"})

    def wait_for(self, predicate, timeout=6):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.05)
        self.fail("observer did not reach expected file state within deadline")

    def page_contains(self, text):
        page = self.run / progress.PAGE
        return page.exists() and text in page.read_text()

    def watch(self):
        process = subprocess.Popen([sys.executable, "-B", str(CLI), "view", "--run-dir", str(self.run),
                                    "--watch", "--interval", ".1", "--idle-timeout", "10"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   env={**os.environ, "SHIPLOOP_PROGRESS": "off"})
        self.processes.append(process)
        self.wait_for(lambda: (self.run / progress.PAGE).is_file())
        return process

    def test_snapshot_is_portable_and_does_not_change_authority(self):
        before = (self.run / "state.md").read_bytes()
        result = self.cli("view", "--run-dir", str(self.run))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.page_contains("Add a progress view"))
        self.assertEqual(before, (self.run / "state.md").read_bytes())
        self.assertFalse((self.run / "report.html").exists())
        self.assertFalse(progress.running(self.run))

    def test_open_observer_updates_document_between_transitions(self):
        docs = self.repo / "docs"
        docs.mkdir()
        architecture = docs / "ARCHITECTURE.md"
        architecture.write_text("# Architecture\nFirst design text")
        before = (self.run / "state.md").read_bytes()
        self.watch()
        self.wait_for(lambda: self.page_contains("First design text"))
        store.atomic_write_text(architecture, "# Architecture\nRevised design while parent is parked")
        self.wait_for(lambda: self.page_contains("Revised design while parent is parked"))
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_observer_updates_accepted_transition(self):
        self.watch()
        self.state = navigator.apply(self.state, navigator.current_action(self.state)["id"],
                                     {"outcome": "done", "summary": "Scope accepted for the progress page."})
        with (self.run / ".lock").open() as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            navigator.save(self.run, self.state)
        self.wait_for(lambda: self.page_contains("Scope accepted for the progress page."))

    def test_pending_transaction_is_never_recovered(self):
        journal = self.run / "transaction.md"
        journal.write_text("An interrupted transaction must belong to ShipLoop")
        before = (self.run / "state.md").read_bytes()
        result = self.cli("view", "--run-dir", str(self.run))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(journal.read_text(), "An interrupted transaction must belong to ShipLoop")
        self.assertEqual(before, (self.run / "state.md").read_bytes())
        self.assertFalse((self.run / progress.PAGE).exists())

    def test_busy_lock_skips_without_blocking(self):
        with (self.run / ".lock").open() as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            started = time.monotonic()
            result = self.cli("view", "--run-dir", str(self.run))
            self.assertEqual(result.returncode, 2)
            self.assertLess(time.monotonic() - started, 3)

    def test_duplicate_start_and_cooperative_stop_then_restart(self):
        first = self.cli("view", "--run-dir", str(self.run), "--start", "--interval", ".1")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.wait_for(lambda: (self.run / progress.STATUS).is_file())
        identity = json.loads((self.run / progress.STATUS).read_text())["instance"]
        second = self.cli("view", "--run-dir", str(self.run), "--start")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(identity, json.loads((self.run / progress.STATUS).read_text())["instance"])
        self.assertEqual(self.cli("view", "--run-dir", str(self.run), "--stop").returncode, 0)
        self.wait_for(lambda: not progress.running(self.run))
        with mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "watch"}):
            progress.ensure(self.run)
        self.assertFalse(progress.running(self.run))
        self.assertEqual(self.cli("view", "--run-dir", str(self.run)).returncode, 0)
        self.assertEqual(json.loads((self.run / progress.STATUS).read_text())["status"], "snapshot")
        self.assertEqual(self.cli("view", "--run-dir", str(self.run), "--start", "--interval", ".1").returncode, 0)
        self.wait_for(lambda: json.loads((self.run / progress.STATUS).read_text())["instance"] != identity)

    def test_default_init_starts_observer_after_cli_exits(self):
        for path in self.run.iterdir():
            if path.is_file():
                path.unlink()
        # Existing navigator.save created directories; use a genuinely fresh run.
        self.run = self.base / "automatic run"
        result = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run),
                          "--prompt", "Default progress creation", auto="watch")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.wait_for(lambda: self.page_contains("Default progress creation"))
        self.assertTrue(progress.running(self.run))
        self.assertIn("progress.html", result.stdout)

    def test_terminal_snapshot_reconciles_and_stops(self):
        process = self.watch()
        result = self.cli("halt", "--run-dir", str(self.run), "--reason", "Synthetic terminal test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.wait_for(lambda: process.poll() is not None)
        self.assertTrue(self.page_contains("Synthetic terminal test"))
        self.assertEqual(json.loads((self.run / progress.STATUS).read_text())["status"], "final")
        self.assertTrue((self.run / "report.html").is_file())

    def test_failed_render_preserves_last_good_file(self):
        self.assertEqual(progress.observe(self.run, watch=False), 0)
        before = (self.run / progress.PAGE).read_bytes()
        with mock.patch("shiploop_progress_render.render", side_effect=ValueError("synthetic renderer failure")):
            self.assertEqual(progress.observe(self.run, watch=False), 2)
        self.assertEqual(before, (self.run / progress.PAGE).read_bytes())

    def test_restarted_observer_replaces_stale_status_before_start_succeeds(self):
        self.assertEqual(progress.observe(self.run, watch=False), 0)
        old = json.loads((self.run / progress.STATUS).read_text())["instance"]
        (self.repo / "ARCHITECTURE.md").write_text("A newly saved architecture draft")
        self.assertTrue(progress.start(self.run, interval=.1))
        record = json.loads((self.run / progress.STATUS).read_text())
        self.assertNotEqual(record["instance"], old)
        self.assertTrue(self.page_contains("A newly saved architecture draft"))

    def test_terminal_one_shot_remains_a_snapshot(self):
        result = self.cli("halt", "--run-dir", str(self.run), "--reason", "stop fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        with mock.patch("shiploop_progress.publish", wraps=progress.publish) as publish:
            self.assertEqual(progress.observe(self.run, watch=False), 0)
            self.assertFalse(publish.call_args.kwargs["final"])
        self.assertEqual(json.loads((self.run / progress.STATUS).read_text())["status"], "snapshot")

    def test_failed_shutdown_render_still_records_stop(self):
        real_publish = progress.publish
        calls = 0
        def publish(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise ValueError("cannot render stopped page")
            real_publish(*args, **kwargs)
        with mock.patch("shiploop_progress.publish", side_effect=publish):
            progress.observe(self.run, watch=True, interval=.1, idle_timeout=.1)
        record = json.loads((self.run / progress.STATUS).read_text())
        self.assertIn("final display publication failed", record["status"])
        self.assertIn("stopped_at", record)
        self.assertFalse(progress.running(self.run))

    def test_progress_output_symlink_cannot_overwrite_target(self):
        target = self.base / "outside"
        target.write_text("preserve")
        (self.run / progress.PAGE).symlink_to(target)
        result = self.cli("view", "--run-dir", str(self.run))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(target.read_text(), "preserve")

    def test_missing_run_and_bad_intervals_are_refused(self):
        missing = self.base / "missing"
        self.assertEqual(self.cli("view", "--run-dir", str(missing)).returncode, 2)
        self.assertFalse(missing.exists())
        for interval in ("0", "nan", "inf", "-1"):
            result = self.cli("view", "--run-dir", str(self.run), "--interval", interval)
            self.assertNotEqual(result.returncode, 0)

    def test_status_does_not_create_or_recover_files(self):
        before = sorted(str(p.relative_to(self.run)) for p in self.run.rglob("*"))
        result = self.cli("view", "--run-dir", str(self.run), "--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["running"])
        self.assertEqual(before, sorted(str(p.relative_to(self.run)) for p in self.run.rglob("*")))


class ProgressChainTests(ChainFixture):
    def test_legacy_child_status_is_unknown_and_revised_plan_retires_old_graph(self):
        import shiploop_progress_data as data

        self.bind()
        legacy = self.child_state_path().with_name("state.json")
        legacy.write_text("{}")
        before = self.run_bytes()
        snapshot = data.build_snapshot(self.run)
        graph = next(row for row in snapshot["graphs"] if row.get("edges"))
        self.assertTrue(all(node["status"] == "unknown" for node in graph["nodes"]))
        self.assertEqual(before, self.run_bytes())
        legacy.unlink()
        child_path = self.child_state_path()
        child_bytes = child_path.read_bytes()
        child = json.loads(child_bytes)
        child["graph_sha256"] = "0" * 64
        child_path.write_text(json.dumps(child))
        mismatched = data.build_snapshot(self.run)
        graph = next(row for row in mismatched["graphs"] if row.get("edges"))
        self.assertTrue(all(node["status"] == "unknown" for node in graph["nodes"]))
        self.assertTrue(any("identity or state mismatch" in message for message in mismatched["warnings"]))
        child_path.write_bytes(child_bytes)
        state = store.loads((self.run / "state.md").read_text())
        revised = navigator.apply(state, self.action, {"outcome": "revise", "summary": "Replan the implementation."})
        navigator.save(self.run, revised)
        after = data.build_snapshot(self.run)
        self.assertFalse(any(row["id"] == self.action for row in after["graphs"]))

    def test_real_dispatcher_graph_updates_while_parent_action_is_parked(self):
        import shiploop_progress_data as data

        self.bind()
        parent_before = (self.run / "state.md").read_bytes()
        first = data.build_snapshot(self.run)
        graph = next(row for row in first["graphs"] if row.get("edges"))
        self.assertEqual({(edge["from"], edge["to"]) for edge in graph["edges"]},
                         {("A", "C"), ("B", "J"), ("C", "J")})
        def cleanup():
            progress.stop(self.run)
            deadline = time.monotonic() + 5
            while progress.running(self.run) and time.monotonic() < deadline:
                time.sleep(.05)
        self.addCleanup(cleanup)
        self.assertTrue(progress.start(self.run, interval=.1))
        page_before = (self.run / progress.PAGE).read_bytes()
        self.claim(["A"])
        after = data.build_snapshot(self.run)
        graph = next(row for row in after["graphs"] if row.get("edges"))
        self.assertEqual(next(row for row in graph["nodes"] if row["id"] == "A")["status"], "claimed")
        self.assertNotEqual(first["source_fingerprint"], after["source_fingerprint"])
        self.assertEqual(parent_before, (self.run / "state.md").read_bytes())
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            page = (self.run / progress.PAGE).read_bytes()
            if page != page_before and b"claimed" in page.lower():
                break
            time.sleep(.05)
        else:
            self.fail("observer did not publish the real dispatcher step transition")
        self.assertIn(b"Implement A", page)
        self.assertIn(b"Implement J", page)


if __name__ == "__main__":
    unittest.main()
