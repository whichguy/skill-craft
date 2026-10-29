#!/usr/bin/env python3
"""The medium brownfield case pair: `ticket-assignment` on fixtures/node-tickets and its follow-on `ticket-escalation` (D7 of
docs/shiploop-brownfield-baseline-design-2026-10-28.md, "a medium brownfield case with a follow-on run"). No model is called.

SPEC "A brownfield case" asks each case's calibration: the base fails every fail-to-pass check and passes every pass-to-pass
check and the pristine suite; the reference passes every check and the pristine suite; each targeted defect fails exactly the
checks its defect reads; an independently written alternative passes everything. The follow-on starts from the first run's
delivery, so its base is the first case's reference. These tests grade every variant of
test/fixtures/quality/reference_ticket_assignment.py and reference_ticket_escalation.py with:

* the held-out acceptance (checks/ticket_assignment_accept.py, checks/ticket_escalation_accept.py) through
  ``quality.acceptance``, as a run's quality phase calls it, the delivered copy (``quality.Product``) included;
* the base's pristine tests (checks/base_tests.py pristine node-tickets).

Then the cases' own checks through ``run.run_checks`` (the follow-on's with $PRIOR_WORK and its retention checks), the catalog
entries, the fixture, the ground-truth table, and one fake-host run of the first case through ``run.main``.

The variants are graded side by side, a thread each (``quality.free_port`` never hands out a port twice), and the pristine
runs start only after every acceptance run has ended, so no server of the base's own tests takes a port handed to a product.
"""

from __future__ import annotations

import concurrent.futures
import functools
import importlib.util
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


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The fake hosts and the harness cases of the main harness suite; only classes defined in this file are tests of this file.
e2e = _load("shiploop_e2e_main_tests", "shiploop-e2e.test.py")
run = e2e.run

import boundary  # noqa: E402
import brownfield  # noqa: E402
import quality  # noqa: E402
import reference_ticket_assignment as first  # noqa: E402
import reference_ticket_escalation as second  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
FIXTURE = brownfield.FIXTURES / "node-tickets"
BASE_TESTS = run.HERE / "checks" / "base_tests.py"
GROUND_TRUTH = ROOT / "docs" / "experiments" / "brownfield-baseline-20261028" / "ground-truth" / "node-tickets-expected.md"
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
# Threads that grade variants side by side: most of a variant's time is spent waiting on its servers and its worker.
POOL = min(16, max(4, 2 * (os.cpu_count() or 2)))


class Case:
    """One case of the pair: its catalog entry, its builder and what each of its variants must fail."""

    def __init__(self, name: str, builder, expected: dict, pristine: set):
        self.name, self.builder, self.entry = name, builder, CASES[name]
        self.block = self.entry["quality"]["acceptance"]
        self.ids = [item["id"] for item in self.block["checks"]]
        self.fail_to_pass = {item["id"] for item in self.block["checks"] if item["grade"] == "fail-to-pass"}
        self.pass_to_pass = {item["id"] for item in self.block["checks"] if item["grade"] == "pass-to-pass"}
        self.expected = {"base": self.fail_to_pass, "reference": set(), "alternative": set(), **expected}
        self.pristine = pristine  # the variants the base's pristine tests reject


ASSIGNMENT = Case("ticket-assignment", first, {
    "filter-or": {"filters-combine"},
    "filter-after-page": {"assignee-filter-pages"},
    "no-envelope": {"assignee-validation", "assign-state-and-missing"},
    "conflict-as-invalid": {"assign-state-and-missing"},
    "closed-assignable": {"assign-state-and-missing"},
    "notify-inline": {"assignee-notified"},
    "notify-no-template": {"assignee-notified"},
    "notify-key-per-ticket": {"assignee-notified"},
    "notify-requester": {"assignee-notified"},
    "audit-bypassed": {"assign-audited"},
    "actor-ignored": {"assign-audited"},
    "same-agent-not-noop": {"assign-same-agent-noop"},
    "memory-only-assignee": {"assignee-persists", "old-tickets-unassigned", "cli-shows-assignee"},
    "old-data-refused": {"old-data-loads", "old-tickets-unassigned"},
    "old-assignee-undefined": {"old-tickets-unassigned"},
    "raw-column-inserted": {"cli-raw-columns"},
    "cli-no-assignee": {"cli-shows-assignee"},
    # The unassign of a closed ticket is refused as invalid before its state is read: a 400 where 409 is due.
    "no-unassign": {"assign-and-unassign", "assign-state-and-missing", "assign-audited"},
    "empty-filter-ignored": {"assignee-filter", "old-tickets-unassigned"},
    "name-limit-off-by-one": {"assignee-validation"},
    # The command line lists through the store too, so it loses the assignee with the listing.
    "listing-hides-assignee": {"assign-and-unassign", "cli-shows-assignee"},
    "update-rejects-resolved": {"ticket-lifecycle-unchanged"},
    "default-limit-changed": {"listing-unchanged"},
    "resolved-template-replaced": {"notifications-unchanged"},
    "audit-not-saved": {"restart-keeps-state"},
    "backoff-linear": set(),
    "validate-renamed": set(),
}, pristine={"default-limit-changed", "resolved-template-replaced", "audit-not-saved", "backoff-linear", "validate-renamed"})

ESCALATION = Case("ticket-escalation", second, {
    "reassign-same-allowed": {"reassign-validation"},
    "reassign-plain-errors": {"reassign-validation"},
    "reassign-moves-resolved": {"reassign-moves"},
    "reassign-unordered": {"reassign-moves"},
    "reassign-unaudited": {"reassign-audited"},
    "reassign-no-notify": {"reassign-notifies"},
    "escalation-also-in-request": {"worker-off-is-quiet"},
    "escalation-own-timer": {"worker-off-is-quiet"},
    "escalation-in-memory": {"escalation-at-most-once"},
    "escalation-repeats": {"escalation-at-most-once"},
    "escalation-includes-assigned": {"escalation-rules"},
    "escalation-includes-in-progress": {"escalation-rules"},
    "escalation-minutes-as-seconds": {"escalation-rules"},
    "escalation-default-oncall": {"escalation-notifies-oncall"},
    "filter-or-again": {"assignment-listing-kept"},
    "assignment-notify-dropped": {"assignment-notified-kept"},
    "raw-column-moved": {"cli-raw-columns-kept"},
    # Tickets saved without their assignee load as not unassigned (undefined), so they are never escalated either.
    "assignee-lost-on-restart": {"assignment-persists-kept", "escalation-rules", "escalation-at-most-once"},
    "unassign-broken": {"assignment-kept"},
    "update-rejects-resolved": {"existing-api-kept"},
    "outbox-enqueue-renamed": set(),
}, pristine={"outbox-enqueue-renamed"})

PAIR = (ASSIGNMENT, ESCALATION)

needs_node = unittest.skipUnless(shutil.which("node"), "the deliveries are Node: this class needs node on PATH")
needs_lsof = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                 "the cases' HTTP checks run through serve.py, which needs node and lsof")


def committed(folder: Path) -> Path:
    """The folder as a delivery: a repository with its files committed, as a run leaves work/."""
    env = {**os.environ, **GIT_ENV}
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "d"]):
        subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True, env=env)
    return folder


def base_tests(delivery: Path, subcommand: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BASE_TESTS), subcommand, "node-tickets"], cwd=delivery, capture_output=True,
                          text=True, timeout=600, stdin=subprocess.DEVNULL)


def failing(done: subprocess.CompletedProcess) -> str:
    """What a base_tests.py run printed: its return code, its FAIL line and the end of its error output."""
    return f"rc {done.returncode}: {done.stdout.strip()[-1500:]} {done.stderr.strip()[-1500:]}"


def suite_wanted(case: Case, variant: str) -> bool:
    """Whether a test reads the delivery's own suite: the base, the deliveries and the defects that edit the base's tests."""
    return variant in ("base", "reference", "alternative") or variant in case.builder.EDITS_BASE_TESTS


def agrees(case: Case, variant: str, kind: str, result) -> bool:
    """Whether a graded result is the one the variant declares: its failed held-out checks, its pristine verdict, or its own
    suite's (which only the first case's base fails: it adds no test)."""
    if kind == "accepted":
        return bool(result.get("observed")) and {row["id"] for row in result["checks"] if not row["pass"]} == case.expected[variant]
    if kind == "pristine":
        return (result.returncode != 0) == (variant in case.pristine)
    return (result.returncode != 0) == (case is ASSIGNMENT and variant == "base")


@functools.cache
def graded() -> dict:
    """Every variant of both cases built, committed and graded: {"deliveries", "accepted", "pristine", "suite", "groups",
    "regraded"}, each keyed by (case name, variant). The acceptance runs side by side first, the longest first (a base waits out
    each bounded wait for what it lacks, and the follow-on's variants run more checks); the node --test runs follow, side by
    side.

    A result that disagrees with what its variant declares is graded once more, alone, and that grade stands (``regraded``
    names them). A defect disagrees both times. What does not is the machine: a hundred node --test runs at once, each starting
    dozens of servers on recycled ports, on a host other work also loads, have shown a test of the base's own suite end in a
    reset connection ("socket hang up") about once in two hundred runs, never twice in a row, and never in a run alone."""
    tmp = Path(tempfile.mkdtemp(prefix="brownfield-tickets-"))
    unittest.addModuleCleanup(shutil.rmtree, tmp, True)
    jobs = sorted(((case, variant) for case in PAIR for variant in case.builder.VARIANTS),
                  key=lambda job: (job[1] != "base", job[0] is not ESCALATION))
    groups: set = set()

    def build(job):
        case, variant = job
        return (case.name, variant), committed(case.builder.build(tmp / case.name / variant, variant))

    with concurrent.futures.ThreadPoolExecutor(POOL) as pool:
        deliveries = dict(pool.map(build, jobs))

        def accept(job):
            case, variant = job
            return (case.name, variant), quality.acceptance(deliveries[case.name, variant], case.block, groups=groups,
                                                            stop=lambda: None, logs=tmp / "logs" / case.name / variant,
                                                            ports=case.entry["quality"]["refuse_ports"])

        accepted = dict(pool.map(accept, jobs))
        runs = [(job, kind) for job in jobs for kind in ("pristine", "suite") if kind == "pristine" or suite_wanted(*job)]
        ran = dict(pool.map(lambda run_: ((run_[1], run_[0][0].name, run_[0][1]),
                                          base_tests(deliveries[run_[0][0].name, run_[0][1]], run_[1])), runs))
    results = {"accepted": accepted, "pristine": {key[1:]: done for key, done in ran.items() if key[0] == "pristine"},
               "suite": {key[1:]: done for key, done in ran.items() if key[0] == "suite"}}
    by_name = {case.name: case for case in PAIR}
    regraded = []
    for kind, graded_kind in results.items():
        for (name, variant), result in list(graded_kind.items()):
            if not agrees(by_name[name], variant, kind, result):
                regraded.append((kind, name, variant))
                graded_kind[name, variant] = (accept((by_name[name], variant))[1] if kind == "accepted"
                                              else base_tests(deliveries[name, variant], kind))
    return {"deliveries": deliveries, "groups": groups, "regraded": regraded, **results}


class CaseDeclarationTest(unittest.TestCase):
    """The catalog entries: the pin, the follow-on, the grades and the held-out files."""

    def test_the_declared_ids_are_exactly_each_modules_checks_with_a_grade_and_a_source_and_the_existing_behaviour_first(self):
        for case in PAIR:
            with self.subTest(case=case.name):
                self.assertEqual(case.ids, list(quality.load_checks(case.block["module"], quality.HERE / "checks").CHECKS))
                for item in case.block["checks"]:
                    self.assertIn(item["grade"], ("fail-to-pass", "pass-to-pass"), item["id"])
                    self.assertTrue(item["source"].strip(), f"{item['id']} quotes what it reads")
                count = len(case.pass_to_pass)
                self.assertEqual(set(case.ids[:count]), case.pass_to_pass, "the existing behaviour is checked first")
                self.assertEqual(case.entry["quality"]["refuse_ports"], [4180])

    def test_the_pin_is_the_fixtures_digest_and_resolves(self):
        self.assertEqual(ASSIGNMENT.entry["base"]["fixture"], "node-tickets")
        self.assertEqual(brownfield.digest(FIXTURE), ASSIGNMENT.entry["base"]["digest"],
                         "a change to fixtures/node-tickets is a change to this case: update the pin with it")
        self.assertEqual(brownfield.resolve(ASSIGNMENT.entry), FIXTURE)

    def test_the_follow_on_runs_the_first_cases_checks_again_and_retention_and_starts_from_no_base(self):
        name, _prompt, checks, follows = run.load_case(run.parser().parse_args(["--case", "ticket-escalation"]))
        self.assertEqual((name, follows), ("ticket-escalation", "ticket-assignment"))
        self.assertEqual(checks, ASSIGNMENT.entry["checks"] + ESCALATION.entry["checks"] + ESCALATION.entry["retention"])
        self.assertTrue(all("PRIOR_WORK" in check for check in ESCALATION.entry["retention"]))
        self.assertNotIn("base", ESCALATION.entry, "a follow-on starts from the followed run's checkout")
        self.assertEqual(run.case_quality("ticket-escalation")["acceptance"]["module"], "ticket_escalation_accept")
        self.assertTrue(ESCALATION.entry.get("retention_source"))

    def test_the_acceptance_modules_and_the_references_are_held_out(self):
        held = boundary.held_out_files(CASES)
        markers = quality.held_out_markers([case.block for case in PAIR])
        for path in ("test/shiploop_e2e/checks/ticket_assignment_accept.py", "test/shiploop_e2e/checks/ticket_escalation_accept.py",
                     "test/fixtures/quality/reference_ticket_assignment.py", "test/fixtures/quality/reference_ticket_escalation.py"):
            with self.subTest(path=path):
                self.assertIn(path, held)
                self.assertIn(Path(path).stem, markers)

    def test_the_prompts_name_none_of_the_latent_facts(self):
        # What the base keeps in its documents and code, which the requests depend on and leave unnamed.
        for case in PAIR:
            prompt = case.entry["prompt"].lower()
            for word in ("audit", "outbox", "envelope", "409", "cursor", "data_file", "--raw", "weekly", "worker_interval",
                         "x-actor", "decision"):
                with self.subTest(case=case.name, word=word):
                    self.assertNotIn(word, prompt)

    def test_the_style_is_left_out_of_breadth_by_name(self):
        breadth = json.loads(run.SUITES.read_text())["breadth"]
        self.assertNotIn("brownfield", breadth["styles"])
        for case in PAIR:
            self.assertEqual(case.entry["style"], "brownfield")
        self.assertIn("ticket-assignment", breadth["not_covered"]["brownfield"])

    def test_the_scorecard_requires_both_cases_acceptance(self):
        for case in PAIR:
            with self.subTest(case=case.name):
                self.assertTrue(scorecard.requires_acceptance(case.name))
                unmeasured: dict = {}
                result = {"case": case.name, "pass": True, "quality": {"acceptance": {"observed": False, "reason": "r"}}}
                self.assertEqual(scorecard.accuracy(result, unmeasured)["floor"], scorecard.UNOBSERVED)


class BaseFixtureTest(unittest.TestCase):
    """fixtures/node-tickets: an ordinary team's service of the size D7 asks for, which never names the harness."""

    def files(self) -> list[Path]:
        return brownfield.base_files(FIXTURE)

    def test_it_never_names_the_harness_or_what_is_planted(self):
        pattern = re.compile(r"shiploop|e2e|held.out|calibrat|planted|latent|fail-to-pass|pass-to-pass|\bai\b|llm", re.I)
        found = [f"{path.relative_to(FIXTURE)}: {match.group(0)}" for path in self.files()
                 for match in [pattern.search(path.read_text())] if match]
        self.assertEqual(found, [])

    def test_it_is_medium_sized(self):
        lines = {path: len(path.read_text().splitlines()) for path in self.files()}
        source = sum(n for path, n in lines.items() if path.suffix == ".js" and path.relative_to(FIXTURE).parts[0] != "test")
        tests = sum(n for path, n in lines.items() if path.relative_to(FIXTURE).parts[0] == "test")
        self.assertTrue(1500 <= source <= 2500, f"{source} lines of source")
        self.assertTrue(3000 <= sum(lines.values()) <= 4500, f"{sum(lines.values())} lines in all")
        self.assertGreater(tests, 1000)

    def test_its_decision_records_include_a_superseded_one_and_a_template_that_is_not_a_decision(self):
        records = sorted(path.name for path in (FIXTURE / "docs" / "decisions").glob("0*.md"))
        self.assertEqual(len(records), 8)
        self.assertIn("Status: Superseded by", (FIXTURE / "docs/decisions/0003-offset-pagination.md").read_text())
        self.assertTrue((FIXTURE / "docs/decisions/template.md").is_file())

    def test_the_ground_truth_names_every_check_and_every_decision_record(self):
        table = GROUND_TRUTH.read_text()
        for case in PAIR:
            for ident in case.ids:
                with self.subTest(check=ident):
                    self.assertIn(f"`{ident}`", table)
        for record in (FIXTURE / "docs" / "decisions").glob("*.md"):
            with self.subTest(record=record.name):
                self.assertIn(record.name, table)


@needs_node
class CalibrationTest(unittest.TestCase):
    """Every variant of both cases, graded by the held-out checks and the base's pristine tests."""

    @classmethod
    def setUpClass(cls):
        cls.graded = graded()

    def failed(self, case: Case, variant: str) -> set:
        block = self.graded["accepted"][case.name, variant]
        self.assertTrue(block["observed"], block)
        return {row["id"] for row in block["checks"] if not row["pass"]}

    def notes(self, case: Case, variant: str) -> dict:
        return {row["id"]: row["note"] for row in self.graded["accepted"][case.name, variant].get("checks", []) if not row["pass"]}

    def test_each_base_fails_every_fail_to_pass_check_and_passes_the_pass_to_pass_ones_and_its_pristine_tests(self):
        for case in PAIR:
            with self.subTest(case=case.name):
                self.assertEqual(self.failed(case, "base"), case.fail_to_pass, self.notes(case, "base"))
                pristine = self.graded["pristine"][case.name, "base"]
                self.assertEqual(pristine.returncode, 0, pristine.stdout)
                self.assertIn("117 of 117 tests", pristine.stdout)

    def test_the_references_and_the_alternatives_pass_every_check_and_the_pristine_tests(self):
        for case in PAIR:
            for variant in ("reference", "alternative"):
                with self.subTest(case=case.name, variant=variant):
                    self.assertEqual(self.failed(case, variant), set(), self.notes(case, variant))
                    pristine = self.graded["pristine"][case.name, variant]
                    self.assertEqual(pristine.returncode, 0, pristine.stdout)

    def test_a_disagreeing_grade_is_rare(self):
        # Regrading is for the machine, not the variants: more than a few would say the variants or the checks waver.
        self.assertLessEqual(len(self.graded["regraded"]), 4, self.graded["regraded"])

    def test_each_variant_fails_exactly_the_checks_its_defect_reads(self):
        for case in PAIR:
            self.assertEqual(set(case.expected), set(case.builder.VARIANTS))
            for variant, expected in case.expected.items():
                with self.subTest(case=case.name, variant=variant):
                    self.assertEqual(self.failed(case, variant), expected, self.notes(case, variant))
                    pristine = self.graded["pristine"][case.name, variant]
                    self.assertEqual(pristine.returncode != 0, variant in case.pristine, failing(pristine))
        self.assertEqual(set(), self.graded["groups"], "every server the checks started was ended")

    def test_every_check_is_failed_by_some_defect_and_every_defect_by_some_check(self):
        for case in PAIR:
            with self.subTest(case=case.name):
                defects = list(case.builder.DEFECTS)
                caught = set().union(*(case.expected[variant] for variant in defects))
                self.assertEqual(caught, set(case.ids), "a check no defect fails could never fail")
                unseen = [variant for variant in defects if not case.expected[variant] and variant not in case.pristine]
                self.assertEqual(unseen, [], "a defect neither the held-out checks nor the pristine tests fail would go unnoticed")

    def test_the_pass_to_pass_checks_see_what_the_bases_own_tests_do_not(self):
        # A regression of existing behaviour the base's tests leave untested: only a held-out pass-to-pass check sees it.
        for case in PAIR:
            with self.subTest(case=case.name):
                self.assertTrue(case.expected["update-rejects-resolved"] <= case.pass_to_pass)
                self.assertNotIn("update-rejects-resolved", case.pristine)

    def test_the_defects_that_edit_the_bases_tests_pass_their_own_suite_and_fail_the_pristine_one(self):
        for case in PAIR:
            for variant, test_file in case.builder.EDITS_BASE_TESTS.items():
                with self.subTest(case=case.name, variant=variant):
                    delivery = self.graded["deliveries"][case.name, variant]
                    self.assertNotEqual((delivery / test_file).read_bytes(), (FIXTURE / test_file).read_bytes())
                    own = self.graded["suite"][case.name, variant]
                    self.assertEqual(own.returncode, 0, own.stdout)
                    self.assertIn("FAIL: the base's pristine tests against the delivered source",
                                  self.graded["pristine"][case.name, variant].stdout)

    def test_the_planted_defect_is_the_bases_own_listing_filter(self):
        # The base lists a ticket that matches any one filter; the request's "every filter" needs it fixed, and never names it.
        line = "  return given.some(([field, value]) => ticket[field] === value);\n"
        self.assertIn(line, (FIXTURE / "src/tickets/query.js").read_text())
        for case, variant in ((ASSIGNMENT, "filter-or"), (ESCALATION, "filter-or-again")):
            with self.subTest(variant=variant):
                self.assertIn(line, (self.graded["deliveries"][case.name, variant] / "src/tickets/query.js").read_text())
        self.assertNotIn(line, (self.graded["deliveries"][ASSIGNMENT.name, "reference"] / "src/tickets/query.js").read_text())

    def test_the_suite_check_asks_for_new_tests_beside_the_bases(self):
        self.assertIn("no more than the base's 117", self.graded["suite"][ASSIGNMENT.name, "base"].stdout)
        self.assertEqual(self.graded["suite"][ESCALATION.name, "base"].returncode, 0, "the first run added tests of its own")
        for case in PAIR:
            for variant in ("reference", "alternative"):
                with self.subTest(case=case.name, variant=variant):
                    own = self.graded["suite"][case.name, variant]
                    self.assertEqual(own.returncode, 0, own.stdout)

    def test_an_edit_that_no_longer_applies_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            for builder in (first, second):
                with self.subTest(builder=builder.__name__), \
                        mock.patch.dict(builder.DEFECTS, {"stale": [("src/server.js", "no such text", "x")]}), \
                        mock.patch.object(builder, "VARIANTS", (*builder.VARIANTS, "stale")):
                    with self.assertRaisesRegex(ValueError, "occurs 0 times"):
                        builder.build(Path(tmp) / builder.__name__, "stale")


SPEC_BEFORE = "# Spec\n\n## R-1 Ticket assignment\n\nPUT /tickets/:id/assignee assigns a ticket.\n\n## R-2 The assignee filter\n"
SPEC_AFTER = SPEC_BEFORE + "\n## R-3 Bulk reassignment\n\n## R-4 Escalation of urgent tickets to ONCALL\n"


@needs_lsof
class CaseChecksTest(unittest.TestCase):
    """The cases' own checks, run as the harness runs them after a delivery (run.run_checks)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        e2e.isolate_git(self)

    def checks(self, work: Path, checks: list[str], prior: Path | None = None) -> list[bool]:
        env = {"PRIOR_WORK": str(prior)} if prior else None
        return [row["pass"] for row in run.run_checks(work, checks, timeout=180, env=env)]

    def test_the_first_cases_base_fails_the_suite_and_http_checks_and_its_deliveries_pass_all(self):
        for variant, expected in (("base", [False, True, False]), ("reference", [True, True, True]),
                                  ("alternative", [True, True, True])):
            with self.subTest(variant=variant):
                work = committed(first.build(self.tmp / variant, variant))
                self.assertEqual(self.checks(work, ASSIGNMENT.entry["checks"]), expected)

    def delivery(self, name: str, builder, variant: str, spec: str) -> Path:
        work = builder.build(self.tmp / name, variant)
        (work / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        (work / "docs" / "shiploop" / "spec.md").write_text(spec)
        return committed(work)

    def test_the_follow_on_passes_its_regression_feature_and_retention_checks_only_when_it_builds_on_the_first_run(self):
        prior = self.delivery("prior", first, "reference", SPEC_BEFORE)
        checks = ASSIGNMENT.entry["checks"] + ESCALATION.entry["checks"] + ESCALATION.entry["retention"]
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                work = self.delivery(variant, second, variant, SPEC_AFTER)
                self.assertEqual(self.checks(work, checks, prior), [True] * len(checks))
        unchanged = self.delivery("unchanged", second, "base", SPEC_BEFORE)
        self.assertEqual(self.checks(unchanged, checks, prior),
                         [True, True, True, False, False, True, True, False, False],
                         "the first run's delivery as it was: regression passes, the new feature, the tests and the spec do not")
        lost = self.delivery("lost", second, "reference", SPEC_AFTER.replace("## R-2 The assignee filter\n", ""))
        (lost / "docs" / "operations.md").unlink()
        self.assertEqual(self.checks(lost, ESCALATION.entry["retention"], prior), [False, True, True, False],
                         "a file of the first run deleted and a requirement ID dropped")


@needs_lsof
class ThroughMainTest(e2e.CaseRunCase):
    """One fake-host run of the first case: the host starts in the committed base, the run is counted from it, and the quality
    phase grades the delivery fail-to-pass. The fake product adds hello.py and changes nothing of the base, so it is the base."""

    def setUp(self):
        super().setUp()
        e2e.isolate_git(self)

    def test_the_host_starts_in_the_base_and_the_delivery_is_graded_from_it(self):
        with mock.patch.object(run, "review_export", return_value="review export: fake"):
            code, result, _printed, out = self.case_main("ticket-assignment", "--case", "ticket-assignment")
        self.assertEqual(code, 1, "the unchanged base fails its new-feature checks")
        self.assertEqual(result["base"]["fixture"], "node-tickets")
        self.assertEqual(json.loads((out / "invocation.json").read_text())["base"], result["base"])
        self.assertEqual(result["committed"]["start_head"], result["base"]["start_head"])
        self.assertEqual([check["pass"] for check in result["checks"]], [False, True, False])
        acceptance = result["quality"]["acceptance"]
        self.assertTrue(acceptance["observed"], acceptance)
        self.assertEqual({row["id"] for row in acceptance["checks"] if not row["pass"]}, ASSIGNMENT.fail_to_pass)
        card = scorecard.score(out)
        self.assertEqual(card["accuracy"]["floor"], scorecard.FAIL)
        self.assertTrue(card["accuracy"]["acceptance_required"])


if __name__ == "__main__":
    unittest.main()
