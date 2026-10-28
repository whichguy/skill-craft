#!/usr/bin/env python3
"""Tests for baseline_check.py (experiment X4): C1 sources, C2 basis, C3 stale, on a throwaway Git repository.

    python3 docs/experiments/brownfield-baseline-20261028/test_baseline_check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baseline_check as check  # noqa: E402

ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def run(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          capture_output=True, text=True, check=True, env=ENV).stdout.strip()


def write(repo: Path, name: str, text: str) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(self.repo, "init", "-q")
        write(self.repo, "README.md", "# demo\n\nLists the users.\n")
        write(self.repo, "src/app.py", "class Store:\n    def handle(self):\n        return []\n")
        write(self.repo, "tests/test_app.py", "def test_lists_users():\n    assert True\n")
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "base")
        self.sha = run(self.repo, "rev-parse", "--short", "HEAD")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def baseline(self, r1: str = "", ad1: str = "") -> None:
        # Dedent the template first, then fill it: text interpolated at column 0 would stop dedent from working.
        write(self.repo, "docs/shiploop/spec.md", textwrap.dedent("""
            # Spec

            Baseline coverage: deep: src; overview: none; not inspected: none. As of SHA.

            ## Requirements

            ### R-1 Users are listed
            Status: baseline · Source: tested (`tests/test_app.py` "test_lists_users") · As of: SHA
            - The list answers every user (`src/app.py` `Store.handle`)R1

            ### R-2 Accepted later
            Status: accepted · Source: documented (README.md:3)
            - A requirement a run established.
            """).replace("SHA", self.sha).replace("R1", r1))
        write(self.repo, "docs/shiploop/architecture.md", textwrap.dedent("""
            # Architecture

            ## Decisions

            - AD-1 (inherited) Users live in memory. Why: inferred. Evidence: `src/app.py` `Store`.AD1

            ## Superseded
            """).replace("AD1", ad1))


class Sources(Fixture):
    def test_a_clean_baseline_has_no_finding(self) -> None:
        self.baseline()
        report = check.sources(self.repo)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["stats"]["entries"], 3)

    def test_each_fault_is_named(self) -> None:
        self.baseline()
        with (self.repo / "docs/shiploop/spec.md").open("a") as handle:
            handle.write(textwrap.dedent("""
                ### R-3 No source line
                Status: baseline
                - Something (`src/missing.py`)

                ### R-4 A symbol that is not there
                Status: baseline · Source: observed (`src/app.py` `nothere`)

                ### R-5 A docs line past the end
                Status: baseline · Source: documented (README.md:99)
                """))
        with (self.repo / "docs/shiploop/architecture.md").open("a") as handle:
            handle.write("- AD-2 Something without a status. Evidence: `src/app.py`.\n")
        problems = {(f["ident"], f["problem"]) for f in check.sources(self.repo)["findings"]}
        self.assertIn(("R-3", "no Source line"), problems)
        self.assertIn(("R-3", "locator: no such path"), problems)
        self.assertIn(("R-4", "locator: 'nothere' not in src/app.py"), problems)
        self.assertIn(("R-5", "locator: README.md has 4 lines"), problems)
        self.assertIn(("AD-2", "no (inherited) or (accepted) status"), problems)
        self.assertNotIn("R-1", {ident for ident, _ in problems})


class Basis(Fixture):
    REQUEST = "Make the list faster. Keep the users in memory."

    def commit_baseline(self) -> str:
        self.baseline()
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "docs(shiploop): record demo knowledge at baseline")
        return run(self.repo, "rev-parse", "HEAD")

    def test_silence_preserves(self) -> None:
        since = self.commit_baseline()
        self.assertEqual(check.basis(self.repo, since, self.REQUEST)["findings"], [])

    def test_a_changed_inherited_requirement_needs_a_basis(self) -> None:
        since = self.commit_baseline()
        self.baseline(r1="\n- It answers within 10 ms.")
        report = check.basis(self.repo, since, self.REQUEST)
        self.assertEqual([f["ident"] for f in report["findings"]], ["R-1"])
        self.baseline(r1="\n- It answers within 10 ms.\nBasis: S1")
        self.assertEqual(check.basis(self.repo, since, self.REQUEST)["findings"], [])
        self.baseline(r1="\nBasis: S7")
        self.assertEqual([f["ident"] for f in check.basis(self.repo, since, self.REQUEST)["findings"]], ["R-1"])

    def test_superseding_an_inherited_decision_needs_a_basis(self) -> None:
        since = self.commit_baseline()
        text = (self.repo / "docs/shiploop/architecture.md").read_text()
        moved = text.replace("- AD-1 (inherited) Users live in memory. Why: inferred. Evidence: `src/app.py` `Store`.\n", "")
        moved += "- AD-1 (inherited) Users live in memory. Why: inferred. Evidence: `src/app.py` `Store`.\n"
        (self.repo / "docs/shiploop/architecture.md").write_text(moved)
        self.assertEqual([f["ident"] for f in check.basis(self.repo, since, self.REQUEST)["findings"]], ["AD-1"])
        (self.repo / "docs/shiploop/architecture.md").write_text(moved.rstrip("\n") + " Basis: assumption A-1\n")
        self.assertEqual([f["ident"] for f in check.basis(self.repo, since, self.REQUEST)["findings"]], ["AD-1"])
        self.assertEqual(check.basis(self.repo, since, self.REQUEST, assumptions={"A-1"})["findings"], [])

    # Round 2 (Astra's max review, 2026-10-28, reproduced): every entry that existed when the run began is covered,
    # a sentence number is 1..N, an assumption must name a recorded one, an obligation needs the request itself, and
    # an evidence-only change (its As of) is no change.
    def test_an_accepted_entry_needs_a_basis_too(self) -> None:
        since = self.commit_baseline()
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text(spec.read_text().replace("A requirement a run established.", "Reworded by a later run."))
        self.assertEqual([f["ident"] for f in check.basis(self.repo, since, self.REQUEST)["findings"]], ["R-2"])

    def test_sentence_zero_and_a_bare_assumption_are_refused(self) -> None:
        since = self.commit_baseline()
        for basis in ("Basis: S0", "Basis: assumption", "Basis: assumption A-9"):
            self.baseline(r1="\n- It answers within 10 ms.\n" + basis)
            found = check.basis(self.repo, since, self.REQUEST, assumptions={"A-1"})["findings"]
            self.assertEqual([f["ident"] for f in found], ["R-1"], basis)
        self.baseline(r1="\n- It answers within 10 ms.\nBasis: assumption A-1")
        self.assertEqual(check.basis(self.repo, since, self.REQUEST, assumptions={"A-1"})["findings"], [])

    def test_an_obligation_changes_only_with_the_request(self) -> None:
        since = self.commit_baseline()
        spec = self.repo / "docs/shiploop/spec.md"
        text = spec.read_text().replace("A requirement a run established.", "Reworded.\nBasis: assumption A-1")
        spec.write_text(text)
        found = check.basis(self.repo, since, self.REQUEST, assumptions={"A-1"})["findings"]
        self.assertEqual([f["ident"] for f in found], ["R-2"])
        spec.write_text(text.replace("Basis: assumption A-1", "Basis: S2"))
        self.assertEqual(check.basis(self.repo, since, self.REQUEST, assumptions={"A-1"})["findings"], [])

    def test_an_as_of_refresh_is_no_change(self) -> None:
        since = self.commit_baseline()
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text(spec.read_text().replace("As of: " + self.sha, "As of: 0123456789ab"))
        self.assertEqual(check.basis(self.repo, since, self.REQUEST)["findings"], [])

    def test_the_rendered_request_file_counts_its_own_sentences(self) -> None:
        rendered = check.request_index.render(self.REQUEST)
        self.assertEqual(check.request_sentences(rendered), 2)


class Stale(Fixture):
    def test_an_edit_to_a_cited_file_marks_its_entries(self) -> None:
        self.baseline()
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "baseline")
        self.assertEqual(check.stale(self.repo)["stale"], [])
        write(self.repo, "src/app.py", "class Store:\n    def handle(self):\n        return ['changed']\n")
        run(self.repo, "commit", "-qam", "a human edit after the baseline")
        ids = [row["id"] for row in check.stale(self.repo)["stale"]]
        self.assertEqual(ids, ["R-1", "AD-1"])

    # Round 2 (Astra's max review): missing evidence is never fresh.
    def test_a_deleted_source_a_dirty_edit_and_a_bad_revision_are_not_fresh(self) -> None:
        self.baseline()
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "baseline")
        (self.repo / "tests/test_app.py").write_text("def test_lists_users():\n    assert False\n")  # dirty, uncommitted
        states = {row["id"]: row["state"] for row in check.stale(self.repo)["entries"]}
        self.assertEqual(states["R-1"], "stale")
        run(self.repo, "checkout", "-q", "--", "tests/test_app.py")
        run(self.repo, "rm", "-q", "src/app.py")
        run(self.repo, "commit", "-qm", "delete the store")
        states = {row["id"]: row["state"] for row in check.stale(self.repo)["entries"]}
        self.assertEqual((states["R-1"], states["AD-1"]), ("stale", "stale"))
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text(spec.read_text().replace("As of: " + self.sha, "As of: 0badc0de0bad"))
        states = {row["id"]: row["state"] for row in check.stale(self.repo)["entries"]}
        self.assertEqual(states["R-1"], "unknown")

    def test_an_entry_without_its_own_as_of_is_judged_from_the_commit_that_wrote_it(self) -> None:
        # Not from the coverage line: moving that line after refreshing one area must not vouch for other entries.
        self.baseline()
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-qm", "baseline")
        states = {row["id"]: row["state"] for row in check.stale(self.repo)["entries"]}
        self.assertEqual(states["AD-1"], "fresh")
        write(self.repo, "src/app.py", "class Store:\n    def handle(self):\n        return ['moved on']\n")
        run(self.repo, "commit", "-qam", "a human edit")
        head = run(self.repo, "rev-parse", "--short", "HEAD")
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text(spec.read_text().replace(f"As of {self.sha}.", f"As of {head}."))  # another area refreshed
        run(self.repo, "commit", "-qam", "refresh the coverage line")
        states = {row["id"]: row["state"] for row in check.stale(self.repo)["entries"]}
        self.assertEqual(states["AD-1"], "stale")


if __name__ == "__main__":
    unittest.main(verbosity=1)
