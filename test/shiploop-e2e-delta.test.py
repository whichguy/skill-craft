#!/usr/bin/env python3
"""A follow-on chain and its delta ledger (test/shiploop_e2e/chains.py; test/shiploop_e2e/delta.py). No model is called.

Two things a run after the first needs, which a pair of passes did not show:

* ``chains``: ``follows`` read to its end, so a third pass is held to the first pass's checks and quality measures as well as the
  second's. Before it, ``load_case`` read one level: link 3 of a chain re-ran link 2's checks and dropped link 1's, and its quality
  acceptance fell out when link 2 declared none. The cases the catalog holds today keep exactly the lists they had.
* ``delta``: the block of metrics.json that says what a run changed against the head it started from and what it left for the next
  run, built here on synthetic Git repositories for every part and on the eight saved runs of the ticket pair (the files and ledgers
  in docs/experiments/multipass-20261031/) for the shapes that were seen: an `AD-<n>` appended after `## Superseded`, which the
  engine then reads as retired, and dated sections appended to environment.md.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import chains  # noqa: E402
import counters  # noqa: E402
import delta  # noqa: E402
import metrics  # noqa: E402
import run  # noqa: E402
import scorecard  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402

EVIDENCE = ROOT / "docs" / "experiments" / "multipass-20261031"
LIVING = ("spec.md", "environment.md", "architecture.md")
IDENTITY = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid")


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env)
    return done.stdout.strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, *IDENTITY, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def write(repo: Path, files: dict[str, str | None]) -> None:
    """Write each file; None removes it."""
    for name, text in files.items():
        path = repo / name
        if text is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def make_run(tmp: Path, start: dict, final: dict, *, kind: str = "follow-on", messages: tuple[str, ...] = ()) -> tuple[Path, str]:
    """An output folder as run.py leaves one: ``work/`` is a repository whose first commit is what the run started from and whose
    later commits are the run; ``invocation.json`` names the start head. Returns (the folder, the start head)."""
    out = tmp / "out"
    work = out / "work"
    work.mkdir(parents=True)
    git(work, "init", "-q")
    write(work, start)
    head = commit(work, "start")
    write(work, final)
    commit(work, "run")
    for message in messages:
        commit(work, message)
    record = ({"follow_on": {"start_head": head, "prior_case": "earlier"}} if kind == "follow-on"
              else {"base": {"start_head": head}} if kind == "base" else {})
    (out / "invocation.json").write_text(json.dumps(record))
    return out, head


class Tools:
    """What delta reads of a tool log: ``sequence``, one row per call."""

    def __init__(self, *rows: dict) -> None:
        self.sequence = [{"event": n, "t": None, "tool": row.get("tool", "shell"), "command": row.get("command", ""),
                          "paths": row.get("paths", [])} for n, row in enumerate(rows)]


SPEC_BEFORE = """# Product spec

## Requirements

### R-1 First
First behaviour.

### R-2 Second
Second behaviour, original wording.

### R-5 Fifth
Fifth behaviour.

## Non-functional requirements
Standard library only.

## Retired
None.
"""
SPEC_AFTER = """# Product spec

## Requirements

### R-1 First
First behaviour.

### R-2 Second
Second behaviour, reworded.

### R-3 Third
Third behaviour. Basis: current request.

## Non-functional requirements
Standard library only.

## Retired
### R-5 Fifth
Fifth behaviour. Retired: replaced by R-3.

### R-4 Fourth
Fourth behaviour, filed here by mistake.
"""
ARCH_BEFORE = """# Architecture

## Decisions
### AD-1 First choice
Chosen because.

## Stack
Node.

## Superseded
None.
"""
ARCH_AFTER = """# Architecture

## Decisions
### AD-1 First choice
Chosen because.

## Stack
Node.

## Superseded
None.

## Extra checks
Checks of the second change.

### AD-2 Second choice
Chosen because.
"""
ENV_BEFORE = """# Environment

## Targets and runtimes
Node 22.

## Commands
npm test
"""
ENV_AFTER = """# Environment

## Targets and runtimes
Node 22.

## Commands
npm test

## This run discovery (2026-10-29)
Observed on the current request.

## Commands
npm run lint
"""


class ChainTest(unittest.TestCase):
    """``chains``, and ``load_case``, ``case_quality`` and the scorecard's requiredness read through it."""

    def catalog(self, cases: dict):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "cases.json"
        path.write_text(json.dumps(cases))
        patched = mock.patch.object(run, "CASES", path)
        patched.start()
        self.addCleanup(patched.stop)

    @staticmethod
    def loaded(name: str):
        return run.load_case(types.SimpleNamespace(prompt=None, case=name, check=None))

    CHAIN = {
        "link1": {"prompt": "P1", "checks": ["check-1a", "check-1b"], "quality": {"acceptance": {"module": "m1"}, "refuse_ports": [4180]}},
        "link2": {"prompt": "P2", "follows": "link1", "checks": ["check-2a", "check-1a"], "retention": ["ret-2"],
                  "quality": {"mutation": {"operators": "x"}}},
        "link3": {"prompt": "P3", "follows": "link2", "checks": ["check-3a"], "retention": ["ret-3"]},
        "link4": {"prompt": "P4", "follows": "link3", "checks": ["check-4a"], "retention": ["ret-4"]},
    }

    def test_a_chain_is_listed_oldest_first(self) -> None:
        self.assertEqual(chains.of(self.CHAIN, "link4"), ["link1", "link2", "link3", "link4"])
        self.assertEqual(chains.of(self.CHAIN, "link1"), ["link1"])

    def test_the_third_pass_is_held_to_the_first_passes_checks(self) -> None:
        self.catalog(self.CHAIN)
        self.assertEqual(self.loaded("link3")[2], ["check-1a", "check-1b", "check-2a", "check-3a", "ret-3"])

    def test_the_fourth_pass_carries_every_earlier_checks_and_only_its_own_retention(self) -> None:
        self.catalog(self.CHAIN)
        checks = self.loaded("link4")[2]
        self.assertEqual(checks, ["check-1a", "check-1b", "check-2a", "check-3a", "check-4a", "ret-4"])
        self.assertNotIn("ret-2", checks)  # retention compares with the pass just before, so each pass has its own
        self.assertNotIn("ret-3", checks)

    def test_a_check_two_earlier_passes_share_runs_once_and_a_cases_own_list_is_never_thinned(self) -> None:
        self.catalog(self.CHAIN)
        two = self.loaded("link2")[2]
        self.assertEqual(two, ["check-1a", "check-1b", "check-2a", "check-1a", "ret-2"])  # its own list repeats check-1a, as written
        three = self.loaded("link3")[2]
        self.assertEqual(three.count("check-1a"), 1)

    def test_the_followed_case_is_still_the_fourth_value(self) -> None:
        self.catalog(self.CHAIN)
        self.assertEqual(self.loaded("link3")[3], "link2")
        self.assertIsNone(self.loaded("link1")[3])

    def test_quality_is_the_nearest_declaration_key_by_key(self) -> None:
        self.catalog(self.CHAIN)
        self.assertEqual(run.case_quality("link1"), {"acceptance": {"module": "m1"}, "refuse_ports": [4180]})
        self.assertEqual(run.case_quality("link2"), {"acceptance": {"module": "m1"}, "refuse_ports": [4180],
                                                      "mutation": {"operators": "x"}})
        # Link 3 declares nothing and link 2 declares only a mutation block: the first pass's acceptance still measures it.
        self.assertEqual(run.case_quality("link3"), run.case_quality("link2"))
        self.assertEqual(run.case_quality("link4"), run.case_quality("link2"))

    def test_a_case_that_declares_its_own_acceptance_is_not_overridden_by_an_earlier_one(self) -> None:
        cases = {**self.CHAIN, "link3": {**self.CHAIN["link3"], "quality": {"acceptance": {"module": "m3"}}}}
        self.catalog(cases)
        self.assertEqual(run.case_quality("link4")["acceptance"], {"module": "m3"})
        self.assertEqual(run.case_quality("link4")["mutation"], {"operators": "x"})

    def test_a_name_that_is_no_case_has_no_quality(self) -> None:
        self.catalog(self.CHAIN)
        self.assertEqual(run.case_quality("custom"), {})

    def test_a_loop_is_refused(self) -> None:
        looped = {"a": {"prompt": "A", "follows": "b", "checks": []}, "b": {"prompt": "B", "follows": "a", "checks": []}}
        with self.assertRaises(chains.ChainError) as raised:
            chains.of(looped, "a")
        self.assertIn("follows itself", str(raised.exception))
        self.assertIn("a -> b -> a", str(raised.exception))

    def test_a_follows_that_names_no_case_is_refused_by_name(self) -> None:
        with self.assertRaises(chains.ChainError) as raised:
            chains.of({"a": {"prompt": "A", "follows": "gone", "checks": []}}, "a")
        self.assertIn("'gone'", str(raised.exception))
        with self.assertRaises(chains.ChainError):
            chains.of({}, "nothing")

    def test_the_command_line_is_told_in_one_line_and_the_known_cases(self) -> None:
        self.catalog({"a": {"prompt": "A", "follows": "gone", "checks": []}})
        with self.assertRaises(SystemExit) as raised:
            self.loaded("a")
        self.assertIn("'gone'", str(raised.exception))
        self.assertIn("known: a", str(raised.exception))
        with self.assertRaises(SystemExit):
            run.case_quality("a")

    def test_the_scorecard_requires_the_acceptance_a_later_link_inherits(self) -> None:
        self.catalog(self.CHAIN)
        with mock.patch.object(scorecard, "CASES", run.CASES):
            self.assertTrue(scorecard.requires_acceptance("link1"))
            self.assertTrue(scorecard.requires_acceptance("link4"))  # declared by link 1, inherited through two links that name none
            self.assertFalse(scorecard.requires_acceptance("no-such-case"))

    def test_the_scorecard_falls_back_to_the_cases_own_declaration_when_its_chain_is_gone(self) -> None:
        self.catalog({"a": {"prompt": "A", "follows": "gone", "checks": [], "quality": {"acceptance": {"module": "m"}}},
                      "b": {"prompt": "B", "follows": "gone", "checks": []}})
        with mock.patch.object(scorecard, "CASES", run.CASES):
            self.assertTrue(scorecard.requires_acceptance("a"))
            self.assertFalse(scorecard.requires_acceptance("b"))

    def test_only_the_new_link_requires_an_acceptance_it_does_not_declare_itself(self) -> None:
        cases = json.loads(run.CASES.read_text())
        inheriting = [name for name, case in cases.items()
                      if scorecard.requires_acceptance(name) != bool((case.get("quality") or {}).get("acceptance"))]
        # Every case before the third link requires exactly what it declares, so scorecard/6 keeps its meaning for the saved cards.
        self.assertEqual(inheriting, ["ticket-comments"])

    def test_every_follows_in_the_catalog_resolves_to_a_chain_that_ends_at_a_fresh_start(self) -> None:
        cases = json.loads(run.CASES.read_text())
        for name in cases:
            chain = chains.of(cases, name)
            self.assertEqual(chain[-1], name)
            self.assertIsNone(cases[chain[0]].get("follows"), name)

    def test_the_two_pass_cases_keep_the_lists_they_had(self) -> None:
        cases = json.loads(run.CASES.read_text())
        for name in ("battleship-scoring", "ticket-escalation"):
            case = cases[name]
            before = cases[case["follows"]]["checks"] + case["checks"] + case.get("retention", [])
            self.assertEqual(self.loaded(name)[2], before, name)

    def test_every_case_keeps_the_quality_one_level_gave_it(self) -> None:
        cases = json.loads(run.CASES.read_text())
        for name, case in cases.items():
            own, earlier = case.get("quality") or {}, (cases.get(case.get("follows")) or {}).get("quality") or {}
            before = {key: own.get(key) or earlier.get(key) for key in ("mutation", "acceptance", "refuse_ports")}
            self.assertEqual(run.case_quality(name), {key: value for key, value in before.items() if value}, name)


class IdsTest(unittest.TestCase):
    def test_added_dropped_changed_retired_and_born_retired_are_told_apart(self) -> None:
        spec = delta.ids_block(SPEC_BEFORE, SPEC_AFTER, "R")
        self.assertEqual((spec["prior"], spec["final"]), (3, 5))
        self.assertEqual(spec["added"], ["R-3", "R-4"])
        self.assertEqual(spec["dropped"], [])
        self.assertEqual(spec["changed"], ["R-2", "R-5"])  # R-5's text gained its retirement note
        self.assertEqual(spec["unchanged"], 1)
        self.assertEqual(spec["retired_by_run"], ["R-5"])
        self.assertEqual(spec["born_retired"], ["R-4"])

    def test_a_dropped_entry_is_listed_in_numeric_order(self) -> None:
        before = "## Requirements\n### R-2 a\nx\n### R-10 b\ny\n### R-9 c\nz\n"
        after = "## Requirements\n### R-9 c\nz\n"
        self.assertEqual(delta.ids_block(before, after, "R")["dropped"], ["R-2", "R-10"])

    def test_whitespace_alone_is_no_change(self) -> None:
        before = "## Requirements\n### R-1 a\nOne  line\n"
        after = "## Requirements\n### R-1 a\nOne line   \n\n"
        self.assertEqual(delta.ids_block(before, after, "R")["changed"], [])

    def test_a_file_that_did_not_exist_adds_everything_and_a_missing_final_drops_everything(self) -> None:
        self.assertEqual(delta.ids_block(None, SPEC_BEFORE, "R")["added"], ["R-1", "R-2", "R-5"])
        self.assertEqual(delta.ids_block(SPEC_BEFORE, None, "R")["dropped"], ["R-1", "R-2", "R-5"])
        self.assertEqual(delta.ids_block(None, None, "R")["final"], 0)

    def test_a_decision_after_the_last_heading_is_born_superseded_when_that_heading_is_superseded(self) -> None:
        # The shape the pass-2 runs wrote: heredoc-appended after a file whose last section is Superseded.
        before = "# Architecture\n\n## Decisions\n### AD-1 a\nx\n\n## Superseded\nNone.\n"
        after = before + "\n### AD-2 Appended\nlive decision.\n"
        block = delta.ids_block(before, after, "AD")
        self.assertEqual(block["added"], ["AD-2"])
        self.assertEqual(block["born_retired"], ["AD-2"])


class PlacementTest(unittest.TestCase):
    def test_spec_placement(self) -> None:
        block = delta.placement_block("spec.md", SPEC_BEFORE, SPEC_AFTER)
        self.assertEqual(block["title"], {"prior": "Product spec", "final": "Product spec"})
        self.assertEqual(block["stray"], [])
        # R-5 moved there by title it already had; only the heading the run created under Retired is new.
        self.assertEqual(block["added_under_retired"], ["R-4 Fourth"])
        self.assertEqual(block["changed_sections"], ["Requirements", "Retired"])  # not "Non-functional requirements"
        self.assertEqual(block["relative_wording"]["n"], 1)
        self.assertEqual(block["relative_wording"]["examples"], ["current request"])

    def test_environment_placement_counts_the_stray_and_duplicate_sections_the_run_added(self) -> None:
        block = delta.placement_block("environment.md", ENV_BEFORE, ENV_AFTER)
        self.assertEqual(block["stray"], ["This run discovery (2026-10-29)"])
        self.assertEqual(block["stray_added"], ["This run discovery (2026-10-29)"])
        self.assertEqual(block["duplicate"], ["Commands"])
        self.assertEqual(block["changed_sections"], [])  # everything the run added is in sections of its own: no named section changed
        self.assertEqual(block["relative_wording"]["n"], 2)  # the heading's "This run" and the line's "current request"
        self.assertIn("Skills", block["named_missing"])

    def test_a_stray_section_the_start_already_had_is_not_added_by_the_run(self) -> None:
        before = ENV_BEFORE + "\n## Old notes\nx\n"
        after = before + "\n## New notes\ny\n"
        block = delta.placement_block("environment.md", before, after)
        self.assertEqual(block["stray"], ["Old notes", "New notes"])
        self.assertEqual(block["stray_added"], ["New notes"])

    def test_a_section_written_twice_under_one_title_counts_twice(self) -> None:
        block = delta.placement_block("environment.md", ENV_BEFORE, ENV_BEFORE + "\n## Notes\na\n\n## Notes\nb\n")
        self.assertEqual(block["stray_added"], ["Notes", "Notes"])

    def test_an_empty_named_section_is_told_from_a_missing_one(self) -> None:
        block = delta.placement_block("environment.md", None, "# Environment\n\n## Targets and runtimes\n\n## Commands\nnpm test\n")
        self.assertIn("Targets and runtimes", block["named_empty"])
        self.assertNotIn("Commands", block["named_empty"] + block["named_missing"])
        self.assertIn("Skills", block["named_missing"])

    def test_a_named_section_updated_in_place_is_a_changed_section_and_a_nested_heading_belongs_to_its_parent(self) -> None:
        before = "# Architecture\n\n## Decisions\n### AD-1 a\nx\n\n## Structure\nOne module.\n\n## Superseded\nNone.\n"
        in_place = before.replace("One module.", "One module and a worker job.")
        self.assertEqual(delta.placement_block("architecture.md", before, in_place)["changed_sections"], ["Structure"])
        appended = before + "\n### AD-2 b\ny\n"  # level 3 after Superseded: inside the Superseded section
        self.assertEqual(delta.placement_block("architecture.md", before, appended)["changed_sections"], ["Superseded"])
        decided = before.replace("x\n\n## Structure", "x\n### AD-2 b\ny\n\n## Structure")
        self.assertEqual(delta.placement_block("architecture.md", before, decided)["changed_sections"], ["Decisions"])

    def test_section_texts_takes_the_first_heading_of_a_name_and_ends_at_the_next_of_its_level_or_higher(self) -> None:
        text = "# T\n## Commands\na\n### Sub\nb\n## Other\nc\n## Commands\nd\n"
        found = delta.section_texts(text, ("Commands", "Skills"))
        self.assertEqual(found, {"Commands": "## Commands\na\n### Sub\nb"})

    def test_a_title_the_run_changed_is_recorded_on_both_sides(self) -> None:
        block = delta.placement_block("spec.md", "# Ticket assignment specification\n## Requirements\nx\n",
                                      "# Ticket service specification\n## Requirements\nx\n")
        self.assertEqual(block["title"], {"prior": "Ticket assignment specification", "final": "Ticket service specification"})

    def test_an_absent_file_has_no_title_and_zero_bytes(self) -> None:
        block = delta.placement_block("architecture.md", None, None)
        self.assertEqual(block["title"], {"prior": None, "final": None})
        self.assertEqual(block["bytes"], {"prior": 0, "final": 0})
        self.assertEqual(block["level2"], 0)


class FootprintTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_classes_counts_and_the_earlier_tests_the_run_touched(self) -> None:
        start = {"src/app.js": "a\n", "src/old.js": "o\n", "package.json": "{}\n", "test/app.test.js": "t\n", "test/old.test.js": "t\n",
                 "docs/api.md": "d\n", "README.md": "r\n", "docs/shiploop/spec.md": "s\n"}
        final = {"src/app.js": "a\nb\nc\n", "src/new.js": "n\n", "src/old.js": None, "test/app.test.js": "t\nu\n", "test/new.test.js": "n\nn\n",
                 "test/old.test.js": None, "docs/api.md": "d\ne\n", "docs/shiploop/spec.md": "s\nt\n", "node_modules/x/i.js": "ignored\n",
                 "server.log": "ignored\n"}
        out, head = make_run(self.tmp, start, final)
        block = delta.footprint_block(out / "work", head, counters._commit_id(out / "work", "HEAD"))
        classes = block["by_class"]
        self.assertEqual({k: classes["source"][k] for k in ("added", "modified", "deleted")}, {"added": 1, "modified": 1, "deleted": 1})
        self.assertEqual({k: classes["tests"][k] for k in ("added", "modified", "deleted")}, {"added": 1, "modified": 1, "deleted": 1})
        self.assertEqual({k: classes["docs"][k] for k in ("added", "modified", "deleted")}, {"added": 0, "modified": 1, "deleted": 0})
        self.assertEqual(classes["living"]["modified"], 1)
        self.assertEqual(classes["living"]["insertions"], 1)
        self.assertEqual(block["prior_tests_modified"], ["test/app.test.js", "test/old.test.js"])
        self.assertEqual(block["prior_source_files"], 3)  # app.js, old.js, package.json: neither the docs nor the tests
        self.assertEqual(block["prior_source_modified"], 2)  # app.js changed, old.js deleted

    def test_a_fresh_run_is_measured_against_nothing(self) -> None:
        out, _ = make_run(self.tmp, {"README.md": "r\n"}, {"src/a.js": "a\n"}, kind="fresh")
        work = out / "work"
        block = delta.footprint_block(work, None, counters._commit_id(work, "HEAD"))
        self.assertEqual(block["by_class"]["source"]["added"], 1)
        self.assertEqual(block["by_class"]["docs"]["added"], 1)
        self.assertEqual(block["prior_source_files"], 0)

    def test_the_class_of_a_path(self) -> None:
        for path, kind in (("docs/shiploop/architecture.md", "living"), ("test/helpers.js", "tests"), ("src/a.test.js", "tests"),
                           ("src/test_a.py", "tests"), ("spec/a_spec.rb", "tests"), ("docs/api.md", "docs"), ("README.md", "docs"),
                           ("src/latest.js", "source"), ("src/contest/a.js", "source"), ("package.json", "source"), ("bin/tool", "source")):
            self.assertEqual(delta.classify(path), kind, path)


class WritesTest(unittest.TestCase):
    def test_a_shell_append_is_told_from_a_read_and_a_rewrite(self) -> None:
        tools = Tools(
            {"command": "cat docs/shiploop/spec.md"},
            {"command": "sed -n '1,40p' /w/docs/shiploop/spec.md"},
            {"command": "cat >> docs/shiploop/architecture.md <<'EOF'\n### AD-3 new\nEOF"},
            {"command": "echo more | tee -a docs/shiploop/architecture.md"},
            {"command": "python3 - <<'PY'\np='docs/shiploop/spec.md'\nopen(p,'w').write(open(p).read().replace('a','b'))\nPY"},
            {"command": "cat > docs/shiploop/environment.md <<'EOF'\n# Environment\nEOF"},
            {"command": "sed -i 's/a/b/' docs/shiploop/environment.md"},
            {"command": "rg --files src | head"},
        )
        written = delta.writes_block(tools)
        self.assertEqual(written["spec.md"], {"reads": 2, "appends": 0, "other_writes": 1})
        self.assertEqual(written["architecture.md"], {"reads": 0, "appends": 2, "other_writes": 0})
        self.assertEqual(written["environment.md"], {"reads": 0, "appends": 0, "other_writes": 2})

    def test_a_tool_call_that_names_the_file_is_a_read_or_a_write_by_its_tool(self) -> None:
        tools = Tools({"tool": "Read", "paths": ["/w/docs/shiploop/spec.md"]},
                      {"tool": "Edit", "paths": ["/w/docs/shiploop/spec.md"]},
                      {"tool": "Write", "paths": ["/w/docs/shiploop/environment.md"]},
                      {"tool": "Read", "paths": ["/w/src/app.js"]})
        written = delta.writes_block(tools)
        self.assertEqual(written["spec.md"], {"reads": 1, "appends": 0, "other_writes": 1})
        self.assertEqual(written["environment.md"], {"reads": 0, "appends": 0, "other_writes": 1})

    def test_a_log_without_a_sequence_is_a_measured_none(self) -> None:
        self.assertEqual(delta.writes_block(object())["spec.md"], {"reads": 0, "appends": 0, "other_writes": 0})


STATE = {
    "history": [{"stage": "spec", "action": "a1", "outcome": "done"},
                {"stage": "step-plan", "action": "a2", "outcome": "done"},
                {"stage": "step-plan", "action": "a3", "outcome": "blocked"},
                {"stage": "test-spec", "action": "a4", "outcome": "done"}],
    "accepted": {"a1": {"primary": ["R-3", "R-1"]},
                 "a2": {"follows": ["R-3", "R-1", "AD-2", "R-99"]},
                 "a3": {"follows": ["R-2"]},
                 "a4": {"test_cases": [{"requirement": "R-3"}, {"requirement": "R-3"}, {"requirement": "R-1"}, {"id": "TC_9"}]}},
}


class PlanTest(unittest.TestCase):
    def run_dir(self, state: dict | str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        text = state if isinstance(state, str) else "# State\n\n```shiploop-state\n" + json.dumps(state) + "\n```\n"
        (folder / "state.md").write_text(text)
        return folder

    def test_the_runs_records_are_read_against_the_ids_it_added_and_kept(self) -> None:
        block, why = delta.plan_block(self.run_dir(STATE), {"R-2", "R-3", "AD-2"}, {"R-1", "R-2"})
        self.assertIsNone(why)
        self.assertEqual(block["delta_ids"], ["AD-2", "R-2", "R-3"])
        self.assertEqual(block["primary"], {"delta": 1, "preserved": 1, "unknown": 0})
        # The blocked step plan's follows is no accepted result; R-99 is in neither set.
        self.assertEqual(block["step_plan_follows"], {"delta": 2, "preserved": 1, "unknown": 1})
        self.assertEqual(block["test_cases"], {"delta": 2, "preserved": 1, "unknown": 0, "no_requirement": 1})

    def test_a_run_with_no_readable_state_is_unmeasured_with_the_reason(self) -> None:
        for run_dir in (None, self.run_dir("no state block here")):
            block, why = delta.plan_block(run_dir, set(), set())
            self.assertIsNone(block)
            self.assertIn("state.md", why)


class HandoffTest(unittest.TestCase):
    def test_the_lessons_commit_and_the_sections_a_file_still_lacks(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        body = ("docs(shiploop): record add-things-1a2b3c knowledge at release-verify\n\nLearned\nOne fact.\n\n"
                "Key considerations\nTwo facts here.\n\nOpen for the next run\nNone.\n\n"
                "Open items left at release-verify (generated by ShipLoop)\n- A-1 (release): something\n")
        out, head = make_run(Path(tmp.name), {"README.md": "r\n"}, {"docs/shiploop/spec.md": SPEC_AFTER}, messages=(body,))
        work = out / "work"
        block = delta.handoff_block(work, head, counters._commit_id(work, "HEAD"), {"spec.md": SPEC_AFTER, "environment.md": None,
                                                                                    "architecture.md": ARCH_AFTER})
        self.assertEqual(len(block["lessons_commit"]), 12)
        self.assertEqual(block["lessons_chars"], {"learned": len("One fact."), "considerations": len("Two facts here."),
                                                  "open_next": len("None.")})
        self.assertIsNone(block["sections"]["environment.md"])
        self.assertEqual(block["sections"]["spec.md"], {"missing": [], "empty": []})
        self.assertIn("Real-boundary checks", block["sections"]["architecture.md"]["missing"])
        self.assertEqual(block["tracked"], {"spec.md": True, "environment.md": False, "architecture.md": False})

    def test_a_run_that_made_no_lessons_commit_says_so(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out, head = make_run(Path(tmp.name), {"README.md": "r\n"}, {"src/a.js": "a\n"})
        work = out / "work"
        block = delta.handoff_block(work, head, counters._commit_id(work, "HEAD"), {name: None for name in LIVING})
        self.assertIsNone(block["lessons_commit"])
        self.assertIsNone(block["lessons_chars"])


def synthetic_run(tmp: Path, **kwargs) -> tuple[Path, str]:
    """A run over the synthetic living files above: R-3, R-4 and AD-2 added; R-2 reworded; R-5 moved under Retired; R-4 filed there
    by mistake; one source file changed and one test added."""
    start = {"README.md": "r\n", "src/app.js": "a\n", "test/app.test.js": "t\n",
             "docs/shiploop/spec.md": SPEC_BEFORE, "docs/shiploop/architecture.md": ARCH_BEFORE,
             "docs/shiploop/environment.md": ENV_BEFORE}
    final = {"src/app.js": "a\nb\n", "test/new.test.js": "n\n", "docs/shiploop/spec.md": SPEC_AFTER,
             "docs/shiploop/architecture.md": ARCH_AFTER, "docs/shiploop/environment.md": ENV_AFTER}
    return make_run(tmp, start, final, **kwargs)


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def synthetic(self, **kwargs):
        return synthetic_run(self.tmp, **kwargs)

    def test_the_block_holds_every_part_for_a_follow_on(self) -> None:
        out, head = self.synthetic()
        built = delta.build(out, None, Tools({"command": "cat >> docs/shiploop/architecture.md <<'EOF'\nx\nEOF"}))
        block = built["delta"]
        self.assertEqual(block["basis"]["kind"], "follow-on")
        self.assertEqual(block["basis"]["followed_case"], "earlier")
        self.assertEqual(block["basis"]["start_head"], head)
        self.assertEqual(set(block["ids"]), {"spec.md", "architecture.md"})
        self.assertEqual(block["ids"]["spec.md"]["added"], ["R-3", "R-4"])
        self.assertEqual(block["ids"]["architecture.md"]["added"], ["AD-2"])
        self.assertEqual(set(block["placement"]), set(LIVING))
        self.assertEqual(block["footprint"]["by_class"]["source"]["modified"], 1)
        self.assertEqual(block["writes"]["architecture.md"]["appends"], 1)
        self.assertIsNone(block["plan"])
        self.assertIn("plan", built["delta_unmeasured"])  # no run folder was given, and the reason says what is missing
        self.assertIn("heuristic", block["heuristics"])

    def test_the_kind_of_run_comes_from_its_invocation_record(self) -> None:
        for kind, expected in (("base", "base"), ("fresh", "fresh")):
            with self.subTest(kind):
                tmp = tempfile.TemporaryDirectory()
                self.addCleanup(tmp.cleanup)
                self.tmp = Path(tmp.name)
                out, _ = self.synthetic(kind=kind)
                self.assertEqual(delta.build(out, None, Tools())["delta"]["basis"]["kind"], expected)

    def test_a_run_folder_with_no_work_repository_is_unmeasured_with_the_reason(self) -> None:
        built = delta.build(self.tmp, None, Tools())
        self.assertIsNone(built["delta"])
        self.assertIn("no work repository", built["delta_unmeasured"]["delta"])

    def test_a_run_whose_start_cannot_be_known_is_unmeasured_not_a_fresh_run(self) -> None:
        out, _ = self.synthetic()
        (out / "invocation.json").unlink()
        built = delta.build(out, None, Tools())
        self.assertIsNone(built["delta"])
        self.assertIn("invocation.json", built["delta_unmeasured"]["delta"])

    def test_a_part_that_raises_fails_open_with_the_error_as_its_reason(self) -> None:
        out, _ = self.synthetic()
        with mock.patch.object(delta, "footprint_block", side_effect=RuntimeError("boom")):
            built = delta.safe_build(out, None, Tools())
        self.assertIsNone(built["delta"])
        self.assertEqual(built["delta_unmeasured"]["delta"], "failed: RuntimeError: boom")

    def test_the_block_is_plain_json(self) -> None:
        out, _ = self.synthetic()
        json.dumps(delta.build(out, None, Tools()))


class SavedRunTest(unittest.TestCase):
    """``delta.saved`` and the command line: a run folder on disk, read the way a regrade reads it."""

    def test_the_tool_log_and_the_state_are_read_from_the_folder(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out, _ = synthetic_run(Path(tmp.name))
        events = [{"type": "tool_call", "toolCallId": "c1", "title": "Run shell command",
                   "rawInput": {"command": "cat >> docs/shiploop/architecture.md <<'EOF'\nx\nEOF"}},
                  {"type": "tool_call", "toolCallId": "c2", "title": "Run shell command",
                   "rawInput": {"command": "cat docs/shiploop/spec.md"}}]
        (out / "events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
        run_dir = out / "ledger"
        run_dir.mkdir()
        (run_dir / "state.md").write_text("```shiploop-state\n" + json.dumps(STATE) + "\n```\n")
        (out / "shiploop-run.json").write_text(json.dumps({"run_dir": str(run_dir)}))
        block = delta.saved(out)["delta"]
        self.assertEqual(block["writes"]["architecture.md"]["appends"], 1)
        self.assertEqual(block["writes"]["spec.md"]["reads"], 1)
        # Added: R-3, R-4, AD-2. Changed: R-2 (reworded) and R-5 (its retirement note).
        self.assertEqual(block["plan"]["delta_ids"], ["AD-2", "R-2", "R-3", "R-4", "R-5"])
        self.assertEqual(block["plan"]["step_plan_follows"], {"delta": 2, "preserved": 1, "unknown": 1})  # R-3, AD-2; R-1; R-99

    def test_the_command_line_prints_one_line_per_run_and_json_on_request(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out, _ = synthetic_run(Path(tmp.name))
        shown = io.StringIO()
        with contextlib.redirect_stdout(shown):
            self.assertEqual(delta.main([str(out)]), 0)
        text = shown.getvalue().strip().splitlines()
        self.assertEqual(len(text), 1)
        self.assertIn("follow-on", text[0])
        self.assertIn("born-retired 1", text[0])
        shown = io.StringIO()
        with contextlib.redirect_stdout(shown):
            delta.main(["--json", str(out)])
        self.assertIn("born_retired", json.loads(shown.getvalue())[out.name]["delta"]["ids"]["spec.md"])

    def test_an_unmeasured_run_prints_its_reason(self) -> None:
        shown = io.StringIO()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with contextlib.redirect_stdout(shown):
            delta.main([tmp.name])
        self.assertIn("not measured", shown.getvalue())


class SavedPairsTest(unittest.TestCase):
    """The eight saved runs of the ticket pair (2026-10-29 rounds on Codex Terra 6.1): the shapes the ledger was built to see."""

    PREFIXES = ("bf-codex-r1", "bf-codex-r2", "hooks-before", "hooks-after")

    @classmethod
    def setUpClass(cls) -> None:
        cls.saved = json.loads((EVIDENCE / "ledger-saved-pairs.json").read_text())
        cls.rebuilt = {}
        cls.tmp = tempfile.TemporaryDirectory()
        for prefix in cls.PREFIXES:
            folder = Path(cls.tmp.name) / prefix
            folder.mkdir()
            files = {}
            for passed in ("pass1", "pass2"):
                files[passed] = {f"docs/shiploop/{name}": (EVIDENCE / "saved-pairs" / prefix / passed / name).read_text() for name in LIVING}
            out, _ = make_run(folder, files["pass1"], files["pass2"])
            cls.rebuilt[prefix] = delta.build(out, None, Tools())["delta"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_the_living_file_blocks_of_the_saved_ledger_are_what_the_files_give_now(self) -> None:
        for prefix in self.PREFIXES:
            was = self.saved[f"{prefix}-ticket-escalation"]["delta"]
            for part in ("ids", "placement"):
                self.assertEqual(self.rebuilt[prefix][part], was[part], f"{prefix} {part}")

    def test_no_pass_two_dropped_changed_or_retired_an_earlier_requirement_or_decision(self) -> None:
        for prefix, block in self.rebuilt.items():
            for name in ("spec.md", "architecture.md"):
                entry = block["ids"][name]
                self.assertEqual((entry["dropped"], entry["changed"], entry["retired_by_run"]), ([], [], []), f"{prefix} {name}")

    def test_every_pass_two_added_two_requirements_and_one_decision(self) -> None:
        for prefix, block in self.rebuilt.items():
            self.assertEqual(len(block["ids"]["spec.md"]["added"]), 2, prefix)
            self.assertEqual(len(block["ids"]["architecture.md"]["added"]), 1, prefix)

    def test_one_pass_two_filed_a_live_decision_under_superseded(self) -> None:
        born = {prefix: block["ids"]["architecture.md"]["born_retired"] for prefix, block in self.rebuilt.items()}
        self.assertEqual(born, {"bf-codex-r1": [], "bf-codex-r2": ["AD-3"], "hooks-before": [], "hooks-after": []})
        under = self.rebuilt["bf-codex-r2"]["placement"]["architecture.md"]["added_under_retired"]
        self.assertEqual(under, ["Bulk and escalation boundary checks", "AD-3 Bulk assignment and escalation (implemented)"])

    def test_every_pass_two_grew_architecture_md_by_a_heading_outside_its_sections_or_a_decision_filed_as_superseded(self) -> None:
        for prefix, block in self.rebuilt.items():
            arch = block["placement"]["architecture.md"]
            self.assertTrue(arch["stray_added"] or block["ids"]["architecture.md"]["born_retired"], prefix)

    def test_environment_md_gains_headings_of_its_own_in_every_pass_one_and_every_pass_two(self) -> None:
        for prefix in self.PREFIXES:
            first = self.saved[f"{prefix}-ticket-assignment"]["delta"]["placement"]["environment.md"]
            second = self.rebuilt[prefix]["placement"]["environment.md"]
            self.assertGreaterEqual(len(first["stray_added"]), 3, prefix)
            self.assertGreaterEqual(len(second["stray_added"]), 1, prefix)

    def test_where_pass_two_updated_architecture_md_in_place(self) -> None:
        changed = {prefix: block["placement"]["architecture.md"]["changed_sections"] for prefix, block in self.rebuilt.items()}
        self.assertEqual(changed, {"bf-codex-r1": ["Structure", "Interfaces and boundaries"], "bf-codex-r2": ["Superseded"],
                                   "hooks-before": ["Decisions"], "hooks-after": []})
        in_place = [prefix for prefix, sections in changed.items() if set(sections) & {"Decisions", "Structure", "Interfaces and boundaries"}]
        self.assertEqual(len(in_place), 2)  # two of four runs updated the architecture where it lives

    def test_pass_two_changed_no_named_section_of_environment_md_in_three_of_four_runs(self) -> None:
        changed = {prefix: block["placement"]["environment.md"]["changed_sections"] for prefix, block in self.rebuilt.items()}
        self.assertEqual(changed, {"bf-codex-r1": [], "bf-codex-r2": [], "hooks-before": [], "hooks-after": ["Harnesses and suites"]})

    def test_every_pass_two_wrote_the_request_as_current_in_the_spec_lines_it_added(self) -> None:
        for prefix, block in self.rebuilt.items():
            self.assertGreaterEqual(block["placement"]["spec.md"]["relative_wording"]["n"], 1, prefix)

    def test_the_saved_pass_one_runs_start_from_the_base_and_pass_two_from_pass_one(self) -> None:
        for prefix in self.PREFIXES:
            self.assertEqual(self.saved[f"{prefix}-ticket-assignment"]["delta"]["basis"]["kind"], "base")
            self.assertEqual(self.saved[f"{prefix}-ticket-escalation"]["delta"]["basis"]["kind"], "follow-on")
            self.assertEqual(self.saved[f"{prefix}-ticket-escalation"]["delta"]["basis"]["followed_case"], "ticket-assignment")

    def test_no_pass_two_touched_a_test_the_first_pass_wrote_and_every_test_case_it_planned_cites_a_new_requirement(self) -> None:
        for prefix in self.PREFIXES:
            block = self.saved[f"{prefix}-ticket-escalation"]["delta"]
            self.assertEqual(block["footprint"]["prior_tests_modified"], [], prefix)
            tests = block["plan"]["test_cases"]
            self.assertEqual((tests["preserved"], tests["unknown"]), (0, 0), prefix)
            self.assertGreater(tests["delta"], 0, prefix)


def load_harness_tests():
    spec = importlib.util.spec_from_file_location("e2e_harness_tests_for_delta", ROOT / "test" / "shiploop-e2e.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = load_harness_tests()


class ThroughMainTest(HARNESS.PrintedCase):
    """run._main builds the block once from the run's own records, for each host's event stream."""

    def setUp(self):
        super().setUp()
        HARNESS.isolate_git(self)

    def test_a_run_of_each_host_carries_a_measured_delta_block_in_metrics_json_only(self) -> None:
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, _printed = self.invoke_printed(host, "done")
                out = Path(result["output"])
                written = json.loads((out / "metrics.json").read_text())
                block = written["delta"]
                self.assertIsInstance(block, dict, written["delta_unmeasured"])
                self.assertEqual(block["basis"]["kind"], "fresh")  # the fake host's run has no earlier head
                self.assertEqual(set(block["ids"]), {"spec.md", "architecture.md"})
                self.assertEqual(set(block["placement"]), set(LIVING))
                self.assertIsNotNone(block["footprint"])
                self.assertEqual(set(block["writes"]), set(LIVING))
                self.assertNotIn("delta", result)
                self.assertNotIn("delta", json.loads((out / "result.json").read_text()))


class ThirdPassPacketTest(unittest.TestCase):
    """What the first packet of a third pass tells its model about the files the second pass left (render_pass3_intake.py).

    A characterization of the engine as published in 1.26.0, not a requirement: it pins what a third pass is shown today, so that a
    change to what the stages write or to how the packet lists a file (the plan's D2 and D3) shows up as a deliberate edit here and
    the committed listings in docs/experiments/multipass-20261031/ are regenerated with it.
    """

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("render_pass3_intake", EVIDENCE / "render_pass3_intake.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.rendered = {prefix: module.render(prefix) for prefix in ("bf-codex-r2", "hooks-after")}

    def test_the_committed_listings_are_what_the_engine_prints_now(self) -> None:
        for prefix, text in self.rendered.items():
            self.assertEqual(text, (EVIDENCE / f"pass3-intake-{prefix}.txt").read_text(), prefix)

    def test_the_live_decision_the_second_pass_appended_is_listed_under_superseded(self) -> None:
        listing = self.rendered["bf-codex-r2"]
        self.assertIn("  ## Superseded\n  ### Bulk and escalation boundary checks: AD-3 Bulk assignment and escalation (implemented)\n", listing)
        self.assertIn("  ## Decisions: AD-1 Existing store and outbox · AD-2 Filter intersection and CLI\n", listing)  # AD-3 is not here

    def test_environment_md_is_listed_with_its_stage_reports_and_a_named_section_twice(self) -> None:
        listing = self.rendered["bf-codex-r2"]
        self.assertEqual(listing.count("  ## Commands\n"), 2)
        for report in ("Prepared environment", "Returned result", "Operational observations"):
            self.assertIn("  ## " + report + "\n", listing)

    def test_the_spec_is_still_titled_for_the_first_feature_while_it_lists_the_second(self) -> None:
        listing = self.rendered["bf-codex-r2"]
        self.assertIn("  # Ticket assignment specification\n", listing)
        self.assertIn("R-6 Bulk reassignment · R-7 Urgent escalation", listing)

    def test_the_inherited_learnings_are_the_last_commit_messages_with_the_lessons(self) -> None:
        for listing in self.rendered.values():
            self.assertIn("Inherited learnings: the last 3 commit messages", listing)
            self.assertIn("The second pass's lesson.", listing)  # the newest lessons commit, quoted in full
            self.assertIn("Open for the next run", listing)
            self.assertIn("in <work>.", listing)


class Round1ReadoutTest(unittest.TestCase):
    """round1_readout.py scores the journal's predictions from a run's result.json and its delta block, and says "unknown" where the run
    recorded nothing."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("round1_readout", EVIDENCE / "round1_readout.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def folder(self, **result) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out, _ = synthetic_run(Path(tmp.name))
        (out / "result.json").write_text(json.dumps(result))
        return out

    def test_every_prediction_is_scored_and_the_ones_the_run_did_not_record_are_unknown(self) -> None:
        report = self.module.read(self.folder(**{"pass": True, "checks": [{"command": "a", "pass": True}], "quality": {}}))
        self.assertEqual([row["n"] for row in report["predictions"]], [1, 2, 3, 4, 5, 6])
        verdicts = {row["n"]: row["verdict"] for row in report["predictions"]}
        self.assertEqual(verdicts[1], "missed")  # the hidden acceptance was not observed, so "every check passes" cannot hold
        self.assertEqual(verdicts[2], "unknown")  # no comment-notices check in this result
        self.assertEqual(verdicts[3], "unknown")  # no run state, so no plan
        self.assertIn("born_retired", report["predictions"][3]["observed"])

    def test_a_run_whose_checks_and_acceptance_all_pass_holds_the_first_two_predictions(self) -> None:
        checks = [{"command": "x Check comment notices y", "pass": True}, {"command": "other", "pass": True}]
        quality = {"acceptance": {"observed": True, "checks": [{"id": "a", "pass": True}]}}
        report = self.module.read(self.folder(**{"pass": True, "checks": checks, "quality": quality}))
        verdicts = {row["n"]: row["verdict"] for row in report["predictions"]}
        self.assertEqual((verdicts[1], verdicts[2]), ("held", "held"))

    def test_a_failing_notice_check_misses_the_second_prediction(self) -> None:
        checks = [{"command": "Check comment notices", "pass": False}]
        report = self.module.read(self.folder(**{"pass": False, "checks": checks, "quality": {}}))
        self.assertEqual({row["n"]: row["verdict"] for row in report["predictions"]}[2], "missed")


class EngineNamesTest(unittest.TestCase):
    """The names delta reads from the engine and the harness: a rename there fails here, not silently as a null."""

    def test_the_engine_names_exist(self) -> None:
        for name in ("_entries", "_outline", "_section_state", "SECTIONS", "LIVING", "LESSON_FIELDS", "LESSONS_SUBJECT", "HOME",
                     "ARCHITECTURE"):
            self.assertTrue(hasattr(knowledge, name), name)
        self.assertEqual(knowledge.Entry._fields, ("text", "retired"))
        self.assertEqual(delta.FILES, knowledge.LIVING)
        self.assertEqual(set(delta.PREFIX), {"spec.md", knowledge.ARCHITECTURE})
        self.assertTrue(set(delta.RETIRED_WORD) >= set(delta.PREFIX))
        self.assertEqual(set(delta.RETIRED_WORD.values()), {"retired", "superseded"})

    def test_the_headings_of_every_named_section_are_the_ones_the_engine_counts(self) -> None:
        for name, words in knowledge.SECTIONS.items():
            self.assertIn(name, knowledge.LIVING)
            self.assertTrue(words)

    def test_the_harness_names_exist(self) -> None:
        for module, name in ((counters, "_starting_point"), (counters, "_git"), (counters, "_commit_id"), (metrics, "RECORD_BLOCK"),
                             (metrics, "WRITE_TOOL"), (metrics, "events"), (metrics, "ToolLog")):
            self.assertTrue(hasattr(module, name), name)
        self.assertTrue(hasattr(metrics.ToolLog(), "sequence"))

    def test_run_py_adds_the_block_beside_the_counters(self) -> None:
        source = (ROOT / "test" / "shiploop_e2e" / "run.py").read_text()
        self.assertIn("run_metrics.update(delta.safe_build(out, ledger, tool_log))", source)
        self.assertLess(source.index("counters.safe_build(out, ledger, tool_log)"), source.index("delta.safe_build(out, ledger, tool_log)"))


if __name__ == "__main__":
    unittest.main()
