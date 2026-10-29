"""No-model checks for v2 mission-anchored review and its independent judge."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import judge
import review


def discovery(*, ident="d-1", materiality="material", confidence="low", target="shiploop",
              eligible=False, disposition="owner_review", clause=None, relationship="novel",
              challenge="The run suggests a useful design challenge not stated by the specification.", files=None):
    files = files if files is not None else (["skills/shiploop/SKILL.md"] if eligible else [])
    return {
        "id": ident,
        "title": "Preserve the repeated setup decision",
        "evidence": [{"reference": "transcript.md:14", "observation": "The run repeated the same setup step.",
                      "interpretation": "A reusable setup decision may be missing."}],
        "mission_anchor": {"clause_id": clause, "relationship": relationship, "challenge": challenge},
        "materiality": materiality,
        "confidence": confidence,
        "potential_impact": "The repeated setup could add avoidable turns to later runs.",
        "alternatives": ["The repeated step may be necessary for a clean start."],
        "next_experiment": "Compare one follow-on run with and without the recorded setup decision.",
        "target": target,
        "files": files,
        "proposal": "Record the stable setup decision in a reusable ShipLoop reference.",
        "implementation_eligible": eligible,
        "proposed_disposition": disposition,
    }


def review_payload(discoveries=None):
    return {
        "outcome": "The run delivered the request.",
        "version": 2,
        "learnings": [],
        "missing_considerations": [],
        "optimizations": [],
        "discoveries": discoveries if discoveries is not None else [discovery()],
        "harness": {},
    }


def exited():
    return {"status": "exited", "returncode": 0, "elapsed_seconds": 0.1}


class ReviewDiscoveryContractTest(unittest.TestCase):
    def test_codex_reviewer_is_read_only_and_records_its_requested_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            agent = mock.Mock()
            agent.env.return_value = {}
            agent.argv.return_value = ["codex", "exec", "-s", "danger-full-access"]
            agent.translator.return_value = None
            with mock.patch.object(review.hosts, "host", return_value=agent), \
                    mock.patch.object(review.hosts, "run_agent", return_value=exited()) as launch, \
                    mock.patch.object(review.hosts, "final_text", return_value=json.dumps(review_payload([]))):
                verdict = review.review(run_dir, skill_root=ROOT / "skills" / "shiploop")
            argv = launch.call_args.args[0]
            self.assertEqual(argv[argv.index("-s") + 1], "read-only")
            self.assertEqual(verdict["driver"], {"host": "codex", "model": "gpt-6-astra", "effort": "xhigh"})

    def test_a_material_clause_free_challenge_is_valid_and_survives_as_owner_work(self):
        payload = review_payload()
        payload["validity"] = review.validity(payload, exited())
        self.assertEqual(payload["validity"]["status"], "valid")
        self.assertTrue(payload["validity"]["discovery_qualified"])
        verdict = {"validity": {"status": "valid"}, "assessments": [
            {"id": "d-1", "status": "disputed", "reason": "The transcript does not establish this change.",
             "evidence": ["transcript.md:14 shows repeated setup, not the cost of a reusable decision."],
             "disposition": "investigate"}]}
        routed = judge.admitted(payload, verdict)
        self.assertEqual(routed["implementation"], [])
        self.assertEqual(routed["owner_challenges"][0]["routing"], "owner_review")
        self.assertEqual(routed["owner_challenges"][0]["id"], "d-1")
        payload["actionable"] = []
        payload["judge"] = verdict
        self.assertFalse(review.counts_as_clean(payload), "a material challenge remains pending even if disputed")

    def test_an_ordinary_run_needs_no_novelty_and_can_be_clean_after_a_valid_judge(self):
        payload = review_payload([])
        payload["validity"] = review.validity(payload, exited())
        payload["actionable"] = []
        payload["judge"] = {"validity": {"status": "valid"}, "assessments": []}
        self.assertEqual(payload["validity"]["status"], "valid")
        self.assertEqual(judge.admitted(payload, payload["judge"]),
                         {"implementation": [], "owner_challenges": [], "harness": []})
        self.assertTrue(review.counts_as_clean(payload))
        self.assertIn("Do not invent a discovery", review.reviewer_prompt(Path("/run"), Path("/skill")))

    def test_v2_rejects_malformed_category_and_discovery_findings(self):
        valid_legacy_finding = {"title": "Keep a receipt", "evidence": "transcript.md:8", "proposal": "Keep it",
                                "files": ["skills/shiploop/SKILL.md"], "severity": "material",
                                "preserves_premise": True, "premise_note": "The script remains authoritative."}
        for payload in (
            {**review_payload([]), "learnings": ["not a finding"]},
            {**review_payload([]), "learnings": [{**valid_legacy_finding, "files": "wrong"}]},
            {**review_payload([discovery()]), "discoveries": [{**discovery(), "evidence": [{"reference": "x"}]}]},
        ):
            with self.subTest(payload=payload):
                checked = review.validity(payload, exited())
                self.assertEqual(checked["status"], "invalid")
                self.assertFalse(checked["discovery_qualified"])
                self.assertFalse(review.counts_as_clean({"validity": checked, "actionable": [],
                                                         "discoveries": payload.get("discoveries", [])}))
                review.render_markdown(payload)

    def test_eligibility_requires_an_existing_aligned_clause_and_nonconflicting_route(self):
        no_authority = discovery(eligible=True, disposition="implement")
        contradiction = discovery(eligible=True, disposition="implement", clause="S-1", relationship="challenges")
        for candidate in (no_authority, contradiction):
            with self.subTest(candidate=candidate):
                checked = review.validity(review_payload([candidate]), exited())
                self.assertEqual(checked["status"], "invalid")
                self.assertIn("implementation eligibility", checked["reason"])

    def test_eligible_findings_need_an_existing_clause_and_candidate_paths(self):
        missing_clause = discovery(eligible=True, disposition="implement", clause="S-99", relationship="supports")
        harness_path = discovery(eligible=True, disposition="implement", clause="S-1", relationship="supports",
                                 files=["test/shiploop_e2e/review.py"])
        traversal = discovery(eligible=True, disposition="implement", clause="S-1", relationship="supports",
                              files=["skills/shiploop/../../README.md"])
        for candidate in (missing_clause, harness_path, traversal):
            with self.subTest(candidate=candidate):
                self.assertEqual(review.validity(review_payload([candidate]), exited())["status"], "invalid")

    def test_harness_findings_stay_separate_from_shiploop_implementation(self):
        candidate = discovery(target="harness", clause="S-1", relationship="supports", disposition="investigate")
        payload = review_payload([candidate])
        self.assertEqual(review.validity(payload, exited())["status"], "valid")
        verdict = {"validity": {"status": "valid"}, "assessments": [
            {"id": "d-1", "status": "supported", "reason": "Run evidence supports the observation.",
             "evidence": ["metrics.json shows repeated stage starts."], "disposition": "investigate"}]}
        routed = judge.admitted(payload, verdict)
        self.assertEqual(routed["implementation"], [])
        self.assertEqual([item["id"] for item in routed["harness"]], ["d-1"])
        self.assertEqual(routed["owner_challenges"], [])

    def test_legacy_reviews_render_but_cannot_claim_discovery_qualified_completion(self):
        legacy = {"outcome": "Completed.", "learnings": [], "missing_considerations": [], "optimizations": [],
                  "harness": {}}
        checked = review.validity(legacy, exited())
        self.assertEqual(checked, {"status": "valid", "reason": None})
        self.assertFalse(review.counts_as_clean({"validity": checked, "actionable": []}))
        self.assertIn("## Learnings", review.render_markdown(legacy))

    def test_reviewer_exit_status_must_agree_with_return_code(self):
        checked = review.validity(review_payload([]), {"status": "exited", "returncode": 1})
        self.assertEqual(checked["status"], "failed")


class JudgeContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()
        self.review = review_payload()

    def parsed(self, assessments=None, *, identity=None):
        return {"review_sha256": identity or judge.review_sha256(self.run_dir, self.review),
                "assessments": assessments if assessments is not None else [{
                    "id": "d-1", "status": "supported", "reason": "The source supports the observation.",
                    "evidence": ["transcript.md:14 shows the repeated setup."], "disposition": "investigate"}]}

    def test_judge_requires_a_one_to_one_exact_id_and_review_identity_match(self):
        missing = judge.validity(self.parsed([]), exited(), self.review,
                                 judge.review_sha256(self.run_dir, self.review))
        duplicate = judge.validity(self.parsed([self.parsed()["assessments"][0], self.parsed()["assessments"][0]]),
                                   exited(), self.review, judge.review_sha256(self.run_dir, self.review))
        mismatch = judge.validity(self.parsed(identity="0" * 64), exited(), self.review,
                                  judge.review_sha256(self.run_dir, self.review))
        self.assertEqual(missing["status"], "invalid")
        self.assertIn("missing assessments", missing["reason"])
        self.assertEqual(duplicate["status"], "invalid")
        self.assertIn("duplicated", duplicate["reason"])
        self.assertEqual(mismatch["status"], "invalid")
        self.assertIn("not bound", mismatch["reason"])

    def test_a_sealed_review_mismatch_does_not_fall_back_to_a_new_canonical_identity(self):
        sealed = self.run_dir / "review.json"
        sealed.write_text(json.dumps(self.review) + "\n")
        changed = {**self.review, "outcome": "A different review."}
        with self.assertRaisesRegex(ValueError, "does not match the sealed review file"):
            judge.review_sha256(self.run_dir, changed)

    def test_judge_exit_status_must_agree_with_return_code(self):
        parsed = self.parsed()
        checked = judge.validity(parsed, {"status": "exited", "returncode": 1}, self.review,
                                 judge.review_sha256(self.run_dir, self.review))
        self.assertEqual(checked["status"], "failed")

    def test_valid_judge_admits_only_supported_eligible_material_shiploop_findings(self):
        eligible = discovery(eligible=True, disposition="implement", clause="S-1", relationship="supports")
        payload = review_payload([eligible])
        assessment = {"id": "d-1", "status": "supported", "reason": "The run evidence supports the improvement.",
                      "evidence": ["transcript.md:14 shows the source behavior."], "disposition": "implement"}
        result = {"review_sha256": judge.review_sha256(self.run_dir, payload),
                  "validity": {"status": "valid"}, "assessments": [assessment]}
        self.assertEqual(judge.admitted(payload, result)["implementation"][0]["id"], "d-1")
        result["assessments"][0]["status"] = "unknown"
        self.assertEqual(judge.admitted(payload, result)["implementation"], [])
        self.assertEqual(judge.admitted(payload, result)["owner_challenges"][0]["routing"], "investigate")

    def test_fresh_judge_uses_read_only_codex_astra_and_preserves_discoveries_on_failure(self):
        launched = []
        outputs = [self.parsed(), self.parsed()]

        class FakeCodex:
            def env(self, home):
                return {"HOME": str(home), "CODEX_HOME": str(home / ".codex")}

            def argv(self, **kwargs):
                prompt_file = Path(kwargs["prompt_file"])
                prompt_file.write_text(kwargs["prompt"])
                return ["codex", "exec", "--json", "-m", kwargs["model"], "-s", "danger-full-access",
                        "-c", f"model_reasoning_effort={kwargs['effort']}", "-C", str(kwargs["cwd"]), kwargs["prompt"]]

            def translator(self):
                return None

        def fake_run_agent(argv, cwd, env, events_path, stderr_path, timeout, translate=None):
            launched.append((list(argv), dict(env), Path(events_path), Path(stderr_path)))
            Path(events_path).write_text("")
            Path(stderr_path).write_text("offline failure")
            return {"status": "failed", "returncode": 1, "elapsed_seconds": 0.2}

        with mock.patch.object(judge.hosts, "host", return_value=FakeCodex()) as get_host, \
                mock.patch.object(judge.hosts, "run_agent", side_effect=fake_run_agent), \
                mock.patch.object(judge.hosts, "final_text", side_effect=lambda _path: json.dumps(outputs.pop(0))):
            first = judge.judge(self.run_dir, self.review, assessment_id="fresh-a")
            second = judge.judge(self.run_dir, self.review, assessment_id="fresh-b")

        self.assertEqual(get_host.call_args_list[0].args, ("codex", "codex"))
        self.assertEqual(len(launched), 2, "a failed judge is not retried through another host")
        self.assertEqual([item[0][item[0].index("-s") + 1] for item in launched], ["read-only", "read-only"])
        self.assertTrue(all("gpt-6-astra" in item[0] for item in launched))
        self.assertTrue(all("model_reasoning_effort=xhigh" in item[0] for item in launched))
        self.assertNotEqual(launched[0][1]["HOME"], launched[1][1]["HOME"])
        self.assertEqual(first["validity"]["status"], "failed")
        self.assertEqual(second["validity"]["status"], "failed")
        self.assertEqual(first["admitted"]["implementation"], [])
        self.assertEqual(first["admitted"]["owner_challenges"][0]["id"], "d-1")
        self.assertTrue(Path(first["judge_receipt"]["verdict"]).is_file())
        self.assertTrue(Path(second["judge_receipt"]["verdict"]).is_file())

    def test_review_defaults_to_astra_xhigh_and_assessment_ids_keep_separate_receipts(self):
        calls = []
        reply = json.dumps(review_payload([]))

        class FakeReviewer:
            def env(self, home):
                return {"HOME": str(home)}

            def argv(self, **kwargs):
                calls.append(kwargs)
                Path(kwargs["prompt_file"]).write_text(kwargs["prompt"])
                return ["fake-reviewer", "-s", "danger-full-access"]

            def translator(self):
                return None

        def fake_run_agent(_argv, _cwd, _env, events_path, stderr_path, _timeout, translate=None):
            Path(events_path).write_text("")
            Path(stderr_path).write_text("")
            return exited()

        with mock.patch.object(review.hosts, "host", return_value=FakeReviewer()), \
                mock.patch.object(review.hosts, "run_agent", side_effect=fake_run_agent), \
                mock.patch.object(review.hosts, "final_text", return_value=reply):
            first = review.review(self.run_dir, prior_learnings="", assessment_id="review-a")
            second = review.review(self.run_dir, prior_learnings="", model="gpt-6.1-terra", effort="high",
                                   assessment_id="review-b")

        self.assertEqual((calls[0]["model"], calls[0]["effort"]), ("gpt-6-astra", "xhigh"))
        self.assertEqual((calls[1]["model"], calls[1]["effort"]), ("gpt-6.1-terra", "high"))
        first_receipt = first["review_receipt"]
        second_receipt = second["review_receipt"]
        self.assertNotEqual(first_receipt["review_json"], second_receipt["review_json"])
        self.assertTrue(Path(first_receipt["review_json"]).is_file())
        self.assertTrue(Path(second_receipt["review_json"]).is_file())
        self.assertEqual(judge.review_sha256(self.run_dir, first),
                         hashlib.sha256(Path(first_receipt["review_json"]).read_bytes()).hexdigest())
        self.assertEqual(judge.review_sha256(self.run_dir, {**first, "judge": {"status": "valid"}}),
                         judge.review_sha256(self.run_dir, first), "an in-memory judge attachment does not change the seal")


if __name__ == "__main__":
    unittest.main()
