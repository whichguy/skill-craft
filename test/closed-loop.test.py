#!/usr/bin/env python3
"""closed-loop: the orchestrator (skills/closed-loop/scripts/closed_loop.py) against a fake subject, and against the real Until Loop.

The fake subject (test/fixtures/closed-loop-fake/adapter.py) has three planted defects in three styles of case, a scripted improver
and an idempotent step protocol, so every property here is deterministic and no model is called. The classes follow the plan
(docs/closed-loop-plan-2026-11-15.md) and the Astra max review of the first build (docs/experiments/closed-loop-review-20261115/):
manifest and execution boundary, readiness as script-proven claims, the gates that stop anything running before the owner has
ratified the boundary, state that is never silently recreated or silently trusted, evidence that is validated before it can count,
the seven-check convergence certificate and its incomplete outcome, the escalation demo (converge, widen on an uncovered style, find
what only the new case exposes, stop on an owner-only rung), duplicate resume, an aggregate quota that charges failures and hangs,
campaign isolation, and an emitted contract that the vendored Until Loop runtime accepts, completes on the script-owned certificate
and refuses to complete on a failing or stale check.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import state_home

state_home.isolate()
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "closed-loop"
SCRIPT = SKILL / "scripts" / "closed_loop.py"
FAKE = ROOT / "test" / "fixtures" / "closed-loop-fake" / "adapter.py"
RUNTIME = ROOT / "skills" / "improve" / "runtime" / "until-loop" / "scripts" / "until_loop_ephemeral.py"
_spec = importlib.util.spec_from_file_location("closed_loop", SCRIPT)
cl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cl)
DEFAULT_BUDGET = "seconds=100000,turns=100000"
START_CLAIMS = {"cases.runs:A1": {"effect": "effectful"}, "grading.scores": {"effect": "effectful"},
                "improver.bounded": {"effect": "effectful"}}  # the three the start rule needs: most tests need nothing more
FULL_CLAIMS = {**START_CLAIMS, "grading.sensitive:d1": {"effect": "effectful"}, "grading.calibrated:fake": {"effect": "read-only"},
               "improver.invocable": {"effect": "effectful"}}
SH = {"shell": True, "executable": "/bin/sh", "capture_output": True, "text": True}


def tree_digest(folder: Path) -> dict:
    """Relative path -> content hash of every file under folder, ignoring Git's own folder."""
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.rglob("*")) if path.is_file() and ".git" not in path.relative_to(folder).parts}


class Lab:
    """A throwaway campaign: a workspace, a manifest over the fake subject, and helpers that drive the orchestrator in process."""

    def __init__(self, case: unittest.TestCase, timeout: float = 60, **overrides) -> None:
        self.case = case
        self.tmp = Path(tempfile.mkdtemp(prefix="closed-loop-test-")).resolve()  # resolved: Until Loop refuses a /var symlink
        case.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = self.tmp / "ws"
        self.ws.mkdir()
        self.adapter = self.tmp / "adapter.py"  # a copy, so a test can edit the pinned adapter
        shutil.copy(FAKE, self.adapter)
        self.campaign = self.tmp / "campaign"
        self.work = self.tmp / "campaign.work"
        self.manifest_path = self.tmp / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest(self.adapter, timeout, **overrides), indent=2))

    @staticmethod
    def manifest(adapter=FAKE, timeout: float = 60, **overrides) -> dict:
        commands = {verb: [sys.executable, str(adapter), verb] for verb in ("cases", "records", "identity", "probe")}
        commands["step"] = [sys.executable, str(adapter), "step"]
        base = {
            "contract": "closed-loop-adapter/1", "subject": {"name": "fake", "mission": ["planted defects d1 to d3"]},
            "execution": {"cwd": ".", "env_allow": [], "capability": "writes-worktree", "timeout_seconds": timeout,
                          "cleanup": [sys.executable, str(adapter), "cleanup"], "pin": [str(adapter)]},
            "commands": commands,
            "claims": dict(START_CLAIMS),
            "dimensions": ["style"], "quiet_window": 2, "evaluation_class": "scripted",
            "authority": {"routine": ["run cases", "investigate"], "owner_only": ["hosted cases"],
                          "owner_only_requires": ["hosted"]}}
        base.update(overrides)
        return base

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cl.main([str(item) for item in argv])
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def ok(self, *argv):
        code, out, err = self.cli(*argv)
        self.case.assertEqual(code, 0, f"{argv} -> {code} {err}")
        return out

    def init(self, cases="A1", *extra, ready=True, campaign=None):
        target = campaign or self.campaign
        args = ["init", "--manifest", self.manifest_path, "--campaign", target, "--workspace", self.ws, "--cases", cases]
        if "--budget" not in extra:
            args += ["--budget", DEFAULT_BUDGET]
        out = self.ok(*args, *extra)
        if ready:
            self.ready(target)
        return out

    def ready(self, campaign=None):
        """What the owner and the operator do before anything runs: ratify the boundary, then show the start rule."""
        target = campaign or self.campaign
        self.ok("ratify", "--campaign", target, "--yes-owner-approved", "--note", "test boundary")
        return self.ok("readiness", "--manifest", self.manifest_path, "--campaign", target, "--require-start")

    def config(self, **updates) -> None:
        path = self.ws / "fake-config.json"
        current = json.loads(path.read_text()) if path.is_file() else {}
        current.update(updates)
        path.write_text(json.dumps(current))

    def state(self) -> dict:
        return json.loads((self.campaign / "campaign.json").read_text())

    def write_state(self, state: dict) -> None:
        (self.campaign / "campaign.json").write_text(json.dumps(state))

    def step(self, campaign=None):
        return self.ok("step", "--campaign", campaign or self.campaign)

    def run(self, limit=60) -> list:
        """Step until the orchestrator stops or hands the operator a task; return every action taken."""
        actions = []
        for _ in range(limit):
            actions.append(self.step())
            if actions[-1]["action"] in ("stop", "task"):
                return actions
        raise AssertionError("the campaign did not stop within the limit")

    def certificate(self) -> dict:
        return self.cli("certificate", "--campaign", self.campaign)[1]

    def check(self, clause: str, *extra):
        return self.cli("check", "--campaign", self.campaign, "--clause", clause, *extra)

    def starts(self) -> list:
        path = self.ws / "fake-starts.log"
        return path.read_text().split() if path.is_file() else []


CATALOG_AB = [{"id": case, "dimensions": {"a": first, "b": second}, "cost": 1, "requires": [], "hosted": False}
              for case, first, second in (("AX", "A", "X"), ("BY", "B", "Y"), ("AY", "A", "Y"))]
STDLIB_IMPORTS = {"__future__", "argparse", "contextlib", "datetime", "fcntl", "hashlib", "json", "math", "os", "pathlib", "posixpath",
                  "secrets", "shlex", "signal", "subprocess", "sys", "time"}  # a new import of the orchestrator is a deliberate edit of this set


def good_facts(cases, build_before="b0", build_after="b0") -> dict:
    return {
        "build_before": build_before, "build_after": build_after, "scoring": "score-1",
        "cases": {case: {"ran": True, "floors_met": True, "baseline": "comparable"} for case in cases},
        "review": {"valid": True, "complete": True}, "judge": {"valid": True, "complete": True}, "discoveries": [],
        "candidate": None, "invalid": [], "cleanup": {"verified": True, "receipt": "r"},
        "tier": {"green": True, "build": build_after}, "acceptance": None, "consumed": {"seconds": 1}}


class ManifestTests(unittest.TestCase):
    def test_a_valid_manifest_passes_and_reports_its_boundary(self):
        lab = Lab(self)
        out = lab.ok("adapter-check", "--manifest", lab.manifest_path)
        self.assertTrue(out["ok"])
        self.assertEqual(cl.validate_manifest(Lab.manifest()), [])
        self.assertEqual(len(out["boundary_sha256"]), 64)

    def test_shell_strings_and_whitespace_programs_are_refused(self):
        bad = Lab.manifest()
        bad["commands"]["cases"] = "python3 adapter.py cases"
        self.assertTrue(any("argument list" in error for error in cl.validate_manifest(bad)))
        bad["commands"]["cases"] = ["python3 adapter.py", "cases"]
        self.assertTrue(any("whitespace" in error for error in cl.validate_manifest(bad)))

    def test_the_execution_boundary_and_verbs_are_required_and_known(self):
        bad = Lab.manifest()
        del bad["commands"]["identity"]
        bad["commands"]["shell"] = ["sh", "-c", "true"]
        bad["execution"]["capability"] = "root"
        errors = " | ".join(cl.validate_manifest(bad))
        self.assertIn("commands.identity is required", errors)
        self.assertIn("commands.shell is not a known verb", errors)
        self.assertIn("execution.capability must be one of", errors)

    def test_a_judge_only_evaluation_needs_its_reliability_recorded(self):
        bad = Lab.manifest(evaluation_class="judge-only")
        self.assertTrue(any("judge_reliability" in error for error in cl.validate_manifest(bad)))
        good = Lab.manifest(evaluation_class="judge-only", judge_reliability={"kappa": 0.8})
        self.assertEqual(cl.validate_manifest(good), [])

    def test_the_timeout_pins_window_and_combinations_are_validated(self):
        for field, value, expected in (("timeout", 0, "timeout_seconds"), ("pin", "adapter.py", "execution.pin"),
                                       ("quiet_window", 0, "quiet_window"), ("quiet_window", True, "quiet_window"),
                                       ("combinations", [["style", "nope"]], "combinations")):
            manifest = Lab.manifest()
            if field == "timeout":
                manifest["execution"]["timeout_seconds"] = value
            elif field == "pin":
                manifest["execution"]["pin"] = value
            else:
                manifest[field] = value
            self.assertTrue(any(expected in error for error in cl.validate_manifest(manifest)), (field, value))

    def test_the_boundary_hash_follows_commands_authority_and_pinned_files_not_descriptive_text(self):
        pinned = Path(tempfile.mkdtemp(prefix="closed-loop-pin-"))
        self.addCleanup(shutil.rmtree, pinned, True)
        (pinned / "grader.py").write_text("print('v1')\n")
        base = Lab.manifest()
        base["execution"]["pin"] = [str(pinned / "grader.py")]
        before = cl.boundary_hash(base, ROOT)
        changed = json.loads(json.dumps(base))
        changed["commands"]["cases"] = [sys.executable, str(FAKE), "cases", "--extra"]
        wider = json.loads(json.dumps(base))
        wider["authority"]["owner_only_requires"] = []
        reworded = json.loads(json.dumps(base))
        reworded["subject"]["mission"] = ["something else entirely"]
        self.assertNotEqual(before, cl.boundary_hash(changed, ROOT))
        self.assertNotEqual(before, cl.boundary_hash(wider, ROOT))
        self.assertEqual(before, cl.boundary_hash(reworded, ROOT))
        (pinned / "grader.py").write_text("print('v2')\n")  # the evaluator changed under an unchanged manifest
        self.assertNotEqual(before, cl.boundary_hash(base, ROOT))
        (pinned / "grader.py").unlink()
        with self.assertRaisesRegex(cl.LoopError, "does not exist"):
            cl.boundary_hash(base, ROOT)

    def test_a_manifest_changed_after_init_is_refused(self):
        lab = Lab(self)
        lab.init()
        lab.manifest_path.write_text(json.dumps(Lab.manifest(lab.adapter, quiet_window=3)))
        code, _, err = lab.cli("status", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("changed since init", err)

    def test_a_pinned_adapter_file_changed_after_init_is_refused_even_though_the_manifest_is_not(self):
        lab = Lab(self)
        lab.init()
        lab.adapter.write_text(lab.adapter.read_text() + "\n# an edit after the owner ratified the boundary\n")
        for verb in ("status", "step", "certificate"):
            code, _, err = lab.cli(verb, "--campaign", lab.campaign)
            self.assertEqual(code, cl.EXIT_ERROR, verb)
            self.assertIn("changed since init", err)
        self.assertEqual(lab.starts(), [])

    def test_the_adapter_runs_in_a_controlled_environment(self):
        script = ("import json, os; print(json.dumps({'visible': os.environ.get('CL_TEST_VISIBLE'), "
                  "'hidden': os.environ.get('CL_TEST_HIDDEN'), 'workspace': os.environ.get('CLOSED_LOOP_WORKSPACE')}))")
        manifest = Lab.manifest()
        manifest["execution"]["env_allow"] = ["CL_TEST_VISIBLE"]
        manifest["commands"]["identity"] = [sys.executable, "-c", script]
        with mock.patch.dict(os.environ, {"CL_TEST_VISIBLE": "yes", "CL_TEST_HIDDEN": "no"}):
            out = cl.call_adapter(manifest, ROOT, "identity", workspace="/somewhere")
        self.assertEqual(out, {"visible": "yes", "hidden": None, "workspace": "/somewhere"})

    def test_adapter_failures_are_loud_errors_never_silently_empty(self):
        manifest = Lab.manifest()
        for code, expected in (("print('not json')", "printed no JSON object"), ("print('[1]')", "must print a JSON object"),
                               ("import sys; sys.exit(3)", "exited 3"), ("raise SystemExit('boom')", "exited 1")):
            manifest["commands"]["identity"] = [sys.executable, "-c", code]
            with self.assertRaisesRegex(cl.LoopError, expected):
                cl.call_adapter(manifest, ROOT, "identity")
        manifest["commands"]["identity"] = ["/no/such/program"]
        with self.assertRaisesRegex(cl.LoopError, "could not start"):
            cl.call_adapter(manifest, ROOT, "identity")


class AdapterProcessTests(unittest.TestCase):
    """What the orchestrator does to the programs it calls: close their input, bound them, and kill what a timeout leaves behind."""

    @staticmethod
    def manifest(code: str, *args, timeout=2) -> dict:
        manifest = Lab.manifest()
        manifest["execution"]["timeout_seconds"] = timeout
        manifest["commands"]["identity"] = [sys.executable, "-c", code, *args]
        return manifest

    @staticmethod
    def alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def reap_later(self, pid: int) -> None:
        def kill():
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, 9)
        self.addCleanup(kill)

    def test_a_timeout_kills_the_whole_process_group_and_returns_on_time(self):
        folder = Path(tempfile.mkdtemp(prefix="closed-loop-pid-"))
        self.addCleanup(shutil.rmtree, folder, True)
        code = ("import pathlib, subprocess, sys, time\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"  # holds the output pipe
                "pathlib.Path(sys.argv[1]).write_text(str(child.pid))\n"
                "time.sleep(60)\n")
        started = time.monotonic()
        with self.assertRaisesRegex(cl.LoopError, "did not finish within 2 s.*process group was killed"):
            cl.call_adapter(self.manifest(code, str(folder / "pid")), ROOT, "identity")
        self.assertLess(time.monotonic() - started, 20)  # subprocess.run would have waited for the grandchild's 60 s
        grandchild = int((folder / "pid").read_text())
        self.reap_later(grandchild)
        deadline = time.monotonic() + 5
        while self.alive(grandchild) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(self.alive(grandchild))

    def test_a_launcher_that_detaches_its_run_returns_at_once_and_the_run_survives(self):
        code = ("import json, subprocess, sys\n"
                "run = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], stdin=subprocess.DEVNULL,\n"
                "                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)\n"
                "print(json.dumps({'pid': run.pid}))\n")
        out = cl.call_adapter(self.manifest(code, timeout=15), ROOT, "identity")
        self.reap_later(out["pid"])
        self.assertTrue(self.alive(out["pid"]))

    def test_an_adapter_reads_an_empty_standard_input(self):
        out = cl.call_adapter(self.manifest("import json, sys; print(json.dumps({'stdin': sys.stdin.read()}))"), ROOT, "identity")
        self.assertEqual(out, {"stdin": ""})


class ProposalTests(unittest.TestCase):
    """A definer's proposal is validated by a script: its shape, its evidence, and that no grader is in the improver's candidate set."""

    @staticmethod
    def proposal(**changes) -> dict:
        slots = {name: {"status": "proposed", "evidence": ["README.md:1"], "value": value} for name, value in (
            ("mission", ["a clause a reviewer can cite"]), ("cases", [{"id": "A1"}]), ("steps", {"start": ["true"]}),
            ("evaluation", {"evaluation_class": "scripted"}), ("improvement", None),
            ("authority", {"routine": [], "owner_only": ["hosted"], "owner_only_requires": ["hosted"]}),
            ("records", {"ledger": "records.jsonl"}))}
        slots["improvement"]["value"] = {"candidate_paths": ["skills/x/"], "withheld_paths": ["held/"],
                                         "evaluator_paths": ["graders/", "adapter.json"], "verify": ["true"]}
        base = {"contract": "closed-loop-definer/1", "slots": slots, "risks": [], "needs_owner": [], "unknowns": []}
        base.update(changes)
        return base

    def test_a_well_formed_proposal_passes_adapter_check_and_lists_its_unknown_slots(self):
        lab = Lab(self)
        proposal = self.proposal()
        proposal["slots"]["records"] = {"status": "unknown", "evidence": [], "value": None}  # unknown needs no value
        path = lab.tmp / "definer-proposal.json"
        path.write_text(json.dumps(proposal))
        out = lab.ok("adapter-check", "--manifest", lab.manifest_path, "--proposal", path)
        self.assertEqual(out["proposal"], {"ok": True, "unknown_slots": ["records"]})

    def test_a_grader_or_withheld_path_among_the_candidate_paths_is_refused(self):
        for candidate in ("graders/", "graders/score.py", "adapter.json", "held/notes.md", "./graders", "skills/../graders", ".", ""):
            proposal = self.proposal()
            proposal["slots"]["improvement"]["value"]["candidate_paths"] = [candidate]
            errors = cl.validate_proposal(proposal)
            self.assertTrue(any("overlaps an evaluator or withheld path" in error for error in errors), candidate)
        proposal = self.proposal()
        proposal["slots"]["improvement"]["value"]["candidate_paths"] = ["skills/x/", "graders-notes/", "docs"]
        self.assertEqual(cl.validate_proposal(proposal), [])  # a shared name prefix is not overlap

    def test_paths_must_be_relative_to_the_subject_root_and_stay_inside_it(self):
        for candidate in ("/", "/abs/graders", "../outside", "a/../../b"):
            proposal = self.proposal()
            proposal["slots"]["improvement"]["value"]["candidate_paths"] = [candidate]
            self.assertTrue(any("relative to the subject's root" in error for error in cl.validate_proposal(proposal)), candidate)
        proposal = self.proposal()
        proposal["slots"]["improvement"]["value"]["evaluator_paths"] = ["/etc/graders"]
        self.assertTrue(any("relative to the subject's root" in error for error in cl.validate_proposal(proposal)))

    def test_found_and_proposed_slots_need_nonblank_evidence_and_a_typed_value(self):
        for slot, change, expected in (("cases", {"evidence": [None]}, "evidence must be a list of non-blank text"),
                                       ("cases", {"evidence": [" "]}, "evidence must be a list of non-blank text"),
                                       ("cases", {"status": "found", "evidence": []}, "found without evidence"),
                                       ("steps", {"value": {}}, "non-empty dict"), ("steps", {"value": None}, "non-empty dict"),
                                       ("cases", {"value": "A1"}, "non-empty list"), ("mission", {"value": []}, "non-empty list")):
            proposal = self.proposal()
            proposal["slots"][slot].update(change)
            self.assertTrue(any(expected in error for error in cl.validate_proposal(proposal)), (slot, change))

    def test_a_proposal_is_reconciled_with_the_manifest_the_owner_ratifies(self):
        manifest = Lab.manifest()
        self.assertEqual(cl.validate_proposal(self.proposal(), manifest), [])
        wrong_class = self.proposal()
        wrong_class["slots"]["evaluation"]["value"]["evaluation_class"] = "judge-only"
        self.assertTrue(any("evaluation_class is not the manifest's" in e for e in cl.validate_proposal(wrong_class, manifest)))
        wrong_gate = self.proposal()
        wrong_gate["slots"]["authority"]["value"]["owner_only_requires"] = []
        self.assertTrue(any("owner_only_requires is not the manifest's" in e for e in cl.validate_proposal(wrong_gate, manifest)))
        hosted = Lab.manifest()
        hosted["execution"]["capability"] = "hosted"
        self.assertTrue(any("needs_owner" in e for e in cl.validate_proposal(self.proposal(), hosted)))
        self.assertEqual(cl.validate_proposal(self.proposal(needs_owner=["deploys to the owner's org"]), hosted), [])

    def test_a_malformed_proposal_is_refused_with_its_reasons(self):
        self.assertTrue(cl.validate_proposal("text"))
        self.assertTrue(cl.validate_proposal(self.proposal(contract="other/1")))
        missing = self.proposal()
        del missing["slots"]["steps"]
        self.assertIn("slots must be exactly", cl.validate_proposal(missing)[0])
        bad_status = self.proposal()
        bad_status["slots"]["cases"]["status"] = "guessed"
        self.assertTrue(any("slot cases needs a status" in error for error in cl.validate_proposal(bad_status)))
        no_evidence = self.proposal()
        no_evidence["slots"]["cases"] = {"status": "found", "evidence": [], "value": []}
        self.assertTrue(any("found without evidence" in error for error in cl.validate_proposal(no_evidence)))
        self.assertTrue(any("risks must be a list" in error for error in cl.validate_proposal(self.proposal(risks="none"))))
        lab = Lab(self)
        path = lab.tmp / "bad.json"
        path.write_text(json.dumps(self.proposal(contract="other/1")))
        code, _, err = lab.cli("adapter-check", "--manifest", lab.manifest_path, "--proposal", path)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("invalid definer proposal", err)
        code, _, err = lab.cli("adapter-check", "--manifest", lab.manifest_path, "--proposal", lab.tmp / "missing.json")
        self.assertIn("cannot read the proposal", err)


class ReadinessTests(unittest.TestCase):
    def test_effectful_claims_are_not_probed_until_the_owner_ratifies(self):
        lab = Lab(self, claims=FULL_CLAIMS)
        lab.init(ready=False)
        before = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertFalse(before["start_ok"])
        self.assertEqual(before["claims"]["cases.runs:A1"]["state"], "declared")
        self.assertIn("not run", before["claims"]["cases.runs:A1"]["evidence"])
        self.assertEqual(before["claims"]["grading.calibrated:fake"]["state"], "unmeasured")  # read-only: probed
        self.assertEqual(lab.starts(), [])

    def test_ratification_is_the_owners_act(self):
        lab = Lab(self)
        lab.init(ready=False)
        code, _, err = lab.cli("ratify", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("owner's decision", err)
        self.assertIsNone(lab.state()["ratification"])
        out = lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved", "--note", "boundary read")
        self.assertEqual(out["ratified"]["boundary_sha256"], cl.boundary_hash(Lab.manifest(lab.adapter), lab.tmp))

    def test_after_ratification_claims_are_proven_say_what_they_allow_and_are_recorded(self):
        lab = Lab(self, claims=FULL_CLAIMS)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        report = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--require-start")
        self.assertTrue(report["start_ok"])
        self.assertEqual(report["claims"]["cases.runs:A1"]["state"], "runs")
        self.assertEqual(report["claims"]["grading.scores"]["state"], "scores")
        self.assertEqual(report["claims"]["improver.invocable"]["state"], "invocable")
        allowed = " | ".join(report["allowed_claims"])
        self.assertIn("labelled 'stated, not measured'", allowed)
        self.assertIn("no quality claim is allowed yet", allowed)  # the oracle scores but is not shown sensitive
        self.assertIn("plumbing only", report["note"])
        recorded = lab.state()["readiness"]  # persisted: the start gate, the certificate and the report read it
        self.assertTrue(recorded["start_ok"])
        self.assertEqual(recorded["boundary_sha256"], report["boundary_sha256"])
        self.assertEqual(recorded["allowed_claims"], report["allowed_claims"])

    def test_sensitivity_and_calibration_unlock_the_claims_they_prove(self):
        lab = Lab(self, claims=FULL_CLAIMS)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(sensitive={"d1": True}, calibrated={"fake": True})
        report = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        allowed = " | ".join(report["allowed_claims"])
        self.assertIn("quality claims about d1", allowed)
        self.assertIn("measured efficiency on profile fake", allowed)

    def test_an_insensitive_evaluator_scores_but_is_not_sensitive_and_a_missing_bound_blocks_the_start(self):
        lab = Lab(self, claims=FULL_CLAIMS)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(bounded=False)
        code, report, _ = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--require-start")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertEqual(report["claims"]["grading.scores"]["state"], "scores")  # valid scores, not "declared"
        self.assertEqual(report["claims"]["grading.sensitive:d1"]["state"], "unknown")
        self.assertIn("no improver.bounded claim has reached 'bounded'", report["blocked"])

    def test_a_proven_claim_without_evidence_is_refused(self):
        lab = Lab(self)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(probe_no_evidence=True)
        code, _, err = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("without evidence", err)
        self.assertIsNone(lab.state()["readiness"])  # nothing was recorded on a probe that showed nothing

    def test_quality_claims_are_withdrawn_when_the_evaluator_changes_until_readiness_is_rerun(self):
        lab = Lab(self, claims=FULL_CLAIMS)
        lab.config(sensitive={"d1": True})
        lab.init("A1")
        for _ in range(3):
            lab.step()
        self.assertIn("quality claims about d1", " ".join(lab.certificate()["claims"]["allowed"]))
        recorded = lab.state()["readiness"]
        self.assertEqual(recorded["scoring"], "score-1")
        self.assertEqual(recorded["claims"]["grading.sensitive:d1"]["state"], "sensitive")
        self.assertIn("seeded defect", recorded["claims"]["grading.sensitive:d1"]["evidence"])  # the evidence is kept
        lab.config(scoring="score-2", sensitive={})  # the evaluator changed, and sensitivity is no longer shown
        lab.step()
        lab.step()  # two fresh quiet iterations under the new evaluator
        cert = lab.certificate()
        self.assertEqual(cert["status"], "converged", cert["reasons"])
        self.assertEqual(cert["claims"]["allowed"], [])
        self.assertIn("proven under scoring identity 'score-1'", cert["claims"]["note"])
        self.assertEqual(lab.ok("report", "--campaign", lab.campaign)["allowed_claims"], [])
        lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        again = lab.certificate()["claims"]
        self.assertEqual(lab.state()["readiness"]["scoring"], "score-2")
        self.assertIn("no quality claim is allowed yet", " ".join(again["allowed"]))

    def test_a_later_failing_readiness_keeps_a_converged_scope_incomplete_and_blocks_the_next_start(self):
        lab = Lab(self)
        lab.init("A1")
        for _ in range(3):
            lab.step()
        self.assertEqual(lab.certificate()["status"], "converged")
        lab.config(bounded=False)  # the improvement stage is no longer shown to be bounded
        lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        cert = lab.certificate()
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any("latest readiness does not show the start rule" in reason for reason in cert["reasons"]))
        code, out, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual((code, out["action"]), (cl.EXIT_NOT_READY, "blocked"))

    def test_a_probe_state_outside_the_claims_ladder_is_refused(self):
        manifest = Lab.manifest()
        with mock.patch.object(cl, "call_adapter", return_value={"state": "magnificent"}), \
                self.assertRaisesRegex(cl.LoopError, "allowed: declared, runs"):
            cl.claim_states(dict(manifest, claims={"cases.runs:A1": {"effect": "read-only"}}), ROOT, None, None, True)

    def test_a_manifest_without_the_three_start_claims_cannot_start(self):
        none = Lab(self, claims={})
        report = none.ok("readiness", "--manifest", none.manifest_path)
        self.assertFalse(report["start_ok"])
        self.assertEqual(len(report["blocked"]), 3)
        one = Lab(self, claims={"cases.runs:A1": {"effect": "read-only"}})  # a read-only claim is probed without ratification
        report = one.ok("readiness", "--manifest", one.manifest_path)
        self.assertEqual(report["claims"]["cases.runs:A1"]["state"], "runs")
        self.assertEqual(report["blocked"], ["no grading.scores claim has reached 'scores'",
                                             "no improver.bounded claim has reached 'bounded'"])


class GateTests(unittest.TestCase):
    """Nothing runs before the owner has ratified the boundary, readiness has shown the start rule and every case is authorized."""

    def test_nothing_starts_before_the_owner_ratifies_the_boundary(self):
        lab = Lab(self)
        lab.init(ready=False)
        code, out, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual((code, out["action"]), (cl.EXIT_NOT_READY, "blocked"))
        self.assertIn("not ratified", out["reason"])
        self.assertEqual(lab.starts(), [])
        self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["action"], "blocked")

    def test_ratification_alone_is_not_readiness(self):
        lab = Lab(self)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        code, out, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertIn("readiness has not shown the start rule", out["reason"])
        self.assertEqual(lab.starts(), [])

    def test_readiness_that_fails_the_start_rule_blocks_the_start(self):
        lab = Lab(self)
        lab.init(ready=False)
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(bounded=False)
        lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)  # recorded, though it does not pass
        code, out, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertIn("readiness has not shown the start rule", out["reason"])
        self.assertEqual(lab.starts(), [])

    def test_an_owner_gated_case_cannot_be_in_the_first_scope_without_the_owner(self):
        lab = Lab(self)
        code, _, err = lab.cli("init", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--workspace", lab.ws,
                               "--cases", "C1", "--budget", DEFAULT_BUDGET)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("owner-gated cases need --approve-case", err)
        code, _, err = lab.cli("init", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--workspace", lab.ws,
                               "--cases", "C1", "--budget", DEFAULT_BUDGET, "--approve-case", "C1")
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("owner's decision", err)
        self.assertFalse((lab.campaign / "campaign.json").exists())
        lab.init("C1", "--approve-case", "C1", "--yes-owner-approved")
        self.assertEqual(lab.step()["action"], "start")  # the owner released the hosted case, so it runs
        self.assertEqual(len(lab.starts()), 1)

    def test_cleanup_is_an_adapter_command_so_it_waits_for_the_owner_and_never_runs_for_an_empty_set(self):
        lab = Lab(self)
        lab.init(ready=False)
        code, _, err = lab.cli("cleanup", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("has not ratified", err)
        self.assertFalse((lab.ws / "fake-cleanups.log").exists())  # the adapter's cleanup command was never run
        lab.ready()
        out = lab.ok("cleanup", "--campaign", lab.campaign)
        self.assertEqual((out["covered"], out["receipt"]), ([], None))
        self.assertFalse((lab.ws / "fake-cleanups.log").exists())  # ratified, but no run lacks evidence: still not run

    def test_a_changed_boundary_after_ratification_runs_nothing(self):
        lab = Lab(self)
        lab.init()
        lab.adapter.write_text(lab.adapter.read_text() + "\n# widened\n")
        code, _, err = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("changed since init", err)
        self.assertEqual(lab.starts(), [])


class StateTests(unittest.TestCase):
    def test_missing_state_is_an_error_and_is_never_recreated(self):
        lab = Lab(self)
        for verb in ("status", "step", "certificate", "report"):
            code, _, err = lab.cli(verb, "--campaign", lab.campaign)
            self.assertEqual(code, cl.EXIT_ERROR, verb)
            self.assertIn("run init", err)
        self.assertFalse(lab.campaign.exists())  # no verb but init creates a campaign folder

    def test_corrupt_state_is_refused_and_left_untouched(self):
        lab = Lab(self)
        lab.init()
        (lab.campaign / "campaign.json").write_text("{not json")
        code, _, err = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("unreadable", err)
        self.assertEqual((lab.campaign / "campaign.json").read_text(), "{not json")

    def test_a_file_of_another_schema_is_refused(self):
        lab = Lab(self)
        lab.init()
        (lab.campaign / "campaign.json").write_text(json.dumps({"schema": "something-else/1"}))
        code, _, err = lab.cli("status", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("is not a closed-loop-campaign/1 file", err)

    def test_deeply_malformed_state_is_a_json_error_never_a_traceback(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        good = lab.state()
        breakers = {"an iteration that is not an object": lambda s: s.update(iterations=[1]),
                    "an empty budget": lambda s: s.update(budget={}),
                    "a negative quiet window": lambda s: s.update(quiet_window=-1),
                    "steps as a list": lambda s: s.update(steps=[]),
                    "a missing scope": lambda s: s.update(scope="S9"),
                    "an iteration without cases": lambda s: s["iterations"][0].pop("cases"),
                    "a non-numeric consumption": lambda s: s.update(consumed={"seconds": "ten"})}
        for name, breaker in breakers.items():
            state = json.loads(json.dumps(good))
            breaker(state)
            lab.write_state(state)
            done = subprocess.run([sys.executable, str(SCRIPT), "status", "--campaign", str(lab.campaign)], capture_output=True,
                                  text=True, check=False)
            self.assertEqual(done.returncode, cl.EXIT_ERROR, name)
            self.assertNotIn("Traceback", done.stderr, name)
            self.assertIn("malformed", json.loads(done.stderr)["error"], name)

    def test_init_never_reinitialises_in_place_and_validates_its_inputs(self):
        lab = Lab(self)
        lab.init()
        code, _, err = lab.cli("init", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--workspace", lab.ws,
                               "--cases", "A1", "--budget", DEFAULT_BUDGET)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("already exists", err)
        other = Lab(self)
        base = ["init", "--manifest", other.manifest_path, "--campaign", other.campaign, "--workspace", other.ws]
        for extra, expected in ((["--cases", "A9", "--budget", DEFAULT_BUDGET], "not in the adapter's catalog"),
                                (["--cases", "", "--budget", DEFAULT_BUDGET], "needs at least one case"),
                                (["--cases", "A1"], "needs a budget"),
                                (["--cases", "A1", "--budget", "seconds=0"], "positive amount"),
                                (["--cases", "A1", "--budget", DEFAULT_BUDGET, "--quiet-window", "0"], "at least 1"),
                                (["--cases", "A1", "--budget", DEFAULT_BUDGET, "--quiet-window", "-1"], "at least 1")):
            code, _, err = other.cli(*base, *extra)
            self.assertEqual(code, cl.EXIT_ERROR, extra)
            self.assertIn(expected, err)
            self.assertFalse((other.campaign / "campaign.json").exists())

    def test_the_campaign_folder_and_the_subject_workspace_are_kept_apart(self):
        lab = Lab(self)
        for campaign, workspace in ((lab.ws / "campaign", lab.ws), (lab.tmp, lab.ws), (lab.ws, lab.ws)):
            code, _, err = lab.cli("init", "--manifest", lab.manifest_path, "--campaign", campaign, "--workspace", workspace,
                                   "--cases", "A1", "--budget", DEFAULT_BUDGET)
            self.assertEqual(code, cl.EXIT_ERROR, (campaign, workspace))
            self.assertIn("separate folders", err)

    def test_concurrent_initialisations_create_exactly_one_campaign(self):
        lab = Lab(self)
        args = [sys.executable, str(SCRIPT), "init", "--manifest", str(lab.manifest_path), "--campaign", str(lab.campaign),
                "--workspace", str(lab.ws), "--cases", "A1", "--budget", DEFAULT_BUDGET]
        procs = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = [(proc.communicate(), proc.returncode) for proc in procs]
        self.assertEqual(sorted(code for _, code in results), [cl.EXIT_OK, cl.EXIT_ERROR])
        loser = next(streams for streams, code in results if code == cl.EXIT_ERROR)
        self.assertIn("already exists", loser[1])
        self.assertEqual(lab.state()["scope"], "S0")

    def test_a_command_waits_a_bounded_time_for_the_campaign_lock_and_then_says_so(self):
        lab = Lab(self)
        lab.init()
        with open(lab.campaign / "campaign.lock", "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)  # another command, or a hung one, holds the campaign
            with mock.patch.object(cl, "LOCK_WAIT_SECONDS", 0.3):
                code, _, err = lab.cli("step", "--campaign", lab.campaign)
            fcntl.flock(held, fcntl.LOCK_UN)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("held the campaign lock for 0.3 s", err)
        self.assertEqual(lab.starts(), [])
        self.assertEqual(lab.step()["action"], "start")  # and it is usable the moment the lock is free

    def test_the_initialisation_existence_check_runs_inside_the_lock(self):
        lab = Lab(self)
        lab.campaign.mkdir()
        args = [sys.executable, str(SCRIPT), "init", "--manifest", str(lab.manifest_path), "--campaign", str(lab.campaign),
                "--workspace", str(lab.ws), "--cases", "A1", "--budget", DEFAULT_BUDGET]
        with open(lab.campaign / "campaign.lock", "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)  # both initialisations get past any check made before the lock, and wait here
            procs = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
            time.sleep(1.5)
            fcntl.flock(held, fcntl.LOCK_UN)
        results = [(proc.communicate(), proc.returncode) for proc in procs]
        self.assertEqual(sorted(code for _, code in results), [cl.EXIT_OK, cl.EXIT_ERROR])
        self.assertIn("already exists", next(streams for streams, code in results if code == cl.EXIT_ERROR)[1])

    def test_saves_are_atomic_and_leave_no_temporary_file(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        self.assertEqual(sorted(path.name for path in lab.campaign.iterdir() if path.name.startswith("campaign.json")),
                         ["campaign.json"])

    def test_bulky_files_go_beside_the_campaign_folder_never_in_it(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        self.assertTrue((lab.work / "runs").is_dir())
        self.assertEqual(sorted(path.name for path in lab.campaign.iterdir()),
                         [".git", ".gitignore", "campaign.json", "campaign.lock", "journal.md"])

    def test_queries_never_write_inside_the_workspace_or_the_campaign_folder(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        before = (tree_digest(lab.ws), tree_digest(lab.campaign), tree_digest(lab.work))
        for verb in ("certificate", "coverage", "status", "next"):
            lab.cli(verb, "--campaign", lab.campaign)
        for clause in cl.CLAUSES:
            lab.check(clause)
        lab.cli("contract", "--campaign", lab.campaign)
        self.assertEqual((tree_digest(lab.ws), tree_digest(lab.campaign), tree_digest(lab.work)), before)  # contents, not names


class FingerprintTests(unittest.TestCase):
    """The Until Loop fingerprints the campaign folder with `git add -A`: nothing in it may be ignored, and Git must work."""

    def test_the_folders_own_ignore_file_outranks_exclude_rules_and_the_users_global_ignore(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        self.assertEqual((lab.campaign / ".gitignore").read_text().splitlines()[-1], "!*")
        (lab.campaign / ".git" / "info" / "exclude").write_text("campaign.json\n*.md\n")
        global_ignore = lab.tmp / "global-ignore"
        global_ignore.write_text("*.json\n*.lock\n")
        gitconfig = lab.tmp / "gitconfig"
        gitconfig.write_text(f"[core]\n\texcludesFile = {global_ignore}\n")
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(gitconfig)}):
            self.assertIsNone(cl.fingerprint_problem(lab.campaign))
            self.assertEqual(lab.check("C1")[0], cl.EXIT_OK)

    def test_an_ignore_rule_that_would_hide_the_state_fails_the_checks_and_the_contract(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        (lab.campaign / ".gitignore").unlink()  # the folder's own rule is gone
        (lab.campaign / ".git" / "info" / "exclude").write_text("campaign.json\n")
        self.assertIn("Git ignores campaign.json", cl.fingerprint_problem(lab.campaign))
        code, _, err = lab.check("C1")
        self.assertEqual(code, cl.EXIT_ERROR)  # exit 2, never a pass: the runtime records it as a failed check
        self.assertIn("Git ignores campaign.json", err)
        code, _, err = lab.cli("contract", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("Git ignores", err)

    def test_a_failing_ignore_check_is_a_problem_even_when_the_fingerprint_command_still_works(self):
        lab = Lab(self)
        lab.init("A1")
        stub = lab.tmp / "stub-bin"
        stub.mkdir()
        (stub / "git").write_text(f'#!/bin/sh\nfor arg in "$@"; do\n  if [ "$arg" = check-ignore ]; then echo "fatal: boom" >&2; exit 128; fi\n'
                                  f'done\nexec "{shutil.which("git")}" "$@"\n')
        (stub / "git").chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{stub}{os.pathsep}{os.environ['PATH']}"}):
            problem = cl.fingerprint_problem(lab.campaign)
        self.assertIn("git cannot read the campaign folder", problem)  # not the `add -n` guard: it succeeded
        self.assertIn("boom", problem)

    def test_a_folder_git_cannot_read_fails_the_checks(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        shutil.move(str(lab.campaign / ".git"), str(lab.tmp / "moved-git"))
        code, _, err = lab.check("C1")
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("git cannot", err)


class EvidenceTests(unittest.TestCase):
    """Evidence is validated before it can count: malformed, partial or unrequested results never make a quiet iteration."""

    def test_validate_facts_accepts_a_well_formed_report_and_rejects_every_malformed_shape(self):
        self.assertEqual(cl.validate_facts(good_facts(["A1"]), ["A1"]), [])
        other = {"ran": True, "floors_met": True, "baseline": "comparable"}
        mutations = {
            "ran as text": lambda f: f["cases"]["A1"].update(ran="true"),
            "floors as a number": lambda f: f["cases"]["A1"].update(floors_met=1),
            "an unknown baseline": lambda f: f["cases"]["A1"].update(baseline="maybe"),
            "an omitted case": lambda f: f["cases"].pop("A1"),
            "an unrequested case": lambda f: f["cases"].update(B1=other),
            "a review without complete": lambda f: f["review"].pop("complete"),
            "a judge valid as text": lambda f: f["judge"].update(valid="true"),
            "a discovery without an id": lambda f: f["discoveries"].append({"material": True}),
            "a discovery with a text flag": lambda f: f["discoveries"].append({"id": "D", "material": "yes"}),
            "a candidate with an unknown outcome": lambda f: f.update(candidate={"id": "c", "hash": "h", "outcome": "MAYBE"}),
            "invalid as text": lambda f: f.update(invalid="none"),
            "a verified cleanup without a receipt": lambda f: f.update(cleanup={"verified": True}),
            "a tier without a build": lambda f: f.update(tier={"green": True}),
            "half an acceptance": lambda f: f.update(acceptance={"candidate": "h"}),
            "a negative consumption": lambda f: f.update(consumed={"seconds": -1}),
            "a boolean consumption": lambda f: f.update(consumed={"seconds": True}),
            "a text consumption": lambda f: f.update(consumed={"seconds": "5"}),
            "a NaN consumption": lambda f: f.update(consumed={"seconds": float("nan")}),
            "an empty build": lambda f: f.update(build_after=""),
            "a missing scoring identity": lambda f: f.update(scoring=None),
            "a promotion that left the build unchanged": lambda f: f.update(candidate={"id": "c", "hash": "h", "outcome": "PROMOTE"}),
            "a build that changed without a promotion": lambda f: f.update(build_after="b1")}
        for name, mutate in mutations.items():
            facts = good_facts(["A1"])
            mutate(facts)
            self.assertTrue(cl.validate_facts(facts, ["A1"]), name)
        self.assertTrue(cl.validate_facts("not an object", ["A1"]))

    def test_a_malformed_report_from_an_adapter_is_a_failed_step_never_a_quiet_iteration(self):
        for name, cases, config, expected in (
                ("a boolean written as text", "A1", {"case_overrides": {"A1": {"ran": "true"}}}, "needs boolean ran"),
                ("a scope case left out", "A1,B1", {"omit_cases": ["B1"]}, "no result for requested cases: B1"),
                ("a case nobody asked for", "A1", {"extra_cases": ["B1"]}, "not requested: B1"),
                ("a blank build identity", "A1", {"iteration_overrides": {"build_after": ""}}, "build_after must be non-empty")):
            with self.subTest(name):
                lab = Lab(self)
                lab.init(cases)
                lab.config(**config)
                self.assertEqual(lab.step()["action"], "start")
                state = lab.state()
                record = state["iterations"][0]
                self.assertTrue(record["failed"] and not record["quiet"])
                self.assertIn("malformed adapter evidence", record["invalid"][0])
                self.assertIn(expected, record["invalid"][0])
                self.assertEqual(state["steps"][record["key"]]["status"], "failed")
                self.assertEqual(lab.certificate()["status"], "incomplete")
                self.assertEqual(lab.check("C7")[0], cl.EXIT_NOT_READY)

    def test_a_record_with_a_malformed_cases_or_target_field_fails_closed_instead_of_leaving_the_scope(self):
        lab = Lab(self)
        lab.init("A1")
        for extra in ({"cases": "A1"}, {"cases": [1]}, {"target": "Subject"}, {"material": "yes"}):
            lab.config(extra_records=[{"id": "R-z", "material": True, "target": "subject", "status": "open", **extra}])
            code, _, err = lab.cli("certificate", "--campaign", lab.campaign)
            self.assertEqual(code, cl.EXIT_ERROR, extra)
            self.assertIn("adapter records must print", err)

    def test_an_iteration_that_ran_on_another_build_than_its_base_is_invalid(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(iteration_overrides={"build_before": "b7"})
        lab.step()
        record = lab.state()["iterations"][0]
        self.assertFalse(record["quiet"])
        self.assertTrue(any("the base was b0" in reason for reason in record["invalid"]))

    def test_widening_starts_with_no_quiet_history_and_retires_the_old_contract(self):
        lab = Lab(self)
        lab.init("A1")
        for _ in range(3):
            lab.step()
        contract = lab.ok("contract", "--campaign", lab.campaign)
        first = contract["exit_checks"][0]["command"]
        self.assertEqual(subprocess.run(first, check=False, **SH).returncode, cl.EXIT_OK)  # C1 holds at S0
        self.assertEqual(lab.step()["action"], "widen")
        cert = lab.certificate()  # S1 has not run: it cannot have converged on S0's evidence
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any(reason.startswith("C2:") and "only 0 iteration(s)" in reason for reason in cert["reasons"]))
        self.assertTrue(any("style=beta" in reason for reason in cert["checks"]["C4"]["reasons"]))
        stale = subprocess.run(first, check=False, **SH)  # the frozen S0 check no longer certifies whichever scope is current
        self.assertEqual(stale.returncode, cl.EXIT_IDENTITY)
        self.assertIn("this contract is for scope S0", json.loads(stale.stdout)["reasons"][0])

    def test_a_contract_for_another_campaign_identity_is_refused(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        code, out, _ = lab.check("C1", "--expect-identity", "0" * 16)
        self.assertEqual(code, cl.EXIT_IDENTITY)
        self.assertIn("another campaign identity", out["reasons"][0])

    def test_an_earlier_unclean_run_cannot_hide_behind_a_later_clean_one(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(iteration_overrides={"cleanup": {"verified": False}})
        lab.step()
        lab.config(iteration_overrides={})
        lab.step()
        lab.step()
        code, out, _ = lab.check("C5")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("iteration 1 has no positive cleanup evidence" in reason for reason in out["reasons"]))
        self.assertEqual(lab.certificate()["status"], "incomplete")
        cleaned = lab.ok("cleanup", "--campaign", lab.campaign)
        self.assertEqual(len(cleaned["covered"]), 1)  # only the run without evidence
        self.assertEqual(lab.certificate()["status"], "converged", lab.certificate()["reasons"])

    def test_cleanup_that_is_not_verified_with_a_receipt_changes_nothing(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(iteration_overrides={"cleanup": {"verified": False}}, cleanup_unverified=True)
        lab.step()
        code, _, err = lab.cli("cleanup", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("did not report verified with a receipt", err)
        self.assertFalse(lab.state()["iterations"][0]["cleanup"]["verified"])

    def test_a_cancelled_step_is_an_invalid_iteration_that_needs_cleanup(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=3)
        key = lab.step()["key"]
        cancelled = lab.ok("cancel", "--campaign", lab.campaign, "--key", key)
        self.assertIn("cleanup", cancelled["next"])
        state = lab.state()
        self.assertTrue(state["iterations"][0]["failed"])
        self.assertEqual(state["steps"][key]["status"], "cancelled")
        self.assertTrue(any("no positive cleanup evidence" in reason for reason in lab.check("C5")[1]["reasons"]))
        self.assertEqual(lab.ok("cleanup", "--campaign", lab.campaign)["covered"], [key])
        _, _, err = lab.cli("cancel", "--campaign", lab.campaign, "--key", key)
        self.assertIn("no running step", err)

    def test_a_start_that_failed_may_have_launched_a_run_so_the_scope_is_unclean_until_cleanup_covers_it(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(crash={"step": True})
        code, _, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        key = next(iter(lab.state()["launch_intents"]))
        reasons = lab.check("C5")[1]["reasons"]
        self.assertTrue(any(f"may have launched step {key}" in reason for reason in reasons), reasons)
        covered = lab.ok("cleanup", "--campaign", lab.campaign)["covered"]
        self.assertEqual(covered, [key])
        self.assertEqual((lab.ws / "fake-cleanups.log").read_text().split(), [key])
        self.assertFalse(any("may have launched" in reason for reason in lab.check("C5")[1]["reasons"]))
        self.assertEqual(lab.ok("cleanup", "--campaign", lab.campaign)["covered"], [])  # and it is not run twice for the same key

    def test_a_new_start_failure_voids_an_earlier_cleanup_of_the_same_launch(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(crash={"step": True})
        lab.cli("step", "--campaign", lab.campaign)
        key = next(iter(lab.state()["launch_intents"]))
        self.assertEqual(lab.ok("cleanup", "--campaign", lab.campaign)["covered"], [key])
        self.assertFalse(any("may have launched" in reason for reason in lab.check("C5")[1]["reasons"]))
        lab.cli("step", "--campaign", lab.campaign)  # the retry fails too, and may have launched the run again
        self.assertTrue(any(f"may have launched step {key}" in reason for reason in lab.check("C5")[1]["reasons"]))
        self.assertEqual(lab.ok("cleanup", "--campaign", lab.campaign)["covered"], [key])
        self.assertEqual((lab.ws / "fake-cleanups.log").read_text().split(), [key, key])

    def test_a_running_step_keeps_a_converged_scope_incomplete(self):
        lab = Lab(self)
        lab.init("A1")
        for _ in range(3):
            lab.step()
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "is the oracle sensitive?", "--inside-claim")
        lab.config(poll_delay=2)
        started = lab.step()  # the certificate is incomplete, so the loop starts another iteration
        self.assertEqual((started["action"], started["status"]), ("start", "running"))
        lab.ok("unknown", "--campaign", lab.campaign, "resolve", "--index", "0")
        cert = lab.certificate()  # the unknown is answered, but a run is in flight and its outcome and cleanup are not known
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any("is still running" in reason for reason in cert["reasons"]), cert["reasons"])

    def test_work_added_after_a_converged_stop_makes_that_stop_stale(self):
        lab, task = self.hunt_lab()
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--result", json.dumps(
            {"blind_spots": [{"what": "timing", "disposition": "rejected", "reason": "the scope does not claim timing"}]}))
        self.assertEqual(lab.step()["status"], "converged")
        added = lab.ok("task", "--campaign", lab.campaign, "add", "--kind", "review", "--text", "the owner wants a second look",
                       "--needs-owner")["task"]
        stale = lab.ok("next", "--campaign", lab.campaign)
        self.assertEqual((stale["action"], stale["status"]), ("stop", "incomplete"))
        self.assertIn(f"task {added['id']} (review) is open", stale["reason"])
        report = lab.ok("report", "--campaign", lab.campaign)
        self.assertEqual((report["stop"]["status"], report["campaign_status"]), ("converged", "incomplete"))

    def test_a_persisted_review_flag_that_is_not_a_boolean_makes_the_state_malformed(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        state = lab.state()
        state["iterations"][0]["review"]["valid"] = "false"  # truthy text, which the checks would have read as valid
        lab.write_state(state)
        code, _, err = lab.cli("certificate", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("holds malformed evidence", err)

    def test_a_persisted_quiet_flag_must_follow_from_the_evidence(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        state = lab.state()
        self.assertFalse(state["iterations"][0]["quiet"])  # the first iteration found and fixed d1
        state["iterations"][0]["quiet"] = True
        lab.write_state(state)
        code, _, err = lab.cli("certificate", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("quiet flag does not follow from its evidence", err)

    def hunt_lab(self):
        """A one-case catalog with no defects: two quiet iterations converge it and the next step asks for a blind-spot hunt."""
        lab = Lab(self)
        lab.config(catalog=[{"id": "A1", "dimensions": {"style": "alpha"}, "cost": 1, "requires": [], "hosted": False}], defects={})
        lab.init("A1")
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "task"])
        return lab, actions[-1]["task"]

    def test_a_hunt_result_needs_a_disposition_for_every_blind_spot(self):
        lab, task = self.hunt_lab()
        for result, expected in (({}, "closes with --result"),
                                 ({"blind_spots": [{"what": "x", "disposition": "rejected"}]}, "needs a reason"),
                                 ({"blind_spots": [{"what": "x", "disposition": "maybe"}]}, "disposition of"),
                                 ({"blind_spots": ["x"]}, "disposition of")):
            code, _, err = lab.cli("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--result", json.dumps(result))
            self.assertEqual(code, cl.EXIT_ERROR, result)
            self.assertIn(expected, err)
        self.assertEqual(lab.step()["task"]["id"], task["id"])  # still open

    def test_a_blind_spot_handed_to_the_owner_or_left_as_a_task_keeps_the_campaign_incomplete(self):
        for disposition in ("deferred-to-owner", "added-as-task"):
            with self.subTest(disposition):
                lab, task = self.hunt_lab()
                lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"],
                       "--result", json.dumps({"blind_spots": [{"what": "the grader ignores timing", "disposition": disposition}]}))
                stop = lab.step()
                self.assertEqual((stop["action"], stop["status"], stop["rung"]), ("stop", "incomplete", "E3"))
                self.assertIn("without a rejection", stop["reason"])
                self.assertEqual(json.loads((lab.campaign / "report.json").read_text())["campaign_status"], "incomplete")

    def test_only_a_rejected_blind_spot_with_a_reason_lets_the_campaign_converge_and_a_new_unknown_makes_that_stale(self):
        lab, task = self.hunt_lab()
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--result", json.dumps(
            {"blind_spots": [{"what": "timing", "disposition": "rejected", "reason": "the scope does not claim timing"}]}))
        stop = lab.step()
        self.assertEqual((stop["status"], stop["rung"]), ("converged", "E5"))
        self.assertEqual(json.loads((lab.campaign / "report.json").read_text())["campaign_status"], "converged")
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "is the oracle sensitive?", "--inside-claim")
        stale = lab.ok("report", "--campaign", lab.campaign)  # the recorded stop is still "converged"; the report must not repeat it
        self.assertEqual((stale["stop"]["status"], stale["campaign_status"]), ("converged", "incomplete"))
        self.assertEqual(json.loads((lab.campaign / "report.json").read_text())["campaign_status"], "incomplete")
        again = lab.step()  # the cached converged stop is stale: the evidence changed after it
        self.assertEqual((again["action"], again["status"]), ("stop", "incomplete"))
        self.assertIn("stale", again["reason"])
        self.assertEqual(json.loads((lab.campaign / "report.json").read_text())["campaign_status"], "incomplete")

    def test_a_converged_scope_is_not_a_converged_campaign_until_the_widening_ends(self):
        lab = Lab(self)
        lab.init("A1")
        for _ in range(3):
            lab.step()
        report = lab.ok("report", "--campaign", lab.campaign)
        self.assertEqual((report["scope_certificate"], report["campaign_status"]), ("converged", "in progress"))

    def test_declared_combinations_widen_the_scope_to_the_pair_no_single_value_exposes(self):
        lab = Lab(self, dimensions=["a", "b"], combinations=[["a", "b"]])
        lab.config(catalog=CATALOG_AB, defects={})
        lab.init("AX")
        actions = lab.run()
        widened = [item["cases"] for item in actions if item["action"] == "widen"]
        self.assertEqual(widened, [["AX", "BY"], ["AX", "BY", "AY"]])  # AY is selected for the pair a=A&b=Y
        self.assertEqual(actions[-1]["task"]["kind"], "hunt")
        covers = [item["covers"] for item in actions if item["action"] == "widen"]
        self.assertIn("a=A&b=Y", covers[-1])

    def test_without_declared_combinations_the_marginal_values_are_all_that_is_tracked(self):
        lab = Lab(self, dimensions=["a", "b"])
        lab.config(catalog=CATALOG_AB, defects={})
        lab.init("AX")
        actions = lab.run()
        self.assertEqual([item["cases"] for item in actions if item["action"] == "widen"], [["AX", "BY"]])
        self.assertEqual(lab.ok("coverage", "--campaign", lab.campaign)["not_covered"], {})  # AY adds no value: the gap combinations close


class CertificateTests(unittest.TestCase):
    def converge_scope_zero(self, lab: Lab) -> None:
        lab.init()
        for _ in range(3):
            lab.step()

    def test_a_campaign_with_no_iteration_is_incomplete_for_a_stated_reason(self):
        lab = Lab(self)
        lab.init()
        cert = lab.certificate()
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any("no iteration has run" in reason for reason in cert["reasons"]))

    def test_three_iterations_converge_scope_zero_with_all_seven_checks(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        cert = lab.certificate()
        self.assertEqual(cert["status"], "converged", cert["reasons"])
        self.assertEqual(sorted(cert["checks"]), list(cl.CLAUSES))
        self.assertEqual(cert["binds"]["scope"], "S0")
        self.assertEqual(cert["binds"]["build"], "b1")
        self.assertEqual(cert["binds"]["candidates"], ["h-d1-b1"])
        self.assertEqual(cert["binds"]["campaign_identity"], lab.ok("status", "--campaign", lab.campaign)["identity"])
        iterations = lab.state()["iterations"]
        self.assertEqual([item["quiet"] for item in iterations], [False, True, True])
        self.assertEqual(iterations[0]["build_before"], "b0")
        self.assertEqual(iterations[0]["build_after"], "b1")

    def test_the_certificate_carries_what_readiness_allows_it_to_claim(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        claims = lab.certificate()["claims"]
        self.assertTrue(claims["recorded"])
        self.assertIn("no quality claim is allowed yet", " ".join(claims["allowed"]))  # the oracle is not shown sensitive
        self.assertIn("no quality claim is allowed yet", (lab.ok("report", "--campaign", lab.campaign) or {})["allowed_claims"][-1])

    def test_the_quiet_window_needs_k_iterations_on_the_current_build(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        lab.step()  # iteration 2 is quiet, but only one iteration has run on build b1
        cert = lab.certificate()
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any("quiet window needs 2" in reason for reason in cert["reasons"]))

    def test_a_deferred_material_record_keeps_the_scope_incomplete_and_the_loop_stops_for_the_owner(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        lab.config(extra_records=[{"id": "R-x", "title": "deferred", "material": True, "target": "subject",
                                   "status": "deferred", "reopen_when": "the owner decides"}])
        cert = lab.certificate()
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any("R-x is deferred" in reason for reason in cert["reasons"]))
        stop = lab.step()
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertIn("owner decisions are needed", stop["reason"])
        report = json.loads((lab.campaign / "report.json").read_text())
        self.assertEqual(report["unresolved"][0]["reopen_when"], "the owner decides")
        self.assertIn("reopen when: the owner decides", (lab.campaign / "report.md").read_text())

    def test_records_for_the_evaluator_and_for_other_cases_do_not_block_a_subject_certificate(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        lab.config(extra_records=[
            {"id": "R-adapter", "material": True, "target": "adapter", "status": "open"},
            {"id": "R-elsewhere", "material": True, "target": "subject", "status": "open", "cases": ["B1"]},
            {"id": "R-minor", "material": False, "target": "subject", "status": "open"}])
        cert = lab.certificate()
        self.assertEqual(cert["status"], "converged", cert["reasons"])
        detail = cert["checks"]["C1"]["detail"]
        self.assertEqual(detail["adapter_backlog"], ["R-adapter"])
        self.assertEqual(detail["outside_scope"], ["R-elsewhere"])

    def test_a_record_resolves_only_with_a_known_status_and_evidence_and_an_unknown_status_fails_closed(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        for status, evidence, blocks in (("dropped", None, True), ("dropped", "the prediction was refuted", False),
                                         ("promoted", "predicted effect seen", True), ("verified", None, True),
                                         ("verified", "   ", True), ("verified", "checked on build b1", False),
                                         ("refuted", "the effect did not appear", False), ("wontfix", "the owner said so", True),
                                         ("rejected", "", True)):
            lab.config(extra_records=[{"id": "R-y", "material": True, "target": "subject", "status": status,
                                       "evidence": evidence}])
            self.assertEqual(lab.check("C1")[0], cl.EXIT_NOT_READY if blocks else cl.EXIT_OK, (status, evidence))

    def test_an_invalid_review_is_not_quiet_and_delays_convergence_by_two_quiet_passes(self):
        lab = Lab(self)
        lab.init()
        lab.config(invalid_review_at=[3])
        for _ in range(3):
            lab.step()
        third = lab.state()["iterations"][2]
        self.assertFalse(third["quiet"])
        self.assertTrue(any("review was not valid" in reason for reason in third["quiet_reasons"]))
        self.assertEqual(lab.check("C7")[0], cl.EXIT_NOT_READY)  # in the last two
        lab.step()  # iteration 4 is quiet, but the invalid iteration 3 is still inside the last two
        self.assertEqual(lab.certificate()["status"], "incomplete")
        self.assertEqual(lab.check("C2")[0], cl.EXIT_NOT_READY)
        lab.step()  # iteration 5: the last two, 4 and 5, are quiet
        self.assertEqual(lab.certificate()["status"], "converged")
        self.assertEqual(len(lab.state()["iterations"]), 5)

    def test_an_invalid_review_inside_the_window_fails_c7_with_its_reason(self):
        lab = Lab(self)
        lab.init()
        lab.config(invalid_review_at=[2])
        lab.step()
        lab.step()
        code, out, _ = lab.check("C7")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("invalid or incomplete evidence" in reason for reason in out["reasons"]))

    def test_an_unknown_or_missing_baseline_blocks_green(self):
        lab = Lab(self)
        lab.init()
        lab.config(baseline={"A1": "none"})
        for _ in range(3):
            lab.step()
        code, out, _ = lab.check("C3")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("no comparable baseline" in reason for reason in out["reasons"]))
        self.assertEqual(lab.certificate()["status"], "incomplete")  # unknown blocks: the scope cannot converge on it

    def test_the_coverage_statement_must_be_complete(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        state = lab.state()
        del state["scopes"][0]["not_covered"]["style=gamma"]
        lab.write_state(state)
        code, out, _ = lab.check("C4")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("style=gamma is neither covered nor listed" in reason for reason in out["reasons"]))

    def test_cleanup_and_the_quick_tier_receipt_need_positive_evidence_for_the_current_build(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        for field, value, expect in (("cleanup", {"verified": False}, "no positive cleanup evidence"),
                                     ("tier", {"green": True, "build": "b0"}, "quick-tier receipt is for build"),
                                     ("tier", {"green": False, "build": "b1"}, "no green quick-tier receipt")):
            state = lab.state()
            original = state["iterations"][-1][field]
            state["iterations"][-1][field] = value
            lab.write_state(state)
            out = lab.check("C5")[1]
            self.assertTrue(any(expect in reason for reason in out["reasons"]), out["reasons"])
            state["iterations"][-1][field] = original
            lab.write_state(state)
        self.assertEqual(lab.check("C5")[0], cl.EXIT_OK)

    def test_a_promoted_candidate_without_acceptance_for_it_keeps_the_scope_incomplete(self):
        lab = Lab(self)
        lab.init()
        lab.config(no_acceptance=True)
        for _ in range(3):
            lab.step()
        code, out, _ = lab.check("C6")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("without acceptance evidence" in reason for reason in out["reasons"]))
        lab.config(no_acceptance=False)
        state = lab.state()
        state["iterations"][0]["acceptance"] = {"candidate": "some-other-hash", "evidence": "x"}  # names a different candidate
        lab.write_state(state)
        self.assertEqual(lab.check("C6")[0], cl.EXIT_NOT_READY)

    def test_with_nothing_promoted_the_certificate_says_there_is_no_candidate(self):
        lab = Lab(self)
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 1, "fixed": ["d1"], "known": ["d1"]}))
        lab.init()
        for _ in range(2):
            lab.step()
        out = lab.check("C6")[1]
        self.assertTrue(out["pass"])
        self.assertEqual(out["detail"]["note"], "no candidate")

    def test_an_unknown_inside_the_claim_blocks_until_it_is_resolved_and_one_outside_does_not(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "noise on the other driver is unmeasured")
        self.assertEqual(lab.certificate()["status"], "converged")  # outside the claim: listed, not blocking
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "is the oracle sensitive to d1?", "--inside-claim")
        code, out, _ = lab.check("C7")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("an unknown lies inside the scope's claim" in reason for reason in out["reasons"]))
        lab.ok("unknown", "--campaign", lab.campaign, "resolve", "--index", "1")
        self.assertEqual(lab.certificate()["status"], "converged")
        lab.ok("report", "--campaign", lab.campaign)
        self.assertEqual(len(json.loads((lab.campaign / "report.json").read_text())["unknowns"]), 1)  # the resolved one is gone
        code, _, err = lab.cli("unknown", "--campaign", lab.campaign, "resolve", "--index", "9")
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("existing unknown", err)
        code, _, err = lab.cli("unknown", "--campaign", lab.campaign, "add", "--text", " ")
        self.assertIn("names what is not known", err)

    def test_a_changed_scoring_identity_makes_the_evidence_stale_until_it_is_regathered(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        lab.config(scoring="score-2")
        cert = lab.certificate()
        self.assertEqual(cert["status"], "incomplete")
        self.assertTrue(any(reason.startswith("C2: stale") for reason in cert["reasons"]))
        self.assertTrue(any(reason.startswith("C3: stale") for reason in cert["reasons"]))
        self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["action"], "start")  # it re-evaluates, it does not stop
        lab.step()
        lab.step()
        self.assertEqual(lab.certificate()["status"], "converged")
        self.assertEqual(lab.certificate()["binds"]["scoring"], "score-2")

    def test_a_subject_that_changed_outside_the_campaign_is_stale_too(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 9, "fixed": ["d1"], "known": ["d1"]}))
        self.assertTrue(any("subject's build is now" in reason for reason in lab.certificate()["reasons"]))

    def test_a_check_prints_the_identity_of_the_script_and_refuses_a_changed_one(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        code, out, _ = lab.check("C1", "--expect-sha", cl.script_sha())
        self.assertEqual((code, out["script_sha256"]), (cl.EXIT_OK, cl.script_sha()))
        code, out, _ = lab.check("C1", "--expect-sha", "0" * 64)
        self.assertEqual(code, cl.EXIT_IDENTITY)
        self.assertIn("check script changed", out["reasons"][0])
        done = subprocess.run([sys.executable, str(SCRIPT), "check", "--campaign", str(lab.campaign), "--clause", "C1",
                               "--expect-sha", "0" * 64], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, cl.EXIT_IDENTITY)


class EscalationTests(unittest.TestCase):
    def test_the_demo_converges_widens_on_an_uncovered_style_and_stops_on_the_owner_only_rung(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=1000")
        actions = lab.run()
        kinds = [item["action"] for item in actions]
        self.assertEqual(kinds, ["start", "start", "start", "widen", "start", "start", "start", "start", "stop"])
        widen = actions[3]
        self.assertEqual((widen["scope"], widen["cases"], widen["covers"]), ("S1", ["A1", "B1"], ["style=beta"]))
        self.assertIn("B1 is the cheapest case", widen["reason"])  # B2 also covers beta, at cost 5
        self.assertIn("baseline sweep", widen["first_iteration"])
        state = lab.state()
        modes = [(item["scope"], item["mode"], item["quiet"]) for item in state["iterations"]]
        self.assertEqual(modes, [("S0", "iterate", False), ("S0", "iterate", True), ("S0", "iterate", True),
                                 ("S1", "sweep", False), ("S1", "iterate", False), ("S1", "iterate", True),
                                 ("S1", "iterate", True)])
        sweep = state["iterations"][3]
        self.assertEqual([item["id"] for item in sweep["discoveries"]], ["D-d2"])  # only the new case exposes d2
        self.assertIsNone(sweep["candidate"])  # a sweep runs the cases with no improver
        self.assertEqual([item["candidate"]["hash"] for item in state["iterations"] if item["candidate"]],
                         ["h-d1-b1", "h-d2-b2"])
        stop = actions[-1]
        self.assertEqual((stop["status"], stop["rung"], stop["scope_certificate"]), ("incomplete", "E5", "converged"))
        self.assertIn("C1 (covers style=gamma)", stop["reason"])
        self.assertEqual(stop["owner_gated_cases"], ["C1"])
        self.assertEqual(state["consumed"], {"seconds": 70, "turns": 35})
        report = (lab.campaign / "report.md").read_text()
        self.assertIn("Campaign status: incomplete", report)
        self.assertIn("Scope S1 (A1, B1) certificate: converged", report)
        self.assertIn("style=gamma", report)
        self.assertEqual(len((lab.campaign / "journal.md").read_text().splitlines()), 7)

    def test_coverage_lists_what_could_widen_the_scope_and_what_needs_the_owner(self):
        lab = Lab(self)
        lab.init("A1")
        out = lab.ok("coverage", "--campaign", lab.campaign)
        self.assertEqual(out["values"], ["style=alpha"])
        self.assertEqual([item["id"] for item in out["widening_candidates"]], ["B1", "B2"])  # cheapest first
        self.assertEqual([item["id"] for item in out["owner_gated"]], ["C1"])

    def test_the_owner_can_approve_the_gated_case_and_the_campaign_resumes_and_ends_with_a_hunt_task(self):
        lab = Lab(self)
        lab.init("A1")
        lab.run()
        code, _, err = lab.cli("approve", "--campaign", lab.campaign, "--case", "C1")
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("owner's decision", err)
        self.assertEqual(lab.ok("approve", "--campaign", lab.campaign, "--case", "C1", "--yes-owner-approved",
                                "--note", "the owner released the hosted case")["reopened"], True)
        widen = lab.step()
        self.assertEqual((widen["action"], widen["scope"], widen["cases"]), ("widen", "S2", ["A1", "B1", "C1"]))
        actions = lab.run()
        self.assertEqual(actions[-1]["action"], "task")
        task = actions[-1]["task"]
        self.assertEqual(task["kind"], "hunt")
        self.assertIn("blind-spot hunter", task["text"])
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--result", json.dumps({"blind_spots": []}))
        final = lab.step()
        self.assertEqual((final["action"], final["status"], final["rung"]), ("stop", "converged", "E5"))
        self.assertIn("not a claim that no material problem remains", final["reason"])
        self.assertEqual(lab.certificate()["checks"]["C1"]["pass"], True)

    def test_a_stall_asks_for_a_diagnosis_and_two_failed_diagnoses_stop_the_campaign_for_the_owner(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(outcome="DROP")
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "task"])
        diagnose = actions[-1]["task"]
        self.assertEqual(diagnose["kind"], "diagnose")
        self.assertIn("rung E0", diagnose["text"])
        self.assertEqual(lab.step()["task"]["id"], diagnose["id"])  # the open task is handed back until it is done
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", diagnose["id"], "--result", '{"found": "nothing yet"}')
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "task"])
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", actions[-1]["task"]["id"])
        stop = lab.step()
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertIn("two diagnoses", stop["reason"])

    def test_tasks_that_need_the_owner_cannot_be_closed_without_approval(self):
        lab = Lab(self)
        lab.init("A1")
        added = lab.ok("task", "--campaign", lab.campaign, "add", "--kind", "author-case", "--text", "a new hosted case",
                       "--needs-owner")["task"]
        code, _, err = lab.cli("task", "--campaign", lab.campaign, "done", "--id", added["id"])
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("needs the owner's approval", err)
        self.assertEqual(lab.step()["task"]["id"], added["id"])
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", added["id"], "--approve")
        self.assertEqual(lab.step()["action"], "start")
        code, _, err = lab.cli("task", "--campaign", lab.campaign, "done", "--id", added["id"])
        self.assertIn("already done", err)


class ResumeTests(unittest.TestCase):
    def test_a_running_step_is_polled_never_started_again(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=2)
        first = lab.step()
        self.assertEqual((first["action"], first["status"]), ("start", "running"))
        self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["action"], "poll")
        self.assertEqual(lab.step()["status"], "running")
        done = lab.step()
        self.assertEqual((done["action"], done["status"], done["iteration"]), ("poll", "done", 1))
        self.assertEqual(len(lab.starts()), 1)

    def test_a_crash_between_the_adapter_start_and_the_state_save_does_not_launch_a_second_run(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=2)
        lab.step()
        state = lab.state()
        key = next(iter(state["steps"]))
        del state["steps"][key]  # as if the orchestrator died after the adapter started the step and before it saved
        lab.write_state(state)
        again = lab.step()
        self.assertEqual((again["action"], again["key"]), ("start", key))  # the same key, recomputed from the state
        self.assertEqual(len(lab.starts()), 1)  # the adapter recognised the key and launched nothing
        self.assertEqual(lab.state()["steps"][key]["status"], "running")

    def test_a_crash_after_the_adapter_launched_the_run_replays_from_the_recorded_base_and_the_run_finishes_valid(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=2)
        key = lab.step()["key"]
        state = lab.state()
        self.assertNotIn(key, state["launch_intents"])  # the intent is cleared once the step is recorded
        # As if the process died after the adapter launched the run (it already promoted d1, so the live build is b1) and before
        # it saved the step: the intent, written ahead of the call, is what survives.
        del state["steps"][key]
        state["launch_intents"][key] = {"base": "b0", "scope": "S0", "cases": ["A1"], "mode": "iterate", "at": "2026-11-15T00:00:00Z"}
        lab.write_state(state)
        replay = lab.ok("next", "--campaign", lab.campaign)
        self.assertEqual((replay["action"], replay["key"], replay["base"]), ("start", key, "b0"))  # not the live b1
        lab.step()
        for _ in range(4):
            if lab.step().get("status") == "done":
                break
        record = lab.state()["iterations"][0]
        self.assertEqual((record["build_before"], record["build_after"], record["invalid"]), ("b0", "b1", []))
        self.assertEqual(len(lab.starts()), 1)  # the adapter recognised the key and launched nothing twice

    def test_a_kill_while_the_adapter_runs_leaves_the_launch_intent_behind(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(hang={"step": 3})  # the adapter call is in flight for a few seconds
        process = subprocess.Popen([sys.executable, str(SCRIPT), "step", "--campaign", str(lab.campaign)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(process.kill)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not lab.state()["launch_intents"]:
            time.sleep(0.05)
        process.kill()  # SIGKILL runs no handler: only what was saved before the adapter call survives
        process.communicate()
        intents = lab.state()["launch_intents"]
        self.assertEqual(len(intents), 1)
        key, intent = next(iter(intents.items()))
        self.assertEqual(intent["base"], "b0")
        self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["key"], key)  # the replay recomputes the same key

    def test_a_failed_start_keeps_its_base_for_the_retry_even_if_the_subject_moves_meanwhile(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(crash={"step": True})
        self.assertEqual(lab.cli("step", "--campaign", lab.campaign)[0], cl.EXIT_ERROR)
        key, intent = next(iter(lab.state()["launch_intents"].items()))
        self.assertEqual(intent["base"], "b0")
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 3, "fixed": ["d1"], "known": ["d1"]}))
        lab.config(crash={})
        retry = lab.ok("next", "--campaign", lab.campaign)
        self.assertEqual((retry["key"], retry["base"]), (key, "b0"))

    def test_a_crash_before_the_journal_is_saved_cannot_duplicate_its_line(self):
        lab = Lab(self)
        lab.init("A1")
        lab.step()
        camp = cl.Campaign(lab.campaign)
        cl.journal(camp, camp.state["iterations"][0])  # the same iteration journalled again, as a recovery would
        cl.journal(camp, camp.state["iterations"][0])
        self.assertEqual(len((lab.campaign / "journal.md").read_text().splitlines()), 1)

    def test_a_subject_changed_while_the_owner_reviewed_the_boundary_is_adopted_not_flagged_invalid(self):
        lab = Lab(self)
        lab.init("A1")  # the campaign saw build b0
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 5, "fixed": ["d1"], "known": ["d1"]}))
        self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["base"], "b5")  # the live build, not the one init saw
        lab.step()
        state = lab.state()
        record = state["iterations"][0]
        self.assertEqual((record["build_before"], record["invalid"], record["quiet"]), ("b5", [], True))
        self.assertTrue(any(event["event"] == "subject-changed-outside" and (event["expected"], event["found"]) == ("b0", "b5")
                            for event in state["events"]))

    def test_a_failed_step_is_an_invalid_iteration_and_the_same_error_three_times_stops(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=1)
        results = []
        for _ in range(3):
            lab.step()  # start
            for handle in (path for path in (lab.ws / "fake-steps").glob("*.json")):
                handle.unlink()  # the adapter loses the step: its poll answers "failed"
            results.append(lab.step())
        self.assertEqual([item["status"] for item in results], ["failed"] * 3)
        iterations = lab.state()["iterations"]
        self.assertEqual(len(iterations), 3)
        self.assertTrue(all(not item["quiet"] and item["invalid"] for item in iterations))
        self.assertEqual([item["key"].rsplit("-", 1)[1] for item in iterations], ["1", "2", "3"])  # a retry is the next index
        stop = lab.step()
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertIn("same step error three times", stop["reason"])

    def test_three_iterations_without_progress_stop_the_campaign_for_the_owner(self):
        lab = Lab(self)
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 1, "fixed": ["d1"], "known": ["d1"]}))
        lab.init("A1")
        lab.config(invalid_review_at=[1, 2, 3])  # nothing to fix, and no review is ever valid
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "start", "stop"])
        self.assertIn("3 iterations without progress", actions[-1]["reason"])

    def test_a_metric_regression_stops_until_the_owner_reopens_the_campaign(self):
        lab = Lab(self)
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 1, "fixed": ["d1"], "known": ["d1"]}))
        lab.init("A1,B1")
        lab.config(regress={"case": "A1", "from_version": 2})  # the fix for d2 breaks A1
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "stop"])
        self.assertIn("metric regression: A1 met its floors before candidate C-d2", actions[-1]["reason"])
        _, _, err = lab.cli("reopen", "--campaign", lab.campaign)
        self.assertIn("owner's decision", err)
        lab.ok("reopen", "--campaign", lab.campaign, "--yes-owner-approved", "--note", "the owner reviewed the regression")
        self.assertIn(lab.ok("next", "--campaign", lab.campaign)["action"], ("start", "task"))  # not the same stop again


class QuotaTests(unittest.TestCase):
    def test_an_exhausted_budget_ends_the_scope_incomplete_never_converged(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=25,turns=1000")
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "start", "stop"])
        self.assertEqual((actions[-1]["status"], actions[-1]["reason"]), ("incomplete", "budget used: seconds"))
        report = json.loads((lab.campaign / "report.json").read_text())
        # The budget is checked between steps, so the iteration that used the last of it can also be the one that converged the
        # scope: the scope certificate is then converged and the campaign is still incomplete, and the report says both.
        self.assertEqual((report["scope_certificate"], report["campaign_status"]), ("converged", "incomplete"))
        self.assertIn("budget exhausted: seconds", (lab.campaign / "report.md").read_text())

    def test_widening_does_not_renew_the_quota(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=45")
        actions = lab.run()
        self.assertEqual(actions[-1]["reason"], "budget used: seconds")
        state = lab.state()
        self.assertEqual(state["scope"], "S1")  # S0 converged and the campaign widened, then ran out
        self.assertEqual(state["consumed"]["seconds"], 50)  # S0's 30 seconds still count against S1: the quota is aggregate
        self.assertEqual(len(state["iterations"]), 5)

    def test_budgets_are_parsed_strictly(self):
        self.assertEqual(cl.parse_budget("seconds=3600,turns=400"), {"seconds": 3600, "turns": 400})
        for bad in ("seconds", "seconds=abc", "seconds=0", "=5", "seconds=nan", "seconds=inf", "seconds=-4"):
            with self.assertRaises(cl.LoopError):
                cl.parse_budget(bad)

    def test_a_failed_step_still_costs_what_it_reported(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=1, fail_poll={"error": "the adapter crashed", "consumed": {"seconds": 7, "turns": 2}})
        lab.step()
        out = lab.step()
        self.assertEqual((out["status"], out["error"]), ("failed", "the adapter crashed"))
        state = lab.state()
        self.assertEqual(state["consumed"], {"seconds": 7, "turns": 2})
        self.assertEqual(state["iterations"][0]["consumed"], {"seconds": 7, "turns": 2})

    def test_probes_and_tasks_are_charged_to_the_budget_too(self):
        lab = Lab(self)
        lab.init("A1", ready=False)
        lab.config(probe_consumed={"seconds": 7})
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertEqual(lab.state()["consumed"], {"seconds": 21})  # three claims, 7 seconds each
        task = lab.ok("task", "--campaign", lab.campaign, "add", "--kind", "diagnose", "--text", "look at the failing run")["task"]
        _, _, err = lab.cli("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--consumed", '{"seconds": -3}')
        self.assertIn("non-negative", err)
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--consumed", '{"seconds": 40}')
        self.assertEqual(lab.state()["consumed"], {"seconds": 61})

    def test_readiness_stops_before_the_probe_that_would_exceed_the_budget_and_keeps_what_it_spent(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=10", ready=False)
        lab.config(probe_consumed={"seconds": 7})
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        code, _, err = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("budget used: seconds", err)
        self.assertEqual(lab.state()["consumed"]["seconds"], 14)  # two probes finished; the guard stopped the third
        code, _, err = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertIn("budget used: seconds", err)  # the budget is spent: nothing is probed again
        self.assertEqual(lab.state()["consumed"]["seconds"], 14)

    def test_a_failing_probe_still_charges_the_probes_that_finished_before_it(self):
        lab = Lab(self)
        lab.init("A1", ready=False)
        lab.config(probe_consumed={"seconds": 7}, crash_probe=["grading.scores"])
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        code, _, err = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("exited 1", err)
        self.assertTrue(7 <= lab.state()["consumed"]["seconds"] < 8, lab.state()["consumed"])  # one probe plus the failed call

    def test_a_poll_that_keeps_failing_stops_the_campaign_and_the_step_is_left_for_cancel_and_cleanup(self):
        lab = Lab(self)
        lab.init("A1")
        lab.config(poll_delay=9)
        key = lab.step()["key"]
        lab.config(crash_step=["poll"])
        for _ in range(3):
            code, _, err = lab.cli("step", "--campaign", lab.campaign)
            self.assertEqual(code, cl.EXIT_ERROR)
            self.assertIn("exited 1", err)
        stop = lab.ok("step", "--campaign", lab.campaign)
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertIn(f"failed to poll step {key} 3 time(s)", stop["reason"])
        self.assertEqual(lab.state()["steps"][key]["status"], "running")  # still in flight: C5 refuses until it is cancelled
        self.assertTrue(any("is still running" in reason for reason in lab.check("C5")[1]["reasons"]))
        lab.config(crash_step=[])
        lab.ok("cancel", "--campaign", lab.campaign, "--key", key)
        self.assertEqual(lab.ok("cleanup", "--campaign", lab.campaign)["covered"], [key])

    def test_once_the_budget_is_used_a_single_failed_poll_ends_the_campaign(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=50")
        lab.config(poll_delay=9)
        lab.step()  # a step is running
        task = lab.ok("task", "--campaign", lab.campaign, "add", "--kind", "note", "--text", "work that cost money")["task"]
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--consumed", '{"seconds": 60}')
        lab.config(crash_step=["poll"])
        code, _, _ = lab.cli("step", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        stop = lab.ok("step", "--campaign", lab.campaign)
        self.assertEqual(stop["status"], "incomplete")
        self.assertIn("after the budget was used", stop["reason"])

    def test_a_stop_is_recorded_and_reported_even_when_the_adapter_can_no_longer_be_queried(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=5")
        lab.step()  # ten seconds used against a budget of five
        lab.config(crash={"records": True})
        stop = lab.ok("step", "--campaign", lab.campaign)
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertEqual(lab.state()["stop"]["reason"], "budget used: seconds")
        report = json.loads((lab.campaign / "report.json").read_text())
        self.assertEqual((report["scope_certificate"], report["campaign_status"]), ("unavailable", "incomplete"))
        self.assertTrue(any("could not be queried" in reason for reason in report["reasons"]))

    def test_the_owner_can_raise_a_spent_budget_but_never_below_what_is_used(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=25")
        lab.run()
        self.assertEqual(lab.state()["stop"]["reason"], "budget used: seconds")
        _, _, err = lab.cli("reopen", "--campaign", lab.campaign, "--budget", "seconds=1000")
        self.assertIn("owner's decision", err)
        _, _, err = lab.cli("reopen", "--campaign", lab.campaign, "--yes-owner-approved", "--budget", "seconds=20")
        self.assertIn("must exceed what is already consumed", err)
        lab.ok("reopen", "--campaign", lab.campaign, "--yes-owner-approved", "--budget", "seconds=1000")
        self.assertIn(lab.ok("next", "--campaign", lab.campaign)["action"], ("start", "widen"))

    def test_a_hanging_adapter_times_out_and_its_time_is_charged_and_the_lock_is_released(self):
        lab = Lab(self, timeout=2)
        lab.init("A1")
        lab.config(hang={"step": 30})
        code, _, err = lab.cli("step", "--campaign", lab.campaign)  # the call is killed at the manifest's timeout
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("did not finish within 2 s", err)
        state = lab.state()
        self.assertEqual(state["iterations"], [])  # the key did not move: a retry cannot launch a second run
        self.assertEqual([len(errors) for errors in state["start_failures"].values()], [1])
        self.assertGreaterEqual(state["consumed"]["seconds"], 1.9)  # the wall time of the failed call
        self.assertEqual(lab.ok("status", "--campaign", lab.campaign)["iterations"], 0)  # and the campaign is usable again

    def test_a_start_that_fails_three_times_with_one_error_ends_the_campaign_for_the_owner(self):
        lab = Lab(self)
        lab.init("A1")
        key = lab.ok("next", "--campaign", lab.campaign)["key"]
        lab.config(crash={"step": True})
        for _ in range(2):
            code, _, err = lab.cli("step", "--campaign", lab.campaign)
            self.assertEqual((code, "exited 1" in err), (cl.EXIT_ERROR, True))
            self.assertEqual(lab.ok("next", "--campaign", lab.campaign)["key"], key)  # the same key every time
        lab.cli("step", "--campaign", lab.campaign)
        stop = lab.ok("step", "--campaign", lab.campaign)
        self.assertEqual((stop["action"], stop["status"]), ("stop", "incomplete"))
        self.assertIn(f"failed to start step {key} three times", stop["reason"])
        self.assertEqual(lab.starts(), [])  # the crashing adapter never launched anything


class IsolationTests(unittest.TestCase):
    def test_two_campaigns_created_together_on_one_workspace_never_share_a_step_key(self):
        lab = Lab(self)
        second = lab.tmp / "campaign2"
        lab.init("A1")
        lab.init("B1", campaign=second)
        first_id, second_id = lab.state()["id"], json.loads((second / "campaign.json").read_text())["id"]
        self.assertNotEqual(first_id, second_id)
        lab.step()
        lab.step(second)
        keys = lab.starts()
        self.assertEqual(len(keys), 2)  # the adapter, which is idempotent on the key, launched both
        self.assertNotEqual(keys[0], keys[1])
        self.assertTrue(keys[0].startswith(first_id) and keys[1].startswith(second_id))


class ContractTests(unittest.TestCase):
    def test_the_scope_contract_has_script_owned_checks_bound_to_scope_and_identity_and_no_native_streak(self):
        lab = Lab(self)
        lab.init("A1")
        out_file = lab.tmp / "contract.json"
        contract = lab.ok("contract", "--campaign", lab.campaign, "--out", out_file)
        self.assertEqual(json.loads(out_file.read_text()), contract)
        self.assertEqual(contract["required_trivial_reviews"], 0)  # one counter: the script-owned quiet window
        self.assertEqual(contract["workspace"], str(lab.campaign))  # the folder the checks' evidence lives in
        self.assertEqual([item["id"] for item in contract["exit_checks"]], list(cl.CLAUSES))
        identity = lab.ok("status", "--campaign", lab.campaign)["identity"]
        for item in contract["exit_checks"]:
            self.assertEqual(item["clause"], cl.CLAUSE_TEXT[item["id"]])
            self.assertIn(f"--expect-sha {cl.script_sha()}", item["command"])
            self.assertIn("--expect-scope S0", item["command"])
            self.assertIn(f"--expect-identity {identity}", item["command"])
            self.assertIn(item["id"], item["command"])
            self.assertEqual(subprocess.run(["/bin/sh", "-n", "-c", item["command"]], check=False).returncode, 0)
        for text in cl.CLAUSE_TEXT.values():
            self.assertIn(text, contract["exit_condition"])
        self.assertEqual(sorted(contract["context"]), ["authority", "environment", "request", "resources", "scope"])
        self.assertTrue(all(str(value).strip() for key, value in contract["context"].items() if key != "resources"))
        for resource in contract["context"]["resources"]:
            self.assertTrue(Path(resource["locator"]).is_absolute())
        self.assertIn("not convergence", contract["context"]["authority"])

    def test_there_is_no_readiness_contract_because_exit_checks_only_read_recorded_evidence(self):
        lab = Lab(self)
        lab.init("A1")
        self.assertEqual([item["id"] for item in lab.ok("contract", "--campaign", lab.campaign)["exit_checks"]], list(cl.CLAUSES))
        self.assertFalse(any("readiness" in item["command"] for item in lab.ok("contract", "--campaign", lab.campaign)["exit_checks"]))

    def test_the_contract_names_the_current_scope_after_a_widening(self):
        lab = Lab(self)
        lab.init("A1")
        lab.run()
        contract = lab.ok("contract", "--campaign", lab.campaign)
        self.assertIn("Scope S1", contract["exit_condition"])
        self.assertIn("A1, B1", contract["context"]["scope"])
        self.assertIn("style=gamma", contract["context"]["scope"])
        self.assertIn("--expect-scope S1", contract["exit_checks"][0]["command"])


class UntilLoopTests(unittest.TestCase):
    """The emitted contract against the real runtime: isolated mode, a durable directory and receipt kept beside the campaign."""

    def setUp(self):
        self.lab = Lab(self)
        self.lab.init("A1")
        self.start_contract("")

    def start_contract(self, scope: str) -> None:
        """Emit the campaign's current contract and start it in isolated mode, with its state and receipt beside the campaign."""
        self.contract = self.lab.tmp / f"contract{scope}.json"
        self.lab.ok("contract", "--campaign", self.lab.campaign, "--out", self.contract)
        self.durable = self.lab.tmp / f"until{scope}"
        self.durable.mkdir()
        self.receipt = self.lab.tmp / f"receipt{scope}.json"
        started = subprocess.run([sys.executable, str(RUNTIME), "start", "--isolated", "--directory", str(self.durable),
                                  "--receipt", str(self.receipt)], input=self.contract.read_text(), capture_output=True,
                                 text=True, check=False)
        self.assertEqual(started.returncode, 0, started.stderr)
        self.packet = json.loads(started.stdout)

    def complete_contract(self, limit: int) -> list:
        """Iterate as the card says (step, verify, report) until the contract completes; return each report's status."""
        statuses = []
        for _ in range(limit):
            converged = self.one_iteration()
            quiet = self.lab.state()["iterations"][-1]["quiet"]
            _, reply = self.done("satisfied" if converged else "unsatisfied", quiet)
            statuses.append(reply["status"])
            if reply["status"] == "complete":
                break
        return statuses

    def verify(self) -> subprocess.CompletedProcess:
        return subprocess.run(self.packet["verify_script"], shell=True, executable="/bin/sh", capture_output=True, text=True,
                              check=False)

    def done(self, assessment: str, quiet: bool) -> tuple:
        report = {"classification": "trivial" if quiet else "non-trivial", "exit_assessment": assessment,
                  "continuation_assessment": "allowed", "evidence": "ran the orchestrator and read the certificate",
                  "handoff": "campaign S0; see campaign.json"}
        finished = subprocess.run(self.packet["done_argv"], input=json.dumps(report), capture_output=True, text=True, check=False)
        reply = json.loads(finished.stdout) if finished.stdout.strip() else None
        if reply and reply.get("status") == "active":
            self.packet = reply
        return finished, reply

    def one_iteration(self) -> bool:
        """Run a step, run the verify script as the operator would, and say whether the certificate converged."""
        self.lab.step()
        self.verify()
        return self.lab.certificate()["status"] == "converged"

    def test_the_contract_completes_when_the_certificate_converges_and_not_before(self):
        self.assertEqual(self.packet["status"], "active")
        self.assertEqual(self.packet["progress"]["required_trivial_reviews"], 0)
        seen = []
        for number in range(1, 4):
            converged = self.one_iteration()
            quiet = self.lab.state()["iterations"][-1]["quiet"]
            _, reply = self.done("satisfied" if converged else "unsatisfied", quiet)
            seen.append((number, converged, reply["status"]))
        self.assertEqual(seen, [(1, False, "active"), (2, False, "active"), (3, True, "complete")])  # three passes, not four
        self.assertEqual(json.loads(self.receipt.read_text())["status"], "complete")

    def test_a_widened_scope_is_completed_by_its_own_contract_and_the_campaign_then_stops_for_the_owner(self):
        self.assertEqual(self.complete_contract(5), ["active", "active", "complete"])  # S0: three passes
        widened = self.lab.step()
        self.assertEqual((widened["action"], widened["scope"]), ("widen", "S1"))
        self.start_contract("-S1")  # new files and a new receipt, as the card says
        self.assertIn("Scope S1", json.loads(self.contract.read_text())["exit_condition"])
        self.assertEqual(self.complete_contract(8), ["active", "active", "active", "complete"])  # a sweep, a fix, two quiet passes
        self.assertEqual(json.loads(self.receipt.read_text())["status"], "complete")
        stop = self.lab.step()
        self.assertEqual((stop["action"], stop["status"], stop["rung"]), ("stop", "incomplete", "E5"))
        self.assertEqual(stop["scope_certificate"], "converged")  # the scope converged; the campaign waits for the owner

    def test_a_satisfied_report_over_a_failing_check_does_not_complete(self):
        self.one_iteration()
        self.done("unsatisfied", False)
        self.lab.step()  # iteration 2: quiet, but the quiet window is not full
        verified = self.verify()
        self.assertIn("UNTIL-LOOP-CHECK C2 exit=1", verified.stdout)
        _, reply = self.done("satisfied", True)
        self.assertEqual(reply["status"], "active")
        self.assertEqual(reply["progress"]["trivial_streak"], 0)  # a failed frozen check never counts toward a streak
        failed = [item["id"] for item in reply["last_check_results"] if not item["passed"]]
        self.assertEqual(failed, ["C2"])

    def test_a_satisfied_report_without_a_recorded_verify_run_is_refused(self):
        for _ in range(3):
            self.lab.step()
        finished, reply = self.done("satisfied", True)  # the operator never ran the verify script
        self.assertIn("no verify run is recorded", finished.stdout + finished.stderr)
        self.assertNotEqual((reply or {}).get("status"), "complete")

    def test_a_change_to_the_campaign_after_the_verify_run_is_refused(self):
        for _ in range(3):
            self.lab.step()
        self.assertEqual(self.lab.certificate()["status"], "converged")
        self.verify()
        (self.lab.campaign / "late-edit.txt").write_text("a change after the checks ran\n")
        finished, reply = self.done("satisfied", True)
        self.assertIn("workspace changed after the recorded verify run", finished.stdout + finished.stderr)
        self.assertNotEqual((reply or {}).get("status"), "complete")

    def test_a_state_change_made_through_the_sanctioned_verbs_after_a_green_verify_cannot_be_reported_satisfied(self):
        """Astra's reproduction: green verification, then `unknown add --inside-claim`, then the old satisfied report."""
        for _ in range(3):
            self.lab.step()
        verified = self.verify()
        self.assertNotIn("exit=1", verified.stdout)
        self.assertEqual(self.lab.certificate()["status"], "converged")
        self.lab.ok("unknown", "--campaign", self.lab.campaign, "add", "--text", "is the oracle sensitive?", "--inside-claim")
        self.assertEqual(self.lab.certificate()["status"], "incomplete")
        finished, reply = self.done("satisfied", True)
        self.assertIn("workspace changed after the recorded verify run", finished.stdout + finished.stderr)
        self.assertNotEqual((reply or {}).get("status"), "complete")
        self.verify()  # even a fresh verify cannot pass: C7 now fails
        _, reply = self.done("satisfied", True)
        self.assertEqual(reply["status"], "active")
        self.assertIn("C7", [item["id"] for item in reply["last_check_results"] if not item["passed"]])

    def test_a_contract_frozen_at_one_scope_cannot_complete_another(self):
        for _ in range(3):
            self.lab.step()
        self.assertEqual(self.lab.step()["action"], "widen")
        verified = self.verify()
        self.assertIn(f"exit={cl.EXIT_IDENTITY}", verified.stdout)
        _, reply = self.done("satisfied", True)
        self.assertNotEqual((reply or {}).get("status"), "complete")

    def test_a_changed_check_script_fails_its_frozen_check(self):
        for _ in range(3):
            self.lab.step()
        contract = json.loads(self.contract.read_text())
        stale = contract["exit_checks"][0]["command"].replace(cl.script_sha(), "0" * 64)
        ran = subprocess.run(stale, check=False, **SH)
        self.assertEqual(ran.returncode, cl.EXIT_IDENTITY)


class CardTests(unittest.TestCase):
    """The card, references and prompts stay consistent with the script and the release rules."""

    card = (SKILL / "SKILL.md").read_text()
    docs = "\n".join(path.read_text() for path in sorted((SKILL / "references").glob("*.md")))

    def test_the_frontmatter_names_the_skill_and_matches_its_first_change_note(self):
        front = self.card.split("\n---\n", 1)[0]
        self.assertTrue(front.startswith("---\nname: closed-loop\n"))
        self.assertIn("version: 0.1.0", front)
        self.assertIn("kind: script-backed", front)
        note = ROOT / "changes" / "closed-loop" / "initial.md"
        if note.is_file():  # release.py consumes the first change note, so it exists only before the release
            self.assertIn("version: 0.1.0", note.read_text())
        for other in ("improve", "improve-loop"):  # the description must separate this skill from its neighbours
            self.assertIn(other, front)

    def test_every_relative_link_resolves_inside_the_package(self):
        import re
        for path in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md")), *sorted((SKILL / "prompts").glob("*.md"))]:
            for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", path.read_text()):
                if "://" in target:
                    continue
                self.assertTrue((path.parent / target).resolve().exists(), f"{path.name} links to {target}")
                self.assertTrue(SKILL in (path.parent / target).resolve().parents or (path.parent / target).resolve() == SKILL,
                                f"{path.name} links outside the package: {target}")

    def test_every_script_verb_is_documented_by_name(self):
        parser = cl.build_parser()
        verbs = next(action.choices for action in parser._actions if hasattr(action, "choices") and action.choices)
        documented = self.card + self.docs
        for verb in verbs:
            self.assertIn(verb, documented, f"verb {verb} is not documented")

    def test_the_seven_checks_are_defined_in_the_convergence_reference(self):
        convergence = (SKILL / "references" / "convergence.md").read_text()
        for clause in cl.CLAUSES:
            self.assertIn(f"**{clause} ", convergence)

    def test_the_prompts_exist_and_the_card_links_each_of_them(self):
        for name in ("definer", "blind-spot-hunter", "adapter-gap"):
            self.assertTrue((SKILL / "prompts" / f"{name}.md").is_file())
            self.assertIn(f"prompts/{name}.md", self.card)

    def test_the_card_binds_the_runtime_that_improve_ships_and_its_tests_validate(self):
        self.assertIn("../improve/runtime/until-loop/scripts/until_loop_ephemeral.py", self.card)
        self.assertTrue(RUNTIME.is_file())

    def test_the_orchestrator_script_uses_only_the_standard_library(self):
        import ast
        modules = {name.split(".")[0] for node in ast.walk(ast.parse(SCRIPT.read_text()))
                   for name in ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                                else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])}
        self.assertLessEqual(modules - {""}, STDLIB_IMPORTS)  # a new import is a deliberate edit of this list

    def test_the_orchestrator_parses_under_the_python_3_9_floor(self):
        import ast
        ast.parse(SCRIPT.read_text(), feature_version=(3, 9))
        ast.parse(FAKE.read_text(), feature_version=(3, 9))

    def binding_block(self) -> str:
        import re
        blocks = [block for block in re.findall(r"```sh\n(.*?)```", self.card, re.DOTALL) if "loop() {" in block]
        self.assertEqual(len(blocks), 1, "the card has exactly one binding block that defines loop()")
        return blocks[0]

    def test_the_card_binds_its_scripts_as_functions_that_work_in_bash_and_zsh_with_a_space_in_the_path(self):
        self.assertNotIn('LOOP="python3', self.card)  # a scalar command is split by bash and not split by zsh
        block = self.binding_block()
        home = Path(tempfile.mkdtemp(prefix="closed loop card "))
        self.addCleanup(shutil.rmtree, home, True)
        script = home / "closed_loop.py"
        shutil.copy(SCRIPT, script)
        lab = Lab(self)
        bound = block.replace("/path/to/skills/closed-loop/scripts/closed_loop.py", str(script))
        self.assertNotEqual(bound, block, "the card's binding block names the script path to substitute")
        shells = [name for name in ("bash", "zsh") if shutil.which(name)]
        self.assertTrue(shells)
        for shell in shells:
            done = subprocess.run([shell, "-c", bound + f'\nloop adapter-check --manifest "{lab.manifest_path}"\n'],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, (shell, done.stderr))
            self.assertTrue(json.loads(done.stdout)["ok"], shell)

    def test_the_definer_prompt_writes_a_proposal_and_a_bare_manifest_that_adapter_check_reads(self):
        definer = (SKILL / "prompts" / "definer.md").read_text()
        self.assertIn("adapter.proposed.json", definer)
        self.assertIn("definer-proposal.json", definer)
        self.assertIn("adapter-check --manifest adapter.proposed.json --proposal definer-proposal.json", definer)

    def test_the_docs_state_the_gates_and_limits_the_script_now_enforces(self):
        def flat(path) -> str:  # the docs wrap lines; a phrase may not
            return " ".join((SKILL / path).read_text().split())
        card, schema, convergence = flat("SKILL.md"), flat("references/adapter-schema.md"), flat("references/convergence.md")
        until_loop, readiness = flat("references/until-loop.md"), flat("references/readiness.md")
        for phrase in ("**verify now**", "is in flight", "yourself before `init`", "used the last of it", "`cleanup` is an adapter command",
                       "One session acts on a campaign at a time"):
            self.assertIn(phrase, card, phrase)
        for text, phrase in ((until_loop, "`!*`"), (until_loop, "git add -A -n"), (until_loop, "between the last check and the runtime's"),
                             (convergence, "no step is still running"), (convergence, "latest readiness still shows"),
                             (convergence, "scoring identity"), (schema, "launch_intents"), (schema, "readiness` refuses to run a probe"),
                             (readiness, "A proven claim needs evidence")):
            self.assertIn(phrase, text, phrase)

    def test_the_references_state_the_limits_the_script_enforces(self):
        schema = (SKILL / "references" / "adapter-schema.md").read_text()
        for word in ("timeout_seconds", "pin", "combinations", "cleanup"):
            self.assertIn(word, schema)
        self.assertIn("overshoot", self.card + self.docs)  # the budget is checked between steps, not inside one


if __name__ == "__main__":
    unittest.main()
