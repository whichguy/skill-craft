#!/usr/bin/env python3
"""Offline declaration, calibration and chain checks for user-listing -> user-teams -> user-summary -> user-team-casefold."""
from __future__ import annotations

import copy
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

import chains  # noqa: E402
import delta  # noqa: E402
import quality  # noqa: E402
import reference_user_listing as listing  # noqa: E402
import reference_user_teams as teams  # noqa: E402
import reference_user_summary as summaries  # noqa: E402
import reference_user_team_casefold as casefolds  # noqa: E402
import run  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
CASE_NAMES = ("user-teams", "user-summary", "user-team-casefold")
BUILDERS = {"user-teams": teams, "user-summary": summaries, "user-team-casefold": casefolds}
NEW_IDS = {
    "user-teams": {"team-filter-exact", "team-filter-case-sensitive",
                   "team-filters-combine-before-page", "team-include-opt-in"},
    "user-summary": {"summary-total-by-team", "summary-uses-user-filters", "summary-unpaginated-ignores",
                     "summary-no-matches", "summary-team-case-sensitive"},
    "user-team-casefold": {"team-filter-casefold-listing", "summary-team-casefold", "team-casefold-exact-match",
                           "team-response-spelling-preserved", "summary-group-spelling-preserved"},
}
NEW_IDS_ORDER = {
    "user-team-casefold": ["team-filter-casefold-listing", "summary-team-casefold", "team-casefold-exact-match",
                           "team-response-spelling-preserved", "summary-group-spelling-preserved"],
}
STRICT_IDS = {"team-filter-case-sensitive", "summary-team-case-sensitive"}
ORIGINAL_IDS = [row["id"] for row in CASES["user-listing"]["quality"]["acceptance"]["checks"]]
MODULES = {
    "user-teams": "user_teams_accept.py",
    "user-summary": "user_summary_accept.py",
    "user-team-casefold": "user_team_casefold_accept.py",
}

# Frozen before calibration. Each pair is (failed inline check indexes, failed acceptance IDs).
EXPECTED = {
    "user-teams": {
        "base": ({1, 2}, {"team-filter-exact", "team-filter-case-sensitive", "team-filters-combine-before-page", "team-include-opt-in"}),
        "reference": (set(), set()),
        "alternative": (set(), set()),
        "team-after-pagination": ({0}, {"team-filters-combine-before-page"}),
        "team-substring": ({0}, {"team-filter-exact"}),
        "team-casefold-early": ({0}, {"team-filter-case-sensitive"}),
        "team-leaks-default": (
            {0, 2},
            {"list-unchanged", "user-by-id-unchanged", "name-filter", "page-envelope",
             "partial-last-page", "page-defaults", "filter-then-page", "size-bounds",
             "team-filter-exact", "team-filters-combine-before-page", "team-include-opt-in"},
        ),
    },
    "user-summary": {
        "base": ({1}, {"summary-total-by-team", "summary-uses-user-filters", "summary-unpaginated-ignores",
                       "summary-no-matches", "summary-team-case-sensitive"}),
        "reference": (set(), set()),
        "alternative": (set(), set()),
        "summary-drops-filters": ({0, 1}, {"summary-uses-user-filters", "summary-no-matches", "summary-team-case-sensitive"}),
        "summary-counts-page": ({0, 1}, {"summary-unpaginated-ignores"}),
        "summary-validates-page": ({0, 1}, {"summary-unpaginated-ignores"}),
        "summary-shadowed-route": (
            {0, 1},
            {"summary-total-by-team", "summary-uses-user-filters", "summary-unpaginated-ignores",
             "summary-no-matches", "summary-team-case-sensitive"},
        ),
        "summary-empty-team-all": ({0}, {"summary-no-matches"}),
    },
    "user-team-casefold": {
        "base": ({1}, {"team-filter-casefold-listing", "summary-team-casefold",
                       "team-response-spelling-preserved", "summary-group-spelling-preserved"}),
        "reference": (set(), set()),
        "alternative": (set(), set()),
        "listing-only-casefold": (
            {0, 1}, {"summary-team-casefold", "summary-group-spelling-preserved"},
        ),
        "team-substring": (
            {0, 1}, {"team-filter-exact", "summary-no-matches", "team-casefold-exact-match"},
        ),
        "returned-team-lowercase": (
            {0, 1}, {"team-include-opt-in", "team-response-spelling-preserved"},
        ),
        "group-key-lowercase": (
            {0, 1},
            {"summary-total-by-team", "summary-uses-user-filters", "summary-unpaginated-ignores",
             "summary-team-casefold", "summary-group-spelling-preserved"},
        ),
    },
}

SPECS = {
    "user-listing": (
        "# Spec\n\n## Requirements\n\n### R-1 User listing\n"
        "GET /users filters and pages users. Any other query parameter is ignored. GET /users/:id is unchanged.\n"
    ),
    "user-teams": (
        "# Spec\n\n## Requirements\n\n### R-1 User listing\n"
        "GET /users recognizes include=team on list and detail routes; other include values are ignored.\n\n"
        "### R-2 Team filters\nAda and Grace are in Engineering; Alan is in Support. Team matching is exact and case-sensitive.\n"
    ),
    "user-summary": (
        "# Spec\n\n## Requirements\n\n### R-1 User listing\n"
        "GET /users recognizes include=team on list and detail routes; other include values are ignored.\n\n"
        "### R-2 Team filters\nAda and Grace are in Engineering; Alan is in Support. Team matching is exact and case-sensitive.\n\n"
        "### R-3 User summary\nGET /users/summary counts all users using the name and team filters.\n"
    ),
    "user-team-casefold": (
        "# Spec\n\n## Requirements\n\n### R-1 User listing\n"
        "GET /users recognizes include=team on list and detail routes; other include values are ignored.\n\n"
        "### R-2 Team filters\nAda and Grace are in Engineering; Alan is in Support. Team matching ignores case and remains exact.\n\n"
        "### R-3 User summary\nGET /users/summary counts all users using the name and team filters.\n"
    ),
}
ARCHITECTURES = {
    "user-listing": "# Architecture\n\n## Decisions\n\n### AD-1 User store\nThe user store is in memory.\n",
    "user-teams": "# Architecture\n\n## Decisions\n\n### AD-1 User store\nThe in-memory records hold team values.\n",
    "user-summary": (
        "# Architecture\n\n## Decisions\n\n### AD-1 User store\nThe in-memory records hold team values.\n\n"
        "### AD-2 Summary route\nSummary uses the same selector as listing.\n"
    ),
    "user-team-casefold": (
        "# Architecture\n\n## Decisions\n\n### AD-1 User store\nThe in-memory records hold team values.\n\n"
        "### AD-2 Summary route\nSummary uses the same selector as listing.\n\n"
        "### AD-3 Team comparison\nTeam names compare without regard to letter case.\n"
    ),
}
ENVIRONMENT = "# Environment\n\n## Runtime\nNode.js and the standard library only.\n"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def committed(folder: Path, spec: str | None = None, architecture: str | None = None,
              environment: str = ENVIRONMENT) -> Path:
    folder = Path(folder)
    if spec is not None or architecture is not None or environment is not None:
        docs = folder / "docs" / "shiploop"
        docs.mkdir(parents=True, exist_ok=True)
        if spec is not None:
            (docs / "spec.md").write_text(spec)
        if environment is not None:
            (docs / "environment.md").write_text(environment)
        if architecture is not None:
            (docs / "architecture.md").write_text(architecture)
    with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}):
        for args in (["init", "-q"], ["add", "-A"],
                     ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "delivery"]):
            subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)
    return folder


def hidden(work: Path, logs: Path, case: str, only: set[str] | None = None) -> dict:
    block = copy.deepcopy(run.case_quality(case))
    if only is not None:
        block["acceptance"]["checks"] = [row for row in block["acceptance"]["checks"] if row["id"] in only]
    return quality.acceptance(work, block["acceptance"], groups=set(), stop=lambda: None,
                              logs=logs, ports=block["refuse_ports"])


def predecessor(case: str, folder: Path, lineage: str = "reference") -> Path:
    if case == "user-teams":
        return listing.build(folder, lineage)
    if case == "user-summary":
        return teams.build(folder, lineage)
    if case == "user-team-casefold":
        return summaries.build(folder, lineage)
    raise AssertionError(case)


def final_docs(case: str) -> tuple[str, str]:
    return SPECS[case], ARCHITECTURES[case]


def prior_docs(case: str) -> tuple[str, str]:
    prior = {"user-teams": "user-listing", "user-summary": "user-teams",
             "user-team-casefold": "user-summary"}[case]
    return SPECS[prior], ARCHITECTURES[prior]


def commands_for(case: str) -> list[str]:
    args = type("Args", (), {"prompt": None, "case": case, "check": None})
    _, prompt, checks, _ = run.load_case(args)
    if prompt != CASES[case]["prompt"]:
        raise AssertionError(f"{case}: load_case returned a different prompt")
    return checks


class Isolated(unittest.TestCase):
    """Real Git, Node and HTTP checks in disposable delivery folders."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        patched = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        patched.start()
        self.addCleanup(patched.stop)


class CaseDeclarationTest(unittest.TestCase):
    def test_chain_order_and_each_link_has_its_own_acceptance(self) -> None:
        self.assertEqual(chains.of(CASES, CASE_NAMES[-1]),
                         ["user-listing", "user-teams", "user-summary", "user-team-casefold"])
        for index, name in enumerate(CASE_NAMES):
            case = CASES[name]
            previous = "user-listing" if index == 0 else CASE_NAMES[index - 1]
            self.assertEqual(case["follows"], previous)
            self.assertEqual(case["style"], "brownfield")
            self.assertIn("acceptance", run.case_quality(name))
            self.assertTrue(scorecard.requires_acceptance(name))

    def test_full_acceptance_id_sets_keep_original_checks_and_retire_only_the_two_strict_checks_at_k3(self) -> None:
        k2 = [row["id"] for row in CASES["user-teams"]["quality"]["acceptance"]["checks"]]
        k1 = [row["id"] for row in CASES["user-summary"]["quality"]["acceptance"]["checks"]]
        k3 = [row["id"] for row in CASES["user-team-casefold"]["quality"]["acceptance"]["checks"]]
        self.assertEqual(k2[:len(ORIGINAL_IDS)], ORIGINAL_IDS)
        self.assertEqual(k1[:len(k2)], k2)
        self.assertEqual(k3, [ident for ident in k1 if ident not in STRICT_IDS] + NEW_IDS_ORDER["user-team-casefold"])
        self.assertEqual(set(k1) - set(k3), STRICT_IDS)
        self.assertTrue(set(ORIGINAL_IDS).issubset(k3))
        self.assertIn("team-filter-case-sensitive", k2)
        self.assertIn("summary-team-case-sensitive", k1)

    def test_declared_acceptance_modules_have_exactly_the_declared_check_ids(self) -> None:
        for case, filename in MODULES.items():
            module = load_module(ROOT / "test/shiploop_e2e/checks" / filename, f"{case}_checks_test")
            declared = [row["id"] for row in CASES[case]["quality"]["acceptance"]["checks"]]
            self.assertEqual(list(module.CHECKS), declared, case)

    def test_requests_have_only_the_approved_user_listing_semantics(self) -> None:
        q = chr(96)
        k2 = CASES["user-teams"]["prompt"]
        self.assertIn("Engineering", k2)
        self.assertIn("Support", k2)
        for phrase in ("exact, case-sensitive", "empty or unknown", "before pagination",
                       "include=team", "including paged items", "every user returned by GET /users or GET /users/:id"):
            self.assertIn(phrase, k2)
        k1 = CASES["user-summary"]["prompt"]
        self.assertIn("Use the same " + q + "name" + q + " and " + q + "team" + q + " filters GET /users applies.", k1)
        self.assertIn("do not validate them for this route", k1)
        self.assertIn("Other response keys may be present", k1)
        k3 = CASES["user-team-casefold"]["prompt"]
        self.assertIn("both GET /users and GET /users/summary", k3)
        self.assertIn("exact team name after ignoring case", k3)
        self.assertIn("stored and returned spelling stays unchanged", k3)
        self.assertIn("replaces the rule that team matching is case-sensitive", k3)
        self.assertIn("tests that state it", k3)

    def test_only_k2_and_k1_have_isolated_strict_case_acceptance_checks(self) -> None:
        k2 = {row["id"] for row in CASES["user-teams"]["quality"]["acceptance"]["checks"]}
        k1 = {row["id"] for row in CASES["user-summary"]["quality"]["acceptance"]["checks"]}
        k3 = {row["id"] for row in CASES["user-team-casefold"]["quality"]["acceptance"]["checks"]}
        self.assertIn("team-filter-case-sensitive", k2)
        self.assertIn("summary-team-case-sensitive", k1)
        self.assertTrue(STRICT_IDS.isdisjoint(k3))
        self.assertNotIn("team=engineering", " ".join(CASES["user-teams"]["checks"]))
        self.assertNotIn("team=engineering", " ".join(CASES["user-summary"]["checks"]))
        self.assertIn("team=engineering", " ".join(CASES["user-team-casefold"]["checks"]))

    def test_delta_patterns_are_limited_to_the_prior_clauses_the_requests_change(self) -> None:
        k2 = CASES["user-teams"]["delta"]
        self.assertEqual(k2["may_change"]["spec.md"],
                         ["any other query parameter is ignored", "GET /users/:id is unchanged"])
        self.assertIn("any other query parameter is ignored", k2["source"])
        self.assertIn("GET /users/:id is unchanged", k2["source"])
        k3 = CASES["user-team-casefold"]["delta"]
        self.assertEqual(k3["may_change"], {"spec.md": ["team"], "architecture.md": ["team"]})

    def test_k1_inherited_filter_references_name_the_source_check_clauses(self) -> None:
        q = chr(96)
        sources = {row["id"]: row["source"] for row in CASES["user-summary"]["quality"]["acceptance"]["checks"]}
        self.assertIn("user-teams' " + q + "team-filter-exact" + q, sources["summary-uses-user-filters"])
        self.assertIn(q + "team-filters-combine-before-page" + q,
                      sources["summary-uses-user-filters"])
        self.assertIn("user-teams' " + q + "team-filter-case-sensitive" + q,
                      sources["summary-team-case-sensitive"])
        reference = "Use the same " + q + "name" + q + " and " + q + "team" + q + " filters GET /users applies."
        self.assertIn(reference, CASES["user-summary"]["quality"]["acceptance"]["source"])

    def test_links_stay_out_of_suites_and_the_breadth_note_is_descriptive(self) -> None:
        suites = json.loads((ROOT / "test/shiploop_e2e/suites.json").read_text())
        for name, suite in suites.items():
            if isinstance(suite, dict):
                for case in CASE_NAMES:
                    self.assertNotIn(case, suite.get("cases", []), name)
        note = suites["breadth"]["not_covered"]["brownfield"]
        for case in ("user-listing", *CASE_NAMES):
            self.assertIn(case, note)

    def test_retention_checks_do_not_force_ids_words_or_growth_and_allow_zero_prior_decisions(self) -> None:
        for case in CASE_NAMES:
            commands = CASES[case]["retention"]
            self.assertEqual(len(commands), 4)
            joined = " ".join(commands)
            self.assertNotIn("-gt 0", joined)
            self.assertNotIn("grep -qi", joined)
            self.assertNotIn("tests before", joined)
            self.assertIn("requires all three living files", CASES[case]["retention_source"])
            self.assertIn("delta ledger is a locator", CASES[case]["retention_source"])
        self.assertIn("zero prior AD IDs is valid", CASES["user-teams"]["retention_source"])

    def test_every_link_loads_its_own_checks_after_the_prior_inline_checks(self) -> None:
        for case in CASE_NAMES:
            command_list = commands_for(case)
            ancestry = chains.of(CASES, case)
            expected = chains.regression(CASES, case)
            expected += CASES[case]["checks"] + CASES[case]["retention"]
            self.assertEqual(command_list, expected, case)


needs_servers = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                    "offline calibration starts the case's node HTTP server through serve.py")


@needs_servers
class CalibrationTest(Isolated):
    """The complete expected failure sets for two correct lineages and each frozen defect."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.actual = {}
        cls.reasons = {}
        with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                          "PYTHONDONTWRITEBYTECODE": "1"}):
            for case in CASE_NAMES:
                for variant in BUILDERS[case].VARIANTS:
                    work = BUILDERS[case].build(cls.root / case / variant, variant)
                    rows = run.run_checks(work, CASES[case]["checks"], timeout=240)
                    own = {index for index, result in enumerate(rows) if not result["pass"]}
                    note = {f"own[{index}]": f"exit {result['returncode']}: {result['output'][:400]}"
                            for index, result in enumerate(rows) if not result["pass"]}
                    block = hidden(work, cls.root / "logs" / case / variant, case)
                    if not block.get("observed"):
                        raise AssertionError(f"{case}/{variant}: acceptance unobserved: {block}")
                    hidden_failed = {row["id"] for row in block["checks"] if not row["pass"]}
                    note["hidden"] = json.dumps([row for row in block["checks"] if not row["pass"]])[:1600]
                    cls.actual[(case, variant)] = (own, hidden_failed)
                    cls.reasons[(case, variant)] = note

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_every_variant_is_listed_in_the_frozen_matrix(self) -> None:
        for case in CASE_NAMES:
            self.assertEqual(set(BUILDERS[case].VARIANTS), set(EXPECTED[case]), case)
            self.assertEqual({variant for found_case, variant in self.actual if found_case == case},
                             set(EXPECTED[case]), case)

    def test_references_and_alternatives_pass_their_complete_acceptance(self) -> None:
        for case in CASE_NAMES:
            for variant in ("reference", "alternative"):
                with self.subTest(case=case, variant=variant):
                    self.assertEqual(self.actual[(case, variant)], (set(), set()),
                                     self.reasons[(case, variant)])

    def test_each_defect_has_its_frozen_complete_failure_set(self) -> None:
        for case in CASE_NAMES:
            for variant, expected in EXPECTED[case].items():
                with self.subTest(case=case, variant=variant):
                    self.assertEqual(self.actual[(case, variant)], expected,
                                     self.reasons[(case, variant)])

    def test_the_frozen_defects_cover_every_new_acceptance_check(self) -> None:
        for case in CASE_NAMES:
            defects = [variant for variant in EXPECTED[case]
                       if variant not in ("reference", "alternative")]
            seen = set().union(*(self.actual[(case, variant)][1] for variant in defects))
            self.assertEqual(seen & NEW_IDS[case], NEW_IDS[case], case)


@needs_servers
class ChainRunTest(Isolated):
    """Regression and retention checks across the full Chain B, including both reference lineages."""

    def _checks(self, work: Path, prior: Path, commands: list[str]) -> list[bool]:
        env = {"PRIOR_WORK": str(prior)}
        rows = run.run_checks(work, commands, timeout=300, env=env)
        failed = [index for index, row in enumerate(rows) if not row["pass"]]
        if failed:
            retries = run.run_checks(work, [commands[index] for index in failed], timeout=300, env=env)
            for index, result in zip(failed, retries):
                rows[index] = result
        return [row["pass"] for row in rows]

    def test_k3_reference_and_alternative_pass_every_inherited_inline_check_and_retention(self) -> None:
        args = type("Args", (), {"prompt": None, "case": "user-team-casefold", "check": None})
        _, _, commands, _ = run.load_case(args)
        expected_regression = []
        for ancestor in chains.of(CASES, "user-team-casefold")[:-1]:
            expected_regression.extend(check for check in CASES[ancestor]["checks"]
                                       if check not in expected_regression)
        self.assertEqual(chains.regression(CASES, "user-team-casefold"), expected_regression)
        for lineage in ("reference", "alternative"):
            with self.subTest(lineage=lineage):
                prior_folder = self.tmp / f"prior-{lineage}"
                prior_spec, prior_arch = prior_docs("user-team-casefold")
                prior = committed(predecessor("user-team-casefold", prior_folder, lineage), prior_spec, prior_arch)
                product = BUILDERS["user-team-casefold"].build(self.tmp / f"casefold-{lineage}", lineage)
                spec, architecture = final_docs("user-team-casefold")
                work = committed(product, spec, architecture)
                self.assertEqual(self._checks(work, prior, commands), [True] * len(commands))

    def test_both_retired_strict_checks_pass_k1_and_fail_the_correct_k3_reference(self) -> None:
        prior_spec, prior_arch = prior_docs("user-team-casefold")
        k1 = committed(summaries.build(self.tmp / "k1-reference", "reference"),
                       prior_spec, prior_arch)
        k3 = committed(casefolds.build(self.tmp / "k3-reference", "reference"),
                       *final_docs("user-team-casefold"))
        old = copy.deepcopy(run.case_quality("user-summary"))
        old["acceptance"]["checks"] = [row for row in old["acceptance"]["checks"] if row["id"] in STRICT_IDS]
        k1_result = quality.acceptance(k1, old["acceptance"], groups=set(), stop=lambda: None,
                                       logs=self.tmp / "logs" / "old-k1", ports=old["refuse_ports"])
        k3_result = quality.acceptance(k3, old["acceptance"], groups=set(), stop=lambda: None,
                                       logs=self.tmp / "logs" / "old-k3", ports=old["refuse_ports"])
        self.assertTrue(k1_result["observed"], k1_result)
        self.assertTrue(k3_result["observed"], k3_result)
        self.assertEqual({row["id"] for row in k1_result["checks"] if not row["pass"]}, set())
        self.assertEqual({row["id"] for row in k3_result["checks"] if row["pass"] is False}, STRICT_IDS)

    def test_retention_accepts_in_place_and_new_id_retirement_but_does_not_claim_to_detect_stale_active_text(self) -> None:
        prior_spec = (
            "# Spec\n\n## Requirements\n\n### R-1 User listing\nThe list contract stays.\n\n"
            "### R-2 Team matching\nTeam matching is case-sensitive.\n"
        )
        prior_arch = (
            "# Architecture\n\n## Decisions\n\n### AD-1 Store\nThe store is in memory.\n\n"
            "### AD-2 Team comparison\nTeam matching is case-sensitive.\n"
        )
        prior = committed(listing.build(self.tmp / "retention-prior", "reference"), prior_spec, prior_arch)
        in_place_spec = prior_spec.replace("Team matching is case-sensitive.", "Team matching ignores case, still exactly.")
        in_place_arch = prior_arch.replace("Team matching is case-sensitive.", "Team matching ignores case.")
        retired_spec = (
            "# Spec\n\n## Requirements\n\n### R-1 User listing\nThe list contract stays.\n\n"
            "### R-4 Team matching\nTeam matching ignores case, still exactly.\n\n## Retired\n"
            "### R-2 Team matching\nReplaced by R-4.\n"
        )
        retired_arch = (
            "# Architecture\n\n## Decisions\n\n### AD-1 Store\nThe store is in memory.\n\n"
            "### AD-4 Team comparison\nTeam matching ignores case.\n\n## Superseded\n"
            "### AD-2 Team comparison\nReplaced by AD-4.\n"
        )
        scenarios = {
            "in-place": (in_place_spec, in_place_arch),
            "new-id-retired": (retired_spec, retired_arch),
            "stale-active": (prior_spec, prior_arch),
        }
        for name, (spec, architecture) in scenarios.items():
            with self.subTest(name=name):
                work = committed(casefolds.build(self.tmp / name, "reference"), spec, architecture)
                rows = run.run_checks(work, CASES["user-team-casefold"]["retention"],
                                      timeout=180, env={"PRIOR_WORK": str(prior)})
                self.assertEqual([row["pass"] for row in rows], [True] * len(rows))
        in_place = delta.ids_block(prior_spec, in_place_spec, "R", ["team"])
        retired = delta.ids_block(prior_spec, retired_spec, "R", ["team"])
        stale = delta.ids_block(prior_spec, prior_spec, "R", ["team"])
        self.assertEqual(in_place["expected_touched"], ["R-2"])
        self.assertEqual(retired["retired_by_run"], ["R-2"])
        self.assertEqual(stale["expected_untouched"], ["R-2"])

    def test_zero_prior_decisions_is_a_valid_retention_input(self) -> None:
        prior_arch = "# Architecture\n\n## Decisions\nNo decisions were written by the earlier run.\n"
        prior = committed(listing.build(self.tmp / "zero-ad-prior", "reference"),
                          SPECS["user-listing"], prior_arch)
        work = committed(teams.build(self.tmp / "zero-ad-current", "reference"),
                         SPECS["user-teams"], prior_arch)
        rows = run.run_checks(work, CASES["user-teams"]["retention"],
                              timeout=180, env={"PRIOR_WORK": str(prior)})
        self.assertEqual([row["pass"] for row in rows], [True] * len(rows))

    def test_a_missing_prior_nonliving_file_fails_the_file_retention_check(self) -> None:
        prior = committed(listing.build(self.tmp / "prior-file", "reference"),
                          SPECS["user-listing"], ARCHITECTURES["user-listing"])
        product = teams.build(self.tmp / "missing-readme", "reference")
        (product / "README.md").unlink()
        work = committed(product, SPECS["user-teams"], ARCHITECTURES["user-teams"])
        rows = run.run_checks(work, CASES["user-teams"]["retention"], timeout=180,
                              env={"PRIOR_WORK": str(prior)})
        self.assertEqual([row["pass"] for row in rows], [False, True, True, True])
        self.assertIn("missing prior file README.md", rows[0]["output"])


if __name__ == "__main__":
    unittest.main()
