#!/usr/bin/env python3
"""A frozen brownfield case for current, historical and deferred user-summary status."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test" / "fixtures" / "quality"))

import brownfield  # noqa: E402
import quality  # noqa: E402
import reference_user_summary as summaries  # noqa: E402
import run  # noqa: E402

CASES = json.loads(run.CASES.read_text())
CASE_NAME = "user-summary-status"
CASE = CASES[CASE_NAME]
FIXTURE = brownfield.FIXTURES / "node-user-teams-status"
CHECKS = CASE["quality"]["acceptance"]["checks"]
CHECK_IDS = [row["id"] for row in CHECKS]
STATUS_IDS = {"summary-status-records", "summary-status-current", "summary-status-history", "summary-status-deferred"}
FROZEN_HISTORY = "As of 2026-10-31: R-3 was accepted; implementation was pending; verification was not run."
SUMMARY_IDS = {
    "summary-total-by-team", "summary-uses-user-filters", "summary-unpaginated-ignores",
    "summary-no-matches", "summary-team-case-sensitive",
}
BASE_EXPECTED_FAILURES = SUMMARY_IDS | {"summary-status-current"}
EXPECTED_FAILURES = {
    "base": BASE_EXPECTED_FAILURES,
    "reference": set(),
    "alternative": set(),
    "plain-layout": set(),
    "reordered-fields": set(),
    "bulleted-fields": set(),
    "bold-fields": set(),
    "nested-fields": set(),
    "spaced-inline-fields": set(),
    "ws-proof-line": set(),
    "ws-proof-blank-line": set(),
    "fenced-heading": set(),
    "history-id-heading": set(),
    "history-blockquote-spacer": set(),
    "history-adjacent-bullets": set(),
    "history-new-blockquote-paragraph": set(),
    "history-old-date-mentioned-again": set(),
    "node-context": set(),
    "glob-context": set(),
    "other-kind-context": set(),
    "stale-current": {"summary-status-current"},
    "duplicate-current": {"summary-status-current"},
    "history-erased": {"summary-status-history"},
    "history-edited": {"summary-status-history"},
    "deferred-completed": {"summary-status-deferred"},
    "missing-current-field": {"summary-status-current"},
    "unknown-current-field": {"summary-status-current"},
    "absolute-source": {"summary-status-current"},
    "escaping-source": {"summary-status-current"},
    "absolute-verification": {"summary-status-current"},
    "escaping-verification": {"summary-status-current"},
    "source-wrong-kind-only": {"summary-status-current"},
    "verification-wrong-kind-only": {"summary-status-current"},
    "missing-source-evidence": {"summary-status-current"},
    "missing-verification-evidence": {"summary-status-current"},
    "retired-current": {"summary-status-records", "summary-status-current"},
    "summary-broken": {"summary-uses-user-filters", "summary-no-matches", "summary-team-case-sensitive"},
}

BASE_TEST_COMMANDS = [
    'python3 "$E2E_CHECKS/base_tests.py" pristine node-user-teams-status',
    'python3 "$E2E_CHECKS/base_tests.py" suite node-user-teams-status',
]
CURRENT_IMPLEMENTATION = "implemented — src/server.js"
CURRENT_VERIFICATION = "passed — test/user-summary.test.js"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected one {old!r}, found {count}")
    return text.replace(old, new)


def edit_spec(folder: Path, old: str, new: str, label: str) -> None:
    path = folder / "docs/shiploop/spec.md"
    path.write_text(replace_once(path.read_text(), old, new, label))


def update_current(spec: str, implementation: str = CURRENT_IMPLEMENTATION,
                   verification: str = CURRENT_VERIFICATION,
                   layout: str = "plain") -> str:
    previous = "Current implementation: pending\nCurrent verification: not run"
    if layout == "plain":
        fields = f"Current implementation: {implementation}\nCurrent verification: {verification}"
    elif layout == "reordered":
        fields = f"Current verification: {verification}\nCurrent implementation: {implementation}"
    elif layout == "bulleted":
        fields = f"- Current implementation: {implementation}\n- Current verification: {verification}"
    elif layout == "bold":
        fields = f"**Current implementation:** {implementation}\n**Current verification:** {verification}"
    elif layout == "nested":
        fields = ("#### Current state\n\n"
                  f"Current implementation: `{implementation.replace(' — ', '` — `')}`\n\n"
                  f"Current verification: `{verification.replace(' — ', '` — `')}`")
    elif layout == "spaced-inline":
        fields = (f"  **Current verification:**   `{verification}`\n\n"
                  f"  - **Current implementation:**   `{implementation.replace(' — ', '` — `')}`")
    else:
        raise AssertionError(f"unknown field layout {layout!r}")
    return replace_once(spec, previous, fields, f"{layout} status fields")


def product_with_docs(root: Path, name: str, variant: str = "reference", layout: str | None = None,
                      defect: str | None = None, implementation: str = CURRENT_IMPLEMENTATION,
                      verification: str = CURRENT_VERIFICATION, fenced_heading: bool = False,
                      history_id_heading: bool = False) -> Path:
    folder = root / name
    summaries.build(folder, variant)
    shutil.copytree(FIXTURE / "docs/shiploop", folder / "docs/shiploop", dirs_exist_ok=True)
    spec_path = folder / "docs/shiploop/spec.md"
    spec = spec_path.read_text()
    if layout is not None:
        spec = update_current(spec, implementation, verification, layout)
    elif defect != "stale-current":
        spec = update_current(spec, implementation, verification)
    if fenced_heading:
        sample = "```markdown\n### R-4 Example only\nRequirement: this is inside a code sample\n```\n\n### R-4 CSV export"
        spec = replace_once(spec, "### R-4 CSV export", sample, "fenced example heading")
    if history_id_heading:
        spec = replace_once(spec, f"## History\n\n> {FROZEN_HISTORY}",
                            f"## History\n\n### R-3 Earlier state\n\n> {FROZEN_HISTORY}",
                            "historical requirement heading")
    if defect == "duplicate-current":
        spec = replace_once(spec, "### R-4 CSV export", "Current implementation: pending\n\n### R-4 CSV export",
                            "contradictory appended current field")
    elif defect == "history-erased":
        spec = replace_once(spec, f"## History\n\n> {FROZEN_HISTORY}\n", "", "history erasure")
    elif defect == "history-edited":
        spec = replace_once(spec, "implementation was pending", "implementation was complete", "history edit")
    elif defect == "deferred-completed":
        spec = replace_once(spec, "Status: deferred", "Status: accepted", "deferred status")
        spec = replace_once(spec, "Current implementation: not started",
                            "Current implementation: implemented in src/server.js", "deferred implementation")
        spec = replace_once(spec, "Current verification: not run",
                            "Current verification: passed by test/user-summary.test.js", "deferred verification")
    elif defect == "missing-current-field":
        spec = replace_once(spec, f"Current verification: {CURRENT_VERIFICATION}\n", "", "missing verification")
    elif defect == "unknown-current-field":
        spec = replace_once(spec, "Current verification: passed — test/user-summary.test.js",
                            "Current evidence: passed — test/user-summary.test.js", "unknown current field")
    elif defect == "absolute-source":
        spec = replace_once(spec, "Current implementation: implemented — src/server.js",
                            "Current implementation: implemented — /src/server.js", "absolute source path")
    elif defect == "escaping-source":
        spec = replace_once(spec, "Current implementation: implemented — src/server.js",
                            "Current implementation: implemented — ../src/server.js", "escaping source path")
    elif defect == "absolute-verification":
        spec = replace_once(spec, "Current verification: passed — test/user-summary.test.js",
                            "Current verification: passed — /test/user-summary.test.js", "absolute test path")
    elif defect == "escaping-verification":
        spec = replace_once(spec, "Current verification: passed — test/user-summary.test.js",
                            "Current verification: passed — ../test/user-summary.test.js", "escaping test path")
    elif defect == "source-wrong-kind-only":
        spec = replace_once(spec, "Current implementation: implemented — src/server.js",
                            "Current implementation: implemented — test/user-summary.test.js", "source points only to a test")
    elif defect == "verification-wrong-kind-only":
        spec = replace_once(spec, "Current verification: passed — test/user-summary.test.js",
                            "Current verification: passed — src/server.js", "verification points only to source")
    elif defect == "missing-source-evidence":
        spec = replace_once(spec, "Current implementation: implemented — src/server.js",
                            "Current implementation: implemented — src/missing.js", "missing source evidence")
    elif defect == "missing-verification-evidence":
        spec = replace_once(spec, "Current verification: passed — test/user-summary.test.js",
                            "Current verification: passed — test/missing.test.js", "missing verification evidence")
    elif defect == "retired-current":
        start = spec.index("### R-3 User summary\n")
        end = spec.index("### R-4 CSV export\n", start)
        retired = spec[start:end].rstrip()
        spec = spec[:start] + spec[end:]
        spec = replace_once(spec, "## History\n", f"## Retired\n\n{retired}\n\n## History\n",
                            "retired active requirement")
    spec_path.write_text(spec)
    return folder


def modular_alternative(root: Path) -> Path:
    """An independently structured summary in its own source and test files over the pinned team base."""
    folder = summaries.build(root / "alternative", "reference")
    server_path = folder / "src/server.js"
    server = server_path.read_text()
    start = server.index("function summaryAnswer(query) {")
    end = server.index("\n}\n", start) + 2
    server = server[:start] + server[end:]
    server = replace_once(server, "const { findUsers, getUser, listUsers } = require('./users');\n",
                          "const { findUsers, getUser, listUsers } = require('./users');\n"
                          "const { summarize } = require('./summary');\n", "summary module import")
    server = replace_once(server, "summaryAnswer(url.searchParams)", "summarize(url.searchParams)", "summary module route")
    server_path.write_text(server)
    (folder / "src/summary.js").write_text("""'use strict';

const { findUsers, listUsers } = require('./users');

function summarize(query) {
  const named = query.has('name') ? findUsers(query.get('name')) : listUsers();
  const matching = query.has('team') ? named.filter((user) => user.team === query.get('team')) : named;
  const counts = new Map();
  for (const user of matching) counts.set(user.team, (counts.get(user.team) || 0) + 1);
  return { total: matching.length, by_team: Object.fromEntries(counts) };
}

module.exports = { summarize };
""")
    test_path = folder / "test/user-summary.test.js"
    test_path.rename(folder / "test/summary-endpoint.test.js")
    shutil.copytree(FIXTURE / "docs/shiploop", folder / "docs/shiploop", dirs_exist_ok=True)
    spec_path = folder / "docs/shiploop/spec.md"
    spec_path.write_text(update_current(spec_path.read_text(),
                                        "complete — src/summary.js",
                                        "passed — test/summary-endpoint.test.js"))
    return folder


def copy_base(destination: Path) -> Path:
    shutil.copytree(FIXTURE, destination)
    return destination


def acceptance(folder: Path, logs: Path) -> dict:
    return quality.acceptance(folder, CASE["quality"]["acceptance"], groups=set(), stop=lambda: None,
                              logs=logs, ports=CASE["quality"].get("refuse_ports", ()))


def check_base_tests(folder: Path, subcommand: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "test/shiploop_e2e/checks/base_tests.py"), subcommand,
                           "node-user-teams-status"], cwd=folder, capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL)


class CaseDeclarationTest(unittest.TestCase):
    def test_standalone_case_pins_its_hand_authored_base_and_reexports_summary_acceptance(self) -> None:
        self.assertEqual(CASE["style"], "brownfield")
        self.assertNotIn("follows", CASE)
        self.assertEqual(CASE["base"]["fixture"], "node-user-teams-status")
        self.assertEqual(brownfield.digest(FIXTURE), CASE["base"]["digest"])
        self.assertEqual(brownfield.resolve(CASE), FIXTURE)
        self.assertEqual(CASE["checks"][:2], BASE_TEST_COMMANDS)
        self.assertIn("GET /users/summary", CASE["prompt"])
        self.assertIn("same `name` and `team` filters", CASE["prompt"])
        self.assertIn("project documents", CASE["prompt"])
        self.assertIn("dated history", CASE["prompt"])
        self.assertIn("deferred", CASE["prompt"])

        module = load_module(ROOT / "test/shiploop_e2e/checks/user_summary_status_accept.py", "status_case_decl")
        self.assertEqual(list(module.CHECKS), CHECK_IDS)
        prior = json.loads(run.CASES.read_text())["user-summary"]["quality"]["acceptance"]["checks"]
        self.assertEqual(CHECK_IDS[:len(prior)], [row["id"] for row in prior])
        self.assertEqual(set(CHECK_IDS[len(prior):]), STATUS_IDS)
        self.assertEqual(len(CHECK_IDS), len(set(CHECK_IDS)))
        self.assertEqual(run.case_quality(CASE_NAME)["acceptance"]["module"], "user_summary_status_accept")
        args = type("Args", (), {"prompt": None, "case": CASE_NAME, "check": None})
        _, prompt, commands, _ = run.load_case(args)
        self.assertEqual(prompt, CASE["prompt"])
        self.assertEqual(commands, CASE["checks"])

    def test_fixture_starts_with_live_team_behavior_and_pending_summary_status(self) -> None:
        self.assertTrue((FIXTURE / "test/user-listing.test.js").is_file())
        self.assertTrue((FIXTURE / "test/user-teams.test.js").is_file())
        self.assertFalse((FIXTURE / "test/user-summary.test.js").exists())
        self.assertFalse("/users/summary" in (FIXTURE / "src/server.js").read_text())
        spec = (FIXTURE / "docs/shiploop/spec.md").read_text()
        self.assertIn("Current implementation: pending", spec)
        self.assertIn("Current verification: not run", spec)
        self.assertIn(FROZEN_HISTORY, spec)
        self.assertIn("Status: deferred", spec)


class CalibrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix="user-summary-status-")
        cls.root = Path(cls.tmp.name)
        cls.results = {}
        cls.folders = {}
        with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                          "PYTHONDONTWRITEBYTECODE": "1"}):
            base = copy_base(cls.root / "base")
            cls.folders["base"] = base
            cls.folders["reference"] = product_with_docs(cls.root, "reference", layout="plain")
            cls.folders["alternative"] = modular_alternative(cls.root)
            for name, layout in (
                ("plain-layout", "plain"),
                ("reordered-fields", "reordered"),
                ("bulleted-fields", "bulleted"),
                ("bold-fields", "bold"),
                ("nested-fields", "nested"),
                ("spaced-inline-fields", "spaced-inline"),
            ):
                cls.folders[name] = product_with_docs(cls.root, name, layout=layout)
            cls.folders["fenced-heading"] = product_with_docs(cls.root, "fenced-heading", fenced_heading=True)
            cls.folders["history-id-heading"] = product_with_docs(cls.root, "history-id-heading", history_id_heading=True)
            for name, gap in (("ws-proof-line", "\n"), ("ws-proof-blank-line", "\n\n")):
                folder = product_with_docs(cls.root, name, layout="plain")
                edit_spec(folder, CURRENT_VERIFICATION,
                          CURRENT_VERIFICATION + gap + "Served by src/server.js and covered by "
                          "test/user-summary.test.js (W1/S1).", name)
                cls.folders[name] = folder
            history_additions = {
                "history-blockquote-spacer": (
                    f"> {FROZEN_HISTORY}",
                    f"> {FROZEN_HISTORY}\n>\n"
                    "> As of 2026-11-01: R-3 implemented in src/server.js; verification passed."),
                "history-adjacent-bullets": (
                    f"> {FROZEN_HISTORY}",
                    f"- {FROZEN_HISTORY}\n"
                    "- As of 2026-11-01: R-3 implemented in src/server.js; verification passed."),
                "history-new-blockquote-paragraph": (FROZEN_HISTORY,
                                                      FROZEN_HISTORY + "\n\n"
                                                      "> As of 2026-11-01: R-3 implemented in src/server.js; "
                                                      "verification passed."),
                "history-old-date-mentioned-again": (FROZEN_HISTORY,
                                                      FROZEN_HISTORY +
                                                      "\n\n> This supersedes the as of 2026-10-31 note."),
            }
            for name, (old, new) in history_additions.items():
                folder = product_with_docs(cls.root, name, layout="plain")
                edit_spec(folder, old, new, name)
                cls.folders[name] = folder
            contextual_values = {
                "node-context": (CURRENT_IMPLEMENTATION,
                                 "passed — test/user-summary.test.js under Node.js 20, node:test"),
                "glob-context": (CURRENT_IMPLEMENTATION,
                                 "passed — node --test test/*.test.js including test/user-summary.test.js"),
                "other-kind-context": ("implemented — src/server.js, tested by test/user-summary.test.js",
                                       CURRENT_VERIFICATION),
            }
            for name, (implementation, verification) in contextual_values.items():
                folder = product_with_docs(cls.root, name, layout="plain",
                                           implementation=implementation, verification=verification)
                cls.folders[name] = folder
            for name in ("stale-current", "duplicate-current", "history-erased", "history-edited",
                         "deferred-completed", "missing-current-field", "unknown-current-field",
                         "absolute-source", "escaping-source", "absolute-verification", "escaping-verification",
                         "source-wrong-kind-only", "verification-wrong-kind-only",
                         "missing-source-evidence", "missing-verification-evidence", "retired-current"):
                cls.folders[name] = product_with_docs(cls.root, name, defect=name)
            cls.folders["summary-broken"] = product_with_docs(cls.root, "summary-broken",
                                                               variant="summary-drops-filters")
            for name, folder in cls.folders.items():
                result = acceptance(folder, cls.root / "logs" / name)
                if not result.get("observed"):
                    raise AssertionError(f"{name}: acceptance unobserved: {result}")
                failed = {row["id"] for row in result["checks"] if row["pass"] is False}
                unknown = {row["id"] for row in result["checks"] if row["pass"] is None}
                if unknown:
                    raise AssertionError(f"{name}: acceptance unknown: {unknown}")
                cls.results[name] = (result, failed)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_full_failure_sets_for_two_implementations_layouts_and_defects(self) -> None:
        self.assertEqual(set(self.results), set(EXPECTED_FAILURES))
        for name, expected in EXPECTED_FAILURES.items():
            result, failed = self.results[name]
            with self.subTest(variant=name):
                self.assertEqual(set(result["ids"]), set(CHECK_IDS), name)
                self.assertEqual(failed, expected, name)
                self.assertEqual(len(result["checks"]), len(CHECK_IDS), name)

    def test_reference_and_alternative_keep_the_fixture_suite_and_pristine_tests(self) -> None:
        for name in ("reference", "alternative"):
            with self.subTest(variant=name):
                pristine = check_base_tests(self.folders[name], "pristine")
                suite = check_base_tests(self.folders[name], "suite")
                self.assertEqual(pristine.returncode, 0, pristine.stdout + pristine.stderr)
                self.assertEqual(suite.returncode, 0, suite.stdout + suite.stderr)

    def test_false_verified_summary_fails_both_behavior_and_its_own_suite(self) -> None:
        pristine = check_base_tests(self.folders["summary-broken"], "pristine")
        suite = check_base_tests(self.folders["summary-broken"], "suite")
        self.assertEqual(pristine.returncode, 0, pristine.stdout + pristine.stderr)
        self.assertNotEqual(suite.returncode, 0, suite.stdout + suite.stderr)


if __name__ == "__main__":
    unittest.main()
