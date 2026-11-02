"""No-model checks for frozen incremental predecessors and their delivery lineage."""
from __future__ import annotations

import hashlib
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
import delivery
import predecessor
import scorecard


DIMENSIONS = (
    "requested_behavior", "prior_behavior", "decision_handling",
    "knowledge_and_organization", "workflow_and_lineage",
)


def git(cwd: Path, *args: str, env=None) -> str:
    done = subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, env=env)
    return done.stdout.strip()


class PredecessorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "prior-run"
        self.work = self.run / "work"
        self.work.mkdir(parents=True)
        git(self.work, "init", "-q")
        git(self.work, "config", "user.name", "Fixture")
        git(self.work, "config", "user.email", "fixture@example.invalid")
        (self.work / ".gitignore").write_text("*.cache\n")
        (self.work / "product.txt").write_text("first\n")
        git(self.work, "add", ".gitignore", "product.txt")
        git(self.work, "commit", "-qm", "first")
        (self.work / "product.txt").write_text("delivered\n")
        git(self.work, "add", "product.txt")
        git(self.work, "commit", "-qm", "delivered")
        (self.work / "ignored.cache").write_text("must not be copied\n")
        self.before = delivery.capture(self.work, self.run)
        self.result = {
            "case": "hello", "pass": True,
            "metrics": {"turns": 8, "cost_usd": 1.25},
            "environment": {"overlap": {"observed": True, "runs": []}, "mixed_host": False,
                            "environments": [{"host_build": "fixture-build"}]},
            "left_behind": {"observed": True, "survived": []},
            "delivery": {"before": self.before, "after": delivery.fingerprint(self.work)},
        }
        self._write_run_records()
        no_overlap = lambda run, _result: {"observed": True,
                                           "root": str(scorecard.environment.runs_root(run).resolve()), "runs": []}
        self.overlap = mock.patch.object(scorecard, "qualification_overlap", side_effect=no_overlap)
        self.overlap.start()
        self.addCleanup(self.overlap.stop)
        self.live_overlap = mock.patch.object(scorecard.environment, "overlap", side_effect=lambda run: no_overlap(run, {}))
        self.live_overlap.start()
        self.addCleanup(self.live_overlap.stop)
        self.entry = self._entry()

    def _write_run_records(self):
        self.run.mkdir(parents=True, exist_ok=True)
        (self.run / "prompt.txt").write_text("prior prompt\n")
        if not (self.run / "metrics.json").is_file():
            self.run.joinpath("metrics.json").write_text(json.dumps({
                "tmp_writes": [],
                "fidelity": {"end_state": {"status": "done", "unverified": {"entries": 0, "not_restated": 0}},
                             "evidence": {"counts": {"skipped": 0}}, "edits": {"script_owned": []},
                             "refusals": {"count": 0, "repeated": 0}},
                "nomenclature": {"retired": {}},
            }) + "\n")
        (self.run / "timeline.jsonl").write_text("{}\n")
        (self.run / "events.jsonl").write_text("\n")
        (self.run / "stderr.txt").write_text("")
        (self.run / "transcript.md").write_text("fixture\n")
        (self.run / "invocation.json").write_text(json.dumps({"case": self.result["case"], "host": "fixture"}))
        (self.run / "result.json").write_text(json.dumps(self.result))
        self._write_selected_run()

    def _write_selected_run(self, output=None, name="synthetic"):
        output = Path(output or self.run)
        selected_home = output / ".shiploop-runs" / name
        selected = selected_home / "run"
        selected.mkdir(parents=True, exist_ok=True)
        (selected / "state.md").write_text(
            "# Synthetic selected run fixture\n\n"
            "This file exists only to exercise receipt binding; no ShipLoop run occurred.\n"
        )
        (selected / "current-spec.md").write_text(
            "Synthetic current-spec fixture for receipt binding only.\n"
        )
        (selected / "reviewed.md").write_text(
            "Synthetic review fixture; no independent or owner review was performed.\n"
        )
        (selected / "promotion.md").write_text(
            "Synthetic promotion fixture; no promotion decision was made.\n"
        )
        (selected_home / "workspace.md").write_text(
            "Synthetic workspace fixture adjacent to the selected run.\n"
        )
        (selected_home / "return-plan.md").write_text(
            "Synthetic return-plan fixture adjacent to the selected run.\n"
        )
        (selected_home / "return-receipt.md").write_text(
            "Synthetic return-receipt fixture adjacent to the selected run.\n"
        )
        (output / "shiploop-run.json").write_text(json.dumps({
            "preexisting": {},
            "run_dir": str(selected.resolve()),
            "basis": "synthetic fixture explicitly selects this run",
        }) + "\n")
        return selected

    def _entry(self):
        receipt = scorecard.run_receipt(self.run)
        review = {
            "reviewer": "synthetic test fixture",
            "receipt_sha256": receipt["sha256"],
            "dimensions": {name: {"status": "pass", "evidence": [f"synthetic fixture text for {name}"]}
                           for name in DIMENSIONS},
            "basis": "synthetic fixture only; no independent review was performed",
        }
        return {"run": str(self.run.resolve()), "receipt": receipt, "review": review}

    def _refresh_entry(self):
        self.entry = self._entry()

    def _write_follow_output(self, output, work, invocation, result):
        before = delivery.capture(work, output)
        result["delivery"] = {"before": before, "after": delivery.fingerprint(work)}
        (output / "prompt.txt").write_text("follow-on prompt\n")
        (output / "metrics.json").write_text("{}\n")
        (output / "timeline.jsonl").write_text("{}\n")
        (output / "events.jsonl").write_text("\n")
        (output / "stderr.txt").write_text("")
        (output / "transcript.md").write_text("fixture\n")
        (output / "invocation.json").write_text(json.dumps(invocation))
        (output / "result.json").write_text(json.dumps(result))
        self._write_selected_run(output)

    def test_fail_first_clean_restore_preserves_committed_history_and_excludes_ignored_files(self):
        predecessor.validate_entry(self.entry, "hello")
        target = self.root / "restored"
        target.mkdir()

        follow_on = predecessor.restore(self.entry, target, "hello")

        product = self.entry["receipt"]["product"]
        self.assertEqual(delivery.fingerprint(target), product)
        self.assertEqual(git(target, "branch", "--show-current"), "e2e-predecessor")
        self.assertEqual(git(target, "rev-list", "--count", "HEAD"), "2")
        self.assertFalse((target / "ignored.cache").exists())
        self.assertEqual(follow_on["prior"], self.entry["run"])
        self.assertEqual(follow_on["prior_case"], "hello")
        self.assertIs(follow_on["prior_pass"], True)
        self.assertEqual(follow_on["start_head"], product["head"])
        self.assertEqual(follow_on["registered_predecessor"], {
            "receipt_sha256": self.entry["receipt"]["sha256"],
            "bundle_sha256": self.entry["receipt"]["files"]["delivery/work.bundle"],
            "head": product["head"], "tree": product["tree"],
        })

    def test_run_receipt_binds_selected_run_tree_selector_and_adjacent_receipts(self):
        selected = self.run / ".shiploop-runs" / "synthetic" / "run"
        baseline = scorecard.run_receipt(self.run)
        self.assertTrue(baseline["selected_run"]["observed"])
        self.assertEqual(baseline["selected_run"]["path"], str(selected.resolve()))
        self.assertIn("shiploop-run.json", baseline["files"])
        self.assertTrue(baseline["observed"])

        digest = baseline["sha256"]
        evidence = (
            selected / "current-spec.md", selected / "state.md", selected / "reviewed.md",
            selected / "promotion.md", selected.parent / "workspace.md", selected.parent / "return-plan.md",
            selected.parent / "return-receipt.md",
        )
        for path in evidence:
            with self.subTest(path=path.name):
                path.write_text(path.read_text() + "changed in receipt regression\n")
                changed = scorecard.run_receipt(self.run)
                self.assertNotEqual(digest, changed["sha256"], f"receipt did not bind {path}")
                digest = changed["sha256"]

        added = selected / "added-after-run.md"
        added.write_text("Synthetic late addition.\n")
        with_added = scorecard.run_receipt(self.run)
        self.assertNotEqual(digest, with_added["sha256"], "receipt did not bind added selected-run evidence")
        added.unlink()
        after_delete = scorecard.run_receipt(self.run)
        self.assertNotEqual(with_added["sha256"], after_delete["sha256"],
                            "receipt did not bind deletion of selected-run evidence")

        self._write_selected_run(name="retargeted")
        retargeted = scorecard.run_receipt(self.run)
        self.assertNotEqual(after_delete["sha256"], retargeted["sha256"], "receipt did not bind selector retargeting")

    def test_run_receipt_does_not_walk_a_product_internal_selected_run_twice(self):
        selected_home = self.work / ".shiploop"
        selected = selected_home / "run"
        selected.mkdir(parents=True)
        (selected / "state.md").write_text("Synthetic product-internal selected run.\n")
        (selected_home / "workspace.md").write_text("Synthetic product-internal workspace.\n")
        (self.run / "shiploop-run.json").write_text(json.dumps({
            "preexisting": {}, "run_dir": str(selected.resolve()),
            "basis": "synthetic fixture selects a run inside work",
        }) + "\n")

        receipt = scorecard.run_receipt(self.run)

        self.assertTrue(receipt["selected_run"]["observed"])
        self.assertEqual(receipt["selected_run"]["tree"], "work")
        self.assertIn("work/.shiploop/run/state.md", receipt["files"])
        self.assertIn("work/.shiploop/workspace.md", receipt["files"])
        self.assertFalse(any(name.startswith("selected_run/") for name in receipt["files"]))

        self.work.joinpath("state.md").write_text("Synthetic selected run at work root.\n")
        for name in ("workspace.md", "return-plan.md", "return-receipt.md"):
            (self.run / name).write_text(f"Synthetic output-level {name} beside the selected work root.\n")
        (self.run / "shiploop-run.json").write_text(json.dumps({
            "preexisting": {}, "run_dir": str(self.work.resolve()),
            "basis": "synthetic fixture selects the work root",
        }) + "\n")

        root_selected = scorecard.run_receipt(self.run)

        self.assertTrue(root_selected["selected_run"]["observed"])
        self.assertEqual(root_selected["selected_run"]["tree"], "work")
        self.assertIn("work/state.md", root_selected["files"])
        for name in ("workspace.md", "return-plan.md", "return-receipt.md"):
            self.assertIn(f"selected_run_context/{name}", root_selected["files"])

    def test_run_receipt_keeps_absent_or_unchosen_selector_unbound_without_breaking_legacy(self):
        selector = self.run / "shiploop-run.json"
        selector.unlink()
        legacy = scorecard.run_receipt(self.run)
        self.assertTrue(legacy["observed"])
        self.assertFalse(legacy["selected_run"]["observed"])
        self.assertEqual(legacy["selected_run"]["reason"], "shiploop-run.json is absent")
        self.assertNotIn("shiploop-run.json", legacy["files"])

        self._refresh_entry()
        with self.assertRaisesRegex(ValueError, "bound selected run"):
            predecessor.validate_entry(self.entry, "hello", observe=False)

        selector.write_text(json.dumps({"preexisting": {"/prior/run": "f" * 64}}) + "\n")
        unchosen = scorecard.run_receipt(self.run)
        self.assertTrue(unchosen["observed"])
        self.assertFalse(unchosen["selected_run"]["observed"])
        self.assertIn("no chosen run", unchosen["selected_run"]["reason"])

        self._refresh_entry()
        with self.assertRaisesRegex(ValueError, "bound selected run"):
            predecessor.validate_entry(self.entry, "hello", observe=False)

    def test_registered_predecessor_requires_selector_bytes_in_its_receipt(self):
        receipt = json.loads(json.dumps(self.entry["receipt"]))
        receipt["files"].pop("shiploop-run.json")
        receipt["sha256"] = predecessor._receipt_digest(receipt)
        entry = {**self.entry, "receipt": receipt}
        entry["review"] = {**self.entry["review"], "receipt_sha256": receipt["sha256"]}

        with self.assertRaisesRegex(ValueError, "shiploop-run.json digest"):
            predecessor.validate_entry(entry, "hello", observe=False)

    def test_run_receipt_refuses_malformed_missing_outside_and_symlink_selected_runs(self):
        selector = self.run / "shiploop-run.json"

        selector.write_text('{"run_dir": ["not", "a", "path"]}\n')
        malformed = scorecard.run_receipt(self.run)
        self.assertFalse(malformed["observed"])
        self.assertFalse(malformed["selected_run"]["observed"])

        missing = self.run / ".shiploop-runs" / "missing" / "run"
        selector.write_text(json.dumps({"run_dir": str(missing), "basis": "synthetic missing run"}) + "\n")
        missing_receipt = scorecard.run_receipt(self.run)
        self.assertFalse(missing_receipt["observed"])
        self.assertFalse(missing_receipt["selected_run"]["observed"])

        no_state = self.run / ".shiploop-runs" / "no-state" / "run"
        no_state.mkdir(parents=True)
        selector.write_text(json.dumps({"run_dir": str(no_state.resolve()), "basis": "synthetic missing state"}) + "\n")
        missing_state = scorecard.run_receipt(self.run)
        self.assertFalse(missing_state["observed"])
        self.assertIn("state.md", " ".join(missing_state["missing"]))

        outside = self.root / "outside-selected-run"
        outside.mkdir()
        (outside / "state.md").write_text("Synthetic outside selected run.\n")
        sentinel = outside / "secret.txt"
        sentinel.write_text("outside selected run must never be hashed\n")
        outside_digest = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        selector.write_text(json.dumps({"run_dir": str(outside.resolve()), "basis": "synthetic outside run"}) + "\n")
        outside_receipt = scorecard.run_receipt(self.run)
        self.assertFalse(outside_receipt["observed"])
        self.assertFalse(outside_receipt["selected_run"]["observed"])
        self.assertNotIn(outside_digest, outside_receipt["files"].values())

        symlink = self.run / ".shiploop-runs" / "linked-outside"
        symlink.symlink_to(outside, target_is_directory=True)
        selected_via_link = symlink
        selector.write_text(json.dumps({
            "run_dir": str(selected_via_link), "basis": "synthetic symlink run",
        }) + "\n")
        symlink_receipt = scorecard.run_receipt(self.run)
        self.assertFalse(symlink_receipt["observed"])
        self.assertFalse(symlink_receipt["selected_run"]["observed"])
        self.assertNotIn(outside_digest, symlink_receipt["files"].values())

    def test_repeat_restore_when_bundle_default_branch_is_already_fixed_name(self):
        git(self.work, "branch", "e2e-predecessor")
        git(self.work, "checkout", "-q", "e2e-predecessor")
        for branch in git(self.work, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines():
            if branch != "e2e-predecessor":
                git(self.work, "branch", "-D", branch)
        self.before = delivery.capture(self.work, self.run)
        self.result["delivery"] = {"before": self.before, "after": delivery.fingerprint(self.work)}
        self._write_run_records()
        self._refresh_entry()
        bundle = self.run / delivery.BUNDLE
        heads = subprocess.run(["git", "bundle", "list-heads", str(bundle)], check=True,
                               capture_output=True, text=True).stdout
        self.assertIn("refs/heads/e2e-predecessor", heads)
        probe = self.root / "bundle-probe"
        subprocess.run(["git", "clone", "-q", str(bundle), str(probe)], check=True,
                       capture_output=True, text=True)
        self.assertEqual(git(probe, "branch", "--show-current"), "e2e-predecessor")
        shutil.rmtree(probe)

        product = self.entry["receipt"]["product"]
        target = self.root / "repeated-restore"
        target.mkdir()
        follow_on = predecessor.restore(self.entry, target, "hello")

        restored = delivery.fingerprint(target)
        self.assertEqual((restored["head"], restored["tree"], restored["status"]),
                         (product["head"], product["tree"], []))
        self.assertEqual(git(target, "branch", "--show-current"), "e2e-predecessor")
        self.assertEqual(git(target, "rev-list", "--count", "HEAD"), "2")
        self.assertEqual(follow_on["start_head"], product["head"])

    def test_validate_entry_rejects_wrong_case_nonpass_unobserved_receipt_dirty_status_and_bad_score(self):
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "other-case")

        self.result["pass"] = False
        self._write_run_records()
        self._refresh_entry()
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "hello")

        self.result["pass"] = True
        self._write_run_records()
        self._refresh_entry()
        bad = dict(self.entry)
        bad["receipt"] = {**bad["receipt"], "observed": False}
        with self.assertRaises(ValueError):
            predecessor.validate_entry(bad, "hello", observe=False)

        (self.work / "dirty.txt").write_text("uncommitted\n")
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "hello")
        (self.work / "dirty.txt").unlink()

        metrics_path = self.run / "metrics.json"
        data = json.loads(metrics_path.read_text())
        data["fidelity"]["end_state"]["status"] = "waiting"
        metrics_path.write_text(json.dumps(data) + "\n")
        self._refresh_entry()
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "hello")

    def test_validate_entry_requires_review_dimensions_to_be_complete_and_passing(self):
        for mutate in (
            lambda review: review["dimensions"].pop("workflow_and_lineage"),
            lambda review: review["dimensions"].update(extra={"status": "pass", "evidence": ["x"]}),
            lambda review: review["dimensions"]["prior_behavior"].update(status="unknown"),
            lambda review: review["dimensions"]["decision_handling"].update(evidence=[" "]),
            lambda review: review.update(reviewer="  "),
            lambda review: review.update(receipt_sha256="0" * 64),
        ):
            with self.subTest(mutate=mutate):
                entry = json.loads(json.dumps(self.entry))
                mutate(entry["review"])
                with self.assertRaises(ValueError):
                    predecessor.validate_entry(entry, "hello", observe=False)

    def test_validate_entry_rejects_noncanonical_run_and_source_drift(self):
        extra = {**self.entry, "extra": "not part of the binding"}
        with self.assertRaises(ValueError):
            predecessor.validate_entry(extra, "hello", observe=False)
        relative = {**self.entry, "run": str(Path(self.entry["run"]).relative_to(Path(self.entry["run"]).anchor))}
        with self.assertRaises(ValueError):
            predecessor.validate_entry(relative, "hello", observe=False)

        prompt = self.run / "prompt.txt"
        original = prompt.read_text()
        prompt.write_text(original + "changed\n")
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "hello")
        prompt.write_text(original)
        (self.run / "delivery" / "work.bundle").write_bytes(b"changed after the receipt")
        with self.assertRaises(ValueError):
            predecessor.validate_entry(self.entry, "hello")

    def test_validate_registration_enforces_follow_mapping_from_frozen_cases(self):
        reg = {"qualification": {"cases": {
            "base-case": {"base": {"fixture": "tiny"}},
            "next-case": {"follows": "hello"},
        }}, "predecessors": {"next-case": self.entry}}
        predecessor.validate_registration(reg)
        predecessor.validate_registration({"qualification": {"cases": {"ordinary": {}}}})

        for bad in (
            {"qualification": {"cases": {"next-case": {"follows": "hello"}}}},
            {"qualification": {"cases": {"ordinary": {}}}, "predecessors": {"ordinary": self.entry}},
            {"qualification": {"cases": {"next-case": {"follows": "hello"}}},
             "predecessors": {"other-case": self.entry}},
            {"qualification": {"cases": {"next-case": {"follows": "hello", "base": {}}}},
             "predecessors": {"next-case": self.entry}},
        ):
            with self.subTest(reg=bad), self.assertRaises(ValueError):
                predecessor.validate_registration(bad)

    def test_validate_registration_rejects_mixed_invalid_entry_without_accepting_review_language(self):
        bad = json.loads(json.dumps(self.entry))
        bad["review"]["dimensions"]["requested_behavior"]["status"] = "pass_with_notes"
        with self.assertRaises(ValueError):
            predecessor.validate_registration({
                "qualification": {"cases": {"next-case": {"follows": "hello"}}},
                "predecessors": {"next-case": bad},
            })

    def test_restore_refuses_a_bundle_that_does_not_contain_the_pinned_head_and_keeps_partial_product(self):
        other = self.root / "other"
        other.mkdir()
        git(other, "init", "-q")
        git(other, "config", "user.name", "Fixture")
        git(other, "config", "user.email", "fixture@example.invalid")
        (other / "other.txt").write_text("different history\n")
        git(other, "add", "other.txt")
        git(other, "commit", "-qm", "other")
        replacement = self.root / "other.bundle"
        git(other, "bundle", "create", str(replacement), "--all")
        (self.run / "delivery" / "work.bundle").write_bytes(replacement.read_bytes())
        self._refresh_entry()

        target = self.root / "partial"
        target.mkdir()
        with self.assertRaises((RuntimeError, ValueError)):
            predecessor.restore(self.entry, target, "hello")
        self.assertTrue(target.exists())

    def test_restore_rechecks_source_receipt_after_copy_and_keeps_restored_product_on_drift(self):
        target = self.root / "partial-after-drift"
        target.mkdir()
        restore = predecessor.delivery.restore

        def mutate_after_copy(*args, **kwargs):
            restored = restore(*args, **kwargs)
            (self.run / "delivery" / "work.bundle").write_bytes(b"changed after restore")
            return restored

        with mock.patch.object(predecessor.delivery, "restore", side_effect=mutate_after_copy):
            with self.assertRaises(ValueError):
                predecessor.restore(self.entry, target, "hello")
        self.assertTrue((target / ".git").exists())

    def test_restore_ignores_hostile_git_template_and_inherited_git_environment(self):
        home = self.root / "hostile-home"
        template = home / "hostile-template"
        hooks = template / "hooks"
        hooks.mkdir(parents=True)
        marker = self.root / "hook-ran"
        hook = hooks / "post-checkout"
        hook.write_text(f"#!/bin/sh\nprintf ran > {marker}\n")
        hook.chmod(0o755)
        home.mkdir(exist_ok=True)
        (home / ".gitconfig").write_text(f"[init]\n\ttemplateDir = {template}\n")
        target = self.root / "safe-restore"
        target.mkdir()
        hostile = {
            "HOME": str(home), "GIT_TEMPLATE_DIR": str(template),
            "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"), "GIT_DIR": str(self.work / ".git"),
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            predecessor.restore(self.entry, target, "hello")
        self.assertFalse(marker.exists())
        self.assertFalse((target / ".git" / "hooks" / "post-checkout").exists())

    def test_ordinary_delivery_restore_without_git_env_remains_supported(self):
        target = self.root / "ordinary-restore"
        restored = delivery.restore(self.run, target, self.before["head"])
        self.assertEqual(restored, target)
        self.assertEqual(delivery.fingerprint(target)["head"], self.before["head"])

    def test_linkage_accepts_a_descendant_and_rejects_tampering_and_nonancestor_product(self):
        output = self.root / "child-run"
        output.mkdir()
        work = output / "work"
        work.mkdir()
        follow_on = predecessor.restore(self.entry, work, "hello")
        git(work, "config", "user.name", "Descendant fixture")
        git(work, "config", "user.email", "descendant@example.invalid")
        (work / "product.txt").write_text("child change\n")
        git(work, "add", "product.txt")
        git(work, "commit", "-qm", "child change")
        invocation = {"case": "next-case", "host": "fixture", "follow_on": follow_on}
        result = {"case": "next-case", "pass": True, "follow_on": follow_on}
        self._write_follow_output(output, work, invocation, result)
        self.assertEqual(predecessor.linkage_problems(self.entry, output, "hello"), [])

        tampered = json.loads(json.dumps(invocation))
        tampered["follow_on"]["registered_predecessor"]["tree"] = "0" * 40
        (output / "invocation.json").write_text(json.dumps(tampered))
        problems = predecessor.linkage_problems(self.entry, output, "hello")
        self.assertTrue(any("invocation" in problem for problem in problems), problems)

        (output / "invocation.json").write_text(json.dumps(invocation))
        tampered_result = json.loads(json.dumps(result))
        tampered_result["follow_on"]["registered_predecessor"]["receipt_sha256"] = "0" * 64
        (output / "result.json").write_text(json.dumps(tampered_result))
        problems = predecessor.linkage_problems(self.entry, output, "hello")
        self.assertTrue(any("result.json" in problem for problem in problems), problems)

        replacement_head = git(work, "rev-parse", "HEAD")
        git(work, "checkout", "--orphan", "unrelated")
        git(work, "rm", "-rf", "--ignore-unmatch", ".")
        (work / "x.txt").write_text("unrelated\n")
        git(work, "add", "x.txt")
        git(work, "commit", "-qm", "unrelated")
        self._write_follow_output(output, work, invocation, result)
        final_head = git(work, "rev-parse", "HEAD")
        predecessor_head = self.entry["receipt"]["product"]["head"]
        git(work, "replace", final_head, replacement_head)
        fake_ancestry = subprocess.run(["git", "-C", str(work), "merge-base", "--is-ancestor",
                                        predecessor_head, final_head], capture_output=True)
        self.assertEqual(fake_ancestry.returncode, 0, "fixture replacement ref must fake descent in live Git")
        problems = predecessor.linkage_problems(self.entry, output, "hello")
        self.assertTrue(any("ancestor" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)
