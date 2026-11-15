#!/usr/bin/env python3
"""The third link of the ticket chain, `ticket-comments` (SPEC, "Follow-on chains and the delta ledger"). No model is called.

The chain is ticket-assignment (a run on fixtures/node-tickets), ticket-escalation (continues from it) and ticket-comments
(continues from that). The link adds comments to tickets. Its request is the delta alone: it says that everything the service
already does keeps working and describes none of the earlier links; the earlier links' checks and their hidden acceptance run
as regression after the run (SPEC, "A chain is read to its end").

What the link tests besides the new behaviour is whether the run keeps two decisions the base recorded and the first pass
carried into its own notes:

* the outbox holds back a second notice with the same key while the first still waits (decision 6), so a comment's notice needs
  a key that names the comment, or the second of two comments in a row is never told;
* the data file's record functions name every field it keeps, and an older file takes a field's default (decision 8), so a
  comment kept on the ticket must be named there and a file written before the change must still load.

Calibration, as for the pair (reference_ticket_comments.py): the base (the second link's reference) fails every check of the new
feature and passes the earlier links' checks; the reference passes all of them, the retention checks and the hidden acceptance
the link inherits; each defect fails exactly the check that reads the sentence or decision it breaks, and every check is failed
by some defect. No independent alternative is written yet (docs/shiploop-multipass-journal.md).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test" / "fixtures" / "quality"))

import chains  # noqa: E402
import quality  # noqa: E402
import reference_ticket_comments as comments  # noqa: E402
import reference_ticket_escalation as second  # noqa: E402
import run  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
CASE = CASES["ticket-comments"]
OWN, RETENTION = CASE["checks"], CASE["retention"]
NAMES = ("basics", "notified", "persisted")

# The deliveries are Node and the cases' HTTP checks run through serve.py, which finds the listener with lsof: where either is missing the
# classes that start servers are skipped, as the pair's calibration (shiploop-e2e-brownfield-tickets.test.py) skips them.
needs_servers = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                    "the cases' HTTP checks run through serve.py, which needs node and lsof")

SPEC_BEFORE = "# Spec\n\n## Requirements\n\n### R-1 Assignment\nA ticket is assigned.\n\n### R-2 Escalation\nUrgent tickets are escalated.\n"
SPEC_AFTER = SPEC_BEFORE + "\n### R-3 Comments\nA ticket takes comments.\n"
ARCH_BEFORE = "# Architecture\n\n## Decisions\n### AD-1 The store\nOne store method per change.\n\n### AD-2 Filters\nAnd.\n"
ARCH_AFTER = ARCH_BEFORE + "\n### AD-3 Comments on the ticket record\nKept in the data file.\n"

# The check of the new feature each defect fails, by its position in the case's own checks.
EXPECTED = {
    "base": {0, 1, 2},
    "reference": set(),
    "comment-default-key": {1},
    "comment-notifies-author": {1},
    "comments-newest-first": {0},
    "closed-takes-comments": {0},
    "empty-author-accepted": {0},
    "comments-lost-on-restart": {2},
    "legacy-file-refused": {2},
}


# serve.py gives each candidate a port with free_port() (bind to port 0, read the number, close the socket) and the candidate binds it a
# moment later. Another process of the machine can bind that number in between: the candidate then exits before it listens (serve.py says
# "the candidate exited (rc 1) before it listened on PORT=N", and its stderr holds `Error: listen EADDRINUSE`), or the ownership check names
# the other listener. That failed one check of one CI run of this suite (docs/experiments/serve-port-race-20261115/, journal F23). A
# collision touches one server once, so a variant whose own checks fail a different set than its defect declares is graded again, alone,
# until a grade agrees, at most REGRADES more times, and the last grade stands. A defect read by the wrong check disagrees every time and
# fails after REGRADES + 1 grades. checks/serve.py itself is not changed: it scores live deliveries too.
REGRADES = 3


def settle(grade, agrees_now, regrades: int = REGRADES):
    """``grade()`` once, and again (alone) while ``agrees_now(result)`` is false, at most `regrades` more times: the last result stands."""
    result = grade()
    for _ in range(regrades):
        if agrees_now(result):
            break
        result = grade()
    return result


def own_checks(work: Path, expected: set[int]) -> tuple[set[int], list[dict]]:
    """The positions of the own checks that fail on `work`, and the checks' rows, graded again until the positions are the `expected` ones."""
    def once() -> tuple[set[int], list[dict]]:
        rows = run.run_checks(work, OWN, timeout=120)
        return {i for i, row in enumerate(rows) if not row["pass"]}, rows
    return settle(once, lambda graded: graded[0] == expected)


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
    def test_it_is_the_third_link_of_the_ticket_chain(self) -> None:
        self.assertEqual(chains.of(CASES, "ticket-comments"), ["ticket-assignment", "ticket-escalation", "ticket-comments"])
        self.assertEqual(CASE["follows"], "ticket-escalation")
        self.assertEqual(CASE["style"], "brownfield")
        self.assertNotIn("base", CASE)  # a follow-on starts from the run before it, not from a fixture

    def test_it_is_held_to_both_earlier_links_checks_then_its_own_then_its_retention(self) -> None:
        _, prompt, checks, follows = run.load_case(type("Args", (), {"prompt": None, "case": "ticket-comments", "check": None}))
        self.assertEqual(follows, "ticket-escalation")
        self.assertEqual(prompt, CASE["prompt"])
        self.assertEqual(checks, CASES["ticket-assignment"]["checks"] + CASES["ticket-escalation"]["checks"] + OWN + RETENTION)

    def test_its_retention_commands_see_the_pass_just_before_it(self) -> None:
        self.assertEqual(len(RETENTION), 5)
        self.assertTrue(all("PRIOR_WORK" in command for command in RETENTION))
        self.assertTrue(any("AD-" in command for command in RETENTION), "the architecture keeps every earlier decision ID")
        self.assertTrue(CASE.get("retention_source") and CASE.get("checks_source"))

    def test_it_declares_no_quality_and_inherits_the_acceptance_the_scorecard_then_requires(self) -> None:
        self.assertNotIn("quality", CASE)
        inherited = run.case_quality("ticket-comments")
        self.assertEqual(inherited["acceptance"]["module"], "ticket_escalation_accept")
        self.assertEqual(inherited["refuse_ports"], [4180])
        self.assertTrue(scorecard.requires_acceptance("ticket-comments"))

    def test_the_request_is_the_delta_and_names_none_of_the_inherited_decisions(self) -> None:
        prompt = CASE["prompt"].lower()
        for word in ("outbox", "dedup", "idempot", "key", "template", "persistence", "decision", "ad-", "r-1", "data_file", "version"):
            self.assertNotIn(word, prompt, word)
        for earlier in ("reassign", "escalat", "oncall", "put /tickets", "assignee filter"):
            self.assertNotIn(earlier, prompt, f"the request must not restate the earlier links: {earlier}")
        self.assertIn("everything the service already does keeps working", prompt)

    def test_the_style_stays_out_of_every_suite_until_it_has_a_baseline_and_the_breadth_note_names_the_chain(self) -> None:
        suites = {name: suite for name, suite in json.loads((run.HERE / "suites.json").read_text()).items() if isinstance(suite, dict)}
        for name, suite in suites.items():
            self.assertNotIn("ticket-comments", suite.get("cases", []), name)
            self.assertNotIn("brownfield", suite.get("styles", []), name)
        note = suites["breadth"]["not_covered"]["brownfield"]
        for case in ("ticket-assignment", "ticket-escalation", "ticket-comments"):
            self.assertIn(case, note)


@needs_servers
class CalibrationTest(Isolated):
    """The three checks of the new feature against the base, the reference and each defect."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = tempfile.TemporaryDirectory()
        cls.graded, cls.why = {}, {}
        with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}):
            for variant in comments.VARIANTS:
                work = committed(comments.build(Path(cls.root.name) / variant, variant))
                cls.graded[variant], rows = own_checks(work, EXPECTED[variant])
                # A failure the variant's defect does not explain is told with the check's own output, all of it (run_checks keeps its
                # last 2000 characters): a check that fails under machine load (a server slow to listen) must be seen as that and not
                # as a defect, and a candidate that exited before it listened names its error at the end of that text, which the first
                # 300 characters cut off in the record of the CI failure of 2026-11-15.
                cls.why[variant] = {NAMES[i]: f"exit {row['returncode']}: {row['output']}" for i, row in enumerate(rows) if not row["pass"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.cleanup()

    def test_every_variant_is_listed_and_graded(self) -> None:
        self.assertEqual(set(EXPECTED), set(comments.VARIANTS))

    def test_the_base_fails_every_check_of_the_new_feature_and_the_reference_passes_them_all(self) -> None:
        self.assertEqual(self.graded["base"], {0, 1, 2})
        self.assertEqual(self.graded["reference"], set())

    def test_each_defect_fails_exactly_the_check_that_reads_what_it_breaks(self) -> None:
        for variant, expected in EXPECTED.items():
            with self.subTest(variant=variant):
                self.assertEqual(self.graded[variant], expected, self.why[variant])

    def test_every_check_is_failed_by_some_defect_and_every_defect_by_some_check(self) -> None:
        defects = {variant: failed for variant, failed in self.graded.items() if variant not in ("base", "reference")}
        self.assertEqual(set().union(*defects.values()), {0, 1, 2})
        self.assertTrue(all(defects.values()))


@needs_servers
class ChainRunTest(Isolated):
    """The whole chain's checks, as the harness runs them after a delivery, with the second link's reference as the run before."""

    def checks(self, work: Path, commands: list[str], prior: Path) -> list[bool]:
        """Each command's verdict, a failed one tried once more: the base's own node tests drop a connection now and then ("socket hang
        up", seen on the parent tree too, load or no load), and a chain runs them in the pristine check and in two retention counts.
        A check that is really broken fails twice."""
        env = {"PRIOR_WORK": str(prior)}
        rows = run.run_checks(work, commands, timeout=240, env=env)
        failed = [index for index, row in enumerate(rows) if not row["pass"]]
        if failed:
            for index, row in zip(failed, run.run_checks(work, [commands[index] for index in failed], timeout=240, env=env)):
                rows[index] = row
        return [row["pass"] for row in rows]

    def setUp(self) -> None:
        super().setUp()
        self.prior = committed(second.build(self.tmp / "prior", "reference"), SPEC_BEFORE, ARCH_BEFORE)
        _, _, self.every, _ = run.load_case(type("Args", (), {"prompt": None, "case": "ticket-comments", "check": None}))
        self.regression = len(self.every) - len(OWN) - len(RETENTION)

    def test_the_regression_comes_from_both_earlier_links(self) -> None:
        self.assertEqual(self.regression, len(CASES["ticket-assignment"]["checks"]) + len(CASES["ticket-escalation"]["checks"]))

    def test_the_reference_passes_the_regression_the_new_feature_and_every_retention_check(self) -> None:
        work = committed(comments.build(self.tmp / "reference", "reference"), SPEC_AFTER, ARCH_AFTER)
        self.assertEqual(self.checks(work, self.every, self.prior), [True] * len(self.every))

    def test_a_third_pass_that_changes_nothing_how_the_product_is_built_adds_no_decision_and_keeps_every_one(self) -> None:
        work = committed(comments.build(self.tmp / "reference", "reference"), SPEC_AFTER, ARCH_BEFORE)
        self.assertEqual(self.checks(work, RETENTION, self.prior), [True] * len(RETENTION))

    def test_the_run_before_it_unchanged_keeps_the_regression_and_fails_the_new_feature_the_tests_and_the_spec(self) -> None:
        work = committed(second.build(self.tmp / "unchanged", "reference"), SPEC_BEFORE, ARCH_BEFORE)
        got = self.checks(work, self.every, self.prior)
        self.assertEqual(got[:self.regression], [True] * self.regression)
        self.assertEqual(got[self.regression:self.regression + len(OWN)], [False] * len(OWN))
        self.assertEqual(got[self.regression + len(OWN):], [True, True, False, False, True])  # files, dependencies; tests, spec; decisions

    def test_a_file_of_the_run_before_deleted_and_a_requirement_and_a_decision_dropped_fail_their_retention_checks(self) -> None:
        work = comments.build(self.tmp / "lost", "reference")
        (work / "docs" / "operations.md").unlink()
        committed(work, SPEC_AFTER.replace("### R-1 Assignment\nA ticket is assigned.\n\n", ""),
                  ARCH_AFTER.replace("### AD-2 Filters\nAnd.\n\n", ""))
        self.assertEqual(self.checks(work, RETENTION, self.prior), [False, True, True, False, False])


@needs_servers
class InheritedAcceptanceTest(Isolated):
    """The hidden acceptance the link inherits from the second link: the third pass is held to what the second built."""

    def graded(self, variant: str) -> dict:
        work = committed(comments.build(self.tmp / variant, variant))
        spec = run.case_quality("ticket-comments")
        return quality.acceptance(work, spec["acceptance"], groups=set(), stop=lambda: None, logs=self.tmp / "logs" / variant,
                                  ports=spec["refuse_ports"])

    def test_the_reference_passes_every_inherited_check(self) -> None:
        block = self.graded("reference")
        self.assertTrue(block["observed"], block)
        self.assertEqual([row["id"] for row in block["checks"] if not row["pass"]], [])
        self.assertGreaterEqual(len(block["checks"]), 14)

    def test_a_defect_in_the_new_feature_leaves_the_earlier_behaviour_alone(self) -> None:
        block = self.graded("comment-default-key")
        self.assertTrue(block["observed"], block)
        self.assertEqual([row["id"] for row in block["checks"] if not row["pass"]], [])


class SettleTest(unittest.TestCase):
    """The regrade of a variant whose own checks failed a set its defect does not declare (no node needed)."""

    @staticmethod
    def graders(*grades):
        calls = []

        def again():
            calls.append(len(calls))
            return grades[len(calls) - 1]
        return again, calls

    def test_a_grade_that_agrees_is_not_graded_again(self) -> None:
        again, calls = self.graders({0})
        self.assertEqual(settle(again, lambda grade: grade == {0}), {0})
        self.assertEqual(len(calls), 1)

    def test_a_collision_is_graded_again_once_and_the_agreeing_grade_stands(self) -> None:
        again, calls = self.graders({0, 2}, {0}, "never read")
        self.assertEqual(settle(again, lambda grade: grade == {0}), {0})
        self.assertEqual(len(calls), 2, "grading stops at the first grade that agrees")

    def test_a_defect_read_by_the_wrong_check_is_graded_every_time_and_the_last_grade_stands(self) -> None:
        # The cost of the rule: only after REGRADES more grades does the suite say that a variant really disagrees.
        again, calls = self.graders({1}, {2}, {3}, {4}, "never read")
        self.assertEqual(settle(again, lambda grade: False), {4})
        self.assertEqual(len(calls), REGRADES + 1)


@needs_servers
class RegradeRouteTest(Isolated):
    """The regrade through the real serve.py: a candidate that is handed a port another socket holds fails every check of the first grade."""

    def holder(self) -> socket.socket:
        """A listening socket on every address, as a candidate's own, so that the candidate's bind of the same port number fails."""
        sock = socket.socket(socket.AF_INET6 if socket.has_ipv6 else socket.AF_INET)
        self.addCleanup(sock.close)
        try:
            if sock.family == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            sock.bind(("::" if sock.family == socket.AF_INET6 else "0.0.0.0", 0))
        except OSError as why:
            self.skipTest(f"cannot hold a port on every address here: {why}")
        sock.listen()
        return sock

    def test_a_first_grade_that_met_a_taken_port_is_graded_again_and_the_reference_passes(self) -> None:
        work = committed(comments.build(self.tmp / "reference", "reference"))
        holder = self.holder()
        port = holder.getsockname()[1]
        real, first = run.run_checks, []

        def grade(folder, checks, **kwargs):
            if not first:  # serve.py is handed the held port in every check of the first grade (its own regression's pin)
                first.extend(real(folder, checks, env={"E2E_SERVE_PORT": str(port)}, **kwargs))
                return first
            holder.close()
            return real(folder, checks, **kwargs)

        with mock.patch.object(run, "run_checks", grade):
            failed, rows = own_checks(work, set())
        self.assertTrue(any(not row["pass"] and str(port) in row["output"] for row in first), first)
        self.assertEqual(failed, set(), [row["output"] for row in rows])
        self.assertTrue(all(row["pass"] for row in rows))


if __name__ == "__main__":
    unittest.main()
