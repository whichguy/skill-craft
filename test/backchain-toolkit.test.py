#!/usr/bin/env python3
"""Hermetic tests for Backchain's command line (skills/backchain/scripts/backchain.py), run as a subprocess.

check and package are judged against the lib.js verdicts in test/fixtures/backchain-check; export against the
graphs the Backchain checkout's JS exporter recorded in test/fixtures/backchain-export, and against Plan
Dispatcher's own validate-graph.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/backchain/scripts/backchain.py"
CORPUS = ROOT / "test/fixtures/backchain-check"
GOLDENS = ROOT / "test/fixtures/backchain-export"
DISPATCH = ROOT / "skills/plan-dispatcher/scripts/dispatch.js"
sys.path.insert(0, str(CLI.parent))
import backchain_graph as graph  # noqa: E402


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(CLI), *args], capture_output=True, text=True,
                          cwd=str(cwd), timeout=120)


def corpus_inputs() -> list:
    return sorted(path for path in CORPUS.rglob("*.json") if not path.name.endswith(".verdict.json")
                  and path.name not in ("sources.json", "manifest.json", "ecmascript-whitespace.json"))


def verdict(path: Path) -> dict:
    """The lib.js verdict, read with JS number semantics like the port (12345678901234567000 is a float there)."""
    return graph.loads(path.with_name(path.name.replace(".json", ".verdict.json")).read_bytes())


def canon(value) -> str:
    return json.dumps(value, sort_keys=True)


class CheckTests(unittest.TestCase):
    def test_the_receipt_reproduces_every_recorded_lib_js_verdict(self):
        inputs = corpus_inputs()
        self.assertEqual(len(inputs), 88)
        for path in inputs:
            recorded = verdict(path)
            with self.subTest(path.relative_to(CORPUS).as_posix()):
                done = run("check", str(path))
                receipt = graph.loads(done.stdout.encode("utf-8"))
                self.assertEqual(done.returncode, 0 if recorded["ok"] else 1, done.stderr)
                self.assertEqual(receipt["schema"], "backchain-check/v1")
                self.assertEqual(receipt["plan_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                for key in ("ok", "failures", "completion", "parallel_groups", "packaged_sha256", "unconfirmed_produces"):
                    self.assertEqual(canon(receipt[key]), canon(recorded[key]), key)
                self.assertIn("backchain check: " + ("valid" if recorded["ok"] else "invalid"), done.stderr)

    def test_unreadable_or_non_json_input_could_not_run(self):
        with tempfile.TemporaryDirectory(prefix="backchain-toolkit-") as temp:
            for name, data in (("broken.json", b'{"goal": '), ("nan.json", b'{"goal": NaN}'),
                               ("latin1.json", b'"\xe9"')):
                path = Path(temp) / name
                path.write_bytes(data)
                with self.subTest(name):
                    done = run("check", str(path))
                    self.assertEqual((done.returncode, done.stdout), (3, ""))
                    self.assertIn("could not run", done.stderr)
                    self.assertIn("this is not a finding about the plan", done.stderr)
            missing = run("check", str(Path(temp) / "absent.json"))
            self.assertEqual((missing.returncode, missing.stdout), (3, ""))

    def test_a_usage_error_could_not_run(self):
        self.assertEqual(run("check").returncode, 3)
        self.assertEqual(run("nonesuch").returncode, 3)
        self.assertEqual(run("--help").returncode, 0)


class PackageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="backchain-toolkit-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_the_packaged_plan_carries_recomputed_groups_and_validates(self):
        source = CORPUS / "edge/inv6-stored-groups.json"
        out = self.base / "packaged.json"
        done = run("package", str(source), "--out", str(out))
        self.assertEqual(done.returncode, 0, done.stderr)
        packaged = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(packaged, graph.package(graph.loads(source.read_bytes())))
        self.assertEqual(packaged["parallel_groups"], [["S1", "S2"]])
        receipt = json.loads(done.stdout)
        self.assertEqual((receipt["output"], receipt["output_sha256"]),
                         (str(out), hashlib.sha256(out.read_bytes()).hexdigest()))
        self.assertTrue(run("check", str(out)).returncode == 0)

    def test_packaging_is_idempotent_atomic_and_keeps_the_file_mode(self):
        plan = self.base / "plan.json"
        plan.write_bytes((CORPUS / "luna/plan-final.json").read_bytes())
        os.chmod(plan, 0o640)
        self.assertEqual(run("package", str(plan), "--out", str(plan)).returncode, 0)
        first = plan.read_bytes()
        self.assertEqual(run("package", str(plan), "--out", str(plan)).returncode, 0)
        self.assertEqual(plan.read_bytes(), first)
        self.assertEqual(plan.stat().st_mode & 0o777, 0o640)
        fresh = self.base / "fresh.json"
        self.assertEqual(run("package", str(plan), "--out", str(fresh)).returncode, 0)
        self.assertEqual(fresh.stat().st_mode & 0o777, 0o644)
        self.assertEqual(sorted(path.name for path in self.base.iterdir()), ["fresh.json", "plan.json"])

    def test_an_invalid_plan_is_still_packaged_and_reported(self):
        out = self.base / "orphan.json"
        done = run("package", str(CORPUS / "edge/inv4-orphan.json"), "--out", str(out))
        self.assertEqual(done.returncode, 1)
        self.assertTrue(out.is_file())
        self.assertEqual([f["invariant"] for f in json.loads(done.stdout)["failures"]], [4])


class ExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="backchain-toolkit-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_the_goldens_are_the_recorded_js_exports(self):
        manifest = json.loads((GOLDENS / "MANIFEST.json").read_text(encoding="utf-8"))
        names = sorted({path.name.split(".")[0] for path in GOLDENS.glob("*.plan.json")})
        self.assertEqual(names, ["confirmed", "diamond", "fan-in"])
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((GOLDENS / name).read_bytes()).hexdigest(), digest, name)
        for name in names:
            with self.subTest(name):
                done = run("export", str(GOLDENS / f"{name}.plan.json"))
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout),
                                 json.loads((GOLDENS / f"{name}.graph.json").read_text(encoding="utf-8")))

    def test_done_strings_carry_each_confirm_level(self):
        exported = json.loads(run("export", str(GOLDENS / "confirmed.plan.json")).stdout)
        done = [line for step in exported["steps"] for line in step["contract"]["done"]]
        self.assertTrue(any(line.endswith("; pass when all 6 cases pass") for line in done))
        self.assertTrue(any(line.endswith("(inspection is sufficient)") for line in done))
        self.assertTrue(any("Confirm by: unconfirmable here — " in line for line in done))

    def test_every_valid_complete_corpus_plan_exports_and_plan_dispatcher_accepts_it(self):
        exported = refused = 0
        for path in corpus_inputs():
            plan = graph.package(graph.loads(path.read_bytes()))
            structure = graph.validate_structure(plan)
            exportable = (structure["ok"] and graph.completion_status(plan, structure)["status"] == "complete"
                          and bool(plan["steps"]))
            with self.subTest(path.relative_to(CORPUS).as_posix()):
                out = self.base / (path.stem + ".graph.json")
                done = run("export", str(path), "--out", str(out))
                if not exportable:
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("error", json.loads(done.stderr.strip().splitlines()[-1]))
                    self.assertFalse(out.exists())
                    refused += 1
                    continue
                self.assertEqual(done.returncode, 0, done.stderr)
                request = self.base / (path.stem + ".validate.json")
                request.write_text(json.dumps({"graph": json.loads(out.read_text(encoding="utf-8"))}), encoding="utf-8")
                accepted = subprocess.run(["node", str(DISPATCH), "validate-graph", str(request)],
                                          capture_output=True, text=True, timeout=60)
                self.assertEqual(accepted.returncode, 0, accepted.stderr)
                exported += 1
        # The JS exporter, run on each packaged input on 2026-11-01, gave the same verdict for all 88 and the same
        # graph for the 33 it exported (journal, Round 1).
        self.assertEqual((exported, refused), (33, 55))

    def test_an_incomplete_plan_is_refused_with_its_open_needs(self):
        done = run("export", str(CORPUS / "luna/plan-final.json"))
        self.assertEqual((done.returncode, done.stdout), (1, ""))
        self.assertIn("Backchain plan is incomplete", json.loads(done.stderr)["error"])


LOOP_RUNTIME = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
CONFIRMED = GOLDENS / "confirmed.plan.json"


def assessment(change_class: str = "none", gaps=(), blockers=(), findings=()) -> dict:
    """The convergence review prompt's JSON, as a cycle saves it. RunTests.record fills in candidate_identity, the
    reviewed candidate's SHA-256, unless a test sets that key itself."""
    return {"context_identity": "inspected", "change_class": change_class,
            "findings": list(findings), "checks": ["traced every outcome backward; screened every lens category"],
            "planning_gaps": list(gaps), "execution_blockers": list(blockers)}


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def without_one_edge(plan: dict) -> dict:
    """The confirmed plan with S2's second input from S1 removed: still valid, still complete."""
    edited = json.loads(json.dumps(plan))
    edited["steps"][1]["inputs"] = edited["steps"][1]["inputs"][:1]
    return edited


class RunTests(unittest.TestCase):
    """A planning run through the real bundled Until Loop runtime, with scripted assessments."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="backchain-run-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.request = self.base / "request.md"
        self.request.write_text("Planning only: make the CSV importer report rejected rows with line numbers.\n")
        self.plan = json.loads(CONFIRMED.read_text(encoding="utf-8"))
        self.reviews = 0

    def prepare(self, *extra: str, name: str = "run") -> Path:
        run_dir = self.base / name
        done = run("prepare", "--run", str(run_dir), "--request", str(self.request), *extra)
        self.assertEqual(done.returncode, 0, done.stderr)
        return run_dir

    def frozen(self, *extra: str, plan=None, draft=True, name: str = "run") -> Path:
        run_dir = self.prepare(*extra, name=name)
        text = json.dumps(plan if plan is not None else self.plan, indent=2)
        if draft and not (run_dir / "input/draft.json").exists():
            (run_dir / "draft.json").write_text(text)
        (run_dir / "plan.json").write_text(text)
        done = run("freeze", "--run", str(run_dir))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.freeze_output = done.stdout
        return run_dir

    def start(self, run_dir: Path) -> dict:
        with open(run_dir / "loop/contract.json", "rb") as contract:
            started = subprocess.run([sys.executable, "-B", str(LOOP_RUNTIME), "start", "--receipt",
                                      str(run_dir / "loop/receipt.json")], stdin=contract, capture_output=True,
                                     text=True, timeout=60)
        self.assertEqual(started.returncode, 0, started.stderr)
        return json.loads(started.stdout)

    @staticmethod
    def reviewed_identity(run_dir: Path) -> str:
        """The candidate a cycle reviews: the last recorded plan, or the frozen baseline before the first cycle."""
        evidence = run_dir / "evidence.json"
        if evidence.is_file():
            return json.loads(evidence.read_text(encoding="utf-8"))["cycles"][-1]["plan"]["sha256"]
        return file_digest(run_dir / "loop/baseline.json")

    def record(self, run_dir: Path, review: dict, exit_assessment="satisfied", continuation="allowed"):
        self.reviews += 1
        path = self.base / f"assessment-{self.reviews}.json"
        if "candidate_identity" not in review:
            review = dict(review, candidate_identity=self.reviewed_identity(run_dir))
        path.write_text(json.dumps(review))
        return run("record", "--run", str(run_dir), "--review", str(path), "--exit", exit_assessment,
                   "--continuation", continuation)

    def cycle(self, run_dir: Path, packet: dict, review: dict, edit=None, **report) -> dict:
        """One callback as the card asks: edit, record, run the packet's verify_script, submit record's report."""
        if edit is not None:
            plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
            (run_dir / "plan.json").write_text(json.dumps(edit(plan), indent=2))
        recorded = self.record(run_dir, review, **report)
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
        report_path = Path(recorded.stdout.splitlines()[0].removeprefix("Report: "))
        verified = subprocess.run(packet["verify_script"], shell=True, executable="/bin/sh", cwd=str(run_dir),
                                  capture_output=True, text=True, timeout=120)
        self.assertIn("all passed", verified.stdout, verified.stdout[-2000:])
        submitted = subprocess.run(packet["done_argv"], input=report_path.read_text(encoding="utf-8"),
                                   capture_output=True, text=True, timeout=60)
        self.assertEqual(submitted.returncode, 0, submitted.stderr)
        return json.loads(submitted.stdout)

    def test_a_fresh_run_converges_on_its_first_trivial_review(self):
        run_dir = self.frozen()
        contract = json.loads((run_dir / "loop/contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["required_trivial_reviews"], 1)
        self.assertEqual([check["id"] for check in contract["exit_checks"]], ["backchain-check", "backchain-evidence"])
        self.assertTrue(contract["context"]["request"].startswith("Backchain standalone Until Loop binding: "))
        self.assertNotIn("Backchain passes:", contract["context"]["request"])
        bound = {resource["purpose"] for resource in contract["context"]["resources"]}
        # The resources the 2026-10-16 study found missing from hand-written contracts are always bound.
        for purpose in ("Backchain references/convergence.md", "Until Loop runtime", "latest packet (receipt)",
                        "original request", "Until Loop card", "candidate plan"):
            self.assertIn(purpose, bound)
        locators = [resource["locator"] for resource in contract["context"]["resources"]]
        self.assertTrue(all(Path(locator).is_absolute() for locator in locators))
        packet = self.start(run_dir)
        self.assertEqual(packet["status"], "active")
        final = self.cycle(run_dir, packet, assessment("none"))
        self.assertEqual(final["status"], "complete")
        finished = run("finish", "--run", str(run_dir))
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "converged")
        self.assertEqual(result["convergence"]["terminal_receipt"]["status"], "complete")
        self.assertEqual(result["convergence"]["planning_gaps"], [])
        self.assertEqual(result["plan"], json.loads((run_dir / "plan.json").read_text(encoding="utf-8")))
        self.assertIn(" export ", finished.stdout)
        self.assertEqual(run("export", str(run_dir / "plan.json")).returncode, 0)

    def test_a_changed_plan_is_never_trivial_and_gets_a_fresh_review(self):
        run_dir = self.frozen()
        packet = self.start(run_dir)
        # The assessment calls it trivial, but the cycle removed an edge this run generated: measured, non-trivial.
        after = self.cycle(run_dir, packet, assessment("trivial"), edit=without_one_edge)
        report = json.loads((run_dir / "cycles/01/report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["classification"], "non-trivial")
        self.assertEqual(after["status"], "active")
        final = self.cycle(run_dir, after, assessment("none"))
        self.assertEqual(final["status"], "complete")
        evidence = json.loads((run_dir / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual([(c["cycle"], c["classification"], c["changed"]) for c in evidence["cycles"]],
                         [(1, "non-trivial", True), (2, "trivial", False)])
        self.assertEqual(run("finish", "--run", str(run_dir)).returncode, 0)

    def test_one_pass_completes_after_one_repairing_cycle(self):
        run_dir = self.frozen("--passes", "one")
        contract = json.loads((run_dir / "loop/contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["required_trivial_reviews"], 0)
        self.assertIn("\nBackchain passes: one\n", contract["context"]["request"])
        final = self.cycle(run_dir, self.start(run_dir), assessment("material"), edit=without_one_edge)
        self.assertEqual(final["status"], "complete")
        self.assertEqual(run("finish", "--run", str(run_dir)).returncode, 0)

    def test_converge_needs_two_consecutive_trivial_reviews(self):
        run_dir = self.frozen("--passes", "converge")
        contract = json.loads((run_dir / "loop/contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["required_trivial_reviews"], 2)
        self.assertIn("\nBackchain passes: converge\n", contract["context"]["request"])
        first = self.cycle(run_dir, self.start(run_dir), assessment("none"))
        self.assertEqual(first["status"], "active")
        self.assertEqual(self.cycle(run_dir, first, assessment("none"))["status"], "complete")

    def test_record_refuses_lost_obligations_bad_plans_and_inconsistent_reports(self):
        run_dir = self.frozen()
        self.start(run_dir)
        good = (run_dir / "plan.json").read_text(encoding="utf-8")
        lost_goal = json.loads(good)
        lost_goal["goal_needs"] = []
        orphan = json.loads(good)
        orphan["steps"].append({"id": "D1", "statement": "A helper exists.", "produces": ["A helper exists."],
                                "inputs": [], "origin": "discovered"})
        for label, plan, review, exit_assessment, expected in (
                ("goal_needs dropped", lost_goal, assessment("material"), "unsatisfied", "goal_needs"),
                ("orphan discovered step", orphan, assessment("material"), "unsatisfied", "invariant 4"),
                ("malformed assessment", None, {"change_class": "fine"}, "satisfied", "change_class"),
                ("unresolved but satisfied", None, assessment("unknown"), "satisfied", "unresolved cycle")):
            with self.subTest(label):
                (run_dir / "plan.json").write_text(json.dumps(plan) if plan is not None else good)
                refused = self.record(run_dir, review, exit_assessment=exit_assessment)
                self.assertEqual(refused.returncode, 1, refused.stderr)
                self.assertIn(expected, refused.stdout)
                self.assertEqual(list((run_dir / "cycles").iterdir()), [])
                self.assertFalse((run_dir / "evidence.json").exists())

    def test_inherited_edges_stay_while_generated_edges_may_go(self):
        inherited = self.base / "inherited.json"
        inherited.write_text(json.dumps(self.plan))
        refused_dir = self.prepare("--draft", str(inherited), name="inherited")
        (refused_dir / "plan.json").write_text(json.dumps(without_one_edge(self.plan)))
        refused = run("freeze", "--run", str(refused_dir))
        self.assertEqual(refused.returncode, 1)
        self.assertIn("inherited draft: input edge removed: S2 <- S1", refused.stdout)
        self.assertFalse((refused_dir / "loop/contract.json").exists())
        # The same removal is a reviewed repair when this run generated the edge (fresh route): recorded, non-trivial.
        run_dir = self.frozen(name="fresh")
        self.start(run_dir)
        (run_dir / "plan.json").write_text(json.dumps(without_one_edge(self.plan)))
        recorded = self.record(run_dir, assessment("material"), exit_assessment="unsatisfied")
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
        self.assertIn("non-trivial", recorded.stdout)

    def test_verify_rejects_a_late_edit_and_a_changed_record(self):
        run_dir = self.frozen()
        self.start(run_dir)
        self.assertEqual(self.record(run_dir, assessment("none")).returncode, 0)
        self.assertEqual(run("verify", "--run", str(run_dir)).returncode, 0)
        plan_path = run_dir / "plan.json"
        good = plan_path.read_bytes()
        plan_path.write_text(json.dumps(without_one_edge(json.loads(good))))
        late = run("verify", "--run", str(run_dir))
        self.assertEqual(late.returncode, 1)
        self.assertIn("changed after cycle 1 was recorded", late.stdout)
        plan_path.write_bytes(good)
        review = run_dir / "cycles/01/review.json"
        review.write_text(review.read_text(encoding="utf-8").replace('"none"', '"trivial"'))
        tampered = run("verify", "--run", str(run_dir))
        self.assertEqual(tampered.returncode, 1)
        self.assertIn("review record", tampered.stdout)

    def test_finish_reports_an_honest_stop_and_refuses_an_active_loop(self):
        run_dir = self.frozen()
        self.assertEqual(run("finish", "--run", str(run_dir)).returncode, 3)
        packet = self.start(run_dir)
        still = run("finish", "--run", str(run_dir))
        self.assertEqual(still.returncode, 3)
        self.assertIn("still active", still.stderr)
        gap = "The normative redaction policy docs/redaction.md is not in the repository."
        stopped = self.cycle(run_dir, packet, dict(assessment("material", gaps=[gap]), next_action="Supply docs/redaction.md."),
                             exit_assessment="unsatisfied", continuation="blocked")
        self.assertEqual(stopped["status"], "stopped")
        finished = run("finish", "--run", str(run_dir))
        self.assertEqual(finished.returncode, 1)
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual((result["status"], result["convergence"]["planning_gaps"]), ("incomplete", [gap]))
        self.assertEqual(result["convergence"]["next_action"], "Supply docs/redaction.md.")

    def test_prepare_and_freeze_fail_closed(self):
        run_dir = self.prepare()
        self.assertEqual(run("prepare", "--run", str(run_dir), "--request", str(self.request)).returncode, 3)
        missing = run("prepare", "--run", str(self.base / "other"), "--request", str(self.request),
                      "--until-loop", str(self.base / "nowhere/ADAPTER.md"))
        self.assertEqual(missing.returncode, 3)
        self.assertIn("MISSING: Until Loop card", missing.stderr)
        self.assertEqual(run("record", "--run", str(run_dir), "--review", str(self.request), "--exit", "satisfied",
                             "--continuation", "allowed").returncode, 3)
        # A generated draft's goal_needs survive elaboration.
        draft = json.loads(json.dumps(self.plan))
        draft["goal_needs"] = ["Rejected rows are reported with their line numbers.", "Accepted rows are imported."]
        (run_dir / "draft.json").write_text(json.dumps(draft))
        (run_dir / "plan.json").write_text(json.dumps(self.plan))
        lost = run("freeze", "--run", str(run_dir))
        self.assertEqual(lost.returncode, 1)
        self.assertIn("generated draft: goal_needs presence/value changed", lost.stdout)
        (run_dir / "draft.json").write_text(json.dumps(self.plan))
        self.assertEqual(run("freeze", "--run", str(run_dir)).returncode, 0)
        self.assertEqual(run("freeze", "--run", str(run_dir)).returncode, 3)
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(all(len(entry["sha256"]) == 64 for entry in meta["resources"]))
        self.assertEqual(meta["route"], "fresh")

    def test_each_route_reads_its_prompts_once_in_order(self):
        def reads(*extra: str, name: str) -> list:
            done = run("prepare", "--run", str(self.base / name), "--request", str(self.request), *extra)
            self.assertEqual(done.returncode, 0, done.stderr)
            return [line.strip() for line in done.stdout.splitlines() if line.strip()[:3] in ("1. ", "2. ", "3. ")]
        # A fresh request: direct synthesis, its dependency review, the elaborator only when that review finds a change.
        fresh = reads(name="fresh-route")
        self.assertEqual([line.split(": ")[0].rsplit("/", 2)[-2:] for line in fresh],
                         [["prompts", "direct.v1.md"], ["prompts", "dependency-review.prompt.md"],
                          ["prompts", "elaborator.v1.md"]])
        self.assertIn("only when 2 found a change", fresh[2])
        inherited = self.base / "inherited.json"
        inherited.write_text(json.dumps(self.plan))
        draft = reads("--draft", str(inherited), name="draft-route")
        self.assertEqual([line.split(": ")[0].rsplit("/", 1)[-1] for line in draft],
                         ["dependency-review.prompt.md", "elaborator.v1.md"])
        for route in (fresh, draft):
            self.assertFalse(any("generator.v1.md" in line for line in route))  # the checkout's one-shot pipeline only

    # The adversarial review of 2026-11-01 (Sol, medium; findings F1-F5 and F8). Each test is the refuting result the
    # reviewer named; each failed on the code it reviewed.

    def test_finish_refuses_a_receipt_that_is_not_this_runs(self):
        """F1: a fabricated or foreign complete receipt cannot make a run converge."""
        run_dir = self.frozen()
        self.assertEqual(self.cycle(run_dir, self.start(run_dir), assessment("none"))["status"], "complete")
        genuine = (run_dir / "loop/receipt.json").read_text(encoding="utf-8")
        other = self.frozen(name="other")
        self.assertEqual(self.cycle(other, self.start(other), assessment("none"))["status"], "complete")
        for label, receipt in (("fabricated", json.dumps({"status": "complete"})),
                               ("another run's", (other / "loop/receipt.json").read_text(encoding="utf-8"))):
            with self.subTest(label):
                (run_dir / "loop/receipt.json").write_text(receipt)
                done = run("finish", "--run", str(run_dir))
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(result["status"], "incomplete")
                self.assertIn("receipt", result["convergence"]["next_action"])
        (run_dir / "loop/receipt.json").write_text(genuine)
        self.assertEqual(run("finish", "--run", str(run_dir)).returncode, 0)

    def test_verify_rejects_a_changed_binding(self):
        """F2: the frozen request, caller packet, baseline, contract and selected resources cannot change under a run."""
        card = self.base / "until-loop" / "ADAPTER.md"
        shutil.copytree(LOOP_RUNTIME.parents[1], card.parent)
        run_dir, frozen = self.caller_run(lambda plan: plan, "binding", {}, "--until-loop", str(card))
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)
        self.start(run_dir)
        self.assertEqual(self.record(run_dir, assessment("none")).returncode, 0)
        self.assertEqual(run("verify", "--run", str(run_dir)).returncode, 0)
        for target in (run_dir / "input/request.md", run_dir / "input/caller.json", run_dir / "loop/baseline.json",
                       run_dir / "loop/contract.json", card, card.parent / "scripts/until_loop_ephemeral.py"):
            with self.subTest(target.name):
                original = target.read_bytes()
                target.write_bytes(original + b"\n")
                changed = run("verify", "--run", str(run_dir))
                self.assertEqual(changed.returncode, 1, changed.stdout)
                self.assertIn("changed", changed.stdout)
                target.write_bytes(original)
                self.assertEqual(run("verify", "--run", str(run_dir)).returncode, 0)

    def caller_run(self, edit, name: str, bounds: dict, *extra: str):
        """A source-aware run over the confirmed plan with these edit bounds, its candidate edited by ``edit``."""
        inherited = self.base / f"{name}-inherited.json"
        inherited.write_text(json.dumps(self.plan))
        packet = self.base / f"{name}-caller.json"
        packet.write_text(json.dumps({"interface": "backchain-caller/v1", "action": "repair", "stage": "revise",
                                      "action_id": "bounds-test", "owner": "test", "edit_bounds": bounds}))
        run_dir = self.prepare("--draft", str(inherited), "--caller", str(packet), *extra, name=name)
        (run_dir / "plan.json").write_text(json.dumps(edit(json.loads(json.dumps(self.plan)))))
        return run_dir, run("freeze", "--run", str(run_dir))

    def test_caller_edit_bounds_are_enforced(self):
        """F3: an edit outside the caller's bounds is refused and names the bound; one inside them is accepted."""
        fact = self.plan["initial_state"][0]
        bounds = {"provisional_step_ids": ["S2"], "provisional_edge_keys": ["S2<-S1"], "allow_new_steps": False,
                  "allow_new_edges": False, "protected_step_ids": ["S1"], "protected_edge_keys": [],
                  "protected_facts": [fact], "running_or_completed_step_ids": []}

        def protected_step(plan):
            plan["steps"][0]["statement"] += " Also logged."
            return plan

        def new_step(plan):
            plan["steps"].append({"id": "S3", "statement": "A changelog entry exists.",
                                  "produces": ["A changelog entry exists."], "inputs": [], "origin": "seed"})
            plan["goal_needs"] = plan["goal_needs"] + ["A changelog entry exists."]
            return plan

        def new_edge(plan):
            plan["steps"][1]["inputs"].append({"need": fact, "from": None})
            return plan

        def lost_fact(plan):
            plan["steps"][0]["inputs"] = []
            plan["initial_state"] = []
            return plan

        for label, edit, expected in (("protected step", protected_step, "protected step S1"),
                                      ("new step", new_step, "new step S3"),
                                      ("new edge", new_edge, "new edge S2<-null"),
                                      ("protected fact", lost_fact, "protected fact")):
            with self.subTest(label):
                _, refused = self.caller_run(edit, label.replace(" ", "-"), bounds)
                self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
                self.assertIn(expected, refused.stdout)
        # Within the bounds: S2 is provisional and S2<-S1 a provisional edge, so dropping one of its inputs is allowed.
        _, accepted = self.caller_run(without_one_edge, "within-bounds", bounds)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_a_protected_fact_the_plan_never_stated_is_not_required(self):
        """Pilot, 2026-11-01 (bounded-source-edge-repair): a caller's accepted fact outside the inherited initial_state
        is protected from contradiction, not a fact the plan must add; an authorized repair freezes."""
        bounds = {"provisional_step_ids": ["S2"], "provisional_edge_keys": ["S2<-S1"],
                  "running_or_completed_step_ids": ["S1"],
                  "protected_facts": ["S1 is already complete and its header map is recorded in artifacts/map.json"]}
        _, frozen = self.caller_run(without_one_edge, "accepted-fact", bounds)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)

    def test_a_provisional_edge_gains_inputs_only_with_allow_new_edges(self):
        """Round 2's F4: a provisional edge may change, but one that ends with more inputs gained dependencies."""
        produce = "The importer logs each header it cannot map."

        def one_more_input(plan):
            plan["steps"][0]["produces"].append(produce)
            plan["steps"][1]["inputs"].append({"need": produce, "from": "S1"})
            return plan

        bounds = {"provisional_step_ids": ["S1", "S2"], "provisional_edge_keys": ["S2<-S1"], "allow_new_edges": False}
        _, refused = self.caller_run(one_more_input, "gains-refused", bounds)
        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        self.assertIn("edge S2<-S1 gains an input without allow_new_edges", refused.stdout)
        _, accepted = self.caller_run(one_more_input, "gains-allowed", dict(bounds, allow_new_edges=True))
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_the_contract_lets_a_review_remove_what_the_bounds_make_provisional(self):
        """Round 2's F5: with caller bounds the work text no longer forbids an authorized inherited removal."""
        run_dir, frozen = self.caller_run(lambda plan: plan, "removal-text", {"provisional_step_ids": ["S2"]})
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)
        work = json.loads((run_dir / "loop/contract.json").read_text(encoding="utf-8"))["work"]
        self.assertIn("an inherited one only where the caller's edit bounds make it provisional", work)
        self.assertNotIn("never an inherited one", work)
        fresh = json.loads((self.frozen(name="fresh-text") / "loop/contract.json").read_text(encoding="utf-8"))
        self.assertIn("never an inherited one", fresh["work"])

    def test_record_binds_the_assessment_to_the_candidate_it_reviewed(self):
        """F4: a missing or stale candidate identity, or an assessment that records no checks, is refused."""
        run_dir = self.frozen()
        # The identity record expects is the one freeze printed for cycle 1.
        self.assertIn(f"Cycle 1's candidate_identity: {self.reviewed_identity(run_dir)}", self.freeze_output)
        self.start(run_dir)
        stale = "0" * 64
        for label, review, expected in (
                ("missing identity", dict(assessment("none"), candidate_identity=None), "candidate_identity"),
                ("stale identity", dict(assessment("none"), candidate_identity=stale), "candidate_identity"),
                ("no checks", dict(assessment("none"), checks=[]), "checks"),
                ("null checks (round 2, F3)", dict(assessment("none"), checks=[None]), "checks"),
                ("blank checks (round 2, F3)", dict(assessment("none"), checks=["  "]), "checks")):
            with self.subTest(label):
                refused = self.record(run_dir, review)
                self.assertEqual(refused.returncode, 1, refused.stdout)
                self.assertIn(expected, refused.stdout)
                self.assertFalse((run_dir / "evidence.json").exists())
        recorded = self.record(run_dir, assessment("none"))
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
        # ... and record prints, and its report's handoff repeats, the next cycle's.
        identity = self.reviewed_identity(run_dir)
        self.assertIn(f"Next cycle's candidate_identity: {identity}", recorded.stdout)
        report = json.loads((run_dir / "cycles/01/report.json").read_text(encoding="utf-8"))
        self.assertIn(identity, report["handoff"])

    def test_a_cycle_recorded_twice_in_one_callback_still_finishes(self):
        """An edit after record within one callback needs a second record; the first stays unsubmitted, and the
        run's receipt still binds (F1's check refuses only an action with no record behind it)."""
        run_dir = self.frozen()
        packet = self.start(run_dir)
        self.assertEqual(self.record(run_dir, assessment("none")).returncode, 0)
        after = self.cycle(run_dir, packet, assessment("material"), edit=without_one_edge, exit_assessment="unsatisfied")
        self.assertEqual(after["status"], "active")
        self.assertEqual(self.cycle(run_dir, after, assessment("none"))["status"], "complete")
        finished = run("finish", "--run", str(run_dir))
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)

    @staticmethod
    def submit(packet: dict, report: dict) -> dict:
        submitted = subprocess.run(packet["done_argv"], input=json.dumps(report), capture_output=True, text=True,
                                   timeout=60)
        if submitted.returncode != 0:
            raise AssertionError(submitted.stderr)
        return json.loads(submitted.stdout)

    def test_a_callback_submitted_without_record_is_found(self):
        """F1, and round 2's F2: a hand-written report in an earlier callback is refused by the next record (an extra
        record cannot pad it), and one in the last callback by finish."""
        hand = {"classification": "non-trivial", "exit_assessment": "unsatisfied", "continuation_assessment": "allowed",
                "evidence": "A hand-written report.", "handoff": "A hand-written handoff."}
        run_dir = self.frozen(name="earlier")
        after = self.submit(self.start(run_dir), hand)
        refused = self.record(run_dir, assessment("none"))
        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        self.assertIn("callback 1 that is not the last report record wrote", refused.stdout)
        self.assertFalse((run_dir / "evidence.json").exists())
        self.assertEqual(after["status"], "active")
        # The last callback: cycle 1 is recorded and submitted, then callback 2 submits a hand-written trivial report.
        run_dir = self.frozen("--passes", "converge", name="last")
        after = self.cycle(run_dir, self.start(run_dir), assessment("none"))
        verified = subprocess.run(after["verify_script"], shell=True, executable="/bin/sh", cwd=str(run_dir),
                                  capture_output=True, text=True, timeout=120)
        self.assertIn("all passed", verified.stdout, verified.stdout[-2000:])
        final = self.submit(after, dict(hand, classification="trivial", exit_assessment="satisfied"))
        self.assertEqual(final["status"], "complete")
        done = run("finish", "--run", str(run_dir))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertIn("callback(s) 2 have no recorded cycle", result["convergence"]["next_action"])

    @staticmethod
    def final_review(run_dir: Path, **changes) -> dict:
        """The caller review object a source-aware run writes after its loop, assessing the final candidate."""
        review = {"interface": "backchain-caller/v1", "action": "repair", "stage": "revise", "action_id": "bounds-test",
                  "candidate": {"output_sha256": file_digest(run_dir / "plan.json"), "disposition": "unchanged"},
                  "findings": [], "planning_gaps": [], "execution_blockers": [],
                  "coverage": {"source_review_status": "complete"}}
        review.update(changes)
        return review

    def test_finish_refuses_a_final_review_that_is_not_of_the_final_candidate(self):
        """Round 2's F1: an identity-only shell, or the assessment of the inherited candidate after a revision, is not
        the final source assessment; finish refuses it (could not run) instead of stamping the output digest on it."""
        bounds = {"provisional_step_ids": ["S2"], "provisional_edge_keys": ["S2<-S1"]}
        run_dir, frozen = self.caller_run(without_one_edge, "stale-review", bounds)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)
        self.assertEqual(self.cycle(run_dir, self.start(run_dir), assessment("none"))["status"], "complete")
        inherited = file_digest(self.base / "stale-review-inherited.json")
        shell = {key: self.final_review(run_dir)[key] for key in ("interface", "action", "stage", "action_id")}
        for label, review, expected in (
                ("identity fields only", shell, "candidate.output_sha256"),
                ("the inherited candidate's assessment", self.final_review(
                    run_dir, candidate={"output_sha256": inherited, "disposition": "unchanged"}), "final candidate"),
                ("no source status", self.final_review(run_dir, coverage={}), "coverage.source_review_status")):
            with self.subTest(label):
                path = self.base / "review-under-test.json"
                path.write_text(json.dumps(review))
                done = run("finish", "--run", str(run_dir), "--review", str(path))
                self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
                self.assertIn(expected, done.stderr)
                self.assertFalse((run_dir / "result.json").exists())
        path.write_text(json.dumps(self.final_review(run_dir, candidate={
            "output_sha256": file_digest(run_dir / "plan.json"), "disposition": "changed"})))
        self.assertEqual(run("finish", "--run", str(run_dir), "--review", str(path)).returncode, 0)

    def test_a_source_aware_run_returns_plan_and_review(self):
        """F5: a source-aware result is {plan, review} with review.convergence, built from the caller's own review."""
        bounds = {"provisional_step_ids": [], "provisional_edge_keys": [], "allow_new_steps": False,
                  "allow_new_edges": False, "protected_step_ids": [], "protected_edge_keys": [], "protected_facts": [],
                  "running_or_completed_step_ids": []}
        run_dir, frozen = self.caller_run(lambda plan: plan, "source-aware", bounds)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)
        self.assertEqual(self.cycle(run_dir, self.start(run_dir), assessment("none"))["status"], "complete")
        missing = run("finish", "--run", str(run_dir))
        self.assertEqual(missing.returncode, 3)
        self.assertIn("--review", missing.stderr)
        review = self.base / "final-review.json"
        review.write_text(json.dumps(self.final_review(run_dir)))
        finished = run("finish", "--run", str(run_dir), "--review", str(review))
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(result), ["plan", "review", "status", "structure"])
        self.assertEqual(result["review"]["convergence"]["terminal_receipt"]["status"], "complete")
        self.assertEqual(result["review"]["candidate"]["output_sha256"], file_digest(run_dir / "plan.json"))
        self.assertEqual(result["review"]["coverage"]["structural_plan_status"], "valid")
        self.assertEqual(result["review"]["coverage"]["source_review_status"], "complete")

    def test_the_contract_grants_only_the_callers_authority(self):
        """F8: the contract forbids what 0.6.6 forbade, not network access or contact a request may authorize."""
        contract = json.loads((self.frozen() / "loop/contract.json").read_text(encoding="utf-8"))
        authority = contract["context"]["authority"]
        for kept in ("commit", "push", "merge", "project execution", "broadened scope"):
            self.assertIn(kept, authority)
        for dropped in ("network", "contact", "installation"):
            self.assertNotIn(dropped, authority)

    def test_the_gate_texts_are_the_convergence_references(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("backchain_cli", CLI)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        # Owner decision D1 (2026-11-01): the default gate is the first trivial review.
        self.assertEqual(cli.GATES, {"default": 1, "one": 0, "converge": 2})
        reference = " ".join((ROOT / "skills/backchain/references/convergence.md").read_text(encoding="utf-8").split())
        # ShipLoop's plan packet prints the one-pass text; test/shiploop-navigator-contract.test.py pins it there.
        self.assertIn("this exit condition: " + cli.EXIT_CONDITIONS["one"], reference)
        for passes in ("default", "converge"):
            with self.subTest(passes):
                self.assertIn("Its exit condition: " + cli.EXIT_CONDITIONS[passes], reference)


class LensTests(unittest.TestCase):
    def test_every_card_parses_and_only_the_named_cards_print(self):
        done = run("lenses", "T07", "35", "t07")
        self.assertEqual(done.returncode, 0, done.stderr)
        headings = [line for line in done.stdout.splitlines() if line.startswith("## T")]
        self.assertEqual([heading.split(" — ")[0] for heading in headings], ["## T07", "## T35"])
        cards = (ROOT / "skills/backchain/references/technical-lens-cards.md").read_text(encoding="utf-8")
        self.assertIn(done.stdout.split("\n## T35")[0].rstrip(), cards)
        index = (ROOT / "skills/backchain/references/technical-lenses.md").read_text(encoding="utf-8")
        every = run("lenses", *[f"T{n:02d}" for n in range(1, 43)])
        self.assertEqual(every.returncode, 0, every.stderr)
        self.assertEqual(sum(line.startswith("## T") for line in every.stdout.splitlines()), 42)
        self.assertEqual(sum(f"| T{n:02d} |" in index for n in range(1, 43)), 42)

    def test_an_unknown_card_could_not_run(self):
        done = run("lenses", "T99")
        self.assertEqual((done.returncode, done.stdout), (3, ""))
        self.assertIn("no lens card T99; the cards are T01 to T42", done.stderr)


if __name__ == "__main__":
    unittest.main()
