#!/usr/bin/env python3
"""Ask Agent & ShipLoop shared host-bindings/v2: detection from exact environment names,
schema shape, parity between packages, prose alignment, and ShipLoop emit-time host hints.

Hermetic: runs against made-up environments; no native agent runs.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ask-agent"
SCRIPT = SKILL / "scripts" / "ask_agent_host.py"
DATA = SKILL / "references" / "host-bindings.json"
PROSE = SKILL / "references" / "host-capabilities.md"
CARD = SKILL / "SKILL.md"
SHIPLOOP_SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
SHIPLOOP_DATA = ROOT / "skills" / "shiploop" / "references" / "host-bindings.json"
SHIPLOOP_BINDINGS = SHIPLOOP_SCRIPTS / "shiploop_host_bindings.py"
SHIPLOOP_GRANTS = SHIPLOOP_SCRIPTS / "shiploop_grants.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


def sections(text: str) -> dict[str, str]:
    """The prose by second-level heading anchor."""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {slug(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


class HostCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if str(SHIPLOOP_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SHIPLOOP_SCRIPTS))
        cls.host = load_module(SCRIPT, "ask_agent_host_under_test")
        cls.sl_bindings = load_module(SHIPLOOP_BINDINGS, "shiploop_host_bindings_under_test")
        cls.sl_grants = load_module(SHIPLOOP_GRANTS, "shiploop_grants_under_test")
        cls.data = cls.host.load()

    def report(self, **environ: str) -> dict:
        return self.host.report(environ, self.data)

    def test_each_marker_alone_names_its_host(self) -> None:
        for host, names in self.data["detect"]["markers"].items():
            if host in ("grok", "opencode", "cursor"):
                continue
            for name in names:
                with self.subTest(host=host, marker=name):
                    found = self.report(**{name: "1"})
                    self.assertEqual((found["host"], found["detected_by"], found["also_present"]), (host, [name], []))
                    self.assertEqual(found["binding"], self.data["hosts"][host])
                    self.assertEqual(found["section"], self.data["hosts"][host]["section"])

    def test_innermost_host_wins_and_the_others_are_reported(self) -> None:
        cases = [
            ({"CLAUDECODE": "1", "CODEX_THREAD_ID": "t"}, "codex", ["CLAUDECODE"]),
            ({"ANTIGRAVITY_AGENT": "1", "CODEX_THREAD_ID": "t"}, "codex", ["ANTIGRAVITY_AGENT"]),
            ({"ANTIGRAVITY_AGENT": "1", "CLAUDECODE": "1"}, "claude", ["ANTIGRAVITY_AGENT"]),
        ]
        for environ, host, others in cases:
            with self.subTest(environ=environ):
                found = self.report(**environ)
                self.assertEqual((found["host"], found["also_present"]), (host, others))

    def test_prefixes_and_empty_values_are_not_markers(self) -> None:
        # Codex plugin variables are set in Claude Code sessions (journal E10): a CODEX_ prefix match would misdetect Claude as Codex.
        leak = {"CODEX_COMPANION_SESSION_ID": "x", "CODEX_COMPANION_TRANSCRIPT_PATH": "/tmp/t"}
        self.assertEqual(self.report(**leak)["host"], "unknown")
        self.assertEqual(self.report(CLAUDECODE="1", **leak)["host"], "claude")
        self.assertEqual(self.report(CODEX_THREAD_ID="")["host"], "unknown")
        self.assertEqual(self.report(ANTIGRAVITY_AGENT="", ANTIGRAVITY_CONVERSATION_ID="")["host"], "unknown")
        self.assertEqual(self.report(ANTIGRAVITY_AGENT="1")["host"], "antigravity")

    def test_unknown_host_has_no_binding_and_points_to_the_prose(self) -> None:
        found = self.report(PATH="/usr/bin", TERM="xterm")
        self.assertEqual((found["host"], found["binding"], found["section"]), ("unknown", None, "references/host-capabilities.md"))
        self.assertIn("live native tool schema", found["next"])
        self.assertIn("live native tool schema wins", found["authority"])

    def test_shiploop_and_ask_agent_bindings_files_are_byte_identical(self) -> None:
        self.assertTrue(SHIPLOOP_DATA.is_file())
        self.assertEqual(DATA.read_bytes(), SHIPLOOP_DATA.read_bytes(),
                         "skills/shiploop/references/host-bindings.json must stay byte-identical to skills/ask-agent/references/host-bindings.json")

    def test_agrees_with_shiploop_detect_host_and_host_bindings_for_every_marker_combination(self) -> None:
        names = sorted(name for group in self.data["detect"]["markers"].values() for name in group)
        for size in range(len(names) + 1):
            for subset in itertools.combinations(names, size):
                environ = {name: "1" for name in subset}
                expected = self.host.report(environ, self.data)["host"]
                with self.subTest(markers=subset):
                    self.assertEqual(expected, self.sl_grants.detect_host(environ))
                    self.assertEqual(expected, self.sl_bindings.detect_host(environ))

    def test_shiploop_host_bindings_helpers_and_hints(self) -> None:
        self.assertTrue(self.sl_bindings.supports_fork("claude"))
        self.assertTrue(self.sl_bindings.supports_fork("codex"))
        self.assertFalse(self.sl_bindings.supports_fork("antigravity"))
        self.assertFalse(self.sl_bindings.supports_fork("unknown"))
        self.assertEqual(self.sl_bindings.worker_capacity("codex"), 3)
        self.assertEqual(self.sl_bindings.worker_capacity("claude"), 4)
        self.assertEqual(self.sl_bindings.worker_capacity("antigravity"), 4)

        codex_hint = self.sl_bindings.host_hint({"CODEX_THREAD_ID": "t1"}, worktree="/tmp/wt")
        self.assertIn("Host hint (codex):", codex_hint)
        self.assertIn('fork_turns="none"', codex_hint)
        self.assertIn("120000", codex_hint)
        self.assertIn("live native tool schema wins", codex_hint)

        override_hint = self.sl_bindings.host_hint({"CODEX_THREAD_ID": "t1"}, host_override="claude", worktree="/tmp/wt")
        self.assertIn("Host hint (claude):", override_hint)
        self.assertIn('cd "/tmp/wt" &&', override_hint)

        agy_hint = self.sl_bindings.host_hint({"ANTIGRAVITY_AGENT": "1"}, worktree="/tmp/wt")
        self.assertIn("Host hint (antigravity):", agy_hint)
        self.assertIn("invoke_subagent", agy_hint)
        self.assertIn('Workspace="inherit"', agy_hint)
        self.assertIn('cd "/tmp/wt" &&', agy_hint)

        unknown_hint = self.sl_bindings.host_hint({})
        self.assertIn("Host hint (unknown):", unknown_hint)

    def test_command_prints_one_compact_json_line_from_a_path_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ask agent 'host' ") as temp:
            package = Path(temp) / "ask-agent package"
            (package / "references").mkdir(parents=True)
            (package / "scripts").mkdir()
            shutil.copy(DATA, package / "references" / "host-bindings.json")
            shutil.copy(SCRIPT, package / "scripts" / "ask_agent_host.py")
            env = {"PATH": os.environ["PATH"], "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "abc123", "PYTHONDONTWRITEBYTECODE": "1"}
            before = sorted(str(p.relative_to(package)) for p in package.rglob("*"))
            done = subprocess.run([sys.executable, str(package / "scripts" / "ask_agent_host.py")], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual((done.returncode, done.stderr), (0, ""))
            self.assertEqual(len(done.stdout.splitlines()), 1)
            value = json.loads(done.stdout)
            self.assertEqual((value["host"], value["detected_by"]), ("claude", ["CLAUDECODE"]))
            self.assertEqual(done.stdout.strip(), json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            self.assertEqual(sorted(str(p.relative_to(package)) for p in package.rglob("*")), before)   # it writes nothing

    def test_unreadable_binding_data_is_a_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ask-agent-host-") as temp:
            package = Path(temp)
            (package / "references").mkdir()
            (package / "scripts").mkdir()
            (package / "references" / "host-bindings.json").write_text("{not json")
            shutil.copy(SCRIPT, package / "scripts" / "ask_agent_host.py")
            done = subprocess.run([sys.executable, str(package / "scripts" / "ask_agent_host.py")], env={"PATH": os.environ["PATH"]},
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual((done.returncode, done.stdout), (2, ""))
            self.assertEqual(json.loads(done.stderr)["code"], "bindings_unreadable")


class BindingDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(DATA.read_text())
        cls.prose = sections(PROSE.read_text())

    def test_every_host_has_the_fields_the_command_and_the_prose_rely_on(self) -> None:
        self.assertEqual(self.data["schema"], "skill-craft/host-bindings/v2")
        markers, order = self.data["detect"]["markers"], self.data["detect"]["order"]
        self.assertEqual(sorted(order), sorted(markers))
        names = [name for group in markers.values() for name in group]
        self.assertEqual(len(names), len(set(names)), "a marker may name only one host")
        self.assertEqual(sorted(self.data["hosts"]), sorted(markers))
        for host, binding in self.data["hosts"].items():
            with self.subTest(host=host):
                path, _, anchor = binding["section"].partition("#")
                self.assertEqual(path, "references/host-capabilities.md")
                self.assertIn(anchor, self.prose, "the section anchor must be a heading of the host capabilities")
                self.assertTrue(binding["name"] and binding["collect"] and binding["hint"])
                self.assertIn(binding["status"], ("qualified", "pilot-ide", "unqualified"))
                if binding["status"] == "qualified":
                    self.assertTrue(binding["tested"] and all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in binding["tested"]))
                elif binding["status"] == "pilot-ide":
                    self.assertTrue(binding["tested"])
                self.assertTrue(binding["tools"]["spawn"] and all(isinstance(t, str) and t for group in binding["tools"].values() for t in group))
                self.assertIn(binding["serial_mode"], ("foreground", "async-wait", "async-reactive"))
                self.assertIn(binding["parallel_mode"], ("foreground", "async-wait", "async-reactive"))
                self.assertIsInstance(binding["cwd_on_spawn"], bool)
                self.assertIsInstance(binding["spawn_arguments"], dict)
                self.assertIsInstance(binding["fresh_args"], dict)
                self.assertIsInstance(binding["background_args"], dict)
                self.assertIsInstance(binding["forbidden_fresh_args"], list)
                if binding["fork_args"] is not None:
                    self.assertIsInstance(binding["fork_args"], dict)
                capacity = binding["capacity"]
                if capacity is not None:
                    self.assertEqual(capacity["workers"], capacity["slots"] - capacity["parent_holds"])
                    self.assertGreater(capacity["workers"], 0)
                if "wait" in binding["tools"]:
                    self.assertGreater(binding["observation_timeout_ms"], 0)

    def test_the_prose_names_every_tool_and_argument_the_data_names(self) -> None:
        for host, binding in self.data["hosts"].items():
            text = self.prose[binding["section"].partition("#")[2]]
            for tool in (t for group in binding["tools"].values() for t in group):
                with self.subTest(host=host, tool=tool):
                    self.assertRegex(text, rf"\b{re.escape(tool)}\b")
            all_args = set(binding["spawn_arguments"]) | set(binding["fresh_args"]) | set(binding["background_args"]) | set(binding["forbidden_fresh_args"])
            if binding["fork_args"]:
                all_args |= set(binding["fork_args"])
            for argument in sorted(all_args):
                with self.subTest(host=host, argument=argument):
                    self.assertRegex(text, rf"`?{re.escape(argument)}[`=:]")

    def test_the_prose_states_the_numbers_the_data_carries(self) -> None:
        codex = self.data["hosts"]["codex"]
        text = " ".join(self.prose["codex"].split())
        self.assertEqual(codex["capacity"], {"workers": 3, "slots": 4, "parent_holds": 1})
        self.assertIn("four concurrent agents including the parent", text)
        self.assertIn("at most three workers at once", text)
        self.assertIn(f"timeout_ms: {codex['observation_timeout_ms']}", text)
        lifecycle = " ".join((SKILL / "references" / "native-lifecycle.md").read_text().split())
        self.assertIn("about every two minutes", lifecycle)
        self.assertEqual(codex["observation_timeout_ms"], 2 * 60 * 1000)

    def test_the_card_and_the_prose_send_the_parent_to_the_command(self) -> None:
        card, prose = " ".join(CARD.read_text().split()), " ".join(PROSE.read_text().split())
        for text in (card, prose):
            self.assertIn("scripts/ask_agent_host.py", text)
        self.assertIn("before the first native launch of a session", card.lower())
        self.assertLess(card.index("scripts/ask_agent_host.py"), card.index("Read the matching route in [Host capabilities]"))
        self.assertIn("the host binding's `capacity`", card)
        self.assertIn("The live native tool schema wins", self.data["measured"]["authority"])
        self.assertIn("the live schema wins where they differ", prose)


if __name__ == "__main__":
    unittest.main()
