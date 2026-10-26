#!/usr/bin/env python3
"""The brownfield case, `user-listing` on fixtures/node-base (SPEC "The promotion contract", build step 6; R10 of the final
verdict). No model is called.

Astra's done signal for build step 6: the base fails the new-feature checks, and the reference passes them and the pristine
regression suite. The owner's brief adds that at least one targeted broken variant fails and that the case's acceptance is
declared so the scorecard requires it. So these tests run, against every variant of
test/fixtures/quality/reference_user_listing.py (the base, the reference, an independent alternative and fourteen targeted
defects):

* the held-out acceptance (checks/user_listing_accept.py), through ``quality.acceptance`` as a run's quality phase calls it;
* the base's pristine tests and the delivery's own suite (checks/base_tests.py), as the case's checks run them;
* the case's checks in full for the base, the reference and the alternative, through ``run.run_checks``.

Then the base mechanism (brownfield.py and its use in run.py), and one fake-host run of the case through ``run.main``.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
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
import counters  # noqa: E402
import quality  # noqa: E402
import reference_user_listing as reference  # noqa: E402
import scorecard  # noqa: E402

CASE = json.loads(run.CASES.read_text())["user-listing"]
BLOCK = CASE["quality"]["acceptance"]
IDS = [item["id"] for item in BLOCK["checks"]]
FAIL_TO_PASS = {item["id"] for item in BLOCK["checks"] if item["grade"] == "fail-to-pass"}
PASS_TO_PASS = {item["id"] for item in BLOCK["checks"] if item["grade"] == "pass-to-pass"}
BASE_TESTS = run.HERE / "checks" / "base_tests.py"

# The exact set of held-out checks each variant fails: every check is shown to pass the reference and the alternative and to fail
# the defect it reads, and no defect goes unnoticed.
EXPECTED_FAILURES = {
    "base": FAIL_TO_PASS,
    "reference": set(),
    "alternative": set(),
    "floor-pages": {"page-envelope", "partial-last-page", "page-past-end", "page-defaults", "size-bounds"},
    "regex-filter": {"name-plain-text"},
    "case-sensitive": {"name-filter"},
    "parseint": {"bad-page-or-size"},
    "no-size-cap": {"bad-page-or-size"},
    "size-cap-off-by-one": {"size-bounds"},
    "default-size-20": {"page-defaults"},
    "always-envelope": {"list-unchanged", "name-filter", "name-plain-text"},
    "unknown-param-400": {"list-unchanged"},
    "id-route-shadowed": {"user-by-id-unchanged"},
    "past-end-404": {"page-past-end"},
    "total-ignores-filter": {"filter-then-page"},
    "list-users-envelope": set(),
    "paginate-options": set(),
}
# The variants the base's pristine tests reject: the two that break a base module and edit the base's tests to match, and the
# route defect, which the base's own server test also reads.
PRISTINE_FAILURES = {"id-route-shadowed", "list-users-envelope", "paginate-options"}

needs_node = unittest.skipUnless(shutil.which("node"), "the reference delivery is Node: this class needs node on PATH")
needs_lsof = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                 "the case's HTTP check runs through serve.py, which needs node and lsof")
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def committed(folder: Path) -> Path:
    """The folder as a delivery: a repository with its files committed, as a run leaves work/."""
    env = {**os.environ, **GIT_ENV}
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "d"]):
        subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True, env=env)
    return folder


def base_tests(delivery: Path, subcommand: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BASE_TESTS), subcommand, "node-base"], cwd=delivery, capture_output=True,
                          text=True, timeout=300, stdin=subprocess.DEVNULL)


class CaseDeclarationTest(unittest.TestCase):
    """The catalog entry: the base pin, the grades and the held-out files."""

    def test_the_declared_ids_are_exactly_the_modules_checks_and_each_has_a_grade_and_a_source(self):
        module = quality.load_checks("user_listing_accept", quality.HERE / "checks")
        self.assertEqual(IDS, list(module.CHECKS))
        for item in BLOCK["checks"]:
            with self.subTest(check=item["id"]):
                self.assertIn(item["grade"], ("fail-to-pass", "pass-to-pass"))
                self.assertTrue(item["source"].strip(), "each check quotes the sentence it reads")
        self.assertEqual(PASS_TO_PASS, {"list-unchanged", "user-by-id-unchanged"})
        self.assertEqual(IDS[:2], ["list-unchanged", "user-by-id-unchanged"], "the existing API is checked first")

    def test_the_pin_is_the_fixtures_digest(self):
        self.assertEqual(CASE["base"]["fixture"], "node-base")
        self.assertEqual(brownfield.digest(brownfield.FIXTURES / "node-base"), CASE["base"]["digest"],
                         "a change to fixtures/node-base is a change to this case: update the pin with it")

    def test_the_case_digest_moves_with_the_pin(self):
        moved = {**CASE, "base": {**CASE["base"], "digest": "000000000000"}}
        self.assertNotEqual(boundary.fingerprint(run.HERE, CASE)["case"], boundary.fingerprint(run.HERE, moved)["case"])

    def test_the_acceptance_module_and_the_reference_are_held_out(self):
        held = boundary.held_out_files(json.loads(run.CASES.read_text()))
        self.assertIn("test/shiploop_e2e/checks/user_listing_accept.py", held)
        self.assertIn("test/fixtures/quality/reference_user_listing.py", held)
        self.assertTrue({"user_listing_accept", "reference_user_listing"} <= set(quality.held_out_markers([BLOCK])))

    def test_the_style_is_left_out_of_breadth_by_name(self):
        breadth = json.loads(run.SUITES.read_text())["breadth"]
        self.assertEqual(CASE["style"], "brownfield")
        self.assertNotIn("brownfield", breadth["styles"])
        self.assertIn("user-listing", breadth["not_covered"]["brownfield"])


class RequirednessTest(unittest.TestCase):
    """The case declares acceptance, so the scorecard's accuracy floor requires it (SPEC: Requiredness belongs to the case)."""

    def floor(self, acceptance) -> tuple[str, dict]:
        unmeasured: dict = {}
        result = {"case": "user-listing", "pass": True, **({"quality": {"acceptance": acceptance}} if acceptance else {})}
        return scorecard.accuracy(result, unmeasured)["floor"], unmeasured

    def test_unobserved_acceptance_is_unobserved_never_a_pass(self):
        self.assertTrue(scorecard.requires_acceptance("user-listing"))
        for acceptance in (None, {"observed": False, "reason": "the product's server did not listen"}):
            with self.subTest(acceptance=acceptance):
                floor, unmeasured = self.floor(acceptance)
                self.assertEqual(floor, scorecard.UNOBSERVED)
                self.assertIn("accuracy.acceptance", unmeasured)

    def test_a_failed_held_out_check_fails_the_floor_and_all_passing_passes_it(self):
        rows = [{"id": ident, "pass": True} for ident in IDS]
        self.assertEqual(self.floor({"observed": True, "checks": rows})[0], scorecard.PASS)
        rows[5]["pass"] = False
        self.assertEqual(self.floor({"observed": True, "checks": rows})[0], scorecard.FAIL)


@needs_node
class CalibrationTest(unittest.TestCase):
    """Every variant built once, committed as a delivery, and graded by the held-out checks and the base's tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="brownfield-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.groups: set = set()
        cls.deliveries, cls.accepted, cls.pristine = {}, {}, {}
        for variant in reference.VARIANTS:
            delivery = committed(reference.build(cls.tmp / variant, variant))
            cls.deliveries[variant] = delivery
            cls.accepted[variant] = quality.acceptance(delivery, BLOCK, groups=cls.groups, stop=lambda: None,
                                                       logs=cls.tmp / "logs" / variant, ports=CASE["quality"]["refuse_ports"])
            cls.pristine[variant] = base_tests(delivery, "pristine")

    def failed(self, variant: str) -> set:
        block = self.accepted[variant]
        self.assertTrue(block["observed"], block)
        return {row["id"] for row in block["checks"] if not row["pass"]}

    def test_the_base_fails_every_fail_to_pass_check_and_passes_the_pass_to_pass_ones_and_its_pristine_tests(self):
        self.assertEqual(self.failed("base"), FAIL_TO_PASS)
        self.assertEqual(self.pristine["base"].returncode, 0, self.pristine["base"].stdout)
        self.assertIn("7 of 7 tests", self.pristine["base"].stdout)

    def test_the_reference_and_the_alternative_pass_every_check_and_the_pristine_tests(self):
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                self.assertEqual(self.failed(variant), set(), {r["id"]: r["note"] for r in self.accepted[variant]["checks"]})
                self.assertEqual(self.pristine[variant].returncode, 0, self.pristine[variant].stdout)

    def test_each_variant_fails_exactly_the_checks_its_defect_reads(self):
        self.assertEqual(set(EXPECTED_FAILURES), set(reference.VARIANTS))
        for variant, expected in EXPECTED_FAILURES.items():
            with self.subTest(variant=variant):
                self.assertEqual(self.failed(variant), expected, {r["id"]: r["note"] for r in self.accepted[variant]["checks"]
                                                                  if not r["pass"]})
                self.assertEqual(self.pristine[variant].returncode != 0, variant in PRISTINE_FAILURES, self.pristine[variant].stdout)
        self.assertEqual(set(), self.groups, "every server the checks started was ended")

    def test_every_check_is_failed_by_some_defect_and_every_defect_by_some_check(self):
        defects = [variant for variant in reference.DEFECTS]
        caught = set().union(*(EXPECTED_FAILURES[variant] for variant in defects))
        self.assertEqual(caught, set(IDS), "a check no defect fails could never fail")
        unseen = [variant for variant in defects if not EXPECTED_FAILURES[variant] and variant not in PRISTINE_FAILURES]
        self.assertEqual(unseen, [], "a defect neither the held-out checks nor the pristine tests fail would go unnoticed")

    def test_the_pristine_tests_run_apart_from_the_deliverys_own_edits_of_them(self):
        # The two defects edited the base's tests to match the module they broke: their own suite passes, the pristine one fails.
        for variant, test_file in (("list-users-envelope", "test/users.test.js"), ("paginate-options", "test/paginate.test.js")):
            with self.subTest(variant=variant):
                delivery = self.deliveries[variant]
                self.assertNotEqual((delivery / test_file).read_bytes(), (reference.BASE / test_file).read_bytes())
                own = base_tests(delivery, "suite")
                self.assertEqual(own.returncode, 0, own.stdout)
                self.assertIn("FAIL: the base's pristine tests against the delivered source", self.pristine[variant].stdout)

    def test_the_floor_defect_is_the_bases_own_paginate(self):
        # The base's latent defect: the request never names it, and only the partial-page checks find it.
        self.assertEqual((self.deliveries["floor-pages"] / "src/paginate.js").read_bytes(),
                         (reference.BASE / "src/paginate.js").read_bytes())

    def test_the_suite_check_asks_for_new_tests_beside_the_bases(self):
        self.assertIn("no more than the base's 7", base_tests(self.deliveries["base"], "suite").stdout)
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                own = base_tests(self.deliveries[variant], "suite")
                self.assertEqual(own.returncode, 0, own.stdout)

    def test_a_defect_that_no_longer_applies_fails_the_build(self):
        with mock.patch.dict(reference.DEFECTS, {"stale": [("src/server.js", "no such text", "x")]}), \
                mock.patch.object(reference, "VARIANTS", (*reference.VARIANTS, "stale")):
            with self.assertRaisesRegex(ValueError, "occurs 0 times"):
                reference.build(self.tmp / "stale", "stale")


@needs_lsof
class CaseChecksTest(unittest.TestCase):
    """The case's own checks, run as the harness runs them after a delivery (run.run_checks)."""

    def checks(self, variant: str) -> list[bool]:
        with tempfile.TemporaryDirectory() as tmp:
            delivery = committed(reference.build(Path(tmp) / variant, variant))
            with mock.patch.dict(os.environ, GIT_ENV):
                return [row["pass"] for row in run.run_checks(delivery, CASE["checks"], timeout=120)]

    def test_the_base_fails_the_suite_and_http_checks_and_passes_the_pristine_one(self):
        self.assertEqual(self.checks("base"), [False, True, False])

    def test_the_reference_and_the_alternative_pass_every_check(self):
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                self.assertEqual(self.checks(variant), [True, True, True])


class BaseStartTest(unittest.TestCase):
    """brownfield.start and its readers: the base is committed before the host starts and the run counts from it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        e2e.isolate_git(self)

    def test_the_base_is_copied_and_committed_and_the_record_names_its_commit(self):
        work = self.tmp / "work"
        work.mkdir()
        record = brownfield.start(work, CASE)
        head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(record, {"fixture": "node-base", "digest": CASE["base"]["digest"], "start_head": head, "files": 11})
        tracked = subprocess.run(["git", "-C", str(work), "ls-files"], capture_output=True, text=True).stdout.split()
        base = brownfield.FIXTURES / "node-base"
        self.assertEqual(tracked, [str(path.relative_to(base)) for path in brownfield.base_files(base)])
        self.assertEqual(subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True,
                                        text=True).stdout, "")

    def test_a_case_without_a_base_writes_nothing(self):
        work = self.tmp / "empty"
        work.mkdir()
        self.assertIsNone(brownfield.start(work, json.loads(run.CASES.read_text())["hello"]))
        self.assertEqual(list(work.iterdir()), [])

    def test_a_stale_pin_or_a_missing_fixture_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "not the 000000000000 the case pins"):
            brownfield.resolve({**CASE, "base": {**CASE["base"], "digest": "000000000000"}})
        with self.assertRaisesRegex(SystemExit, "is not a folder"):
            brownfield.resolve({**CASE, "base": {**CASE["base"], "fixture": "no-such-base"}})

    def test_the_runs_commits_and_committed_verdict_count_from_the_base_commit(self):
        out, work = self.tmp / "run", self.tmp / "run" / "work"
        work.mkdir(parents=True)
        record = brownfield.start(work, CASE)
        (out / "invocation.json").write_text(json.dumps({"follow_on": None, "seeded": None, "base": record}))
        self.assertEqual(counters._starting_point(out, work), (record["start_head"], None))
        untouched = {"head": record["start_head"], "head_files": 11, "uncommitted": []}
        self.assertFalse(run.committed_facts(untouched, record["start_head"])["pass"], "a run that changed nothing is not committed")


class BaseRefusalTest(e2e.HarnessCase):
    """A base case takes neither --continue-from nor --seed-at, and a stale pin is refused before any folder exists."""

    def test_continue_from_and_seed_at_are_refused_before_the_folder(self):
        for extra in (("--continue-from", str(self.tmp)), ("--seed-at", "step-plan")):
            with self.subTest(option=extra[0]):
                with self.assertRaisesRegex(SystemExit, "starts from its base, fixtures/node-base"):
                    self.invoke("claude", "done", "--case", "user-listing", *extra)
                self.assertFalse((self.tmp / "out-claude-done").exists())

    def test_a_stale_pin_is_refused_before_the_folder(self):
        cases = self.tmp / "cases.json"
        stale = {"user-listing": {**CASE, "base": {**CASE["base"], "digest": "000000000000"}}}
        cases.write_text(json.dumps(stale))
        with mock.patch.object(run, "CASES", cases), self.assertRaisesRegex(SystemExit, "update the pin"):
            self.invoke("claude", "done", "--case", "user-listing")
        self.assertFalse((self.tmp / "out-claude-done").exists())


@needs_lsof
class ThroughMainTest(e2e.CaseRunCase):
    """One fake-host run of the case: the host starts in the committed base, the run is counted from it, and the quality phase
    grades the delivery fail-to-pass. The fake product adds hello.py and changes nothing of the base, so it is the base."""

    def setUp(self):
        super().setUp()
        e2e.isolate_git(self)

    def test_the_host_starts_in_the_base_and_the_delivery_is_graded_from_it(self):
        with mock.patch.object(run, "review_export", return_value="review export: fake"):
            code, result, _printed, out = self.case_main("user-listing", "--case", "user-listing")
        self.assertEqual(code, 1, "the unchanged base fails its new-feature checks")
        invocation = json.loads((out / "invocation.json").read_text())
        self.assertEqual(invocation["base"], result["base"])
        self.assertEqual(result["base"]["fixture"], "node-base")
        self.assertIn("src", json.loads(self.log.read_text())["cwd_listing"], "the host's first sight is the base")
        self.assertEqual(result["committed"]["start_head"], result["base"]["start_head"])
        self.assertTrue(result["committed"]["pass"], "the fake product's commit moved HEAD past the base")
        self.assertEqual([check["pass"] for check in result["checks"]], [False, True, False])
        acceptance = result["quality"]["acceptance"]
        self.assertTrue(acceptance["observed"], acceptance)
        self.assertEqual({row["id"] for row in acceptance["checks"] if not row["pass"]}, FAIL_TO_PASS)
        card = scorecard.score(out)
        self.assertEqual(card["accuracy"]["floor"], scorecard.FAIL)
        self.assertTrue(card["accuracy"]["acceptance_required"])


if __name__ == "__main__":
    unittest.main()
