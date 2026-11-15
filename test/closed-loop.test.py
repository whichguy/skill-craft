#!/usr/bin/env python3
"""closed-loop: the orchestrator (skills/closed-loop/scripts/closed_loop.py) against a fake subject, and against the real Until Loop.

The fake subject (test/fixtures/closed-loop-fake/adapter.py) has three planted defects in three styles of case, a scripted improver
and an idempotent step protocol, so every property here is deterministic and no model is called. The classes follow the plan
(docs/closed-loop-plan-2026-11-15.md): manifest and execution boundary, readiness as script-proven claims, state that is never
silently recreated, the seven-check convergence certificate with its incomplete outcome, the escalation demo (converge, widen on an
uncovered style, find what only the new case exposes, stop on an owner-only rung), duplicate resume, aggregate quota, and an
emitted contract that the vendored Until Loop runtime accepts, completes on the script-owned certificate and refuses to complete on
a failing or stale check.
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
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}


def git(*args, cwd=None):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
                   cwd=cwd, check=True, capture_output=True, text=True, env=GIT_ENV)


class Lab:
    """A throwaway campaign: a workspace, a manifest over the fake subject, and helpers that drive the orchestrator in process."""

    def __init__(self, case: unittest.TestCase, linked_worktree: bool = False, **overrides) -> None:
        self.case = case
        self.tmp = Path(tempfile.mkdtemp(prefix="closed-loop-test-")).resolve()  # resolved: Until Loop refuses a /var symlink
        case.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = self.tmp / "ws"
        if linked_worktree:
            repo = self.tmp / "repo"
            repo.mkdir()
            git("init", "-q", cwd=repo)
            (repo / "README").write_text("a subject repository\n")
            git("add", "-A", cwd=repo)
            git("commit", "-q", "-m", "initial", cwd=repo)
            git("worktree", "add", "-q", "-b", "campaign", str(self.ws), cwd=repo)
        else:
            self.ws.mkdir()
        self.campaign = self.tmp / "campaign"
        self.manifest_path = self.tmp / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest(**overrides), indent=2))

    @staticmethod
    def manifest(**overrides) -> dict:
        commands = {verb: [sys.executable, str(FAKE), verb] for verb in ("cases", "records", "identity", "probe")}
        commands["step"] = [sys.executable, str(FAKE), "step"]
        base = {
            "contract": "closed-loop-adapter/1", "subject": {"name": "fake", "mission": ["planted defects d1 to d3"]},
            "execution": {"cwd": ".", "env_allow": [], "capability": "writes-worktree",
                          "cleanup": [sys.executable, str(FAKE), "cleanup"]},
            "commands": commands,
            "claims": {"cases.runs:A1": {"effect": "effectful"}, "grading.scores": {"effect": "effectful"},
                       "grading.sensitive:d1": {"effect": "effectful"}, "grading.calibrated:fake": {"effect": "read-only"},
                       "improver.bounded": {"effect": "effectful"}, "improver.invocable": {"effect": "effectful"}},
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

    def init(self, cases="A1", *extra):
        return self.ok("init", "--manifest", self.manifest_path, "--campaign", self.campaign, "--workspace", self.ws,
                       "--cases", cases, *extra)

    def config(self, **updates) -> None:
        path = self.ws / "fake-config.json"
        current = json.loads(path.read_text()) if path.is_file() else {}
        current.update(updates)
        path.write_text(json.dumps(current))

    def state(self) -> dict:
        return json.loads((self.campaign / "campaign.json").read_text())

    def write_state(self, state: dict) -> None:
        (self.campaign / "campaign.json").write_text(json.dumps(state))

    def step(self):
        return self.ok("step", "--campaign", self.campaign)

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

    def starts(self) -> list:
        path = self.ws / "fake-starts.log"
        return path.read_text().split() if path.is_file() else []


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

    def test_the_boundary_hash_follows_commands_and_authority_not_descriptive_text(self):
        base = Lab.manifest()
        changed = Lab.manifest()
        changed["commands"]["cases"] = [sys.executable, str(FAKE), "cases", "--extra"]
        reworded = Lab.manifest()
        reworded["subject"]["mission"] = ["something else entirely"]
        wider = Lab.manifest()
        wider["authority"]["owner_only_requires"] = []
        self.assertNotEqual(cl.boundary_hash(base), cl.boundary_hash(changed))
        self.assertNotEqual(cl.boundary_hash(base), cl.boundary_hash(wider))
        self.assertEqual(cl.boundary_hash(base), cl.boundary_hash(reworded))

    def test_a_manifest_changed_after_init_is_refused(self):
        lab = Lab(self)
        lab.init()
        lab.manifest_path.write_text(json.dumps(Lab.manifest(quiet_window=3)))
        code, _, err = lab.cli("status", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("manifest changed since init", err)

    def test_the_adapter_runs_in_a_controlled_environment(self):
        script = ("import json, os; print(json.dumps({'visible': os.environ.get('CL_TEST_VISIBLE'), "
                  "'hidden': os.environ.get('CL_TEST_HIDDEN'), 'workspace': os.environ.get('CLOSED_LOOP_WORKSPACE')}))")
        manifest = Lab.manifest()
        manifest["execution"]["env_allow"] = ["CL_TEST_VISIBLE"]
        manifest["commands"]["identity"] = [sys.executable, "-c", script]
        with mock.patch.dict(os.environ, {"CL_TEST_VISIBLE": "yes", "CL_TEST_HIDDEN": "no"}):
            out = cl.call_adapter(manifest, ROOT, "identity", workspace="/somewhere")
        self.assertEqual(out, {"visible": "yes", "hidden": None, "workspace": "/somewhere"})


class ReadinessTests(unittest.TestCase):
    def test_effectful_claims_are_not_probed_until_the_owner_ratifies(self):
        lab = Lab(self)
        lab.init()
        before = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        self.assertFalse(before["start_ok"])
        self.assertEqual(before["claims"]["cases.runs:A1"]["state"], "declared")
        self.assertIn("not run", before["claims"]["cases.runs:A1"]["evidence"])
        self.assertEqual(before["claims"]["grading.calibrated:fake"]["state"], "unmeasured")  # read-only: probed
        self.assertIsNotNone(before["claims"]["grading.calibrated:fake"]["evidence"] or "probed")

    def test_ratification_is_the_owners_act(self):
        lab = Lab(self)
        lab.init()
        code, _, err = lab.cli("ratify", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("owner's decision", err)
        self.assertIsNone(lab.state()["ratification"])
        out = lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved", "--note", "boundary read")
        self.assertEqual(out["ratified"]["boundary_sha256"], cl.boundary_hash(Lab.manifest()))

    def test_after_ratification_claims_are_proven_and_say_what_they_allow(self):
        lab = Lab(self)
        lab.init()
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        report = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--require-start")
        self.assertTrue(report["start_ok"])
        self.assertEqual(report["claims"]["cases.runs:A1"]["state"], "runs")
        self.assertEqual(report["claims"]["grading.scores"]["state"], "scores")
        self.assertEqual(report["claims"]["improver.invocable"]["state"], "invocable")
        allowed = " | ".join(report["allowed_claims"])
        self.assertIn("labelled 'stated, not measured'", allowed)
        self.assertIn("no quality claim is allowed yet", allowed)  # the oracle is valid but not shown sensitive
        self.assertIn("plumbing only", report["note"])

    def test_sensitivity_and_calibration_unlock_the_claims_they_prove(self):
        lab = Lab(self)
        lab.init()
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(sensitive={"d1": True}, calibrated={"fake": True})
        report = lab.ok("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign)
        allowed = " | ".join(report["allowed_claims"])
        self.assertIn("quality claims about d1", allowed)
        self.assertIn("measured efficiency on profile fake", allowed)

    def test_an_insensitive_evaluator_scores_but_is_not_sensitive_and_a_missing_bound_blocks_the_start(self):
        lab = Lab(self)
        lab.init()
        lab.ok("ratify", "--campaign", lab.campaign, "--yes-owner-approved")
        lab.config(bounded=False)
        code, report, _ = lab.cli("readiness", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--require-start")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertEqual(report["claims"]["grading.scores"]["state"], "scores")  # valid scores, not "declared"
        self.assertEqual(report["claims"]["grading.sensitive:d1"]["state"], "unknown")
        self.assertIn("no improver.bounded claim has reached 'bounded'", report["blocked"])

    def test_a_probe_state_outside_the_claims_ladder_is_refused(self):
        manifest = Lab.manifest()
        with mock.patch.object(cl, "call_adapter", return_value={"state": "magnificent"}), \
                self.assertRaisesRegex(cl.LoopError, "allowed: declared, runs"):
            cl.claim_states(dict(manifest, claims={"cases.runs:A1": {"effect": "read-only"}}),
                            {"manifest_dir": ROOT, "dir": None}, None, True)

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


class StateTests(unittest.TestCase):
    def test_missing_state_is_an_error_and_is_never_recreated(self):
        lab = Lab(self)
        code, _, err = lab.cli("status", "--campaign", lab.campaign)
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("run init", err)
        self.assertFalse((lab.campaign / "campaign.json").exists())

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

    def test_init_never_reinitialises_in_place_and_validates_its_inputs(self):
        lab = Lab(self)
        lab.init()
        code, _, err = lab.cli("init", "--manifest", lab.manifest_path, "--campaign", lab.campaign, "--workspace", lab.ws,
                               "--cases", "A1")
        self.assertEqual(code, cl.EXIT_ERROR)
        self.assertIn("already exists", err)
        other = Lab(self)
        for cases, expected in (("A9", "not in the adapter's catalog"), ("", "needs at least one case")):
            code, _, err = other.cli("init", "--manifest", other.manifest_path, "--campaign", other.campaign, "--workspace",
                                     other.ws, "--cases", cases)
            self.assertEqual(code, cl.EXIT_ERROR)
            self.assertIn(expected, err)

    def test_saves_are_atomic_and_leave_no_temporary_file(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        self.assertEqual(sorted(path.name for path in lab.campaign.iterdir() if path.name.startswith("campaign.json")),
                         ["campaign.json"])

    def test_queries_never_write_inside_the_workspace(self):
        lab = Lab(self)
        lab.init()
        lab.step()
        before = sorted(str(path.relative_to(lab.ws)) for path in lab.ws.rglob("*"))
        for verb in ("certificate", "coverage", "status", "next"):
            lab.cli(verb, "--campaign", lab.campaign)
        for clause in cl.CLAUSES:
            lab.cli("check", "--campaign", lab.campaign, "--clause", clause)
        self.assertEqual(sorted(str(path.relative_to(lab.ws)) for path in lab.ws.rglob("*")), before)


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
        iterations = lab.state()["iterations"]
        self.assertEqual([item["quiet"] for item in iterations], [False, True, True])
        self.assertEqual(iterations[0]["build_before"], "b0")
        self.assertEqual(iterations[0]["build_after"], "b1")

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

    def test_a_dropped_record_resolves_only_with_evidence_and_a_promoted_one_only_when_verified(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        for status, evidence, blocks in (("dropped", None, True), ("dropped", "the prediction was refuted", False),
                                         ("promoted", "predicted effect seen", True), ("verified", None, False)):
            lab.config(extra_records=[{"id": "R-y", "material": True, "target": "subject", "status": status,
                                       "evidence": evidence}])
            self.assertEqual(lab.cli("check", "--campaign", lab.campaign, "--clause", "C1")[0],
                             cl.EXIT_NOT_READY if blocks else cl.EXIT_OK, (status, evidence))

    def test_an_invalid_review_is_not_quiet_and_delays_convergence_by_two_quiet_passes(self):
        lab = Lab(self)
        lab.init()
        lab.config(invalid_review_at=[3])
        for _ in range(3):
            lab.step()
        third = lab.state()["iterations"][2]
        self.assertFalse(third["quiet"])
        self.assertTrue(any("review was not valid" in reason for reason in third["quiet_reasons"]))
        self.assertEqual(lab.cli("check", "--campaign", lab.campaign, "--clause", "C7")[0], cl.EXIT_NOT_READY)  # in the last two
        lab.step()  # iteration 4 is quiet, but the invalid iteration 3 is still inside the last two
        self.assertEqual(lab.certificate()["status"], "incomplete")
        self.assertEqual(lab.cli("check", "--campaign", lab.campaign, "--clause", "C2")[0], cl.EXIT_NOT_READY)
        lab.step()  # iteration 5: the last two, 4 and 5, are quiet
        self.assertEqual(lab.certificate()["status"], "converged")
        self.assertEqual(len(lab.state()["iterations"]), 5)

    def test_an_invalid_review_inside_the_window_fails_c7_with_its_reason(self):
        lab = Lab(self)
        lab.init()
        lab.config(invalid_review_at=[2])
        lab.step()
        lab.step()
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C7")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("invalid or incomplete evidence" in reason for reason in out["reasons"]))

    def test_an_unknown_or_missing_baseline_blocks_green(self):
        lab = Lab(self)
        lab.init()
        lab.config(baseline={"A1": "none"})
        for _ in range(3):
            lab.step()
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C3")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("no comparable baseline" in reason for reason in out["reasons"]))
        self.assertEqual(lab.certificate()["status"], "incomplete")  # unknown blocks: the scope cannot converge on it

    def test_the_coverage_statement_must_be_complete(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        state = lab.state()
        del state["scopes"][0]["not_covered"]["style=gamma"]
        lab.write_state(state)
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C4")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("style=gamma is neither covered nor listed" in reason for reason in out["reasons"]))

    def test_cleanup_and_the_quick_tier_receipt_need_positive_evidence_for_the_current_build(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        for field, value, expect in (("cleanup", {"verified": False}, "no positive cleanup evidence"),
                                     ("tier", {"green": True, "build": "b0"}, "quick-tier receipt is for build"),
                                     ("tier", {"green": False}, "no green quick-tier receipt")):
            state = lab.state()
            original = state["iterations"][-1][field]
            state["iterations"][-1][field] = value
            lab.write_state(state)
            out = lab.cli("check", "--campaign", lab.campaign, "--clause", "C5")[1]
            self.assertTrue(any(expect in reason for reason in out["reasons"]), out["reasons"])
            state["iterations"][-1][field] = original
            lab.write_state(state)
        self.assertEqual(lab.cli("check", "--campaign", lab.campaign, "--clause", "C5")[0], cl.EXIT_OK)

    def test_a_promoted_candidate_without_acceptance_for_it_keeps_the_scope_incomplete(self):
        lab = Lab(self)
        lab.init()
        lab.config(no_acceptance=True)
        for _ in range(3):
            lab.step()
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C6")
        self.assertEqual(code, cl.EXIT_NOT_READY)
        self.assertTrue(any("without acceptance evidence" in reason for reason in out["reasons"]))
        lab.config(no_acceptance=False)
        state = lab.state()
        state["iterations"][0]["acceptance"] = {"candidate": "some-other-hash", "evidence": "x"}  # names a different candidate
        lab.write_state(state)
        self.assertEqual(lab.cli("check", "--campaign", lab.campaign, "--clause", "C6")[0], cl.EXIT_NOT_READY)

    def test_with_nothing_promoted_the_certificate_says_there_is_no_candidate(self):
        lab = Lab(self)
        lab.init()
        lab.config(extra_records=[])
        (lab.ws / "subject-state.json").write_text(json.dumps({"version": 1, "fixed": ["d1"], "known": ["d1"]}))
        for _ in range(2):
            lab.step()
        out = lab.cli("check", "--campaign", lab.campaign, "--clause", "C6")[1]
        self.assertTrue(out["pass"])
        self.assertEqual(out["detail"]["note"], "no candidate")

    def test_an_unknown_inside_the_claim_blocks_until_it_is_resolved_and_one_outside_does_not(self):
        lab = Lab(self)
        self.converge_scope_zero(lab)
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "noise on the other driver is unmeasured")
        self.assertEqual(lab.certificate()["status"], "converged")  # outside the claim: listed, not blocking
        lab.ok("unknown", "--campaign", lab.campaign, "add", "--text", "is the oracle sensitive to d1?", "--inside-claim")
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C7")
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
        self.assertEqual(lab.cli("next", "--campaign", lab.campaign)[1]["action"], "start")  # it re-evaluates, it does not stop
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
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C1", "--expect-sha", cl.script_sha())
        self.assertEqual((code, out["script_sha256"]), (cl.EXIT_OK, cl.script_sha()))
        code, out, _ = lab.cli("check", "--campaign", lab.campaign, "--clause", "C1", "--expect-sha", "0" * 64)
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
        lab.ok("task", "--campaign", lab.campaign, "done", "--id", task["id"], "--result", json.dumps({"proposed": []}))
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


class QuotaTests(unittest.TestCase):
    def test_an_exhausted_budget_ends_the_scope_incomplete_never_converged(self):
        lab = Lab(self)
        lab.init("A1", "--budget", "seconds=25,turns=1000")
        actions = lab.run()
        self.assertEqual([item["action"] for item in actions], ["start", "start", "start", "stop"])
        self.assertEqual((actions[-1]["status"], actions[-1]["reason"]), ("incomplete", "budget used: seconds"))
        self.assertEqual(json.loads((lab.campaign / "report.json").read_text())["campaign_status"], "incomplete")

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
        for bad in ("seconds", "seconds=abc", "seconds=0", "=5"):
            with self.assertRaises(cl.LoopError):
                cl.parse_budget(bad)


class ContractTests(unittest.TestCase):
    def test_the_scope_contract_has_script_owned_checks_and_no_native_streak(self):
        lab = Lab(self)
        lab.init("A1")
        out_file = lab.tmp / "contract.json"
        contract = lab.ok("contract", "--campaign", lab.campaign, "--kind", "scope", "--out", out_file)
        self.assertEqual(json.loads(out_file.read_text()), contract)
        self.assertEqual(contract["required_trivial_reviews"], 0)  # one counter: the script-owned quiet window
        self.assertEqual(contract["workspace"], str(lab.ws))
        self.assertEqual([item["id"] for item in contract["exit_checks"]], list(cl.CLAUSES))
        for item in contract["exit_checks"]:
            self.assertEqual(item["clause"], cl.CLAUSE_TEXT[item["id"]])
            self.assertIn(f"--expect-sha {cl.script_sha()}", item["command"])
            self.assertIn(item["id"], item["command"])
            self.assertEqual(subprocess.run(["/bin/sh", "-n", "-c", item["command"]], check=False).returncode, 0)
        for text in cl.CLAUSE_TEXT.values():
            self.assertIn(text, contract["exit_condition"])
        self.assertEqual(sorted(contract["context"]), ["authority", "environment", "request", "resources", "scope"])
        self.assertTrue(all(str(value).strip() for key, value in contract["context"].items() if key != "resources"))
        for resource in contract["context"]["resources"]:
            self.assertTrue(Path(resource["locator"]).is_absolute())
        self.assertIn("not convergence", contract["context"]["authority"])

    def test_the_readiness_contract_checks_the_start_rule(self):
        lab = Lab(self)
        lab.init("A1")
        contract = lab.ok("contract", "--campaign", lab.campaign, "--kind", "readiness")
        self.assertEqual([item["id"] for item in contract["exit_checks"]], ["R-START"])
        self.assertIn("--require-start", contract["exit_checks"][0]["command"])
        self.assertEqual(contract["required_trivial_reviews"], 0)

    def test_the_contract_names_the_current_scope_after_a_widening(self):
        lab = Lab(self)
        lab.init("A1")
        lab.run()
        contract = lab.ok("contract", "--campaign", lab.campaign, "--kind", "scope")
        self.assertIn("Scope S1", contract["exit_condition"])
        self.assertIn("A1, B1", contract["context"]["scope"])
        self.assertIn("style=gamma", contract["context"]["scope"])


class UntilLoopTests(unittest.TestCase):
    """The emitted contract against the real runtime, in a linked git worktree, isolated mode, durable directory and receipt."""

    def setUp(self):
        self.lab = Lab(self, linked_worktree=True)
        self.lab.init("A1")
        contract = self.lab.tmp / "contract.json"
        self.lab.ok("contract", "--campaign", self.lab.campaign, "--kind", "scope", "--out", contract)
        self.durable = self.lab.tmp / "until"
        self.durable.mkdir()
        self.receipt = self.lab.tmp / "receipt.json"
        started = subprocess.run([sys.executable, str(RUNTIME), "start", "--isolated", "--directory", str(self.durable),
                                  "--receipt", str(self.receipt)], input=contract.read_text(), capture_output=True, text=True,
                                 check=False)
        self.assertEqual(started.returncode, 0, started.stderr)
        self.packet = json.loads(started.stdout)

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

    def test_a_workspace_change_after_the_verify_run_is_refused(self):
        for _ in range(3):
            self.lab.step()
        self.assertEqual(self.lab.certificate()["status"], "converged")
        self.verify()
        (self.lab.ws / "late-edit.txt").write_text("a change after the checks ran\n")
        finished, reply = self.done("satisfied", True)
        self.assertIn("workspace changed after the recorded verify run", finished.stdout + finished.stderr)
        self.assertNotEqual((reply or {}).get("status"), "complete")

    def test_a_changed_check_script_fails_its_frozen_check(self):
        for _ in range(3):
            self.lab.step()
        contract = json.loads((self.lab.tmp / "contract.json").read_text())
        stale = contract["exit_checks"][0]["command"].replace(cl.script_sha(), "0" * 64)
        ran = subprocess.run(stale, shell=True, executable="/bin/sh", capture_output=True, text=True, check=False)
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
        self.assertIn("version: 0.1.0", (ROOT / "changes" / "closed-loop" / "initial.md").read_text())
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
        self.assertLessEqual(modules - {""}, set(sys.stdlib_module_names))


if __name__ == "__main__":
    unittest.main()
