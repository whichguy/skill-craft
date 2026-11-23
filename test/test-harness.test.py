#!/usr/bin/env python3
"""Hermetic checks for the test-harness skill: its own behaviour suite, the packaging contract and a narrow lint.

No network, no model. The bash self-test under skills/test-harness/scripts is the behaviour suite (discovery, scope,
supervision, side-effect classification, redaction, reports). This wrapper runs it in a scratch HOME and TMPDIR so that
nothing it does can land in the caller's home, and adds what that script cannot say about itself: the skill binds its
scripts from the loaded card, runs from any directory, ships no host-specific home directory, and leaves its own tree as
it found it.

The lint is narrow, not a privacy proof. It looks for the shapes of an email address, a home path, a host-specific home
directory used as a default and a few secret formats. Names of people, projects and accounts are not shapes: those need a
denylist kept outside the repository and a person reading the prose.
"""
import os
import json
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "test-harness"
SELF_TEST = SKILL / "scripts" / "test-harness-tests.sh"
JOURNAL = ROOT / "docs" / "test-harness-journal.md"
EVIDENCE = ROOT / "docs" / "evidence" / "test-harness-20261108"

# The self-test reports its own assertion count. A floor, not an exact number, so an added case does not break the
# suite, while an early exit that skips most of it cannot pass.
MINIMUM_ASSERTIONS = 270

SCRIPTS_RUN_BY_THE_CARD = (
    "run-harness.sh", "run-harness-hard-supervisor.py", "run-suite.sh", "discover-test-cmd.sh", "worktree-fixloop.sh",
    "porcelain-delta.py", "classify-side-effects.py", "emit-report.py", "init-run.py", "resolve-scope.py",
    "test-harness-tests.sh",
)

# name -> shape. A shape that matches inside a shipped file is a finding.
SHAPES = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "host home directory": re.compile(r"(?:~|\$HOME|\$\{HOME\}|Path\.home\(\)\s*/)\s*/?\s*[\"']?\.(?:grok|hermes|claude|codex|cursor|opencode)\b"),
    "secret shape": re.compile(
        r"\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\bghp_[A-Za-z0-9]{30,}|\bxox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ),
}


def shipped_files():
    """Every file the skill ships, plus the journal and evidence that describe it."""
    paths = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT / "changes" / "test-harness" / name for name in ("initial.md",) if (ROOT / "changes" / "test-harness" / name).is_file()]
    if JOURNAL.is_file():
        paths.append(JOURNAL)
    if EVIDENCE.is_dir():
        paths += [p for p in EVIDENCE.rglob("*") if p.is_file()]
    return sorted(paths)


def scan(paths):
    """Return (findings, files_read, bytes_read). A scan that read nothing must never look clean."""
    findings, files_read, bytes_read = [], 0, 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        files_read += 1
        bytes_read += len(text.encode("utf-8"))
        for label, shape in SHAPES.items():
            for match in shape.finditer(text):
                findings.append((path, label, match.group(0)))
    return findings, files_read, bytes_read


def barrier_failure_detail(barrier, leftovers, elapsed, stderr):
    sizes = [(row["name"], len(row.get("text", ""))) for row in leftovers]
    return (
        f"operation barrier was not reached; elapsed={elapsed:.3f}s; "
        f"staging_sizes={sizes}; stderr_tail={stderr[-400:]!r}"
    )


def self_test_detail(output):
    """Named FAIL lines / fail-index first, then the last 1500 characters."""
    indexed = re.search(
        r"^=== fail-index ===\n(.*?)^=== end fail-index ===$",
        output,
        re.M | re.S,
    )
    if indexed and indexed.group(1).strip():
        names = indexed.group(1).strip()
        return names + "\n--- last 1500 characters ---\n" + output[-1500:]
    failing = [line for line in output.splitlines() if line.startswith("  FAIL  ")]
    tail = output[-1500:]
    if not failing:
        return tail
    return "\n".join(failing) + "\n--- last 1500 characters ---\n" + tail


def tree_state(root):
    """Every real file under root with its size. Bytecode caches are ignored: CI's own guard allows them, and another
    suite importing a module concurrently could create one between two reads."""
    return {p.relative_to(root).as_posix(): p.stat().st_size for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class TimeoutEvidence(unittest.TestCase):
    """Real main/clock/alarm/process groups with barriers at actual operations.

    Three methods cover six scenarios: cleanup, two interrupted writes, and
    three publication boundaries. A missing barrier always fails the control.
    """

    WRAPPER = r'''
import importlib.util, json, os, signal, sys, time
from pathlib import Path
source, scenario, scratch, timeout_secs = sys.argv[1:]
root = Path(scratch)
spec = importlib.util.spec_from_file_location("hard_supervisor", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
final = root / "run" / "hard-timeout.json"
def snapshot():
    if not final.exists():
        return None
    return {"text": final.read_text(), "mode": final.stat().st_mode & 0o777}
def barrier():
    (root / "barrier.json").write_text(json.dumps({"scenario": scenario, "final": snapshot()}))
    while not (root / "release").exists():
        time.sleep(0.002)
real_killpg = os.killpg
def killpg(pgid, sig):
    real_killpg(pgid, sig)
    if scenario == "cleanup" and sig == signal.SIGTERM:
        barrier()
module.os.killpg = killpg
real_write = module.write_all
def write_all(fd, payload):
    if scenario in ("write-empty", "write-prefix"):
        if scenario == "write-prefix":
            real_write(fd, payload[:7])
        barrier()
    real_write(fd, payload)
module.write_all = write_all
real_link = os.link
def link(src, dst, *args, **kwargs):
    if scenario in ("collision-file", "collision-symlink"):
        barrier()
    result = real_link(src, dst, *args, **kwargs)
    if scenario == "published":
        barrier()
    return result
module.os.link = link
sys.argv = [source, "--timeout-secs", timeout_secs, "--repo", scratch,
            "--run-dir", str(root / "run"), "--", sys.executable,
            str(root / "worker.py"), scratch, scenario, "command-secret-must-not-persist"]
raise SystemExit(module.main())
'''

    WORKER = r'''
import json, os, signal, subprocess, sys, time
from pathlib import Path
root, scenario = Path(sys.argv[1]), sys.argv[2]
child = subprocess.Popen([sys.executable, "-c",
    "import os,signal,sys,time; from pathlib import Path; "
    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
    "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)",
    str(root / "descendant.pid")])
def terminate(sig, frame):
    child.kill()
    child.wait()
    raise SystemExit(0)
signal.signal(signal.SIGTERM, signal.SIG_IGN if scenario == "cleanup" else terminate)
(root / "worker.pid").write_text(str(os.getpid()))
while True:
    time.sleep(0.01)
'''

    def assert_complete(self, artifact, timeout_secs=1):
        self.assertIsNotNone(artifact, "timeout evidence must precede cleanup")
        doc = json.loads(artifact["text"])
        self.assertEqual(set(doc), {"stop", "timeout_secs", "elapsed_ms", "worker_executable", "worker_argument_count"})
        self.assertEqual(doc["stop"], "hard_timeout")
        self.assertEqual(doc["timeout_secs"], timeout_secs)
        self.assertTrue(0 < doc["elapsed_ms"] < timeout_secs * 1000, doc)
        self.assertEqual(doc["worker_executable"], Path(sys.executable).name)
        self.assertEqual(doc["worker_argument_count"], 4)
        self.assertEqual(artifact["mode"], 0o600)
        self.assertNotIn("command-secret-must-not-persist", artifact["text"])

    def scenario(self, name, timeout_secs=1):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wrapper = root / "wrapper.py"
            wrapper.write_text(self.WRAPPER)
            (root / "worker.py").write_text(self.WORKER)
            source = SKILL / "scripts" / "run-harness-hard-supervisor.py"
            argv = [sys.executable, str(wrapper), str(source), name, scratch, str(timeout_secs)]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            started_wall = time.time()
            started = time.monotonic()
            proc = subprocess.Popen(argv, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            marker = root / "barrier.json"
            barrier = None
            try:
                # Cap + existing 1500ms external slack; no production cap changes.
                until = started + timeout_secs + 1.5
                while time.monotonic() < until and proc.poll() is None:
                    if marker.exists() and marker.stat().st_size:
                        barrier = json.loads(marker.read_text())
                        break
                    time.sleep(0.002)
                if barrier is not None and name.startswith("collision-"):
                    final = root / "run" / "hard-timeout.json"
                    target = root / "target"
                    target.write_text("target unchanged")
                    if name == "collision-file":
                        final.write_text("competitor unchanged")
                    else:
                        final.symlink_to(target)
                    collision_inode = final.lstat().st_ino
                    (root / "release").touch()
                stdout, stderr = proc.communicate(timeout=max(0.01, until - time.monotonic()))
                elapsed = time.monotonic() - started
                final = root / "run" / "hard-timeout.json"
                artifact = ({"text": final.read_text(), "mode": final.stat().st_mode & 0o777}
                            if final.exists() else None)
                leftovers = [{"name": p.name, "mode": p.stat().st_mode & 0o777,
                              "text": p.read_text()} for p in (root / "run").glob(".hard-timeout.*")]
                pids = {}
                for label in ("worker", "descendant"):
                    pid_path = root / (label + ".pid")
                    self.assertTrue(pid_path.is_file(), label + " readiness marker missing")
                    pid = int(pid_path.read_text())
                    # A killed orphan may briefly remain a zombie; it cannot execute.
                    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False)
                    pids[label] = {"pid": pid, "state": state.stdout.strip()}
                print(json.dumps({"scenario": name, "argv": argv, "cwd": scratch,
                                  "start_epoch": started_wall, "end_epoch": time.time(),
                                  "exit": proc.returncode, "elapsed": elapsed, "barrier": barrier,
                                  "final": artifact, "staging_leftovers": leftovers, "pids": pids,
                                  "stdout": stdout, "stderr": stderr}), flush=True)
                self.assertIsNotNone(
                    barrier,
                    barrier_failure_detail(barrier, leftovers, elapsed, stderr),
                )
                self.assertEqual(barrier["scenario"], name)
                self.assertEqual(proc.returncode, 124, stderr)
                self.assertLess(elapsed, timeout_secs + 1.5)
                self.assertIn("test-harness hard timeout:", stderr)
                for label, entry in pids.items():
                    self.assertTrue(not entry["state"] or entry["state"].startswith("Z"), (label, entry))
                for stage in leftovers:
                    self.assertEqual(stage["mode"], 0o600)
                if name in ("cleanup", "published"):
                    self.assert_complete(barrier["final"], timeout_secs)
                    self.assert_complete(artifact, timeout_secs)
                elif name.startswith("write-"):
                    self.assertIsNone(barrier["final"], "incomplete final pathname visible at write barrier")
                    self.assertIsNone(artifact, "interrupted pre-publication must not expose final bytes")
                else:
                    self.assertIsNone(barrier["final"])
                    self.assertEqual(final.lstat().st_ino, collision_inode)
                    self.assertEqual(final.is_symlink(), name == "collision-symlink")
                    if final.is_symlink():
                        self.assertEqual(os.readlink(final), str(target))
                    self.assertEqual(final.read_text(), "target unchanged" if final.is_symlink() else "competitor unchanged")
                    self.assertEqual(target.read_text(), "target unchanged")
                    self.assertIn("refusing to replace timeout evidence at hard-timeout.json:", stderr)
                    self.assertNotIn("command-secret-must-not-persist", stderr)
                    self.assertEqual(leftovers, [])
            finally:
                if proc.poll() is None:
                    proc.kill()
                # Only fixture-owned processes; this also cleans up a failed control.
                for label in ("worker", "descendant"):
                    pid_path = root / (label + ".pid")
                    if pid_path.exists():
                        try:
                            os.kill(int(pid_path.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                proc.communicate()

    def test_barrier_failure_detail_names_empty_staging(self):
        msg = barrier_failure_detail(None, [{"name": "x.tmp", "text": ""}], 1.02, "hard timeout\n")
        self.assertIn("staging_sizes=[('x.tmp', 0)]", msg)
        self.assertIn("elapsed=1.020s", msg)

    def test_evidence_precedes_deadline_consuming_cleanup(self):
        # Only this scenario gets a larger cap. At a 1s cap the supervisor has the
        # ~0.2s cleanup reserve between deciding the timeout and the hard alarm to
        # write and fsync the evidence; a stalled runner left the staging file empty
        # and the cleanup barrier was never reached (CI 45134262405 attempt 1). A 4s
        # cap widens that one reserve to ~0.9s without widening every scenario's cap,
        # changing any production limit, or retrying until a pass.
        self.scenario("cleanup", timeout_secs=4)

    def test_interrupted_write_never_exposes_incomplete_final(self):
        for name in ("write-empty", "write-prefix"):
            with self.subTest(scenario=name):
                self.scenario(name)

    def test_atomic_publication_and_raced_collisions(self):
        for name in ("published", "collision-file", "collision-symlink"):
            with self.subTest(scenario=name):
                self.scenario(name)


class SelfTest(unittest.TestCase):
    def test_self_test_detail_prefers_fail_index_block(self):
        body = (
            "=== fail-index ===\n"
            "synthetic early failure\n"
            "=== end fail-index ===\n"
            + ("y" * 3000)
            + "\n=== summary: PASS=10 FAIL=1 ===\n"
        )
        detail = self_test_detail(body)
        self.assertIn("synthetic early failure", detail)
        self.assertNotIn("y" * 100, detail.split("synthetic early failure", 1)[0])

    def test_the_bundled_self_test_passes_in_a_scratch_home(self):
        synthetic = "  FAIL  synthetic early failure\n" + "x" * 3000 + "\n=== summary: PASS=1 FAIL=1 ===\n"
        self.assertIn("  FAIL  synthetic early failure", self_test_detail(synthetic))
        before = tree_state(SKILL)
        with tempfile.TemporaryDirectory() as scratch:
            home, tmp = Path(scratch) / "home", Path(scratch) / "tmp"
            home.mkdir()
            tmp.mkdir()
            env = {k: v for k, v in os.environ.items() if not k.startswith("TEST_HARNESS_") and k != "XDG_STATE_HOME"}
            env.update(HOME=str(home), TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_NOSYSTEM="1")
            run = subprocess.run(["bash", str(SELF_TEST)], env=env, capture_output=True, text=True, timeout=900, check=False)
            detail = self_test_detail(run.stdout + run.stderr)
            self.assertEqual(run.returncode, 0, detail)
            summary = re.search(r"^=== summary: PASS=(\d+) FAIL=(\d+) ===$", run.stdout, re.M)
            self.assertIsNotNone(summary, detail)
            self.assertEqual(summary.group(2), "0", detail)
            self.assertGreaterEqual(int(summary.group(1)), MINIMUM_ASSERTIONS, detail)
            self.assertEqual(list(home.iterdir()), [], "the self-test must not write under the caller's HOME")
        self.assertEqual(tree_state(SKILL), before, "the self-test must leave the skill's own tree as it found it")


class Packaging(unittest.TestCase):
    def card(self):
        return (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_the_card_binds_the_scripts_from_the_loaded_skill(self):
        card = self.card()
        self.assertRegex(card, r'(?m)^SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL\.md"$')
        self.assertNotIn("SKILL_DIR", card, "the card's variable is SKILL_ROOT")
        self.assertIn("TEST_HARNESS_RUN_ROOT", card, "the write root is named apart from the package root")

    def test_every_script_and_reference_the_card_names_exists(self):
        docs = [SKILL / "SKILL.md"] + sorted((SKILL / "references").glob("*.md"))
        for doc in docs:
            text = doc.read_text(encoding="utf-8")
            for rel in set(re.findall(r"(?:(?<![\w/.-])|(?<=SKILL_ROOT/))((?:scripts|references)/[A-Za-z0-9_.-]+\.(?:sh|py|md))", text)):
                self.assertTrue((SKILL / rel).is_file(), f"{doc.name} names {rel}")

    def test_the_scripts_the_card_runs_are_executable(self):
        for name in SCRIPTS_RUN_BY_THE_CARD:
            self.assertTrue(os.access(SKILL / "scripts" / name, os.X_OK), name)

    def test_the_driver_runs_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            run = subprocess.run(["bash", str(SKILL / "scripts" / "run-harness.sh"), "--help"], cwd=elsewhere,
                                 capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("Usage: run-harness.sh", run.stdout)
            self.assertIn("fix-loop", run.stdout)

    def test_no_default_names_a_host_or_a_home_directory(self):
        for name in ("run-harness.sh", "run-harness-hard-supervisor.py"):
            text = (SKILL / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("XDG_STATE_HOME", text, f"{name} computes the default run root")
            self.assertNotRegex(text, r"\.(grok|hermes|claude|codex|cursor)\b", name)


class Hygiene(unittest.TestCase):
    """A narrow lint, proven on seeded leaks so that a clean result cannot mean the scan read nothing."""

    def test_the_lint_finds_each_seeded_shape(self):
        leaks = {
            "email address": "contact " + "someone" + "@" + "example" + ".org",
            "home path": "see " + "/Users/" + "alice" + "/notes.txt",
            "host home directory": 'ROOT="${ROOT:-$HOME/.' + 'grok/skills/x}"',
            "secret shape": "key = " + "sk-" + "A" * 24,
        }
        self.assertEqual(set(leaks), set(SHAPES), "every shape has a seeded leak")
        with tempfile.TemporaryDirectory() as scratch:
            paths = []
            for label, line in leaks.items():
                path = Path(scratch) / (label.replace(" ", "-") + ".txt")
                path.write_text(line + "\n", encoding="utf-8")
                paths.append(path)
            findings, files_read, bytes_read = scan(paths)
        self.assertEqual(files_read, len(leaks))
        self.assertGreater(bytes_read, 0)
        self.assertEqual({label for _path, label, _text in findings}, set(leaks))

    def test_the_lint_reads_every_shipped_file(self):
        paths = shipped_files()
        on_disk = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        self.assertGreaterEqual(len(paths), len(on_disk), "the scan list covers the whole skill tree")
        self.assertGreaterEqual(len(on_disk), 20)
        findings, files_read, bytes_read = scan(paths)
        self.assertEqual(files_read, len(paths))
        self.assertGreater(bytes_read, 300_000, "the skill is about 380 KB; a scan that read far less read the wrong files")
        self.assertEqual(findings, [], "\n".join(f"{p.relative_to(ROOT)}: {label}: {text}" for p, label, text in findings[:20]))


if __name__ == "__main__":
    unittest.main()
