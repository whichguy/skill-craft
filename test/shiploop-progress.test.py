#!/usr/bin/env python3
"""Real file-observer/CLI tests; no browser or model-process claims."""
from __future__ import annotations

import errno
import contextlib
import fcntl
import http.client
import io
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
        self.state_home = self.base / "state-home"
        env_patch = mock.patch.dict(os.environ, {
            "SHIPLOOP_STATE_HOME": str(self.state_home),
            "XDG_STATE_HOME": str(self.state_home),
        })
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
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
            observed = predicate()
            if observed:
                return observed
            time.sleep(.05)
        self.fail("observer did not reach expected file state within deadline")

    def page_contains(self, text):
        page = self.run / progress.PAGE
        return page.exists() and text in page.read_text()

    def start_observer(self):
        """Start once, then establish that the new observer actually published."""
        self.assertFalse(progress.running(self.run), "fresh start requires a stopped observer")
        status = self.run / progress.STATUS
        previous = json.loads(status.read_text())["instance"] if status.is_file() else None
        result = self.cli("view", "--run-dir", str(self.run), "--start", "--interval", ".1")
        # The CLI's bounded startup check can return before its detached child publishes.
        unconfirmed = (result.returncode == 2 and result.stdout == f"{self.run / progress.PAGE}\n"
                       and not result.stderr)
        self.assertTrue(result.returncode == 0 or unconfirmed,
                        f"view --start exit={result.returncode}: stdout={result.stdout!r} stderr={result.stderr!r}")

        def fresh_instance():
            if not status.is_file():
                return None
            record = json.loads(status.read_text())
            instance = record["instance"]
            if (instance and instance != previous and record["status"] == "watching"
                    and progress.running(self.run) and self.page_contains('data-mode="watch"')):
                return instance
            return None

        return self.wait_for(fresh_instance)

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
        identity = self.start_observer()
        self.cli_ok("view", "--run-dir", str(self.run), "--start")
        self.assertEqual(identity, json.loads((self.run / progress.STATUS).read_text())["instance"])
        self.cli_ok("view", "--run-dir", str(self.run), "--stop")
        self.wait_for(lambda: not progress.running(self.run))
        with mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "watch"}):
            progress.ensure(self.run)
        self.assertFalse(progress.running(self.run))
        self.cli_ok("view", "--run-dir", str(self.run))
        self.assertEqual(json.loads((self.run / progress.STATUS).read_text())["status"], "snapshot")
        self.assertNotEqual(self.start_observer(), identity)

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
        before = [(self.run / name).read_bytes() for name in (progress.PAGE, progress.CONTENT)]
        with mock.patch("shiploop_progress_render.render_main", side_effect=ValueError("synthetic renderer failure")):
            self.assertEqual(progress.observe(self.run, watch=False), 2)
        self.assertEqual(before, [(self.run / name).read_bytes() for name in (progress.PAGE, progress.CONTENT)])

    def test_one_snapshot_writes_the_page_its_content_script_and_the_version_script(self):
        self.assertEqual(progress.observe(self.run, watch=False), 0)
        page = (self.run / progress.PAGE).read_text()
        call = "window.__shiploopProgress&&window.__shiploopProgress("
        content = (self.run / progress.CONTENT).read_text()
        self.assertTrue(content.startswith(call) and content.endswith(");\n"))
        content = json.loads(content[len(call):-3])
        self.assertEqual(sorted(content), ["main", "title", "version"])
        # The content script carries exactly the <main> the page holds, so an open page ends up where a fresh
        # load would.
        self.assertIn(content["main"], page)
        self.assertIn('data-version="' + content["version"] + '"', content["main"])
        call = "window.__shiploopVersion&&window.__shiploopVersion("
        version = (self.run / progress.VERSION).read_text()
        self.assertTrue(version.startswith(call) and version.endswith(");\n"))
        version = json.loads(version[len(call):-3])
        self.assertEqual(version["schema"], "shiploop-progress-version/v1")
        self.assertEqual(version["progress"], content["version"])
        self.assertEqual(version["status"], "snapshot")
        self.assertEqual(version["observed_at"], json.loads((self.run / progress.STATUS).read_text())["observed_at"])
        import shiploop_trace as trace
        self.assertTrue(version["trace"])
        self.assertIn('"version":"' + version["trace"] + '"', (self.run / trace.CONTENT).read_text())

    def test_the_page_version_ignores_the_observer_clock_and_follows_what_the_page_shows(self):
        key = progress.page_key("source", "watch", False, "", "ok")
        self.assertEqual(key, progress.page_key("source", "watch", False, "", "ok"))
        for other in (("other", "watch", False, "", "ok"), ("source", "snapshot", False, "", "ok"),
                      ("source", "watch", True, "", "ok"), ("source", "watch", False, "failed", "ok"),
                      ("source", "watch", False, "", "unavailable")):
            self.assertNotEqual(key, progress.page_key(*other))
        # A "<" cannot end the script element of a page that inlines the same payload.
        self.assertNotIn("<", progress._call("__shiploopProgress", {"main": "<main></main>"}))

    def test_restarted_observer_replaces_stale_status_before_start_succeeds(self):
        self.assertEqual(progress.observe(self.run, watch=False), 0)
        old = json.loads((self.run / progress.STATUS).read_text())["instance"]
        old_page = (self.run / progress.PAGE).read_bytes()
        (self.repo / "ARCHITECTURE.md").write_text("A newly saved architecture draft")
        real_popen = subprocess.Popen
        instance = None

        def retain_process(*args, **kwargs):
            nonlocal instance
            command = args[0]
            instance = command[command.index("--instance") + 1]
            process = real_popen(*args, **kwargs)
            self.processes.append(process)
            return process

        # Keep the real child handle until cleanup stops the observer and waits for it.
        with mock.patch.object(progress.subprocess, "Popen", side_effect=retain_process):
            started = progress.start(self.run, interval=.1)
        self.assertEqual(len(self.processes), 1)
        process = self.processes[0]
        self.assertTrue(instance)

        def fresh_publication():
            record = json.loads((self.run / progress.STATUS).read_text())
            if (record["instance"] == instance and record["instance"] != old
                    and record["pid"] == process.pid and record["status"] == "watching"
                    and progress.running(self.run) and process.poll() is None
                    and (self.run / progress.PAGE).read_bytes() != old_page
                    and self.page_contains('data-mode="watch"')
                    and self.page_contains("A newly saved architecture draft")):
                return record
            return None

        if started:
            # Success must already mean fresh publication; waiting here would hide premature True.
            self.assertTrue(fresh_publication())
        else:
            # A bounded start can leave this same child alive before its first publication.
            self.assertIsNone(process.poll(), "unconfirmed observer exited before publication")
            self.wait_for(fresh_publication)
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
            return real_publish(*args, **kwargs)
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
        match = re.search(r"^ShipLoop (?:viewer|hub): http://127\.0\.0\.1:(\d+)/ ", line)
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
        # The scripts an open page loads to update in place: served as scripts, and admitted by the policy.
        self.assertIn("script-src 'unsafe-inline' 'self'", headers["content-security-policy"])
        for path, call in (("/progress-version.js", b"window.__shiploopVersion&&"),
                           ("/progress-content.js", b"window.__shiploopProgress&&"),
                           ("/trace-content.js", b"window.__shiploopTrace&&")):
            status, headers, script = self.get(port, path)
            self.assertEqual((status, headers["content-type"]), (200, "text/javascript; charset=utf-8"), path)
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            self.assertTrue(script.startswith(call), path)
        self.assertEqual(self.get(port, "/state.js")[0], 404)
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
        self.start_observer()
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

    def test_hub_serves_multiple_concurrent_runs_and_shared_repo_warnings(self):
        import shiploop_registry as registry
        repo_a = self.base / "repo-a"
        repo_b = self.base / "repo-b"
        for repo in (repo_a, repo_b):
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        run_a1, run_a2, run_b1 = self.base / "run-a1", self.base / "run-a2", self.base / "run-b1"
        runs_meta = []
        for idx, (rdir, repo, prompt) in enumerate((
            (run_a1, repo_a, "First feature on repo A"),
            (run_a2, repo_a, "Second feature on repo A"),
            (run_b1, repo_b, "Feature on repo B"),
        ), start=1):
            rdir.mkdir()
            (rdir / ".lock").touch()
            st = navigator.new_state(str(repo), prompt, improve_skill="")
            st["run_id"] = f"run-multi-{idx}"
            navigator.save(rdir, st)
            progress.observe(rdir, watch=False)
            registry.register_run(rdir, st)
            runs_meta.append((registry.safe_run_key(st["run_id"], rdir), prompt))
        argv = [sys.executable, "-B", str(CLI), "view", "--serve", "--port", "0", "--interval", ".1"]
        _, port = self.serve(command=argv)
        status, _, api_body = self.get(port, "/api/runs")
        self.assertEqual(status, 200)
        payload = json.loads(api_body)
        self.assertEqual(payload["counts"]["total"], 3)
        by_key = {item["run_key"]: item for item in payload["runs"]}
        for key, prompt in runs_meta:
            self.assertIn(key, by_key)
            s_html, _, body_html = self.get(port, f"/runs/{key}/progress.html")
            self.assertEqual(s_html, 200)
            self.assertIn(prompt.encode(), body_html)
            self.assertEqual(self.get(port, f"/runs/{key}/trace.html")[0], 200)
            self.assertEqual(self.get(port, f"/runs/{key}/progress-version.js")[0], 200)
        self.assertTrue(by_key[runs_meta[0][0]]["shared_repo_peers"])
        self.assertTrue(by_key[runs_meta[1][0]]["shared_repo_peers"])
        self.assertEqual(by_key[runs_meta[2][0]]["shared_repo_peers"], [])
        self.assertIn(str(repo_a), payload["shared_repo_conflicts"])
        hub_status, _, hub_html = self.get(port, "/")
        self.assertEqual(hub_status, 200)
        self.assertIn(b"ShipLoop Hub", hub_html)
        self.assertIn(b"/api/runs", hub_html)
        self.assertEqual(self.get(port, "/runs/does-not-exist/progress.html")[0], 404)
        self.assertEqual(self.get(port, f"/runs/{runs_meta[0][0]}/state.md")[0], 404)
        self.assertEqual(self.get(port, "/runs/../../etc/passwd")[0], 404)
        self.assertEqual(self.get(port, "/", host="evil.example")[0], 403)
        self.assertEqual(self.get(port, "/api/runs", method="POST")[0], 405)

    def test_background_serve_stop_server_and_live_hub_recommendation(self):
        import shiploop_registry as registry
        started = self.cli_ok("view", "--serve", "--background", "--port", "0", "--interval", ".1")
        match = re.search(r"http://127\.0\.0\.1:(\d+)/", started.stdout)
        self.assertIsNotNone(match, started.stdout)
        port = int(match.group(1))
        self.wait_for(lambda: registry.active_viewer() is not None)
        info = registry.active_viewer()
        self.assertEqual(info["mode"], "hub")
        self.assertEqual(info["url"].rstrip("/"), f"http://127.0.0.1:{port}")
        run2 = self.base / "run2"
        run2.mkdir()
        (run2 / ".lock").touch()
        state2 = navigator.new_state(str(self.repo), "Concurrent second run", improve_skill="")
        state2["run_id"] = "run-concurrent-2"
        navigator.save(run2, state2)
        line = navigator._progress_view_line(None, run2, state2)
        self.assertIn(f"http://127.0.0.1:{port}/runs/run-concurrent-2/", line)
        self.assertIn(f"all runs http://127.0.0.1:{port}/", line)
        self.assertIn("share both URLs with the user", line)
        stopped = self.cli_ok("view", "--stop-server")
        self.assertIn("stopped", stopped.stdout.lower())
        self.wait_for(lambda: registry.active_viewer() is None)
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=1).close()

    def test_runs_list_and_status_watch_cli(self):
        import shiploop_registry as registry
        halted_dir = self.base / "halted-run"
        halted_dir.mkdir()
        (halted_dir / ".lock").touch()
        halted_state = navigator.control(
            navigator.new_state(str(self.repo), "Halted CLI run", improve_skill=""),
            "halt", "Done here.",
        )
        halted_state["run_id"] = "run-halted-cli"
        navigator.save(halted_dir, halted_state)
        registry.register_run(self.run, self.state)
        registry.register_run(halted_dir, halted_state)
        all_res = self.cli_ok("runs", "--json")
        rows = json.loads(all_res.stdout)["runs"]
        self.assertEqual({r["run_id"] for r in rows}, {self.state["run_id"], "run-halted-cli"})
        active_res = self.cli_ok("runs", "--active", "--json")
        active_rows = json.loads(active_res.stdout)["runs"]
        self.assertEqual([r["run_id"] for r in active_rows], [self.state["run_id"]])
        text_res = self.cli_ok("runs")
        self.assertIn("Add a progress view", text_res.stdout)
        watch_res = self.cli_ok("status", "--run-dir", str(halted_dir), "--watch", "--interval", ".1")
        self.assertIn("=== ShipLoop status ===", watch_res.stdout)
        self.assertIn("halted at intake", watch_res.stdout)

    def test_first_packet_suggests_a_command_that_serves_the_run(self):
        self.run = self.base / "suggested run"
        result = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run), "--prompt", "Serve this run")
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(line for line in result.stdout.splitlines() if line.startswith("Progress view: "))
        self.assertIn("do not run foreground --serve yourself", line)
        hub_match = re.search(r"(python3 \S+ view --serve)\b", line)
        self.assertIsNotNone(hub_match, line)
        single_part = line.split(" or ", 1)[1].split(" (this run only)", 1)[0]
        argv = shlex.split(single_part)
        self.assertEqual((argv[0], argv[2], argv[-1]), ("python3", "view", "--serve"))
        self.assertEqual(argv[3], f"--run-dir={self.run}")
        _, port = self.serve(command=[sys.executable, "-B", *argv[1:], "--port", "0", "--interval", ".1"])
        self.wait_for(lambda: self.page_contains("Serve this run"))
        self.assertIn(b"Serve this run", self.get(port)[2])

    def test_later_packets_do_not_repeat_the_command(self):
        first = navigator._progress_view_line(None, self.run, self.state)
        self.assertIn("view --serve", first)
        self.assertIn("view --run-dir=", first)
        self.assertTrue(first.startswith("Progress view: [HTML file](<"))
        accepted = navigator.apply(self.state, navigator.current_action(self.state)["id"],
                                   {"outcome": "done", "summary": "Scope accepted for the viewer."})
        later = navigator._progress_view_line(None, self.run, accepted)
        self.assertEqual(first.split(" Recommend to the user", 1)[0], later)
        self.assertNotIn("--serve", later)


class StartupReportingTests(unittest.TestCase):
    """Caller reporting only: no process, server, observer wait, or workflow transition."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="progress-startup-reporting-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        state = navigator.new_state(str(self.repo), "Synthetic startup", improve_skill="")
        (self.root / "state.md").write_text(store.dumps(state))
        for patcher in (mock.patch.object(progress.subprocess, "Popen", side_effect=AssertionError("no process")),
                        mock.patch.object(progress.time, "sleep", side_effect=AssertionError("no wait"))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def set_page(self, present):
        page = self.root / progress.PAGE
        if present:
            page.write_text("old page; freshness unconfirmed")
        elif page.exists():
            page.unlink()

    def test_explicit_start_reports_pending_alive_with_missing_or_old_page(self):
        for present in (False, True):
            with self.subTest(page_present=present):
                self.set_page(present)
                out, err = io.StringIO(), io.StringIO()
                with mock.patch.object(progress, "start", return_value=False), \
                        mock.patch.object(progress, "running", return_value=True) as running, \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = progress.main(["--run-dir", str(self.root), "--start"])
                self.assertEqual(code, 0)
                running.assert_called_once_with(self.root)
                self.assertIn("was running when checked", out.getvalue())
                self.assertIn("pending confirmation", out.getvalue())
                self.assertIn("Wait", out.getvalue())
                self.assertIn("Target page (may not be ready): " + str(self.root / progress.PAGE), out.getvalue())
                self.assertNotEqual(out.getvalue(), str(self.root / progress.PAGE) + "\n")
                self.assertEqual(err.getvalue(), "")
                self.assertEqual((self.root / progress.PAGE).exists(), present)

    def test_explicit_start_failure_stays_unavailable_even_with_old_page(self):
        for present in (False, True):
            with self.subTest(page_present=present):
                self.set_page(present)
                out, err = io.StringIO(), io.StringIO()
                with mock.patch.object(progress, "start", return_value=False), \
                        mock.patch.object(progress, "running", return_value=False), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = progress.main(["--run-dir", str(self.root), "--start"])
                self.assertEqual(code, 2)
                self.assertIn("unavailable", err.getvalue())
                self.assertNotIn("pending", err.getvalue())
                self.assertEqual(out.getvalue(), "")

    def test_ready_explicit_start_keeps_path_only_output(self):
        self.set_page(True)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(progress, "start", return_value=True), \
                mock.patch.object(progress, "running") as running, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = progress.main(["--run-dir", str(self.root), "--start"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), str(self.root / progress.PAGE) + "\n")
        self.assertEqual(err.getvalue(), "")
        running.assert_not_called()

    def test_ensure_distinguishes_pending_from_unavailable_without_a_page(self):
        for alive in (True, False):
            with self.subTest(running_at_check=alive):
                err = io.StringIO()
                with mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "watch"}), \
                        mock.patch.object(progress, "start", return_value=False), \
                        mock.patch.object(progress, "running", return_value=alive), \
                        contextlib.redirect_stderr(err):
                    progress.ensure(self.root)
                self.assertEqual("pending confirmation" in err.getvalue(), alive)
                self.assertEqual("unavailable" in err.getvalue(), not alive)
                self.assertFalse((self.root / progress.PAGE).exists())

    def test_serve_continues_read_only_while_start_publication_is_pending(self):
        for present in (False, True):
            with self.subTest(page_present=present):
                self.set_page(present)
                err = io.StringIO()
                with mock.patch.object(progress, "start", return_value=False) as start, \
                        mock.patch.object(progress, "running", return_value=True), \
                        mock.patch.object(viewer, "serve", return_value=7) as serve, \
                        contextlib.redirect_stderr(err):
                    code = progress.serve(self.root, port=0, interval=.1, idle_timeout=10)
                self.assertEqual(code, 7)
                start.assert_called_once_with(self.root, interval=.1, idle_timeout=10)
                serve.assert_called_once_with(self.root, port=0)
                self.assertIn("pending confirmation", err.getvalue())
                self.assertIn("Serving read-only; pages may not be published yet", err.getvalue())
                self.assertNotIn("unavailable", err.getvalue())
                self.assertEqual((self.root / progress.PAGE).exists(), present)


class ObservationGenerationTests(unittest.TestCase):
    """One-shot fixture observations only; no detached observer or HTTP server."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="progress-generation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.root / ".lock").touch()
        self.state = navigator.new_state(str(self.repo), "Synthetic generation", improve_skill="")
        (self.root / "state.md").write_text(store.dumps(self.state))

    def published_models(self):
        """Read the actual trace payload and progress browser inputs from disk."""
        page = (self.root / "trace.html").read_text()
        start = page.index("const TRACE = ") + len("const TRACE = ")
        trace_model = json.loads(page[start:page.index(";\n", start)])
        page = (self.root / progress.PAGE).read_text()
        progress_inputs = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', page))
        self.assertEqual(trace_model["observed_at"], progress_inputs["observed-at"])
        self.assertEqual(trace_model["observer"]["mode"], progress_inputs["mode"])
        self.assertEqual(str(trace_model["observer"]["final"]).lower(), progress_inputs["final"])
        return trace_model, progress_inputs

    def test_snapshot_trace_explicitly_disables_reload(self):
        self.assertEqual(progress.observe(self.root, watch=False), 0)
        model, inputs = self.published_models()
        self.assertEqual(model["observer"], {"mode": "snapshot", "final": False, "error": ""})

    def test_an_idle_watch_rewrites_no_page_and_the_version_script_carries_the_heartbeat(self):
        import shiploop_story as story
        clock = [100.0]
        models, activity, beats, pages = [], [], [], []
        real_publish, real_sample, real_announce = progress.publish, progress.sample, progress.announce
        def sample(*args, **kwargs):
            value = real_sample(*args, **kwargs)
            activity.append((value["source_fingerprint"], value["activity_fingerprint"]))
            return value
        def publish(*args, **kwargs):
            key = real_publish(*args, **kwargs)
            models.append(self.published_models()[0])
            return key
        def announce(*args, **kwargs):
            real_announce(*args, **kwargs)
            beats.append(kwargs)
            pages.append(((self.root / progress.PAGE).read_bytes(), (self.root / "trace.html").read_bytes()))
        def sleep(interval):
            clock[0] += interval
        with mock.patch.object(progress.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(progress.time, "sleep", side_effect=sleep), \
                mock.patch.object(story, "utc", side_effect=lambda: f"2026-11-14T00:00:{int(clock[0] - 100):02d}Z"), \
                mock.patch.object(progress, "sample", side_effect=sample), \
                mock.patch.object(progress, "publish", side_effect=publish), \
                mock.patch.object(progress, "announce", side_effect=announce):
            self.assertEqual(progress.observe(self.root, watch=True, interval=1, idle_timeout=2), 0)
        self.assertEqual(len(activity), 3)  # Heartbeats must not extend the idle deadline.
        self.assertEqual(len(set(activity)), 1)
        # One publication while watching, then the stopped one: the two idle samples wrote no page.
        self.assertEqual([model["observer"]["mode"] for model in models], ["watch", "snapshot"])
        self.assertIn("idle timeout", models[-1]["observer"]["error"])
        watching = [beat for beat in beats if beat["status"] == "watching"]
        self.assertEqual(len(watching), 3)
        self.assertEqual(len({beat["progress"] for beat in watching}), 1)
        self.assertEqual(len({beat["trace"] for beat in watching}), 1)
        self.assertEqual(len({beat["observed_at"] for beat in watching}), 3)
        self.assertEqual(len(set(pages[:3])), 1)
        self.assertIn("idle timeout", beats[-1]["status"])
        self.assertNotEqual(beats[-1]["progress"], watching[0]["progress"])
        self.assertFalse(hasattr(progress, "HEARTBEAT"))

    def test_terminal_watch_publishes_nonfinal_then_reconciled_final(self):
        self.state.update(status="halted", status_reason="Fixture terminal reconciliation")
        (self.root / "state.md").write_text(store.dumps(self.state))
        clock = [100.0]
        models = []
        real_publish = progress.publish
        def publish(*args, **kwargs):
            key = real_publish(*args, **kwargs)
            models.append(self.published_models()[0])
            return key
        def sleep(interval):
            clock[0] += interval
        with mock.patch.object(progress.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(progress.time, "sleep", side_effect=sleep), \
                mock.patch.object(progress, "publish", side_effect=publish):
            self.assertEqual(progress.observe(self.root, watch=True, interval=1), 0)
        self.assertEqual([model["observer"]["final"] for model in models], [False, True])
        self.assertTrue(all(model["observer"]["mode"] == "watch" for model in models))
        self.assertEqual(json.loads((self.root / progress.STATUS).read_text())["status"], "final")

    def test_trace_publication_recovers_on_unchanged_watch_content(self):
        import shiploop_trace as trace
        clock = [100.0]
        statuses = []
        real_write, real_publish = trace.write_live, progress.publish
        attempts = [0]
        def write(*args, **kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise OSError("fixture transient trace publication error")
            return real_write(*args, **kwargs)
        def publish(*args, **kwargs):
            key = real_publish(*args, **kwargs)
            statuses.append(args[1]["trace_publication"]["status"])
            if statuses[-1] == "ok" and kwargs["mode"] == "watch":
                model, inputs = self.published_models()
                self.assertEqual(model["observer"]["error"], "")
                # Stop cooperatively after the successful retry.
                (self.root / progress.DISABLED).write_text("fixture request")
            return key
        def sleep(interval):
            clock[0] += interval
        with mock.patch.object(progress.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(progress.time, "sleep", side_effect=sleep), \
                mock.patch.object(trace, "write_live", side_effect=write), \
                mock.patch.object(progress, "publish", side_effect=publish):
            self.assertEqual(progress.observe(self.root, watch=True, interval=1), 0)
        self.assertEqual(statuses, ["unavailable", "ok", "ok"])
        model, inputs = self.published_models()
        self.assertEqual(model["observer"]["mode"], "snapshot")
        self.assertIn("stopped by request", model["observer"]["error"])
        status = json.loads((self.root / progress.STATUS).read_text())
        self.assertEqual(status["trace_publication"]["status"], "ok")

    def test_busy_and_pending_transaction_do_not_parse_or_recover(self):
        import shiploop_progress_data as data
        with (self.root / ".lock").open() as handle, mock.patch.object(store, "recover", side_effect=AssertionError("no recovery")), mock.patch.object(data, "build_snapshot") as build:
            fcntl.flock(handle, fcntl.LOCK_EX)
            self.assertIsNone(progress.sample(self.root))
            build.assert_not_called()
            fcntl.flock(handle, fcntl.LOCK_UN)
            journal = self.root / store.JOURNAL_NAME
            journal.write_text("owned by workflow")
            self.assertIsNone(progress.sample(self.root))
            self.assertEqual(journal.read_text(), "owned by workflow")
            build.assert_not_called()

    def test_core_lock_released_before_projection_and_trace_uses_captured_generation(self):
        import shiploop_progress_data as data
        import shiploop_trace as trace
        original = data.build_snapshot
        def project(root, **kwargs):
            with (root / ".lock").open() as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(root, **kwargs)
        with mock.patch.object(data, "build_snapshot", side_effect=project):
            snapshot = progress.sample(self.root)
        action = navigator.current_action(self.state)["id"]
        updated = navigator.apply(self.state, action, {"outcome": "done", "summary": "Later generation"})
        (self.root / "state.md").write_text(store.dumps(updated))
        model = trace.build(self.root, core=snapshot.core, captures=snapshot.captures)
        self.assertEqual(model["run"]["revision"], snapshot["run"]["revision"])
        self.assertNotEqual(model["run"]["revision"], updated["revision"])
        self.assertNotIn("state_raw", json.dumps(snapshot))

    def test_trace_publication_failure_is_visible_in_page_and_status(self):
        import shiploop_trace as trace
        with mock.patch.object(trace, "write_live", side_effect=OSError("fixture publication failure")):
            self.assertEqual(progress.observe(self.root, watch=False), 0)
        status = json.loads((self.root / progress.STATUS).read_text())
        self.assertEqual(status["trace_publication"]["status"], "unavailable")
        self.assertIn("Trace publication failed", (self.root / progress.PAGE).read_text())

    def test_stat_gate_skips_projection_when_idle_and_invalidates_on_doc_or_loop_change(self):
        import shiploop_progress_data as data
        clock = [100.0]
        calls = [0]
        real_build = data.build_snapshot
        def counting_build(*args, **kwargs):
            calls[0] += 1
            return real_build(*args, **kwargs)
        heartbeats = []
        def sleep(interval):
            clock[0] += interval
            ver = (self.root / progress.VERSION).read_text()
            heartbeats.append(ver)
            if len(heartbeats) >= 3:
                (self.root / progress.DISABLED).write_text("stop after idle ticks")
        with mock.patch.object(progress.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(progress.time, "sleep", side_effect=sleep), \
                mock.patch.object(data, "build_snapshot", side_effect=counting_build):
            self.assertEqual(progress.observe(self.root, watch=True, interval=1, idle_timeout=30), 0)
        # First sample builds snapshot; idle sleep ticks reuse stat signature without calling build_snapshot.
        self.assertEqual(calls[0], 1)
        self.assertGreaterEqual(len(heartbeats), 3)
        snap = progress.sample(self.root)
        sig_before = snap.watch_sig
        (self.repo / "docs" / "shiploop").mkdir(parents=True)
        (self.repo / "docs" / "shiploop" / "spec.md").write_text("# Spec\n")
        self.assertNotEqual(progress._watch_signature(self.root, snap), sig_before)
        snap2 = progress.sample(self.root)
        sig_before_loop = snap2.watch_sig
        (self.root / "loops").mkdir(exist_ok=True)
        (self.root / "loops" / "step.md").write_text("# Loop contract\n")
        self.assertNotEqual(progress._watch_signature(self.root, snap2), sig_before_loop)

    def test_idle_timeout_marks_page_revivable_while_snapshot_omits_it(self):
        clock = [100.0]
        def sleep(interval):
            clock[0] += interval
        with mock.patch.object(progress.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(progress.time, "sleep", side_effect=sleep):
            self.assertEqual(progress.observe(self.root, watch=True, interval=1, idle_timeout=1.5), 0)
        page_text = (self.root / progress.PAGE).read_text()
        self.assertIn('data-revivable="true"', page_text)
        self.assertEqual(progress.observe(self.root, watch=False), 0)
        snap_page = (self.root / progress.PAGE).read_text()
        self.assertIn('data-revivable="false"', snap_page)

    def test_registry_is_resilient_to_read_only_state_home(self):
        import shiploop_registry as registry
        blocking_file = self.root / "not-a-directory"
        blocking_file.write_text("file")
        with mock.patch.dict(os.environ, {"SHIPLOOP_STATE_HOME": str(blocking_file)}):
            self.assertFalse(registry.register_run(self.root, self.state))
            self.assertIsNone(registry.active_viewer())


if __name__ == "__main__":
    unittest.main()
