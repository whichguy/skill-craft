#!/usr/bin/env python3
"""Static integrity of the ShipLoop package: links, reachability, hooks, syntax.

Prompt and reference edits reach models through links a script or card names;
nothing else checks that those links still resolve or that every reference is
still reachable.  The integrity checks read files; probe fixtures use fake host CLIs and a built
package, with no model, real host install or network.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills" / "shiploop"

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_HOOK_EVENTS = {"after-shell", "turn-end", "after-skill", "session-end"}


def _texts(package: Path) -> dict[Path, str]:
    return {
        path: path.read_text(errors="ignore")
        for path in package.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def broken_links(package: Path) -> list[str]:
    """Relative Markdown links whose target file does not exist."""

    broken = []
    for path, text in _texts(package).items():
        if path.suffix != ".md":
            continue
        for match in _LINK.finditer(text):
            target = match.group(1).split("#", 1)[0]
            if not target or re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith(("/", "<")):
                continue
            if not (path.parent / target).exists():
                broken.append(f"{path.relative_to(package)} -> {match.group(1)}")
    return sorted(broken)


def orphaned_references(package: Path) -> list[str]:
    """Reference files that no entry point reaches by name, directly or through another reference.

    Entry points are what a host or reader opens first: the card, the README,
    commands, scripts, hooks and the hook manifest.
    """

    texts = _texts(package)
    references = {path for path in texts if path.is_relative_to(package / "references")}
    roots = [path for path in texts
             if path.name in {"SKILL.md", "README.md", "host-hooks.json"} and path.parent == package
             or path.parent.name in {"scripts", "commands", "hooks"}]
    seen, stack = set(roots), list(roots)
    while stack:
        text = texts[stack.pop()]
        for reference in references - seen:
            if reference.name in text or reference.relative_to(package / "references").as_posix() in text:
                seen.add(reference)
                stack.append(reference)
    return sorted(path.relative_to(package).as_posix() for path in references - seen)


def hook_manifest_problems(package: Path) -> list[str]:
    problems = []
    manifest = json.loads((package / "host-hooks.json").read_text())
    ids = [hook.get("id") for hook in manifest["hooks"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate hook id")
    for hook in manifest["hooks"]:
        script = package / hook["script"]
        if not script.is_file():
            problems.append(f"{hook['id']}: missing {hook['script']}")
        elif not os.access(script, os.X_OK):
            problems.append(f"{hook['id']}: {hook['script']} is not executable")
        if hook["event"] not in _HOOK_EVENTS:
            problems.append(f"{hook['id']}: unknown event {hook['event']}")
        if not hook.get("hosts") or not isinstance(hook.get("timeout"), int) or hook["timeout"] <= 0:
            problems.append(f"{hook['id']}: needs hosts and a positive timeout")
    return problems


def python_script_problems(package: Path) -> list[str]:
    """Python sources that do not compile, and entry scripts that are not executable."""

    problems = []
    for path in sorted((package / "scripts").iterdir()):
        if not path.is_file():
            continue
        source = path.read_text(errors="ignore")
        entry = path.suffix == ""
        if entry and not source.startswith("#!/usr/bin/env python3"):
            continue
        if entry and not os.access(path, os.X_OK):
            problems.append(f"{path.name}: entry script is not executable")
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            problems.append(f"{path.name}: {exc.msg} (line {exc.lineno})")
    return problems


CARD_LEDGER = ROOT / "test" / "fixtures" / "shiploop-card-ledger.json"
_RECOVERY_COMMAND = "shiploop next --run-dir"


def _flat(text: str) -> str:
    return " ".join(text.split())


def card_split_problems(package: Path, ledger: dict) -> list[str]:
    """The entry-card split (efficiency unit U22): the recovery block, the size bounds and the moved-obligation ledger.

    The card starts, right after its title, with the recovery block that names ``next --run-dir`` (by line 40) and
    no "newest folder" guess; it is at most ``card_max_bytes`` and every split file at most ``file_max_bytes``; every
    ledger row's anchors are in its home file, the card links that file, and every section of a split file has a row.
    """

    problems: list[str] = []
    card_path = package / "SKILL.md"
    card = card_path.read_text(encoding="utf-8")
    lines = card.splitlines()
    first = next((number for number, line in enumerate(lines, 1) if _RECOVERY_COMMAND in line), None)
    if first is None or first > 40:
        problems.append(f"SKILL.md: '{_RECOVERY_COMMAND}' first at line {first}, not by line 40")
    title = next((number for number, line in enumerate(lines) if line.startswith("# ")), None)
    block = next((line for line in lines[(title or 0) + 1:] if line.strip()), "") if title is not None else ""
    if not block.startswith("Recovering after a reset"):
        problems.append("SKILL.md: the recovery block does not follow the title")
    if "newest" in card.lower():
        problems.append("SKILL.md: a 'newest' fallback is named")
    if len(card.encode("utf-8")) > ledger["card_max_bytes"]:
        problems.append(f"SKILL.md: {len(card.encode('utf-8'))} bytes > {ledger['card_max_bytes']}")
    homes = sorted({row["home"] for row in ledger["rows"]})
    sections: dict[str, set[str]] = {}
    for home in homes:
        path = package / "references" / home
        if not path.is_file():
            problems.append(f"{home}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        if size > ledger["file_max_bytes"]:
            problems.append(f"{home}: {size} bytes > {ledger['file_max_bytes']}")
        heads = [line for line in text.splitlines() if line.startswith("## ")]
        sections[home] = set(heads) | {line for line in text.splitlines()[:1] if line.startswith("# ")}
        if f"references/{home}" not in card:
            problems.append(f"{home}: the card does not link it")
    flat_card = _flat(card)
    covered: dict[str, set[str]] = {home: set() for home in homes}
    for row in ledger["rows"]:
        home, section = row["home"], row["section"]
        path = package / "references" / home
        if not path.is_file():
            continue
        if section not in sections.get(home, set()):
            problems.append(f"{row['id']}: no section {section!r} in {home}")
        covered[home].add(section)
        if row["trigger"] not in flat_card:
            problems.append(f"{row['id']}: the card lacks its trigger {row['trigger']!r}")
        text = _flat(path.read_text(encoding="utf-8"))
        for phrase in row["anchors"]:
            if _flat(phrase) not in text:
                problems.append(f"{row['id']}: {home} lacks {phrase!r}")
    for home, heads in sections.items():
        for head in sorted(heads - covered[home]):
            if head.startswith("## "):
                problems.append(f"{home}: section {head!r} has no ledger row")
    return problems


class PackageIntegrityTests(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self) -> None:
        self.assertEqual(broken_links(PACKAGE), [])

    def test_every_reference_is_reachable_from_an_entry_point(self) -> None:
        self.assertEqual(orphaned_references(PACKAGE), [])

    def test_hook_manifest_names_executable_scripts_for_known_events(self) -> None:
        self.assertEqual(hook_manifest_problems(PACKAGE), [])

    def test_python_scripts_compile_and_entry_scripts_are_executable(self) -> None:
        self.assertEqual(python_script_problems(PACKAGE), [])

    def test_graph_dry_run_scenario_is_valid_json(self) -> None:
        json.loads((PACKAGE / "references" / "graph-dry-run-scenario.json").read_text())

    def test_entry_card_split_holds_its_ledger_and_bounds(self) -> None:
        self.assertEqual(card_split_problems(PACKAGE, json.loads(CARD_LEDGER.read_text(encoding="utf-8"))), [])

    @unittest.skipUnless(shutil.which("node"), "node is required for the OpenCode hook")
    def test_opencode_keepalive_hook_is_valid_module_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "opencode-keepalive.mjs"
            shutil.copyfile(PACKAGE / "hooks" / "opencode-keepalive.js", module)
            result = subprocess.run(["node", "--check", str(module)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class CheckerSensitivityTests(unittest.TestCase):
    """Each check must fail on a package with the defect it looks for."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.package = Path(tmp.name) / "shiploop"
        (self.package / "references").mkdir(parents=True)
        (self.package / "scripts").mkdir()
        (self.package / "SKILL.md").write_text("See [guide](references/guide.md).\n")
        (self.package / "references" / "guide.md").write_text("Also [missing](gone.md#part).\n")
        (self.package / "references" / "lonely.md").write_text("nobody links here\n")
        hook = self.package / "scripts" / "shiploop-hook"
        hook.write_text("#!/usr/bin/env python3\nprint(\n")
        (self.package / "host-hooks.json").write_text(json.dumps({"hooks": [
            {"id": "a", "event": "after-shell", "script": "scripts/shiploop-hook", "timeout": 5, "hosts": ["claude"]},
            {"id": "b", "event": "session-start", "script": "scripts/absent", "timeout": 0, "hosts": []},
        ]}))

    def test_each_defect_is_reported(self) -> None:
        self.assertEqual(broken_links(self.package), ["references/guide.md -> gone.md#part"])
        self.assertEqual(orphaned_references(self.package), ["references/lonely.md"])
        problems = hook_manifest_problems(self.package)
        self.assertIn("a: scripts/shiploop-hook is not executable", problems)
        self.assertIn("b: missing scripts/absent", problems)
        self.assertIn("b: unknown event session-start", problems)
        self.assertIn("b: needs hosts and a positive timeout", problems)
        script_problems = python_script_problems(self.package)
        self.assertIn("shiploop-hook: entry script is not executable", script_problems)
        self.assertTrue(any(problem.startswith("shiploop-hook: ") and "line" in problem
                            for problem in script_problems), script_problems)



class CardSplitSensitivityTests(unittest.TestCase):
    """Each card-split check fails on a copy of the package with the defect it looks for."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.package = Path(tmp.name) / "shiploop"
        shutil.copytree(PACKAGE, self.package, ignore=shutil.ignore_patterns("__pycache__", "scripts", "hooks"))
        self.ledger = json.loads(CARD_LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(card_split_problems(self.package, self.ledger), [])

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.package / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_a_lost_anchor_is_reported(self) -> None:
        self.edit("references/test-loop.md", "in the same way after a genuine fix", "after several attempts")
        self.assertEqual(card_split_problems(self.package, self.ledger),
                         ["tests-pass-or-stop: test-loop.md lacks 'in the same way after a genuine fix'"])

    def test_an_unledgered_section_and_an_unlinked_file_are_reported(self) -> None:
        self.edit("references/test-loop.md", "## Tests pass or the step stops", "## Tests pass\n\n## Or the step stops")
        card = self.package / "SKILL.md"
        card.write_text(card.read_text(encoding="utf-8").replace("references/test-loop.md", "elsewhere"),
                        encoding="utf-8")
        problems = card_split_problems(self.package, self.ledger)
        self.assertIn("test-loop.md: the card does not link it", problems)
        self.assertIn("test-loop.md: section '## Or the step stops' has no ledger row", problems)
        self.assertIn("tests-pass-or-stop: no section '## Tests pass or the step stops' in test-loop.md", problems)

    def test_the_size_bounds_and_the_recovery_block_are_checked(self) -> None:
        card = (self.package / "SKILL.md").read_text(encoding="utf-8")
        title, rest = card.split("# ShipLoop\n\n", 1)
        block, after = rest.split("\n\n", 1)
        (self.package / "SKILL.md").write_text(title + "# ShipLoop\n\n" + after + "\n" + "x" * 31_000 + "\n\n"
                                               + block.replace("instead of guessing", "or take the newest folder")
                                               + "\n", encoding="utf-8")
        with (self.package / "references" / "run-start.md").open("a", encoding="utf-8") as handle:
            handle.write("y" * 8_192)
        problems = card_split_problems(self.package, self.ledger)
        self.assertTrue(any(problem.startswith("SKILL.md: 'shiploop next --run-dir' first at line") for problem in problems))
        self.assertIn("SKILL.md: the recovery block does not follow the title", problems)
        self.assertIn("SKILL.md: a 'newest' fallback is named", problems)
        self.assertTrue(any(problem.startswith("SKILL.md: ") and "> " + str(json.loads((ROOT / "test/fixtures/shiploop-card-ledger.json").read_text())["card_max_bytes"]) in problem for problem in problems))
        self.assertTrue(any(problem.startswith("run-start.md: ") and "> 8192" in problem for problem in problems))


class PublishedInstallProbeTests(unittest.TestCase):
    """Hermetic bootstrap/error checks; fake host commands never install a real plugin."""

    def setUp(self) -> None:
        from package_build import plugins

        tmp = tempfile.TemporaryDirectory(prefix="published probe fixture ")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.fixture = self.root / "fixture package"
        shutil.copytree(plugins() / "skill-craft", self.fixture,
                        ignore=shutil.ignore_patterns("__pycache__"))
        # Keep the built payload, but replace only this fixture's CLI with a bounded stand-in.
        # Production help/workspace behavior belongs to its own suites and the real manual probe.
        entry = self.fixture / "skills/shiploop/scripts/shiploop"
        entry.write_text("#!/usr/bin/env python3\nimport os, pathlib, sys\n"
                         f"assert pathlib.Path(sys.executable).resolve() == pathlib.Path({sys.executable!r}).resolve()\n"
                         "assert 'PROBE_INHERITED_SENTINEL' not in os.environ\n"
                         "assert 'CLAUDE_CONFIG_DIR' not in os.environ\n"
                         "assert os.environ['SHIPLOOP_PROGRESS'] == 'off'\n"
                         "assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'\n"
                         "print('help' if '--help' in sys.argv else 'fixture workspace packet')\n")
        entry.chmod(0o755)
        self.bin = self.root / "fake bin"
        self.bin.mkdir()
        self.calls = self.root / "claude calls"
        self.fault = self.root / "fault"
        # Embed absolute fixture paths: no host CLI is discovered or invoked by these shims.
        common = (f"#!{sys.executable}\nimport json, os, pathlib, shutil, sys, tarfile\n"
                  f"fixture = pathlib.Path({str(self.fixture)!r})\n"
                  f"fault = pathlib.Path({str(self.fault)!r})\n")
        self.stub("claude", common + f"calls = pathlib.Path({str(self.calls)!r})\n" + r'''
with calls.open('a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\n')
if sys.argv[1:3] == ['plugin', 'marketplace']:
    print('installer stdout before failure')
    if fault.exists() and fault.read_text() == 'installer':
        print('installer stderr retained', file=sys.stderr)
        sys.exit(42)
elif sys.argv[1:3] == ['plugin', 'install']:
    destination = pathlib.Path(os.environ['CLAUDE_CONFIG_DIR']) / 'plugins/cache/whichguy/skill-craft/fixture'
    shutil.copytree(fixture, destination)
    if fault.exists() and fault.read_text() == 'tree':
        (destination / 'README.md').write_text('corrupted installed bytes')
elif sys.argv[1:] == ['plugin', 'list', '--json']:
    print(json.dumps([{'id': 'skill-craft@whichguy', 'version': 'fixture', 'enabled': True}]))
else:
    sys.exit('unexpected fake Claude command')
''')
        self.stub("git", common + '''
args = sys.argv[1:]
if 'rev-parse' in args:
    print('fixture-origin-main')
elif 'archive' in args:
    with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as stream:
        stream.add(fixture, arcname='plugins/skill-craft')
elif args[:2] == ['init', '-q']:
    pathlib.Path(args[2]).mkdir()
elif 'commit' not in args:
    sys.exit('unexpected fake Git command')
''')
        self.stub("docker", f"#!{sys.executable}\nimport sys\nsys.exit(1)\n")
        self.python = self.bin / "selected Python"
        self.python.symlink_to(sys.executable)
        self.scratch = self.root / "scratch output"
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.defpath,
                        PYTHON=str(self.python), PYTHONDONTWRITEBYTECODE="1",
                        SKILL_CRAFT_CHECKOUT=str(self.root / "fake checkout"),
                        PROBE_INHERITED_SENTINEL="must disappear")

    def stub(self, name: str, source: str) -> None:
        compile(source, "fake " + name, "exec")
        target = self.bin / name
        target.write_text(source)
        target.chmod(0o755)

    def run_probe(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(ROOT / "test/published-install-smoke.py"),
                               str(self.scratch)], env=self.env, capture_output=True, text=True, timeout=60)

    def test_spaced_paths_selected_python_clean_environment_and_optional_skip(self) -> None:
        done = self.run_probe()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("PASS five hooks quiet without Python", done.stdout)
        self.assertIn("SKIP real old-interpreter check: Docker daemon unavailable", done.stdout)
        self.assertNotIn("PASS real old-interpreter", done.stdout)
        self.assertIn("PASS required published clean-install checks", done.stdout)
        commands = [json.loads(p.read_text()) for p in sorted(self.scratch.glob("*.command.json"))]
        cli = [args for args in commands if len(args) > 2 and args[1] == "-B"]
        self.assertEqual(len(cli), 2)
        self.assertTrue(all(Path(args[0]).resolve() == Path(sys.executable).resolve() for args in cli))
        self.assertEqual(len(self.calls.read_text().splitlines()), 3)

    def test_installer_failure_is_not_hidden_and_both_streams_are_retained(self) -> None:
        self.fault.write_text("installer")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("exit 42", done.stderr)
        self.assertEqual((self.scratch / "01.exit").read_text(), "42\n")
        self.assertIn("installer stdout", (self.scratch / "01.stdout").read_text())
        self.assertIn("installer stderr", (self.scratch / "01.stderr").read_text())
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)

    def test_installed_tree_corruption_fails_before_cli_checks(self) -> None:
        self.fault.write_text("tree")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("installed package differs", done.stderr)
        self.assertNotIn("PASS clean environment", done.stdout)

    def test_existing_scratch_is_preserved_without_calling_host(self) -> None:
        self.scratch.mkdir()
        marker = self.scratch / "keep"
        marker.write_text("user data")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(marker.read_text(), "user data")
        self.assertFalse(self.calls.exists())

    def test_missing_python_override_fails_before_calling_host(self) -> None:
        self.env["PYTHON"] = str(self.root / "absent Python")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("unavailable", done.stderr)
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.scratch.exists())

    def test_installed_modes_are_checked(self) -> None:
        (self.fixture / "skills/shiploop/scripts/shiploop-drive").chmod(0o644)
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("shiploop-drive mode 644", done.stderr)

    def test_published_guard_must_declare_one_two_part_floor(self) -> None:
        guard = self.fixture / "skills/shiploop/scripts/shiploop_pyfloor.py"
        guard.write_text("FLOOR = (3,)\n")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("published guard must declare one two-part FLOOR", done.stderr)

    def test_empty_workspace_packet_is_a_required_failure(self) -> None:
        entry = self.fixture / "skills/shiploop/scripts/shiploop"
        entry.write_text("#!/usr/bin/env python3\n")
        done = self.run_probe()
        self.assertEqual(done.returncode, 1)
        self.assertIn("empty packet", done.stderr)


    @contextmanager
    def retained_failure(self):
        """Keep new regression fixtures/logs when an assertion fails, including RED."""
        try:
            yield
        except BaseException as exc:
            if isinstance(exc, subprocess.TimeoutExpired):
                for suffix, data in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                    if isinstance(data, bytes):
                        data = data.decode(errors="replace")
                    (self.root / ("outer-timeout." + suffix)).write_text(data or "")
            retained = Path(tempfile.mkdtemp(prefix="published-probe-failure-"))
            shutil.copytree(self.root, retained / "fixture", symlinks=True)
            print("Retained failed probe: %s" % retained, file=sys.stderr)
            raise

    def deadline_probe(self, target: str = "claude-marketplace") -> subprocess.CompletedProcess:
        # Shorten only the deliberate stall, leaving setup commands at 180 seconds.
        # Wrap either implementation locally inside this disposable driver process.
        driver = r"""
import importlib.util, pathlib, subprocess, sys
spec = importlib.util.spec_from_file_location('manual_probe', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
target = sys.argv[3]
if target not in ('claude-marketplace', 'docker-run'):
    raise ValueError('unknown deadline target: %s' % target)
original = getattr(module, 'owned_run', subprocess.run)
def bounded(args, *positional, **kwargs):
    argv = [str(arg) for arg in args]
    command = pathlib.Path(argv[0]).name if argv else ''
    matches = (target == 'claude-marketplace' and command == 'claude'
               and argv[1:3] == ['plugin', 'marketplace']
               or target == 'docker-run' and command == 'docker'
               and argv[1:2] == ['run'])
    if matches:
        kwargs['timeout'] = 0.7
    return original(args, *positional, **kwargs)
if hasattr(module, 'owned_run'):
    module.owned_run = bounded
else:
    subprocess.run = bounded
sys.argv = [sys.argv[1], sys.argv[2]]
try:
    module.main()
except (ValueError, OSError, subprocess.SubprocessError) as exc:
    print('FAIL: %s' % exc, file=sys.stderr)
    sys.exit(1)
"""
        done = subprocess.run([sys.executable, "-B", "-c", driver,
                               str(ROOT / "test/published-install-smoke.py"), str(self.scratch), target],
                              env=self.env, capture_output=True, text=True, timeout=10)
        (self.root / "driver.stdout").write_text(done.stdout)
        (self.root / "driver.stderr").write_text(done.stderr)
        return done

    def pid_executing(self, pid: int) -> bool:
        state = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=1)
        # A zombie cannot execute or write the marker; kill(pid, 0) alone is misleading.
        return bool(state.stdout.strip()) and not state.stdout.strip().startswith("Z")

    def test_timeout_stops_owned_descendant_and_preserves_unrelated_sentinel(self) -> None:
        child_pid = self.root / "owned child.pid"
        marker = self.root / "delayed marker"
        child = ("import pathlib, time\n"
                 "time.sleep(2)\n"
                 f"pathlib.Path({str(marker)!r}).write_text('leaked')\n"
                 "time.sleep(2)\n")
        compile(child, "fake-claude-child", "exec")
        self.stub("claude", f"#!{sys.executable}\n" +
                  "import pathlib, subprocess, sys, time\n" +
                  f"child = subprocess.Popen([{sys.executable!r}, '-B', '-c', {child!r}], "
                  "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n" +
                  f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid))\n" +
                  "print('timeout stdout retained', flush=True)\n"
                  "print('timeout stderr retained', file=sys.stderr, flush=True)\n"
                  "time.sleep(5)\n")
        sentinel = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(9)"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with self.retained_failure():
                done = self.deadline_probe()
                self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertIn("timed out", done.stderr)
                self.assertEqual((self.scratch / "01.exit").read_text(), "TIMEOUT\n")
                self.assertIn("timeout stdout retained", (self.scratch / "01.stdout").read_text())
                self.assertIn("timeout stderr retained", (self.scratch / "01.stderr").read_text())
                self.assertTrue(child_pid.is_file(), "fake Claude never started its child")
                self.assertFalse(self.pid_executing(int(child_pid.read_text())), "owned child survived timeout")
                self.assertFalse(marker.exists(), "owned child wrote after probe timeout")
                self.assertIsNone(sentinel.poll(), "unrelated sentinel was stopped")
        finally:
            # Even intentional RED cleans only the explicitly recorded test PID.
            if child_pid.is_file():
                pid = int(child_pid.read_text())
                if self.pid_executing(pid):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            if sentinel.poll() is None:
                sentinel.kill()
            sentinel.wait(timeout=1)

    def test_python_wrapper_is_selected_once_and_cli_uses_actual_interpreter(self) -> None:
        launches = self.root / "wrapper launches"
        wrapper = self.bin / "Python wrapper"
        self.stub(wrapper.name, f"#!{sys.executable}\n" +
                  "import os, pathlib, sys\n" +
                  f"counter = pathlib.Path({str(launches)!r})\n" +
                  "count = int(counter.read_text()) + 1 if counter.exists() else 1\n"
                  "counter.write_text(str(count))\n"
                  "if count > 3: sys.exit('wrapper selection loop')\n" +
                  f"os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n")
        self.env["PYTHON"] = str(wrapper)
        with self.retained_failure():
            done = subprocess.run([sys.executable, "-B", str(ROOT / "test/published-install-smoke.py"),
                                   str(self.scratch)], env=self.env, capture_output=True, text=True, timeout=9)
            (self.root / "driver.stdout").write_text(done.stdout)
            (self.root / "driver.stderr").write_text(done.stderr)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("PASS required published clean-install checks", done.stdout)
            self.assertEqual(launches.read_text(), "1")
            commands = [json.loads(p.read_text()) for p in self.scratch.glob("*.command.json")]
            cli = [args for args in commands if len(args) > 2 and args[1] == "-B"]
            self.assertEqual(len(cli), 2)
            self.assertTrue(all(Path(args[0]) == Path(sys.executable).resolve() for args in cli))

    def test_invalid_python_wrapper_fails_clearly_before_install(self) -> None:
        self.stub("invalid Python", f"#!{sys.executable}\nprint('not an interpreter path')\n")
        self.env["PYTHON"] = str(self.bin / "invalid Python")
        with self.retained_failure():
            done = subprocess.run([sys.executable, "-B", str(ROOT / "test/published-install-smoke.py"),
                                   str(self.scratch)], env=self.env, capture_output=True, text=True, timeout=9)
            (self.root / "driver.stdout").write_text(done.stdout)
            (self.root / "driver.stderr").write_text(done.stderr)
            self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("invalid PYTHON interpreter selection", done.stderr)
            self.assertFalse(self.calls.exists())
            self.assertFalse(self.scratch.exists())

    def test_docker_timeout_removes_only_recorded_owned_container(self) -> None:
        calls = self.root / "docker calls"
        cid = "a" * 64
        self.stub("docker", f"#!{sys.executable}\n" +
                  "import json, pathlib, sys, time\n" +
                  f"calls = pathlib.Path({str(calls)!r})\n" + r"""
args = sys.argv[1:]
with calls.open('a') as stream:
    stream.write(json.dumps(args) + '\n')
if args[0] == 'run':
    if '--cidfile' in args:
        pathlib.Path(args[args.index('--cidfile') + 1]).write_text('a' * 64 + '\n')
    print('fake container stdout', flush=True)
    print('fake container stderr', file=sys.stderr, flush=True)
    time.sleep(5)
elif args[0] not in ('info', 'image', 'rm'):
    sys.exit('unexpected fake Docker command')
""")
        with self.retained_failure():
            done = self.deadline_probe("docker-run")
            self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("TIMEOUT\n", [p.read_text() for p in self.scratch.glob("*.exit")])
            commands = [json.loads(line) for line in calls.read_text().splitlines()]
            self.assertEqual([args for args in commands if args[0] == "rm"], [["rm", "--force", cid]])
            run = next(args for args in commands if args[0] == "run")
            self.assertIn("--pull=never", run)
            self.assertIn("--network=none", run)
            self.assertTrue(Path(run[run.index("--cidfile") + 1]).resolve().is_relative_to(self.scratch.resolve()))
            cleanup = json.loads((self.scratch / "container-cleanup.json").read_text())
            self.assertEqual(cleanup, {"cid": cid, "returncode": 0})
            self.assertTrue(any("fake container stdout" in p.read_text() for p in self.scratch.glob("*.stdout")))
            self.assertTrue(any("fake container stderr" in p.read_text() for p in self.scratch.glob("*.stderr")))


    def test_failed_docker_without_owned_cid_never_removes_a_container(self) -> None:
        calls = self.root / "docker calls"
        self.stub("docker", f"#!{sys.executable}\n" +
                  "import json, pathlib, sys\n" +
                  f"calls = pathlib.Path({str(calls)!r})\n" + r"""
args = sys.argv[1:]
with calls.open('a') as stream:
    stream.write(json.dumps(args) + '\n')
if args[0] == 'run':
    print('fake Docker failed before recording CID', file=sys.stderr)
    sys.exit(42)
""")
        with self.retained_failure():
            done = self.deadline_probe()
            self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("old-interpreter container failed", done.stderr)
            commands = [json.loads(line) for line in calls.read_text().splitlines()]
            self.assertTrue(any(args[0] == "run" for args in commands))
            self.assertFalse(any(args[0] == "rm" for args in commands))
            self.assertFalse((self.scratch / "old-interpreter.cid").exists())
            self.assertFalse((self.scratch / "container-cleanup.json").exists())
            self.assertIn("42\n", [p.read_text() for p in self.scratch.glob("*.exit")])

if __name__ == "__main__":
    unittest.main()
