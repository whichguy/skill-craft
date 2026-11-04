#!/usr/bin/env python3
"""The corpus summariser (test/shiploop_e2e/corpus.py). No model is called.

Why this suite exists. Three corpus figures changed when a later session re-derived them from the records: Improve yield
(19% shipped, 18% in its own scope, 26% pooled), narrative compliance (61%, then 69% once repeated bodies stopped
counting as separate obligations), and the refusal cost (a correlation that was a run-size confound). Each was computed
by a throwaway script, so nothing could re-derive it the same way. `corpus.py` is that one way, and these tests pin the
three mistakes those scripts actually made:

* reading the WORKSPACE folder instead of the navigator run directory inside it, which reported 0 Improve children over
  398 runs because `metrics.improve_reviews` then looked in `<workspace>/../worktree`;
* counting runs that live in a copied repository (`docs/experiments`, `test/fixtures`), which inflated a first pass to
  2,419 runs with 1,603 unmeasurable spans;
* grouping by root name, which collapsed 16 corpora into one row and hid the 11%-to-85% spread that is the finding.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import corpus  # noqa: E402
import metrics  # noqa: E402


def packet(stage: str, body: str) -> str:
    """A packet print asking for a narrative."""
    return (f"ShipLoop navigator | {stage} | revision 3\n\n=== ShipLoop narrative ===\n"
            f"Show the user this narrative exactly as written, as Markdown.\n\n{body}"
            "=== end ShipLoop narrative ===\n")


def workspace(root: Path, name: str, *, started: float, ended: float, children: int = 0,
              edited: int = 0, overlap: int = 0) -> Path:
    """A saved workspace folder with a nested navigator run, shaped as the harness leaves them.

    The Improve evidence the reader parses lives in the WORKTREE at ``.shiploop-improve/<stage>-<id>/reviews``
    (review notes plus ``pass-<n>.json``), with a matching ``<id>-bind.md`` in the run directory to attribute it --
    not in ``run/improve``, which holds the imported child folders.
    """
    out = root / name
    run = out / ".shiploop-runs" / "work-1" / "run"
    (run / "improve").mkdir(parents=True)
    reviews_root = out / ".shiploop-runs" / "work-1" / "worktree" / ".shiploop-improve"
    for number in range(children):
        child_id = f"nav-{number:04d}aaaa"
        reviews = reviews_root / f"plan-{child_id[-8:]}" / "reviews"
        reviews.mkdir(parents=True)
        (reviews / "review-1.md").write_text("a review\n")
        changed = number < edited
        (reviews / "pass-1.json").write_text(json.dumps({"edited": changed, "lines": [3 if changed else 0]}))
        (run / "improve" / f"{child_id}-bind.md").write_text("x")
    (out / "metrics.json").write_text(json.dumps({"span": {"started": started, "ended": ended},
                                                  "tmp_writes": []}))
    (out / "result.json").write_text(json.dumps({"case": "hello", "pass": True,
                                                 "environment": {"overlap": [{"run": f"x{i}"} for i in range(overlap)]}}))
    # The marker discovery looks for: a folder holding one of RUN_MARKERS is a run.
    (out / "timeline.jsonl").write_text(json.dumps({"t": started}) + "\n")
    return out


class CorpusTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "e2e-runs"
        (self.root / "2026-11-01").mkdir(parents=True)
        (self.root / "2026-10-31").mkdir(parents=True)

    def test_it_reads_the_navigator_run_directory_not_the_workspace(self):
        """Passing the workspace folder to metrics.improve_reviews found no Improve evidence at all (0 of 398 runs)."""
        workspace(self.root / "2026-11-01", "candidate-a", started=1000.0, ended=2000.0, children=4, edited=1)
        found = corpus.summarise([self.root], group_by="none")["groups"]["all"]
        self.assertEqual((found["improve_children"], found["improve_editing_children"]), (4, 1))
        self.assertEqual(found["improve_edit_rate"], 25.0)

    def test_a_run_whose_worktree_is_gone_reads_its_archived_reviews(self):
        """The worktree is disposable and the import archives every pass under the run (2026-11-04), so a saved run must
        still report its reviews rather than "notes are missing" once the worktree is deleted."""
        import shutil
        out = workspace(self.root / "2026-11-01", "archived", started=1000.0, ended=2000.0, children=2, edited=1)
        work = out / ".shiploop-runs" / "work-1"
        live = metrics.improve_reviews(work / "run")
        self.assertEqual((live["children"], live["edited_children"]), (2, 1))
        # Move the worktree's notes to where the import now puts them, then drop the worktree.
        archive = work / "run" / "improve"
        for reviews in (work / "worktree" / ".shiploop-improve").glob("*/reviews"):
            destination = archive / reviews.parent.name / "reviews"
            destination.mkdir(parents=True)
            for path in reviews.iterdir():
                shutil.copy2(path, destination / path.name)
        shutil.rmtree(work / "worktree")
        saved = metrics.improve_reviews(work / "run")
        self.assertEqual((saved["children"], saved["edited_children"]), (2, 1),
                         "the archived passes carry the same count the worktree did")
        self.assertIsNone(saved.get("unmeasured"))

    def test_the_worktree_still_wins_when_both_sources_exist(self):
        """Preferring the archive would move every figure measured from a live worktree, so it is only a fallback."""
        out = workspace(self.root / "2026-11-01", "both", started=1000.0, ended=2000.0, children=2, edited=1)
        work = out / ".shiploop-runs" / "work-1"
        archive = work / "run" / "improve"
        for reviews in (work / "worktree" / ".shiploop-improve").glob("*/reviews"):
            destination = archive / reviews.parent.name / "reviews"
            destination.mkdir(parents=True)
            (destination / "review-1.md").write_text("a review\n")
            (destination / "pass-1.json").write_text(json.dumps({"edited": True, "lines": [9]}))
        kept = metrics.improve_reviews(work / "run")
        # The archive says both children edited; the worktree says one. The worktree is the measured source.
        self.assertEqual(kept["edited_children"], 1)

    def test_a_run_inside_a_copied_repository_is_not_an_observation(self):
        """docs/experiments and test/fixtures trees under a corpus hold fixture runs, not observations."""
        (self.root / "2026-11-01" / "candidate-docs" / "docs" / "experiments" / "study").mkdir(parents=True)
        workspace(self.root / "2026-11-01", "real-run", started=1000.0, ended=2000.0)
        workspace(self.root / "2026-11-01" / "candidate-docs" / "docs" / "experiments" / "study",
                  "fixture-run", started=1000.0, ended=2000.0)
        found = corpus.summarise([self.root], group_by="corpus")["groups"]
        self.assertEqual(sum(row["runs"] for row in found.values()), 1, "only the real run is counted")
        self.assertFalse(corpus.is_observation(
            self.root / "2026-11-01" / "x" / "test" / "fixtures" / "run"))

    def test_the_default_grouping_keeps_the_date_folder_so_a_rate_keeps_its_scope(self):
        """Grouping by root name collapsed 16 corpora into one row and hid an 11%-to-85% spread."""
        workspace(self.root / "2026-11-01", "one", started=1000.0, ended=2000.0, children=10, edited=1)
        workspace(self.root / "2026-10-31", "two", started=5000.0, ended=6000.0, children=4, edited=3)
        groups = corpus.summarise([self.root], group_by="corpus")["groups"]
        self.assertEqual(sorted(groups), ["2026-10-31", "2026-11-01"])
        self.assertEqual((groups["2026-11-01"]["improve_edit_rate"], groups["2026-10-31"]["improve_edit_rate"]),
                         (10.0, 75.0))

    def test_overlap_counts_runs_whose_spans_share_more_than_the_floor(self):
        """A run's duration depends on whether another run was executing: contended runs are 1.32x longer in median."""
        workspace(self.root / "2026-11-01", "a", started=1000.0, ended=2000.0)
        workspace(self.root / "2026-11-01", "b", started=1500.0, ended=2500.0)
        workspace(self.root / "2026-11-01", "c", started=9000.0, ended=9500.0)
        rows = corpus.summarise([self.root], group_by="none")["groups"]["all"]
        self.assertEqual((rows["isolated"], rows["contended"]), (1, 2), "a and b overlap; c does not")
        # A shared span shorter than the floor is not an overlap.
        tight = corpus.summarise([self.root], group_by="none", overlap_seconds=600.0)["groups"]["all"]
        self.assertEqual((tight["isolated"], tight["contended"]), (3, 0))

    def test_an_unmeasurable_part_is_named_never_dropped_silently(self):
        """A run discovery finds but whose span cannot be read is counted, and the missing measure is named."""
        out = self.root / "2026-11-01" / "no-span"
        (out / ".shiploop-runs" / "work-1" / "run" / "improve").mkdir(parents=True)
        (out / "metrics.json").write_text(json.dumps({"tmp_writes": []}))
        (out / "result.json").write_text(json.dumps({"case": "hello", "pass": True}))
        (out / "timeline.jsonl").write_text('{"t": 1000}\n')  # what makes discovery see the folder as a run
        summary = corpus.summarise([self.root], group_by="none")
        self.assertEqual(summary["groups"]["all"]["runs"], 1)
        self.assertTrue(any("span" in key for key in summary["unmeasured"]),
                        "a run with no span is counted and its missing measure is named")

    def test_an_unreadable_status_is_unknown_not_unfinished(self):
        """A filter that reads "cannot read" as "did not finish" reports zero completed runs when its reader fails.

        A first version of `run_finished` returned False for an unreadable state, so `--status done` would have
        reported no completed runs at all rather than failing loudly -- the same "unknown read as zero" defect this
        repository's records warn about.
        """
        from unittest import mock

        import shiploop_store

        out = workspace(self.root / "2026-11-01", "unreadable", started=1000.0, ended=2000.0)
        run_dir = next((out / ".shiploop-runs").glob("*/run"))
        # The navigator's own record format: read_record refuses raw JSON by design, so the fixture uses the block.
        (run_dir / "state.md").write_text("# ShipLoop state\n\n```shiploop-state\n"
                                          + json.dumps({"status": "done", "history": []}, indent=1)
                                          + "\n```\n")
        self.assertIs(corpus.run_finished(out), True)
        with mock.patch.object(shiploop_store, "read_record", side_effect=RuntimeError("cannot read")):
            self.assertIsNone(corpus.run_finished(out), "unreadable is unknown, never 'not done'")
        # And the summary names it rather than dropping it into either group.
        with mock.patch.object(shiploop_store, "read_record", side_effect=RuntimeError("cannot read")):
            summary = corpus.summarise([self.root], status="done")
        self.assertEqual(summary["groups"], {}, "no run is claimed as done when none can be read")
        self.assertTrue(any("unreadable" in part for part in summary["status_unreadable"]))

    def test_a_missing_root_is_reported_not_silently_empty(self):
        summary = corpus.summarise([Path(tempfile.gettempdir()) / "definitely-not-a-corpus-xyz"])
        self.assertEqual(summary["missing_roots"], [str(Path(tempfile.gettempdir()) / "definitely-not-a-corpus-xyz")])
        self.assertIn("not a folder", corpus.render(summary))

    def test_the_rendered_spread_names_both_ends_so_a_pooled_rate_cannot_be_quoted_alone(self):
        """A single pooled rate hid a 0-to-93 point range across groups; I quoted a two-corpus 69% as a general
        figure on 2026-11-04 for exactly that reason. The spread line makes the range the headline, and it ignores
        groups too small for a rate to mean anything: a first version read a meaningless 0-to-100 from one-run groups.
        """
        workspace(self.root / "2026-11-01", "a1", started=1000.0, ended=2000.0, children=25, edited=25)
        workspace(self.root / "2026-10-31", "b1", started=5000.0, ended=6000.0, children=25, edited=0)
        # A one-run group whose rate is 100% by arithmetic must not set the high end.
        (self.root / "tiny").mkdir()
        workspace(self.root / "tiny", "c1", started=9000.0, ended=9500.0, children=1, edited=1)
        text = corpus.render(corpus.summarise([self.root], group_by="corpus"))
        self.assertIn("spread Improve edit: 0% (2026-10-31) to 100% (2026-11-01)", text)
        self.assertNotIn("(tiny)", text, "a group below MIN_GROUP takes no part in the spread")
        # Pooling hides it, and the pooled heading says so.
        pooled = corpus.render(corpus.summarise([self.root], group_by="none"))
        self.assertIn("the per-corpus spread is hidden", pooled)
        self.assertNotIn("spread Improve edit", pooled)


if __name__ == "__main__":
    unittest.main()
