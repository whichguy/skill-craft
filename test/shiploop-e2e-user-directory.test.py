#!/usr/bin/env python3
"""Chain B of the multipass study: `user-listing` and the three links that follow it (SPEC, "Follow-on chains and the delta ledger"). No model is called.

The chain is on fixtures/node-base, 174 lines against the ticket service's 3,600, in another domain (a user directory):

* ``user-listing`` (a run on the base; pass 1, built and calibrated earlier): filtering and pagination of GET /users.
* ``user-roles`` (kind K2, a cross-cutting field): every user has a role, shown everywhere a user is, with a ``role`` filter that combines with
  ``name``, and a 400 for a role that is none of the three.
* ``user-team-listing`` (kind K1, an additive link that must reuse an inherited rule): ``GET /teams`` lists teams "the way ``GET /users`` lists users", errors
  included. Five of its seven checks read rules the first request set and the first pass wrote down; the base's own ``paginate`` floors a partly
  filled last page, so a run that works the rules out again, or reuses the helper unmended, fails them.
* ``user-page-size`` (kind K3, a link that CHANGES an earlier rule): the default page size is the PAGE_SIZE setting (25) and the largest size 50, for
  both listings, replacing "10" and "up to 100". The third pass's and the first request's checks of the old values fail a correct delivery by design,
  so the case declares an acceptance of its own (``ModifiedRuleTest``), as `ticket-sla` does.

What the suite pins, per link: the chain and the checks the harness runs; the case's own checks and its new hidden checks against the base, the
reference, an independently written alternative and each defect (each defect fails exactly the checks that read what it breaks, and every check is
failed by some defect); the earlier passes' hidden checks, which the reference keeps passing; and the five retention checks on BOTH routes a spec check
has, a requirement added and a requirement edited in place (the first live run of the fourth ticket link failed a correct delivery because the check
was only ever shown the first route, journal Round 3). The living files of the retention tests are REAL: the saved pass-1 specs and architectures
the words and ledger patterns were written from (docs/experiments/multipass-chain-b-20261101/real-priors/), not text written from the request.
"""

from __future__ import annotations

import copy
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
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import chains  # noqa: E402
import delta  # noqa: E402
import quality  # noqa: E402
import reference_user_listing as listing  # noqa: E402
import reference_user_page_size as sized  # noqa: E402
import reference_user_roles as roles  # noqa: E402
import reference_user_team_listing as teams  # noqa: E402
import run  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
PRIORS = ROOT / "docs" / "experiments" / "multipass-chain-b-20261101" / "real-priors"
REAL = sorted(path.name for path in PRIORS.iterdir() if path.is_dir())
CHAIN = ["user-listing", "user-roles", "user-team-listing", "user-page-size"]

# The deliveries are Node and the cases' HTTP checks run through serve.py, which finds the listener with lsof: where either is missing the classes
# that start servers are skipped, as the pair's calibration (shiploop-e2e-brownfield-tickets.test.py) skips them.
needs_servers = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                    "the cases' HTTP checks run through serve.py, which needs node and lsof")

NEW_HIDDEN = {
    "user-roles": ("role-shown", "role-filter", "filters-combine", "role-then-page", "bad-role"),
    "user-team-listing": ("teams-listing", "team-by-id", "teams-name-filter", "teams-pages", "teams-page-defaults", "teams-size-bounds", "teams-bad-page-or-size"),
    "user-page-size": ("page-size-default", "page-size-setting", "page-size-largest"),
}
REPLACED = ("page-defaults", "size-bounds", "teams-page-defaults", "teams-size-bounds")  # the checks user-page-size's request replaces
MODULE = {"user-roles": roles, "user-team-listing": teams, "user-page-size": sized}
BEFORE = {"user-roles": listing, "user-team-listing": roles, "user-page-size": teams}  # the module whose reference stands in for the pass before
ALL = {name: set(ids) for name, ids in NEW_HIDDEN.items()}

# The own check and the new hidden checks each variant fails, and (last) the inherited hidden checks it fails: (own, new, inherited).
EXPECTED = {
    "user-roles": {
        "base": ({0, 1, 2}, ALL["user-roles"], set()),
        "reference": (set(), set(), set()),
        "alternative": (set(), set(), set()),
        "role-missing-in-listing": ({0}, {"role-shown"}, set()),
        "role-missing-by-id": ({0}, {"role-shown"}, set()),
        "role-filter-ignored": ({0, 1}, {"role-filter", "filters-combine", "role-then-page"}, set()),
        "role-replaces-name": ({1}, {"filters-combine", "role-then-page"}, set()),
        "role-after-paging": ({1}, {"role-then-page"}, set()),
        "bad-role-keeps-nobody": ({2}, {"bad-role"}, set()),
        "empty-role-keeps-all": ({2}, {"bad-role"}, set()),
        "bad-role-not-json": ({2}, {"bad-role"}, set()),
        "unknown-param-400": (set(), {"role-filter"}, {"list-unchanged"}),
        "role-answers-a-page": ({0, 1}, {"role-filter", "filters-combine"}, set()),
    },
    "user-team-listing": {
        "base": ({0, 1, 2}, ALL["user-team-listing"], set()),
        "reference": (set(), set(), set()),
        "alternative": (set(), set(), set()),
        "hand-rolled": (set(), set(), set()),
        "teams-regex-filter": ({1}, {"teams-name-filter"}, set()),
        "teams-case-sensitive": ({1, 2}, {"teams-name-filter", "teams-pages"}, set()),
        "teams-floor-pages": ({2}, {"teams-pages", "teams-page-defaults", "teams-size-bounds"}, set()),
        "teams-default-size-20": (set(), {"teams-page-defaults"}, set()),
        "teams-size-cap-99": (set(), {"teams-size-bounds"}, set()),
        "teams-no-size-cap": ({2}, {"teams-bad-page-or-size"}, set()),
        "teams-bad-size-defaulted": ({2}, {"teams-bad-page-or-size"}, set()),
        "teams-past-end-404": ({2}, {"teams-pages"}, set()),
        "teams-unknown-param-400": ({1}, {"teams-listing"}, set()),
        "teams-members-missing": ({0}, {"teams-listing"}, set()),
        "team-404-text": ({0}, {"team-by-id"}, set()),
        "role-filter-lost": (set(), set(), {"role-filter", "filters-combine", "role-then-page"}),
    },
    "user-page-size": {
        "base": ({0, 1, 2}, ALL["user-page-size"], set()),
        "reference": (set(), set(), set()),
        "alternative": (set(), set(), set()),
        "default-still-10": ({0, 1}, {"page-size-default", "page-size-setting"}, set()),
        "setting-ignored": ({1}, {"page-size-setting"}, set()),
        "largest-still-100": ({2}, {"page-size-largest"}, set()),
        "largest-49": ({2}, {"page-size-largest"}, set()),
        "largest-51": ({2}, {"page-size-largest"}, set()),
        "teams-keep-old-rules": ({0, 1, 2}, ALL["user-page-size"], set()),
        "setting-cuts-the-array": ({1}, {"page-size-setting"}, set()),
        "setting-beats-given-size": ({1}, {"page-size-setting"}, set()),
        "old-tests-left-standing": (set(), set(), set()),  # only the delivery's own suite sees it (ChainRunTest)
    },
}
OWN_NAMES = {"user-roles": ("roles", "combine", "badrole"),
             "user-team-listing": ("teams", "teamsfilter", "teamspage"),
             "user-page-size": ("sizedefault", "sizesetting", "sizelargest")}


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


def real(name: str, living: str) -> str:
    return (PRIORS / name / living).read_text()


def add_requirement(spec: str, ident: str, title: str, text: str) -> str:
    """A requirement entry added as a live one: before `## Retired` when the file has that section, else at the end."""
    entry = f"### {ident}: {title}\n{text}\n\n"
    at = spec.find("\n## Retired")
    return spec + "\n" + entry if at < 0 else spec[:at + 1] + entry + spec[at + 1:]


def add_decision(architecture: str, ident: str, title: str, text: str) -> str:
    entry = f"### {ident}: {title}\n{text}\n\n"
    at = architecture.find("\n## Real-boundary")
    return architecture + "\n" + entry if at < 0 else architecture[:at + 1] + entry + architecture[at + 1:]


def retire(text: str, ident: str, heading: str, note: str) -> str:
    """The entry `ident` moved under the file's `heading` section (made at the end when absent), its ID kept: what a run does to a rule it replaces."""
    text = re.sub(rf"^### {re.escape(ident)}\b.*?(?=^#{{2,3}} |\Z)", "", text, count=1, flags=re.S | re.M)
    entry = f"### {ident}: Replaced\n{note}\n\n"
    found = re.search(rf"^## {heading}\b.*$", text, re.M)
    if found is None:
        return text.rstrip("\n") + f"\n\n## {heading}\n\n{entry}"
    return text[:found.end()] + "\n\n" + entry + text[found.end():].lstrip("\n")


# The living files of the pass before each link: the REAL pass-1 files, and for the later links the earlier links' entries added as a real run
# would add them (a requirement and a decision each). Written once the words below were found absent from every real pass-1 spec.
PRIOR = "hooks-after"
SPEC_1, ARCH_1 = real(PRIOR, "spec.md"), real(PRIOR, "architecture.md")
SPEC_2 = add_requirement(SPEC_1, "R-5", "Roles", "Every user has a role: admin, member or viewer. GET /users filters by role beside name; a bad role answers 400.")
ARCH_2 = add_decision(ARCH_1, "AD-3", "Roles live in the user store", "ROLES is named once in src/users.js and checked at the listing's door.")
SPEC_3 = add_requirement(SPEC_2, "R-6", "Teams", "GET /teams and GET /teams/:id answer five teams; the listing filters and pages as GET /users does (R-1 to R-3).")
ARCH_3 = add_decision(ARCH_2, "AD-4", "One listing answer for every listing", "The array or the page is answered by one function that the users and the teams share.")
PRIORS_OF = {"user-roles": (SPEC_1, ARCH_1), "user-team-listing": (SPEC_2, ARCH_2), "user-page-size": (SPEC_3, ARCH_3)}
WORD = {"user-roles": "viewer", "user-team-listing": "team", "user-page-size": "PAGE_SIZE"}
TEST_WORD = {"user-roles": "role", "user-team-listing": "team", "user-page-size": "page_size"}
NEW_ENTRY = {"user-roles": ("R-5", "Roles", "Every user has a role: admin, member or viewer."),
             "user-team-listing": ("R-6", "Teams", "GET /teams lists the five teams the way GET /users lists users."),
             "user-page-size": ("R-7", "Page size", "The default page size is the PAGE_SIZE setting, 25; the largest size is 50.")}
NEXT_ID = {"user-roles": "R-5", "user-team-listing": "R-6", "user-page-size": "R-7"}


def delivered(link: str, route: str) -> tuple[str, str]:
    """A delivery's living files for a link on a route: ``new-id`` adds a requirement; ``in-place`` edits R-2 to name the new thing and adds none;
    ``silent`` edits R-2 without naming it; ``moved`` (the modifying link) moves R-2 and R-3 under Retired and AD-1 under Superseded."""
    spec, arch = PRIORS_OF[link]
    word = WORD[link]
    if route == "new-id":
        ident, title, text = NEW_ENTRY[link]
        return add_requirement(spec, ident, title, text), arch
    if route == "in-place":
        return spec.replace("### R-2:", f"### R-2: ({word})", 1) if "### R-2:" in spec else spec, arch
    if route == "silent":
        return spec.replace("### R-2:", "### R-2: (edited)", 1), arch
    raise ValueError(route)


def hidden(case: str, work: Path, logs: Path, only=None) -> dict:
    """The case's hidden acceptance on a delivery, all of it or only the checks named."""
    spec = copy.deepcopy(run.case_quality(case))
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
    def test_the_chain_is_the_first_pass_and_the_three_links_that_follow_it_on_a_base_smaller_than_the_ticket_service(self) -> None:
        self.assertEqual(chains.of(CASES, "user-page-size"), CHAIN)
        for name, follows in (("user-roles", "user-listing"), ("user-team-listing", "user-roles"), ("user-page-size", "user-team-listing")):
            self.assertEqual(CASES[name]["follows"], follows)
            self.assertEqual(CASES[name]["style"], "brownfield")
            self.assertNotIn("base", CASES[name])  # a follow-on starts from the run before it, not from a fixture
        base = ROOT / "test" / "shiploop_e2e" / "fixtures"

        def lines(fixture: str) -> int:
            return sum(len(path.read_text().splitlines()) for path in (base / fixture).rglob("*")
                       if path.is_file() and "node_modules" not in path.parts)
        self.assertEqual(CASES["user-listing"]["base"]["fixture"], "node-base")
        self.assertLess(lines("node-base") * 10, lines("node-tickets"))

    def test_each_link_is_held_to_every_earlier_links_checks_then_its_own_then_its_retention(self) -> None:
        seen = []
        for name in CHAIN[1:]:
            seen += CASES[CHAIN[CHAIN.index(name) - 1]]["checks"]
            _, prompt, checks, follows = run.load_case(type("Args", (), {"prompt": None, "case": name, "check": None}))
            self.assertEqual(follows, CASES[name]["follows"])
            self.assertEqual(prompt, CASES[name]["prompt"])
            self.assertEqual(checks, seen + CASES[name]["checks"] + CASES[name]["retention"], name)
            self.assertEqual((len(CASES[name]["checks"]), len(CASES[name]["retention"])), (3, 5))

    def test_its_retention_commands_see_the_pass_just_before_it(self) -> None:
        for name in CHAIN[1:]:
            case = CASES[name]
            self.assertTrue(all("PRIOR_WORK" in command for command in case["retention"]), name)
            self.assertTrue(any("AD-" in command for command in case["retention"]), name)
            self.assertTrue(case.get("retention_source") and case.get("checks_source"), name)
            self.assertIn(f"for word in {TEST_WORD[name]};", case["retention"][2], name)

    def test_the_spec_word_of_each_retention_check_is_the_requests_own_and_no_earlier_request_holds_it(self) -> None:
        """The first live run of ticket-sla failed a correct delivery because its check kept the previous link's word."""
        for position, name in enumerate(CHAIN[1:], start=1):
            words = re.findall(r"grep -qi (\S+) docs/shiploop/spec\.md", " ".join(CASES[name]["retention"]))
            self.assertEqual(words, [WORD[name]], name)
            self.assertRegex(CASES[name]["prompt"], re.compile(re.escape(WORD[name]), re.I), name)
            for earlier in CHAIN[:position]:
                self.assertNotRegex(CASES[earlier]["prompt"], re.compile(re.escape(WORD[name]), re.I), (name, earlier))

    def test_each_request_is_the_delta_and_names_none_of_the_inherited_decisions(self) -> None:
        for name in CHAIN[1:]:
            prompt = CASES[name]["prompt"].lower()
            for word in ("paginate", "helper", "envelope", "decision", "ad-", "r-1", "r-2", "floor", "ceil", "regular expression", "regex", "src/", "module"):
                if name == "user-page-size" and word == "decision":
                    continue  # the modifying request must name what it replaces: "the decisions behind them"
                self.assertNotIn(word, prompt, (name, word))
            self.assertIn("keeps working", prompt, name)
        # The modifying link names what it replaces, because the old rule is written in the spec, in a decision and in tests.
        sized_prompt = CASES["user-page-size"]["prompt"]
        self.assertIn("This replaces the rules", sized_prompt)
        self.assertIn("change those requirements, the decisions behind them and the tests that state them", sized_prompt)
        # The additive links name no rule of an earlier request: roles name neither pages nor sizes, teams ask for the users' ways without stating them.
        roles_prompt = CASES["user-roles"]["prompt"].lower()
        for word in ("total", "pages", "100", " 10", "ignored", "default"):
            self.assertNotIn(word, roles_prompt, word)
        teams_prompt = CASES["user-team-listing"]["prompt"].lower()
        self.assertIn("the way `get /users` lists users", teams_prompt)
        for word in ("100", " 10 ", "plain text", "ignoring case", "total", "partly", "default"):
            self.assertNotIn(word, teams_prompt, word)

    def test_the_own_checks_of_the_additive_links_read_no_rule_a_later_link_replaces(self) -> None:
        """A case's own checks run again as the regression of every later link: the default page size (10) and the largest size (100) are the
        hidden checks' to read, so a correct fourth pass does not fail the second and third links' own checks."""
        probe = (ROOT / "test" / "shiploop_e2e" / "checks" / "user_directory_probe.py").read_text()
        for mode in ("roles", "combine", "bad_role", "teams", "teams_filter", "teams_page"):
            body = probe.split(f"def {mode}(p: Probe)")[1].split("\ndef ")[0]
            self.assertNotRegex(body, r"size=100\b|\(1, 10, |page=1\"\)", mode)

    def test_each_link_declares_an_acceptance_of_its_own_and_the_declared_checks_are_the_modules_checks(self) -> None:
        previous = [row["id"] for row in CASES["user-listing"]["quality"]["acceptance"]["checks"]]
        for name in CHAIN[1:]:
            own = run.case_quality(name)
            self.assertEqual(own["refuse_ports"], [3000], name)
            self.assertTrue(scorecard.requires_acceptance(name), name)
            ids = [row["id"] for row in own["acceptance"]["checks"]]
            kept = [i for i in previous if i not in REPLACED] if name == "user-page-size" else previous
            self.assertEqual(ids, kept + list(NEW_HIDDEN[name]), name)
            self.assertEqual({row["grade"] for row in own["acceptance"]["checks"] if row["id"] in NEW_HIDDEN[name]}, {"fail-to-pass"}, name)
            self.assertEqual({row["grade"] for row in own["acceptance"]["checks"] if row["id"] not in NEW_HIDDEN[name]}, {"pass-to-pass"}, name)
            spec = importlib.util.spec_from_file_location(f"check_{own['acceptance']['module']}",
                                                          ROOT / "test" / "shiploop_e2e" / "checks" / f"{own['acceptance']['module']}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(list(module.CHECKS), ids, name)
            for path in own["acceptance"]["calibration"]:
                self.assertTrue((ROOT / path).is_file(), path)
            previous = ids
        self.assertEqual(len(previous), 22)

    def test_the_modifying_link_names_the_entries_it_may_change_for_the_ledger(self) -> None:
        change = CASES["user-page-size"]["delta"]["may_change"]
        self.assertEqual(set(change), {"spec.md", "architecture.md"})
        for name in ("user-roles", "user-team-listing"):
            self.assertNotIn("delta", CASES[name], name)

    def test_the_style_stays_out_of_every_suite_and_the_breadth_note_names_the_chain(self) -> None:
        suites = {name: suite for name, suite in json.loads((run.HERE / "suites.json").read_text()).items() if isinstance(suite, dict)}
        for name, suite in suites.items():
            for case in CHAIN[1:]:
                self.assertNotIn(case, suite.get("cases", []), (name, case))
        note = suites["breadth"]["not_covered"]["brownfield"]
        for case in CHAIN:
            self.assertIn(case, note)


class RealPriorTest(unittest.TestCase):
    """The words and ledger patterns were written from real pass-1 deliveries (Codex gpt-6.1-terra, ShipLoop 1.20.0 to 1.26.4)."""

    def test_the_retention_words_are_in_no_real_pass_1_spec(self) -> None:
        self.assertGreaterEqual(len(REAL), 7)
        for prior in REAL:
            spec = real(prior, "spec.md")
            for word in WORD.values():
                self.assertNotRegex(spec, re.compile(re.escape(word), re.I), (prior, word))

    def test_the_ledger_patterns_find_the_page_size_rules_in_every_real_pass_1_spec_and_architecture(self) -> None:
        may = CASES["user-page-size"]["delta"]["may_change"]
        for prior in REAL:
            spec, arch = real(prior, "spec.md"), real(prior, "architecture.md")
            self.assertEqual(delta.ids_block(spec, spec, "R", may["spec.md"])["expected"], ["R-2", "R-3"], prior)
            self.assertIn("AD-1", delta.ids_block(arch, arch, "AD", may["architecture.md"])["expected"], prior)

    def test_the_patterns_leave_the_filtering_and_compatibility_requirements_alone(self) -> None:
        """R-1 and R-4 are not the rules this request replaces: a run that edits them is changing what the request did not name."""
        may = CASES["user-page-size"]["delta"]["may_change"]
        for prior in REAL:
            spec = real(prior, "spec.md")
            expected = delta.ids_block(spec, spec, "R", may["spec.md"])["expected"]
            self.assertNotIn("R-1", expected, prior)
            self.assertNotIn("R-4", expected, prior)

    def test_the_ledger_reads_the_modifying_link_on_each_route_a_run_can_take(self) -> None:
        may = CASES["user-page-size"]["delta"]["may_change"]
        spec, arch = SPEC_3, ARCH_3
        # In place: R-2 and R-3 edited to name the setting: both touched, nothing unexplained.
        edited = spec.replace("### R-2:", "### R-2: (PAGE_SIZE)", 1).replace("### R-3:", "### R-3: (largest 50)", 1)
        block = delta.ids_block(spec, edited, "R", may["spec.md"])
        self.assertEqual((block["expected_touched"], block["expected_untouched"], block["unexplained"]), (["R-2", "R-3"], [], []))
        # Retired: both moved under Retired (their IDs kept) and a new requirement says the new rule: touched by retirement.
        moved = add_requirement(retire(retire(spec, "R-2", "Retired", "Replaced by R-7."), "R-3", "Retired", "Replaced by R-7."),
                                "R-7", "Page size", "PAGE_SIZE is 25.")
        block = delta.ids_block(spec, moved, "R", may["spec.md"])
        self.assertEqual((block["expected_touched"], block["retired_by_run"], block["unexplained"]), (["R-2", "R-3"], ["R-2", "R-3"], []))
        # Left standing, and another requirement edited without the request naming it: the two things the ledger exists to say.
        stray = spec.replace("### R-1:", "### R-1: (edited)", 1)
        block = delta.ids_block(spec, stray, "R", may["spec.md"])
        self.assertEqual((block["expected_untouched"], block["unexplained"]), (["R-2", "R-3"], ["R-1"]))
        # The decision: edited in place, or moved under Superseded.
        for final in (arch.replace("### AD-1:", "### AD-1: (edited)", 1), retire(arch, "AD-1", "Superseded", "Superseded by AD-5.")):
            block = delta.ids_block(arch, final, "AD", may["architecture.md"])
            self.assertEqual((block["expected_touched"], block["unexplained"]), (["AD-1"], []))


# Defects the link's own checks do not see: only a hidden check, inherited or new, does.
SILENT = {"user-roles": {"unknown-param-400"}, "user-team-listing": {"teams-default-size-20", "teams-size-cap-99", "role-filter-lost"}, "user-page-size": set()}


class CalibrationBase(Isolated):
    """One link's own checks and new hidden checks against its base, reference, alternative and each defect (a subclass names the link)."""

    link = ""

    @classmethod
    def setUpClass(cls) -> None:
        if not cls.link:
            raise unittest.SkipTest("the base of the per-link calibrations")
        if not (shutil.which("node") and shutil.which("lsof")):
            raise unittest.SkipTest("the cases' HTTP checks run through serve.py, which needs node and lsof")
        module, ids = MODULE[cls.link], NEW_HIDDEN[cls.link]
        cls.root = tempfile.TemporaryDirectory()
        cls.own, cls.new, cls.inherited, cls.why, cls.observed = {}, {}, {}, {}, {}
        with mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}):
            for variant in module.VARIANTS:
                work = committed(module.build(Path(cls.root.name) / variant, variant))
                rows = run.run_checks(work, CASES[cls.link]["checks"], timeout=180)
                cls.own[variant] = {i for i, row in enumerate(rows) if not row["pass"]}
                # A failure the variant's defect does not explain is told with the check's own output: a check that fails under machine
                # load (a server slow to listen) must be seen as that and not as a defect.
                cls.why[variant] = {OWN_NAMES[cls.link][i]: f"exit {row['returncode']}: {row['output'][:300]}" for i, row in enumerate(rows) if not row["pass"]}
                block = hidden(cls.link, work, Path(cls.root.name) / "logs" / variant)
                failed = {row["id"] for row in block["checks"] if not row["pass"]}
                cls.new[variant], cls.inherited[variant] = failed & set(ids), failed - set(ids)
                cls.observed[variant] = block.get("observed")
                cls.why[variant]["hidden"] = json.dumps([row for row in block["checks"] if not row["pass"]])[:700]

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "root", None):
            cls.root.cleanup()

    def test_every_variant_is_listed_graded_and_observed(self) -> None:
        self.assertEqual(set(EXPECTED[self.link]), set(MODULE[self.link].VARIANTS))
        self.assertEqual({variant for variant, seen in self.observed.items() if not seen}, set(), self.why)

    def test_the_base_fails_every_check_of_the_link_and_the_reference_and_the_alternative_pass_them_all(self) -> None:
        self.assertEqual((self.own["base"], self.new["base"], self.inherited["base"]), ({0, 1, 2}, ALL[self.link], set()), self.why["base"])
        for variant in ("reference", "alternative"):
            self.assertEqual((self.own[variant], self.new[variant], self.inherited[variant]), (set(), set(), set()), (variant, self.why[variant]))

    def test_each_defect_fails_exactly_the_checks_that_read_what_it_breaks(self) -> None:
        for variant, (own, new, inherited) in EXPECTED[self.link].items():
            with self.subTest(variant=variant):
                self.assertEqual((self.own[variant], self.new[variant], self.inherited[variant]), (own, new, inherited), self.why[variant])

    def test_every_check_of_the_link_is_failed_by_some_defect(self) -> None:
        defects = [variant for variant in EXPECTED[self.link] if variant not in ("base", "reference", "alternative", "hand-rolled")]
        self.assertEqual(set().union(*(self.own[v] for v in defects)), {0, 1, 2})
        self.assertEqual(set().union(*(self.new[v] for v in defects)), set(NEW_HIDDEN[self.link]))

    def test_some_defects_are_seen_only_by_a_hidden_check(self) -> None:
        silent = {variant for variant in EXPECTED[self.link] if variant not in ("base", "old-tests-left-standing")
                  and not self.own[variant] and (self.new[variant] or self.inherited[variant])}
        self.assertEqual(silent, SILENT[self.link])


@needs_servers
class RolesCalibrationTest(CalibrationBase):
    link = "user-roles"


@needs_servers
class TeamsCalibrationTest(CalibrationBase):
    link = "user-team-listing"

    def test_the_hand_rolled_teams_listing_with_every_rule_right_passes_so_a_defect_differs_in_one_rule_only(self) -> None:
        self.assertEqual((self.own["hand-rolled"], self.new["hand-rolled"], self.inherited["hand-rolled"]), (set(), set(), set()), self.why["hand-rolled"])


@needs_servers
class PageSizeCalibrationTest(CalibrationBase):
    link = "user-page-size"


@needs_servers
class InheritedAcceptanceTest(Isolated):
    """The earlier passes' hidden checks, which each link's reference keeps passing."""

    def test_the_references_pass_every_hidden_check_of_their_link(self) -> None:
        for case, module in MODULE.items():
            with self.subTest(case=case):
                block = hidden(case, committed(module.build(self.tmp / case, "reference")), self.tmp / "logs" / case)
                self.assertTrue(block["observed"], block)
                self.assertEqual([row["id"] for row in block["checks"] if not row["pass"]], [])
        self.assertEqual({case: len(run.case_quality(case)["acceptance"]["checks"]) for case in MODULE},
                         {"user-roles": 16, "user-team-listing": 23, "user-page-size": 22})

    def test_the_first_requests_checks_see_a_user_with_a_role_as_they_saw_one_without(self) -> None:
        """The first pass's checks compare whole user records; the roles link adds a field, and strip_role lets them read the rest."""
        work = committed(roles.build(self.tmp / "roles", "reference"))
        first = hidden("user-roles", work, self.tmp / "logs" / "roles", only=tuple(row["id"] for row in CASES["user-listing"]["quality"]["acceptance"]["checks"]))
        self.assertEqual([row["id"] for row in first["checks"] if not row["pass"]], [])
        self.assertEqual(len(first["checks"]), 11)
        # And the unwrapped first-pass module, shown the same delivery, is right to refuse it: the field IS there.
        spec = copy.deepcopy(run.case_quality("user-listing"))
        bare = quality.acceptance(work, spec["acceptance"], groups=set(), stop=lambda: None, logs=self.tmp / "logs" / "bare", ports=spec["refuse_ports"])
        self.assertTrue(any(not row["pass"] for row in bare["checks"]))


@needs_servers
class ModifiedRuleTest(Isolated):
    """Why the fourth link has an acceptance of its own: four earlier checks read the sentences its request replaces."""

    def old(self, builder, variant: str, ids: tuple, case: str) -> list:
        work = committed(builder.build(self.tmp / variant, variant))
        block = hidden(case, work, self.tmp / "logs" / variant, only=ids)
        self.assertTrue(block["observed"], block)
        return [row["pass"] for row in block["checks"]]

    def test_the_four_checks_the_request_replaces_pass_the_third_pass_and_fail_a_correct_fourth(self) -> None:
        self.assertEqual(self.old(teams, "reference", REPLACED, "user-team-listing"), [True] * 4)
        self.assertEqual(self.old(sized, "reference", REPLACED, "user-team-listing"), [False, False, False, False])

    def test_the_alternative_fails_them_too_and_the_declared_acceptance_holds_neither(self) -> None:
        self.assertEqual(self.old(sized, "alternative", REPLACED, "user-team-listing"), [False, False, False, False])
        ids = [row["id"] for row in run.case_quality("user-page-size")["acceptance"]["checks"]]
        for name in REPLACED:
            self.assertNotIn(name, ids)
        self.assertEqual(len(ids), 22)

    def test_the_other_old_checks_about_pages_still_hold_on_the_fourth_pass(self) -> None:
        """Only the default and the largest size are replaced: the envelope, the partial last page, the refusals and 101 stay as they were."""
        kept = ("page-envelope", "partial-last-page", "page-past-end", "filter-then-page", "bad-page-or-size", "teams-pages", "teams-bad-page-or-size")
        self.assertEqual(self.old(sized, "reference", kept, "user-team-listing"), [True] * len(kept))


@needs_servers
class ChainRunTest(Isolated):
    """Each link's checks as the harness runs them after a delivery, with the pass before it as ``PRIOR_WORK`` and its living files REAL."""

    def checks(self, work: Path, commands: list[str], prior: Path) -> list[bool]:
        """Each command's verdict, a failed one tried once more: the base's own node tests drop a connection now and then ("socket hang up", seen
        on the parent tree too), and a chain runs them in the pristine check and in two retention counts. A check that is really broken fails twice."""
        env = {"PRIOR_WORK": str(prior)}
        rows = run.run_checks(work, commands, timeout=300, env=env)
        failed = [index for index, row in enumerate(rows) if not row["pass"]]
        if failed:
            for index, row in zip(failed, run.run_checks(work, [commands[index] for index in failed], timeout=300, env=env)):
                rows[index] = row
        return [row["pass"] for row in rows]

    def link(self, case: str):
        spec, arch = PRIORS_OF[case]
        prior = committed(BEFORE[case].build(self.tmp / case / "prior", "reference"), spec, arch)
        _, _, every, _ = run.load_case(type("Args", (), {"prompt": None, "case": case, "check": None}))
        own, retention = CASES[case]["checks"], CASES[case]["retention"]
        return prior, every, len(every) - len(own) - len(retention), own, retention

    def test_each_reference_passes_the_regression_the_new_feature_and_every_retention_check(self) -> None:
        for case in MODULE:
            with self.subTest(case=case):
                prior, every, _, _, _ = self.link(case)
                work = committed(MODULE[case].build(self.tmp / case / "work", "reference"), *delivered(case, "new-id"))
                self.assertEqual(self.checks(work, every, prior), [True] * len(every))

    def test_the_regression_of_each_link_comes_from_every_earlier_link(self) -> None:
        self.assertEqual([len(run.load_case(type("Args", (), {"prompt": None, "case": c, "check": None}))[2])
                          for c in CHAIN[1:]], [3 + 3 + 5, 3 + 3 + 3 + 5, 3 + 3 + 3 + 3 + 5])

    def test_the_pass_before_unchanged_keeps_the_regression_and_fails_the_new_feature_the_tests_and_the_spec(self) -> None:
        for case in MODULE:
            with self.subTest(case=case):
                prior, every, regression, own, retention = self.link(case)
                work = committed(BEFORE[case].build(self.tmp / case / "unchanged", "reference"), *PRIORS_OF[case])
                got = self.checks(work, every, prior)
                self.assertEqual(got[:regression], [True] * regression)
                self.assertEqual(got[regression:regression + len(own)], [False] * len(own))
                self.assertEqual(got[regression + len(own):], [True, True, False, False, True])  # files, dependencies; tests, spec; decisions

    def test_a_spec_check_passes_on_both_routes_when_the_word_is_named_and_fails_the_silent_edit(self) -> None:
        """The two routes a spec check has: a requirement added (a new ID), and an earlier requirement edited in place (no new ID, the request's word)."""
        for case in MODULE:
            with self.subTest(case=case):
                prior, _, _, _, retention = self.link(case)
                for route, expected in (("new-id", [True] * 5), ("in-place", [True] * 5), ("silent", [True, True, True, False, True])):
                    work = committed(MODULE[case].build(self.tmp / case / route, "reference"), *delivered(case, route))
                    self.assertEqual(self.checks(work, retention, prior), expected, (case, route))

    def test_a_requirement_moved_under_retired_and_a_decision_under_superseded_keep_their_ids_and_pass(self) -> None:
        prior, _, _, _, retention = self.link("user-page-size")
        spec, arch = PRIORS_OF["user-page-size"]
        spec = add_requirement(retire(retire(spec, "R-2", "Retired", "Replaced by R-7."), "R-3", "Retired", "Replaced by R-7."),
                               "R-7", "Page size", "PAGE_SIZE is 25; the largest size is 50.")
        arch = retire(arch, "AD-1", "Superseded", "Superseded by AD-5.")
        work = committed(sized.build(self.tmp / "moved", "reference"), spec, arch)
        self.assertEqual(self.checks(work, retention, prior), [True] * 5)

    def test_a_file_deleted_a_requirement_dropped_and_a_decision_dropped_fail_their_retention_checks(self) -> None:
        for case in MODULE:
            with self.subTest(case=case):
                prior, _, _, _, retention = self.link(case)
                spec, arch = delivered(case, "new-id")
                work = MODULE[case].build(self.tmp / case / "lost", "reference")
                (work / "README.md").unlink()
                # The check reads every mention of an ID, so a dropped entry is dropped for good only when no other entry still cites it
                # (R-4 of the real prior says "cover R-1 through R-4"): a limit of the check, shared by every case's, recorded in the journal.
                spec = re.sub(r"\bR-1\b", "R-gone", re.sub(r"### R-1:.*?(?=\n### R-2:)", "", spec, flags=re.S))
                arch = re.sub(r"\bAD-1\b", "AD-gone", re.sub(r"### AD-1:.*?(?=\n## )", "", arch, flags=re.S))
                committed(work, spec, arch)
                self.assertEqual(self.checks(work, retention, prior), [False, True, True, False, False], case)

    def test_code_that_changed_while_two_tests_still_state_the_old_page_size_fails_the_delivery_s_own_suite(self) -> None:
        prior, every, regression, own, retention = self.link("user-page-size")
        work = committed(sized.build(self.tmp / "user-page-size" / "stale", "old-tests-left-standing"), *delivered("user-page-size", "new-id"))
        got = self.checks(work, every, prior)
        self.assertEqual([index for index, ok in enumerate(got) if not ok], [0])  # base_tests.py suite node-base: the delivery's own node --test fails


if __name__ == "__main__":
    unittest.main()
