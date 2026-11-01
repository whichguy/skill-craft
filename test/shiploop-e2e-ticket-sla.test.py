#!/usr/bin/env python3
"""The fourth link of the ticket chain, `ticket-sla` (SPEC, "Follow-on chains and the delta ledger"). No model is called.

The chain is ticket-assignment, ticket-escalation, ticket-comments and ticket-sla. The first three add behaviour. This link CHANGES a
rule an earlier link set: escalation waits by priority (urgent and high), and a ticket is escalated at most twice, where the second
link's request said at most once. Its request is the delta alone but must name what it replaces, because the old rule is written
down in the living spec, in a decision and in a hidden check of the second link. What the link tests besides the new behaviour is
whether the run changes the old requirement, decision and test instead of leaving a rule standing that the code now breaks.

Why the link has an acceptance of its own: the second link's hidden ``escalation-at-most-once`` reads the sentence this request
replaces, so a correct delivery fails it. ``ModifiedRuleTest`` pins that. The link's acceptance (ticket_sla_accept) is the second
link's without that check, plus three that read the new rule.

Calibration, as for the third link (reference_ticket_sla.py): the base (the third link's reference) fails every check of the new rule
and passes the earlier links' checks; the reference and the alternative (a differently kept count) pass all of them, the retention
checks and the hidden acceptance; each defect fails exactly the check that reads the sentence it breaks, and two defects are seen only
by the hidden acceptance, which is the point of having one.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test" / "fixtures" / "quality"))

import chains  # noqa: E402
import delta  # noqa: E402
import quality  # noqa: E402
import reference_ticket_comments as third  # noqa: E402
import reference_ticket_sla as sla  # noqa: E402
import run  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
CASE = CASES["ticket-sla"]
OWN, RETENTION = CASE["checks"], CASE["retention"]
NAMES = ("waits", "twice", "persisted")
NEW_HIDDEN = ("sla-waits-by-priority", "sla-second-then-stop", "sla-second-not-immediate")

needs_servers = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                    "the cases' HTTP checks run through serve.py, which needs node and lsof")

# A third pass's living files, and the fourth's: the escalation requirement and decision are CHANGED, not dropped (their IDs stay).
SPEC_BEFORE = ("# Spec\n\n## Requirements\n\n### R-1 Assignment\nA ticket is assigned.\n\n### R-2 Escalation\nUrgent tickets are escalated, at most once.\n\n"
               "### R-3 Comments\nA ticket takes comments.\n")
SPEC_AFTER = SPEC_BEFORE.replace("Urgent tickets are escalated, at most once.", "Urgent and high tickets are escalated, at most twice.") \
    + "\n### R-4 Escalation waits by priority\nUrgent waits 60 minutes, high 240.\n"
ARCH_BEFORE = ("# Architecture\n\n## Decisions\n### AD-1 The store\nOne store method per change.\n\n### AD-2 Escalation once\nThe outbox key is the ticket.\n\n"
               "### AD-3 Comments on the ticket record\nKept in the data file.\n")
ARCH_AFTER = ARCH_BEFORE + "\n## Superseded\n### AD-2 Escalation once\nSuperseded by AD-4.\n\n### AD-4 Escalation twice, by priority\nThe outbox keys count them.\n"

# The own check each defect fails, by position in the case's own checks, and the new hidden checks it fails.
EXPECTED = {
    "base": ({0, 1, 2}, {"sla-waits-by-priority", "sla-second-then-stop"}),
    "reference": (set(), set()),
    "alternative": (set(), set()),
    "high-never-escalated": ({0}, {"sla-waits-by-priority"}),
    "high-uses-urgent-wait": ({0}, {"sla-waits-by-priority"}),
    "normal-escalated": ({0}, {"sla-waits-by-priority"}),
    "escalated-once-only": ({1, 2}, {"sla-second-then-stop"}),
    "third-escalation": ({1, 2}, {"sla-second-then-stop"}),
    "second-immediate": (set(), {"sla-second-not-immediate"}),
    "count-lost-on-restart": ({2}, {"sla-second-then-stop"}),
    "high-unit-seconds": (set(), {"sla-waits-by-priority"}),
}


def committed(folder: Path, spec: str | None = None, architecture: str | None = None) -> Path:
    """The folder as a delivery: the living files written when given, and a repository with everything committed."""
    if spec is not None or architecture is not None:
        (folder / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        if spec is not None:
            (folder / "docs" / "shiploop" / "spec.md").write_text(spec)
        if architecture is not None:
            (folder / "docs" / "shiploop" / "architecture.md").write_text(architecture)
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "d"]):
        subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)
    return folder


def hidden(work: Path, logs: Path, only: tuple[str, ...] | None = None) -> dict:
    """The case's hidden acceptance on a delivery, all of it or only the checks named."""
    spec = copy.deepcopy(run.case_quality("ticket-sla"))
    if only is not None:
        spec["acceptance"]["checks"] = [row for row in spec["acceptance"]["checks"] if row["id"] in only]
    return quality.acceptance(work, spec["acceptance"], groups=set(), stop=lambda: None, logs=logs, ports=spec["refuse_ports"])


class Isolated(unittest.TestCase):
    """Real git and real node, apart from the machine's Git configuration."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        patched = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        patched.start()
        self.addCleanup(patched.stop)


class CaseDeclarationTest(unittest.TestCase):
    def test_it_is_the_fourth_link_of_the_ticket_chain(self) -> None:
        self.assertEqual(chains.of(CASES, "ticket-sla"), ["ticket-assignment", "ticket-escalation", "ticket-comments", "ticket-sla"])
        self.assertEqual(CASE["follows"], "ticket-comments")
        self.assertEqual(CASE["style"], "brownfield")
        self.assertNotIn("base", CASE)

    def test_it_is_held_to_all_three_earlier_links_checks_then_its_own_then_its_retention(self) -> None:
        _, prompt, checks, follows = run.load_case(type("Args", (), {"prompt": None, "case": "ticket-sla", "check": None}))
        self.assertEqual(follows, "ticket-comments")
        self.assertEqual(prompt, CASE["prompt"])
        self.assertEqual(checks, CASES["ticket-assignment"]["checks"] + CASES["ticket-escalation"]["checks"] + CASES["ticket-comments"]["checks"]
                         + OWN + RETENTION)

    def test_its_retention_commands_see_the_pass_just_before_it(self) -> None:
        self.assertEqual(len(RETENTION), 5)
        self.assertTrue(all("PRIOR_WORK" in command for command in RETENTION))
        self.assertIn("for word in high;", RETENTION[2])
        self.assertTrue(any("AD-" in command for command in RETENTION))
        self.assertTrue(CASE.get("retention_source") and CASE.get("checks_source"))

    def test_the_spec_word_of_a_retention_check_comes_from_the_cases_own_request(self) -> None:
        """The first live run of this link failed a correct delivery because the check kept the previous link's word ("comment")."""
        for name, case in CASES.items():
            for command in case.get("retention") or []:
                for word in re.findall(r"grep -qi (\S+) docs/shiploop/spec\.md", command):
                    self.assertRegex(case["prompt"], re.compile(re.escape(word), re.I), (name, word))
        self.assertEqual(re.findall(r"grep -qi (\S+) docs/shiploop/spec\.md", " ".join(RETENTION)), ["ESCALATE_HIGH_MINUTES"])

    def test_the_ledger_patterns_match_the_wording_the_third_pass_really_used(self) -> None:
        """delta.may_change reads the earlier entries' own words. The live third pass wrote the rule as "enqueued once" under "Urgent
        escalation" and the decision as "Bulk assignment and escalation", not "at most once"; the first patterns matched neither."""
        spec = "# Spec\n\n## Requirements\n### R-7 Urgent escalation\nBasis: current request. An open urgent ticket past ESCALATE_AFTER_MINUTES is enqueued once for ONCALL.\n"
        arch = "# Architecture\n\n## Decisions\n### AD-3 Bulk assignment and escalation (implemented)\nBulk moves and escalation share the outbox.\n"
        may = CASE["delta"]["may_change"]
        self.assertEqual(delta.ids_block(spec, spec, "R", may["spec.md"])["expected"], ["R-7"])
        self.assertEqual(delta.ids_block(arch, arch, "AD", may["architecture.md"])["expected"], ["AD-3"])

    def test_it_declares_an_acceptance_of_its_own_because_it_replaces_a_rule_the_inherited_one_reads(self) -> None:
        own = run.case_quality("ticket-sla")
        self.assertEqual(own["acceptance"]["module"], "ticket_sla_accept")
        self.assertEqual(own["refuse_ports"], [4180])
        ids = [row["id"] for row in own["acceptance"]["checks"]]
        before = [row["id"] for row in CASES["ticket-escalation"]["quality"]["acceptance"]["checks"]]
        self.assertEqual(ids, [name for name in before if name != "escalation-at-most-once"] + list(NEW_HIDDEN))
        self.assertEqual({row["grade"] for row in own["acceptance"]["checks"] if row["id"] in NEW_HIDDEN}, {"fail-to-pass"})
        self.assertTrue(scorecard.requires_acceptance("ticket-sla"))

    def test_the_declared_checks_are_the_modules_checks(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ticket_sla_accept_for_test", ROOT / "test" / "shiploop_e2e" / "checks" / "ticket_sla_accept.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(list(module.CHECKS), [row["id"] for row in run.case_quality("ticket-sla")["acceptance"]["checks"]])

    def test_the_request_names_what_it_replaces_and_none_of_the_implementation_decisions(self) -> None:
        prompt = CASE["prompt"].lower()
        self.assertIn("replaces the rule that a ticket is escalated at most once", prompt)
        self.assertIn("escalate_high_minutes", prompt)
        for word in ("outbox", "dedup", "idempot", "key", "template", "persistence", "ad-", "r-2", "data_file", "version"):
            self.assertNotIn(word, prompt, word)

    def test_it_says_which_earlier_entries_it_may_change_for_the_ledger(self) -> None:
        change = CASE["delta"]["may_change"]
        self.assertEqual(set(change), {"spec.md", "architecture.md"})
        self.assertTrue(all(isinstance(pattern, str) and pattern for patterns in change.values() for pattern in patterns))

    def test_the_style_stays_out_of_every_suite_and_the_breadth_note_names_the_chain(self) -> None:
        suites = {name: suite for name, suite in json.loads((run.HERE / "suites.json").read_text()).items() if isinstance(suite, dict)}
        for name, suite in suites.items():
            self.assertNotIn("ticket-sla", suite.get("cases", []), name)
        note = suites["breadth"]["not_covered"]["brownfield"]
        for case in ("ticket-assignment", "ticket-escalation", "ticket-comments", "ticket-sla"):
            self.assertIn(case, note)


@needs_servers
class CalibrationTest(Isolated):
    """The case's own checks, and its new hidden checks, against the base, the reference, the alternative and each defect."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = tempfile.TemporaryDirectory()
        cls.own, cls.why, cls.new = {}, {}, {}
        with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}):
            for variant in sla.VARIANTS:
                work = committed(sla.build(Path(cls.root.name) / variant, variant))
                rows = run.run_checks(work, OWN, timeout=180)
                cls.own[variant] = {i for i, row in enumerate(rows) if not row["pass"]}
                # A failure the variant's defect does not explain is told with the check's own output: a check that fails under
                # machine load must be seen as that and not as a defect.
                cls.why[variant] = {NAMES[i]: f"exit {row['returncode']}: {row['output'][:300]}" for i, row in enumerate(rows) if not row["pass"]}
                block = hidden(work, Path(cls.root.name) / "logs" / variant, NEW_HIDDEN)
                cls.new[variant] = {row["id"] for row in block["checks"] if not row["pass"]}
                cls.why[variant]["hidden"] = json.dumps([row for row in block["checks"] if not row["pass"]])[:600]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.cleanup()

    def test_every_variant_is_listed_and_graded(self) -> None:
        self.assertEqual(set(EXPECTED), set(sla.VARIANTS))

    def test_the_base_fails_the_checks_of_the_new_rule_and_the_reference_and_the_alternative_pass_them_all(self) -> None:
        self.assertEqual(self.own["base"], {0, 1, 2})
        for variant in ("reference", "alternative"):
            self.assertEqual((self.own[variant], self.new[variant]), (set(), set()), self.why[variant])

    def test_each_defect_fails_exactly_the_checks_that_read_what_it_breaks(self) -> None:
        for variant, (own, hidden_ids) in EXPECTED.items():
            with self.subTest(variant=variant):
                self.assertEqual((self.own[variant], self.new[variant]), (own, hidden_ids), self.why[variant])

    def test_every_check_of_the_new_rule_is_failed_by_some_defect(self) -> None:
        defects = [variant for variant in EXPECTED if variant not in ("base", "reference", "alternative")]
        self.assertEqual(set().union(*(self.own[variant] for variant in defects)), {0, 1, 2})
        self.assertEqual(set().union(*(self.new[variant] for variant in defects)), set(NEW_HIDDEN))

    def test_two_defects_are_seen_only_by_the_hidden_acceptance(self) -> None:
        silent = {variant for variant in EXPECTED if variant not in ("base",) and not self.own[variant] and self.new[variant]}
        self.assertEqual(silent, {"second-immediate", "high-unit-seconds"})


@needs_servers
class ChainRunTest(Isolated):
    """The whole chain's checks, as the harness runs them after a delivery, with the third link's reference as the run before."""

    def checks(self, work: Path, commands: list[str], prior: Path) -> list[bool]:
        """Each command's verdict, a failed one tried once more: the base's own node tests drop a connection now and then ("socket hang
        up", seen on the parent tree too, load or no load), and a chain runs them in the pristine check and in two retention counts.
        A check that is really broken fails twice."""
        env = {"PRIOR_WORK": str(prior)}
        rows = run.run_checks(work, commands, timeout=300, env=env)
        failed = [index for index, row in enumerate(rows) if not row["pass"]]
        if failed:
            for index, row in zip(failed, run.run_checks(work, [commands[index] for index in failed], timeout=300, env=env)):
                rows[index] = row
        return [row["pass"] for row in rows]

    def setUp(self) -> None:
        super().setUp()
        self.prior = committed(third.build(self.tmp / "prior", "reference"), SPEC_BEFORE, ARCH_BEFORE)
        _, _, self.every, _ = run.load_case(type("Args", (), {"prompt": None, "case": "ticket-sla", "check": None}))
        self.regression = len(self.every) - len(OWN) - len(RETENTION)

    def test_the_regression_comes_from_all_three_earlier_links(self) -> None:
        self.assertEqual(self.regression, sum(len(CASES[name]["checks"]) for name in ("ticket-assignment", "ticket-escalation", "ticket-comments")))

    def test_the_reference_passes_the_regression_the_new_rule_and_every_retention_check(self) -> None:
        work = committed(sla.build(self.tmp / "reference", "reference"), SPEC_AFTER, ARCH_AFTER)
        self.assertEqual(self.checks(work, self.every, self.prior), [True] * len(self.every))

    def test_the_run_before_it_unchanged_keeps_the_regression_and_fails_the_new_rule_the_tests_and_the_spec(self) -> None:
        work = committed(third.build(self.tmp / "unchanged", "reference"), SPEC_BEFORE, ARCH_BEFORE)
        got = self.checks(work, self.every, self.prior)
        self.assertEqual(got[:self.regression], [True] * self.regression)
        self.assertEqual(got[self.regression:self.regression + len(OWN)], [False] * len(OWN))
        self.assertEqual(got[self.regression + len(OWN):], [True, True, False, False, True])  # files, dependencies; tests, spec; decisions

    def test_an_old_requirement_moved_under_retired_and_an_old_decision_under_superseded_keep_their_ids_and_pass_retention(self) -> None:
        spec = SPEC_AFTER.replace("### R-2 Escalation\nUrgent and high tickets are escalated, at most twice.\n",
                                  "### R-4 Escalation waits by priority\nUrgent waits 60 minutes, high 240.\n\n## Retired\n### R-2 Escalation\nReplaced by R-4.\n", 1)
        work = committed(sla.build(self.tmp / "moved", "reference"), spec, ARCH_AFTER)
        self.assertEqual(self.checks(work, RETENTION, self.prior), [True] * len(RETENTION))


    def test_a_requirement_edited_in_place_passes_retention_when_it_names_the_new_variable_and_fails_when_it_does_not(self) -> None:
        """A modifying link may add no requirement ID: the live run changed its escalation requirement in place, and the prior spec already
        says "comments", so only a word of this link's own can show the spec took the request in."""
        named = SPEC_BEFORE.replace("Urgent tickets are escalated, at most once.",
                                    "Urgent tickets wait ESCALATE_AFTER_MINUTES and high tickets ESCALATE_HIGH_MINUTES; a ticket is escalated at most twice.")
        silent = SPEC_BEFORE.replace("Urgent tickets are escalated, at most once.", "Urgent and high tickets are escalated, at most twice.")
        work = committed(sla.build(self.tmp / "named", "reference"), named, ARCH_AFTER)
        self.assertEqual(self.checks(work, RETENTION, self.prior), [True] * len(RETENTION))
        work = committed(sla.build(self.tmp / "silent", "reference"), silent, ARCH_AFTER)
        self.assertEqual(self.checks(work, RETENTION, self.prior), [True, True, True, False, True])  # only the requirement IDs and the new word

@needs_servers
class ModifiedRuleTest(Isolated):
    """Why the link has an acceptance of its own: the second link's hidden check reads the sentence this request replaces."""

    def old_check(self, variant: str, builder) -> list:
        work = committed(builder.build(self.tmp / variant, variant))
        spec = copy.deepcopy(run.case_quality("ticket-escalation"))
        spec["acceptance"]["checks"] = [row for row in spec["acceptance"]["checks"] if row["id"] == "escalation-at-most-once"]
        block = quality.acceptance(work, spec["acceptance"], groups=set(), stop=lambda: None, logs=self.tmp / "logs" / variant, ports=spec["refuse_ports"])
        self.assertTrue(block["observed"], block)
        return [row["pass"] for row in block["checks"]]

    def test_the_second_links_at_most_once_check_passes_the_third_pass_and_fails_a_correct_fourth(self) -> None:
        self.assertEqual(self.old_check("reference", third), [True])
        self.assertEqual(self.old_check("reference", sla), [False])

    def test_the_link_inherits_nothing_from_it_and_runs_the_other_thirteen_on_the_reference(self) -> None:
        block = hidden(committed(sla.build(self.tmp / "all", "reference")), self.tmp / "logs" / "all")
        self.assertTrue(block["observed"], block)
        self.assertEqual([row["id"] for row in block["checks"] if not row["pass"]], [])
        self.assertEqual(len(block["checks"]), 16)
        self.assertNotIn("escalation-at-most-once", [row["id"] for row in block["checks"]])

    def test_the_alternative_passes_every_hidden_check_too(self) -> None:
        block = hidden(committed(sla.build(self.tmp / "alt", "alternative")), self.tmp / "logs" / "alt")
        self.assertEqual([row["id"] for row in block["checks"] if not row["pass"]], [])


if __name__ == "__main__":
    unittest.main()
