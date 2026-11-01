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
    """The convergence review prompt's JSON, as a cycle saves it."""
    return {"candidate_identity": "inspected", "context_identity": "inspected", "change_class": change_class,
            "findings": list(findings), "checks": ["traced every outcome backward; screened every lens category"],
            "planning_gaps": list(gaps), "execution_blockers": list(blockers)}


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
        return run_dir

    def start(self, run_dir: Path) -> dict:
        with open(run_dir / "loop/contract.json", "rb") as contract:
            started = subprocess.run([sys.executable, "-B", str(LOOP_RUNTIME), "start", "--receipt",
                                      str(run_dir / "loop/receipt.json")], stdin=contract, capture_output=True,
                                     text=True, timeout=60)
        self.assertEqual(started.returncode, 0, started.stderr)
        return json.loads(started.stdout)

    def record(self, run_dir: Path, review: dict, exit_assessment="satisfied", continuation="allowed"):
        self.reviews += 1
        path = self.base / f"assessment-{self.reviews}.json"
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
