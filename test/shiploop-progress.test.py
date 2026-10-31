#!/usr/bin/env python3
"""Real file-observer/CLI tests; no browser or model-process claims."""
from __future__ import annotations

import errno
import fcntl
import http.client
import json
import os
from pathlib import Path
import re
import select
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as navigator
import shiploop_progress as progress
import shiploop_progress_serve as viewer
import shiploop_store as store

CLI = SCRIPTS / "shiploop"


class RunCase(unittest.TestCase):
    """A run directory with saved state, the CLI, and observers that are stopped at the end of each test."""

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

    def cli_ok(self, *args):
        """Run the CLI and require exit 0, showing its own output when it does not."""
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, f"{' '.join(args[2:])}: stdout={result.stdout!r} stderr={result.stderr!r}")
        return result

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


class ProgressTests(RunCase):
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
        first = self.cli_ok("view", "--run-dir", str(self.run), "--start", "--interval", ".1")
        self.wait_for(lambda: (self.run / progress.STATUS).is_file())
        identity = json.loads((self.run / progress.STATUS).read_text())["instance"]
        self.cli_ok("view", "--run-dir", str(self.run), "--start")
        self.assertEqual(identity, json.loads((self.run / progress.STATUS).read_text())["instance"])
        self.cli_ok("view", "--run-dir", str(self.run), "--stop")
        self.wait_for(lambda: not progress.running(self.run))
        with mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "watch"}):
            progress.ensure(self.run)
        self.assertFalse(progress.running(self.run))
        self.cli_ok("view", "--run-dir", str(self.run))
        self.assertEqual(json.loads((self.run / progress.STATUS).read_text())["status"], "snapshot")
        self.cli_ok("view", "--run-dir", str(self.run), "--start", "--interval", ".1")
        self.wait_for(lambda: json.loads((self.run / progress.STATUS).read_text())["instance"] != identity)

    def test_default_init_starts_observer_after_cli_exits(self):
        for path in self.run.iterdir():
            if path.is_file():
                path.unlink()
        # Existing navigator.save created directories; use a genuinely fresh run.
        self.run = self.base / "automatic #1? <run>"
        result = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run),
                          "--prompt", "Default progress creation", auto="watch")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.wait_for(lambda: self.page_contains("Default progress creation"))
        self.assertTrue(progress.running(self.run))
        link = next(line for line in result.stdout.splitlines()
                    if line.startswith("Progress view: "))
        target = link.split("[HTML file](<", 1)[1].split(">)", 1)[0]
        parsed = urlsplit(target)
        self.assertEqual(parsed.query, "")
        self.assertEqual(parsed.fragment, "")
        self.assertNotIn("<", target)
        self.assertNotIn(">", target)
        page = Path(unquote(parsed.path))
        self.assertEqual(page, self.run / "progress.html")
        self.assertTrue(page.is_file())

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


class ViewerTests(RunCase):
    """``view --serve``: the opt-in, read-only, loopback-only browser viewer."""

    def serve(self, *extra, run=None, command=None):
        """Start the viewer on a free port and return (process, port) once it has announced its address."""
        argv = command or [sys.executable, "-B", str(CLI), "view", "--run-dir", str(run or self.run), "--serve",
                           "--port", "0", "--interval", ".1", *extra]
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env={**os.environ, "SHIPLOOP_PROGRESS": "off"})
        self.processes.append(process)

        def stop():
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
        self.addCleanup(stop)
        ready, _, _ = select.select([process.stdout], [], [], 10)
        line = process.stdout.readline() if ready else ""
        match = re.search(r"^ShipLoop viewer: http://127\.0\.0\.1:(\d+)/ ", line)
        self.assertIsNotNone(match, f"announcement {line!r}; exit {process.poll()}")
        return process, int(match.group(1))

    def get(self, port, path="/", method="GET", host=None):
        """One request with the Host and the raw path as given; (status, lower-case headers, body)."""
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            connection.putheader("Host", host or f"127.0.0.1:{port}")
            connection.endheaders()
            response = connection.getresponse()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        finally:
            connection.close()

    def test_viewer_serves_the_published_pages_read_only(self):
        before = (self.run / "state.md").read_bytes()
        _, port = self.serve()
        self.wait_for(lambda: self.page_contains("Add a progress view"))
        status, headers, body = self.get(port)
        self.assertEqual(status, 200)
        self.assertIn(b"Add a progress view", body)
        self.assertEqual(headers["content-type"], "text/html; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("default-src 'none'", headers["content-security-policy"])
        self.assertEqual(self.get(port, "/progress.html")[2], body)
        status, headers, empty = self.get(port, method="HEAD")
        self.assertEqual((status, empty), (200, b""))
        self.assertEqual(int(headers["content-length"]), len(body))
        # The observer publishes the trace page; the report appears only when the run ends.
        self.assertEqual(self.get(port, "/trace.html")[0], 200)
        self.assertEqual(self.get(port, "/report.html")[0], 404)
        (self.run / "report.html").write_text("<p>report page</p>")
        self.assertEqual(self.get(port, "/report.html")[2], b"<p>report page</p>")
        # Nothing else in the run directory is reachable, however the path is spelled.
        for path in ("/state.md", "/../state.md", "/%2e%2e/state.md", "/progress-observer.json", "/notes/", "//state.md",
                     "/progress.html/"):
            with self.subTest(path=path):
                self.assertEqual(self.get(port, path)[0], 404)
        # It never accepts a change.
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            with self.subTest(method=method):
                status, headers, _ = self.get(port, "/", method=method)
                self.assertEqual((status, headers["allow"]), (405, "GET, HEAD"))
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_viewer_refuses_a_request_for_a_name_other_than_its_own(self):
        _, port = self.serve()
        self.wait_for(lambda: self.page_contains("Add a progress view"))
        # A page on another site that resolves its own name to 127.0.0.1 must not read the run.
        for host in ("evil.example", f"evil.example:{port}", "127.0.0.1", f"127.0.0.1:{port + 1}"):
            with self.subTest(host=host):
                self.assertEqual(self.get(port, host=host)[0], 403)
        self.assertEqual(self.get(port, host=f"localhost:{port}")[0], 200)

    def test_viewer_refuses_a_page_that_is_a_link_or_has_another_name(self):
        outside = self.base / "outside"
        outside.write_text("secret outside the run")
        (self.run / progress.PAGE).symlink_to(outside)
        os.link(outside, self.run / "report.html")
        _, port = self.serve()
        for path in ("/", "/progress.html", "/report.html"):
            with self.subTest(path=path):
                status, _, body = self.get(port, path)
                self.assertEqual(status, 403)
                self.assertNotIn(b"secret", body)

    def test_viewer_listens_on_loopback_only(self):
        server = viewer.bind(self.run, 0)
        self.addCleanup(server.server_close)
        self.assertEqual(server.server_address[0], "127.0.0.1")

    def test_default_port_is_stable_per_run_and_moves_on_when_taken(self):
        port = viewer.default_port(Path("/runs/a"))
        self.assertEqual(port, viewer.default_port(Path("/runs/a")))
        self.assertNotEqual(port, viewer.default_port(Path("/runs/b")))
        self.assertTrue(viewer.PORT_BASE <= port < viewer.PORT_BASE + viewer.PORT_SPAN)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            taken = probe.getsockname()[1]
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", taken))
            holder.listen(1)
            with mock.patch.object(viewer, "default_port", return_value=taken):
                server = viewer.bind(self.run, None)
            self.addCleanup(server.server_close)
            self.assertTrue(taken < server.server_address[1] <= taken + viewer.PORT_TRIES)
            with self.assertRaises(OSError) as refused:
                viewer.bind(self.run, taken)  # an explicit port is taken as given
            self.assertEqual(refused.exception.errno, errno.EADDRINUSE)

    def test_interrupt_ends_the_viewer_and_frees_its_port(self):
        lines = []
        with mock.patch.object(viewer._Server, "serve_forever", side_effect=KeyboardInterrupt):
            self.assertEqual(viewer.serve(self.run, port=0, out=lines.append), 0)
        match = re.search(r"^ShipLoop viewer: http://127\.0\.0\.1:(\d+)/ \(read-only", lines[0])
        self.assertIsNotNone(match, lines)
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", int(match.group(1))), timeout=2).close()

    def test_port_belongs_to_serve_and_must_be_a_port(self):
        for args in (("--port", "1"), ("--start", "--serve"), ("--serve", "--port", "70000"), ("--serve", "--port", "-1")):
            with self.subTest(args=args):
                result = self.cli("view", "--run-dir", str(self.run), *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(progress.running(self.run))

    def test_serving_restarts_observation_after_it_was_stopped(self):
        self.cli_ok("view", "--run-dir", str(self.run), "--start", "--interval", ".1")
        self.cli_ok("view", "--run-dir", str(self.run), "--stop")
        self.wait_for(lambda: not progress.running(self.run))
        self.assertTrue((self.run / progress.DISABLED).exists())
        self.serve()
        self.wait_for(lambda: progress.running(self.run))
        self.assertFalse((self.run / progress.DISABLED).exists())

    def test_serving_a_finished_run_shows_what_it_published_and_starts_no_observer(self):
        self.cli_ok("halt", "--run-dir", str(self.run), "--reason", "Synthetic terminal test")
        _, port = self.serve()
        status, _, body = self.get(port)
        self.assertEqual((status, body), (404, b"progress.html is not published yet\n"))
        self.assertFalse((self.run / progress.LOCK).exists())

    def test_first_packet_suggests_a_command_that_serves_the_run(self):
        self.run = self.base / "suggested run"
        result = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run), "--prompt", "Serve this run")
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(line for line in result.stdout.splitlines() if line.startswith("Progress view: "))
        self.assertIn("do not run it yourself", line)
        argv = shlex.split(line.split("it serves until stopped): ", 1)[1])
        self.assertEqual((argv[0], argv[2], argv[-1]), ("python3", "view", "--serve"))
        self.assertEqual(argv[3], f"--run-dir={self.run}")
        _, port = self.serve(command=[sys.executable, "-B", *argv[1:], "--port", "0", "--interval", ".1"])
        self.wait_for(lambda: self.page_contains("Serve this run"))
        self.assertIn(b"Serve this run", self.get(port)[2])

    def test_later_packets_do_not_repeat_the_command(self):
        first = navigator._progress_view_line(None, self.run, self.state)
        self.assertIn("view --run-dir=", first)
        self.assertTrue(first.startswith("Progress view: [HTML file](<"))
        accepted = navigator.apply(self.state, navigator.current_action(self.state)["id"],
                                   {"outcome": "done", "summary": "Scope accepted for the viewer."})
        later = navigator._progress_view_line(None, self.run, accepted)
        self.assertEqual(first.split(" To follow it in a browser", 1)[0], later)
        self.assertNotIn("--serve", later)


if __name__ == "__main__":
    unittest.main()
