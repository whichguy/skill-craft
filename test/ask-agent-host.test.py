#!/usr/bin/env python3
"""Ask Agent's host command and binding data: detection from exact environment names, the data's shape, and its agreement with the card,
the host capabilities prose and ShipLoop's own detector.

Hermetic: the command runs against made-up environments; no native agent runs.
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
SHIPLOOP_GRANTS = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_grants.py"


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
        cls.host = load_module(SCRIPT, "ask_agent_host_under_test")
        cls.data = cls.host.load()

    def report(self, **environ: str) -> dict:
        return self.host.report(environ, self.data)

    def test_each_marker_alone_names_its_host(self) -> None:
        for host, names in self.data["detect"]["markers"].items():
            for name in names:
                with self.subTest(host=host, marker=name):
                    found = self.report(**{name: "1"})
                    self.assertEqual((found["host"], found["detected_by"], found["also_present"]), (host, [name], []))
                    self.assertEqual(found["binding"], self.data["hosts"][host])
                    self.assertEqual(found["section"], self.data["hosts"][host]["section"])

    def test_innermost_host_wins_and_the_others_are_reported(self) -> None:
        cases = [({"CLAUDECODE": "1", "CODEX_THREAD_ID": "t"}, "codex", ["CLAUDECODE"]),
                 ({"CLAUDECODE": "1", "GROK_SESSION_ID": "s"}, "grok", ["CLAUDECODE"]),
                 ({"GROK_AGENT": "1", "CODEX_SANDBOX": "seatbelt"}, "codex", ["GROK_AGENT"]),
                 ({"CLAUDECODE": "1", "GROK_AGENT": "1", "CODEX_THREAD_ID": "t"}, "codex", ["CLAUDECODE", "GROK_AGENT"])]
        for environ, host, others in cases:
            with self.subTest(environ=environ):
                found = self.report(**environ)
                self.assertEqual((found["host"], found["also_present"]), (host, others))

    def test_prefixes_and_empty_values_are_not_markers(self) -> None:
        # Codex plugin variables are set in Claude Code and Grok sessions (journal E10): a CODEX_ prefix match would call both Codex.
        leak = {"CODEX_COMPANION_SESSION_ID": "x", "CODEX_COMPANION_TRANSCRIPT_PATH": "/tmp/t"}
        self.assertEqual(self.report(**leak)["host"], "unknown")
        self.assertEqual(self.report(CLAUDECODE="1", **leak)["host"], "claude")
        self.assertEqual(self.report(GROK_AGENT="1", **leak)["host"], "grok")
        self.assertEqual(self.report(CODEX_THREAD_ID="")["host"], "unknown")
        self.assertEqual(self.report(GROK_AGENT="", CLAUDECODE="1")["host"], "claude")

    def test_unknown_host_has_no_binding_and_points_to_the_prose(self) -> None:
        found = self.report(PATH="/usr/bin", TERM="xterm")
        self.assertEqual((found["host"], found["binding"], found["section"]), ("unknown", None, "references/host-capabilities.md"))
        self.assertIn("live native schema", found["next"])
        self.assertIn("live native tool schema wins", found["authority"])

    def test_agrees_with_shiploop_detect_host_for_every_marker_combination(self) -> None:
        # Two copies of the same eight lines must stay in step: ShipLoop's grant check names the host with its own.
        shiploop = load_module(SHIPLOOP_GRANTS, "shiploop_grants_under_test")
        names = sorted(name for group in self.data["detect"]["markers"].values() for name in group)
        for size in range(len(names) + 1):
            for subset in itertools.combinations(names, size):
                environ = {name: "1" for name in subset}
                with self.subTest(markers=subset):
                    self.assertEqual(self.host.report(environ, self.data)["host"], shiploop.detect_host(environ))

    def test_command_prints_one_compact_json_line_from_a_path_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ask agent 'host' ") as temp:
            package = Path(temp) / "ask-agent package"
            (package / "references").mkdir(parents=True)
            (package / "scripts").mkdir()
            shutil.copy(DATA, package / "references" / "host-bindings.json")
            shutil.copy(SCRIPT, package / "scripts" / "ask_agent_host.py")
            env = {"PATH": os.environ["PATH"], "GROK_AGENT": "1", "GROK_SESSION_ID": "abc123", "PYTHONDONTWRITEBYTECODE": "1"}
            before = sorted(str(p.relative_to(package)) for p in package.rglob("*"))
            done = subprocess.run([sys.executable, str(package / "scripts" / "ask_agent_host.py")], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual((done.returncode, done.stderr), (0, ""))
            self.assertEqual(len(done.stdout.splitlines()), 1)
            value = json.loads(done.stdout)
            self.assertEqual((value["host"], value["detected_by"]), ("grok", ["GROK_AGENT", "GROK_SESSION_ID"]))
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
        self.assertEqual(self.data["schema"], "ask-agent/host-bindings/v1")
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
                self.assertTrue(binding["name"] and binding["collect"])
                self.assertTrue(binding["tested"] and all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in binding["tested"]))
                self.assertTrue(binding["tools"]["spawn"] and all(isinstance(t, str) and t for group in binding["tools"].values() for t in group))
                self.assertIsInstance(binding["spawn_arguments"], dict)
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
            for argument in binding["spawn_arguments"]:
                with self.subTest(host=host, argument=argument):
                    self.assertRegex(text, rf"`?{re.escape(argument)}[`=:]")

    def test_the_prose_states_the_numbers_the_data_carries(self) -> None:
        codex, grok = self.data["hosts"]["codex"], self.data["hosts"]["grok"]
        text = " ".join(self.prose["codex"].split())
        self.assertEqual(codex["capacity"], {"workers": 3, "slots": 4, "parent_holds": 1})
        self.assertIn("four concurrent agents including the parent", text)
        self.assertIn("at most three workers at once", text)
        self.assertIn(f"timeout_ms: {codex['observation_timeout_ms']}", text)
        self.assertEqual(codex["observation_timeout_ms"], grok["observation_timeout_ms"])   # both come from the lifecycle's two-minute cadence
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
