#!/usr/bin/env python3
"""Regression controls for evidence identity, effects, interruption and recovery."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
import evidence
import run

spec = importlib.util.spec_from_file_location("e2e_fake_hosts", ROOT / "test/shiploop-e2e.test.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class EvidenceTests(unittest.TestCase):
    def test_directory_permissions_are_part_of_the_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "directory"
            directory.mkdir(mode=0o755)
            before = evidence.tree_digest(root)
            directory.chmod(0o700)
            self.assertNotEqual(evidence.tree_digest(root), before)

    def test_stale_done_cannot_win_over_current_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name, status in (("old", "done"), ("current", "active")):
                directory = out / name
                directory.mkdir()
                run.store.write_record(directory / "state.md", {"status": status})
                (directory / "report.html").write_text("done")
            grade = run.grade_shiploop(out)
            self.assertFalse(grade["pass"])
            self.assertEqual(grade["evidence_status"], "incomplete")
            evidence.atomic_json(out / "invocation.json", {"invocation_id": "now"})
            evidence.atomic_json(out / "run-binding.json", {"invocation_id": "now", "run_dir": str(out / "current")})
            grade = run.grade_shiploop(out)
            self.assertFalse(grade["pass"])
            self.assertEqual(grade["status"], "active")
            (out / "current/state.md").write_text("truncated record")
            self.assertFalse(run.grade_shiploop(out)["pass"])

    def test_prior_state_is_not_a_new_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            directory = out / "work/old"
            directory.mkdir(parents=True)
            state = directory / "state.md"
            run.store.write_record(state, {"status": "done"})
            (directory / "report.html").write_text("done")
            evidence.atomic_json(out / "invocation.json", {"invocation_id": "new", "initial_states": {str(state.resolve()): evidence.tree_digest(state)}})
            self.assertFalse(run.grade_shiploop(out)["pass"])

    def test_new_session_lookup_does_not_reuse_old_stream_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.jsonl"
            events.write_text(json.dumps({"type": "session_start", "sessionId": "old"}) + '\n' + json.dumps({"type": "text", "text": "interrupted"}) + '\n')
            self.assertIsNone(run.last_session_id(events, start_line=1))
            events.write_text(events.read_text() + '{"type":"session_start","sessionId":"new"}\n')
            self.assertEqual(run.last_session_id(events, start_line=1), "new")

    def test_malformed_or_empty_stream_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            stream = Path(tmp) / "events.jsonl"
            for content in ("", '{"ok":true}\n{"broken":', '[]\n'):
                stream.write_text(content)
                self.assertTrue(evidence.stream_errors(stream))
            stream.write_text('{"ok":true}\n')
            self.assertEqual(evidence.stream_errors(stream), [])

    def test_check_writes_stay_in_copies_including_predecessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work, prior = root / "source", root / "prior"
            work.mkdir(); prior.mkdir()
            (work / "tracked").write_text("original")
            (prior / "retained").write_text("prior")
            command = 'printf changed > tracked; printf scratch > ignored; printf changed > "$PRIOR_WORK/retained"; printf diagnostic'
            result = run.run_checks(work, [command], env={"PRIOR_WORK": str(prior)}, output=root / "checks")[0]
            self.assertTrue(result["pass"], result)
            self.assertEqual((work / "tracked").read_text(), "original")
            self.assertEqual((prior / "retained").read_text(), "prior")
            self.assertFalse((work / "ignored").exists())
            self.assertEqual(Path(result["log"]).read_text(), "diagnostic")
            self.assertEqual((Path(result["scratch"]) / "ignored").read_text(), "scratch")

    def test_absolute_write_to_original_invalidates_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "source"
            work.mkdir()
            target = work / "product"
            target.write_text("before")
            result = run.run_checks(work, [f"printf altered > {shlex.quote(str(target))}"], output=root / "checks")[0]
            self.assertFalse(result["pass"])
            self.assertFalse(result["effects"]["originals_unchanged"])
            self.assertTrue(Path(result["log"]).is_file())

    def test_escaping_symlink_is_unsupported_before_checks_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "source"
            work.mkdir()
            outside = root / "external"
            outside.write_text("safe")
            (work / "link").symlink_to(outside)
            result = run.run_checks(work, ["printf changed > link"], output=root / "checks")[0]
            self.assertFalse(result["pass"])
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(outside.read_text(), "safe")

    def test_timeout_kills_owned_descendant_and_keeps_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "source"
            work.mkdir()
            # A descendant would modify an absolute marker if group cleanup failed.
            marker = root / "leaked-effect"
            program = "import subprocess,time; subprocess.Popen(['" + sys.executable + "','-c'," + repr(f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).write_text('leaked')") + "]); print('started',flush=True); time.sleep(10)"
            command = shlex.join([sys.executable, "-c", program])
            result = run.run_checks(work, [command], timeout=0.2, output=root / "checks")[0]
            self.assertEqual(result["status"], "timeout")
            self.assertFalse(result["pass"])
            self.assertIn("started", Path(result["log"]).read_text())
            # Wait past the child's scheduled write to verify the effect, not merely killpg invocation.
            import time
            time.sleep(1.1)
            self.assertFalse(marker.exists())

    def test_cleanup_error_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(run.os, "killpg", side_effect=PermissionError("cannot clean owned group")):
                result = run.run_checks(Path(tmp), ["true"])[0]
            self.assertFalse(result["pass"])
            self.assertIn("cannot clean", result["effects"]["cleanup_error"])

    def test_cleanup_error_with_a_live_process_has_a_bounded_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            owned = []
            original_kill = os.killpg
            def denied(pid, sig):
                owned.append(pid)
                raise PermissionError("denied group cleanup")
            import time
            start = time.monotonic()
            try:
                with mock.patch.object(run.os, "killpg", side_effect=denied):
                    result = run.run_checks(source, ["sleep 30"], timeout=0.05, output=root / "checks")[0]
                self.assertLess(time.monotonic() - start, 5)
                self.assertFalse(result["pass"])
                self.assertIn("denied group cleanup", result["effects"]["cleanup_error"])
            finally:
                for pid in owned:
                    try:
                        original_kill(pid, run.signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_pinned_ci_failure_cancels_owned_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            work = out / "work"
            work.mkdir()
            monitor = run.CIMonitor("pinned", "pending", interval=0.02)
            with mock.patch.object(run, "main_ci", return_value="failure"):
                monitor.start()
                result = run.launch([sys.executable, "-c", "import time; time.sleep(10)"], work, out, os.environ.copy(), 5,
                                    watch=False, monitor=monitor)
                receipt = monitor.close()
            self.assertEqual(result["status"], "cancelled_ci")
            self.assertTrue(receipt["failed"])
            self.assertEqual(receipt["commit"], "pinned")


class RetainedRunTests(base.HarnessCase):
    def test_declared_active_boundary_does_not_trigger_automatic_resume(self):
        base.SuiteTest.use_catalog(self,
            {"boundary": {"prompt": "Exercise a callback refusal while state stays active.",
                          "kind": "boundary", "expected_terminal": "active",
                          "checks": ["test -f .shiploop/state.md"]}}, {})
        code, result = self.invoke("grok", "stuck", "--case", "boundary")
        self.assertEqual(code, 0, result)
        self.assertEqual(len(result["process"]["sessions"]), 1)
        self.assertEqual(result["criteria"]["kind"], "boundary")
        self.assertFalse(result["committed"]["applicable"])

    def test_reviewer_accepts_runner_identity_with_candidate_digest(self):
        # Structural interoperability only; injected calibration is not model evidence.
        import review
        _, result = self.invoke("grok", "done")
        out = Path(result["output"])
        evaluation = evidence.read_json(out / "evaluation.json")
        coverage = lambda identifier, status: {"id": identifier, "status": status,
            "evidence": ["result.json#/checks"], "contrary_evidence": [], "reason": "fixture evidence"}
        record = {"schema": review.REVIEW_SCHEMA, "identity": result["identity"],
                  "process": {"status": "exited", "returncode": 0}, "summary": "Fixture review",
                  "observed_terminal": "done", "requirements": [coverage(item["id"], "verified")
                    for item in evaluation["criteria"]["requirements"]],
                  "workflow": [coverage(item, "pass") for item in evaluation["criteria"]["workflow"]],
                  "findings": [], "unresolved_material": [], "harness_dispositions": []}
        review.qualify_review(record, result, evaluation, calibration={"status": "passed"},
                              seal_reasons=evidence.verify_seal(out))
        self.assertTrue(record["validity"]["pass"], record)
        self.assertTrue(review.is_clean(record), record)

    def test_resume_rejects_a_replaced_check_recipe_before_launch(self):
        _, stopped = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(stopped["output"])
        invocation = evidence.read_json(out / "invocation.json")
        invocation["checks"] = ["true"] * len(invocation["checks"])
        evidence.atomic_json(out / "invocation.json", invocation)
        with mock.patch.object(run, "launch") as launch:
            with self.assertRaisesRegex(SystemExit, "intact sealed evidence"):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin)])
            launch.assert_not_called()

    def test_reviewer_retains_missing_and_malformed_responses_as_invalid(self):
        # The host and calibration are injected to test orchestration, not model accuracy.
        import review
        subject = self.plugin / "skills/shiploop"
        subject.mkdir(parents=True)
        (subject / "SKILL.md").write_text("Fixture subject")
        _, result = self.invoke("grok", "done")
        out = Path(result["output"])
        criteria = evidence.read_json(out / "evaluation.json")["criteria"]
        coverage = lambda identifier, status: {"id": identifier, "status": status,
            "evidence": ["result.json#/checks"], "contrary_evidence": [], "reason": "fixture evidence"}
        payload = {"summary": "Fixture review", "observed_terminal": "done",
                   "requirements": [coverage(item["id"], "verified") for item in criteria["requirements"]],
                   "workflow": [coverage(item, "pass") for item in criteria["workflow"]],
                   "findings": [], "unresolved_material": [], "harness_dispositions": []}
        variants = [("complete", payload)]
        for key in review.RESPONSE_FIELDS:
            variants.append((f"missing {key}", {k: v for k, v in payload.items() if k != key}))
        malformed = json.loads(json.dumps(payload))
        malformed["requirements"][0]["id"] = []
        variants.append(("malformed id", malformed))
        for label, response in variants:
            with self.subTest(label=label), mock.patch.object(review.hosts, "run_agent", return_value={
                    "status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None}), \
                    mock.patch.object(review.hosts, "final_text", return_value=json.dumps(response)), \
                    mock.patch.object(review, "_calibration_status", return_value={"status": "passed"}):
                record = review.review(out, host="grok")
                self.assertEqual(record["validity"]["pass"], label == "complete", record)
                self.assertEqual(review.is_clean(record), label == "complete", record)
                self.assertEqual(evidence.read_json(out / "review.json")["raw_response"], response)
                self.assertEqual(evidence.verify_seal(out), [])
        self.assertEqual(len(list((out / "reviews").glob("review-*/review.json"))), len(variants))

    def test_reviewer_interruption_keeps_a_terminal_receipt(self):
        import review
        subject = self.plugin / "skills/shiploop"
        subject.mkdir(parents=True)
        (subject / "SKILL.md").write_text("Fixture subject")
        _, result = self.invoke("grok", "done")
        out = Path(result["output"])
        with mock.patch.object(review.hosts, "run_agent", side_effect=KeyboardInterrupt):
            record = review.review(out, host="grok")
        self.assertEqual(record["process"]["status"], "interrupted")
        self.assertFalse(record["validity"]["pass"])
        self.assertFalse(review.is_clean(record))
        self.assertEqual(evidence.read_json(out / "review.json")["process"]["returncode"], 130)

    def test_mechanical_pass_keeps_qualification_pending_and_rejects_tampered_evidence(self):
        code, result = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["qualification"]["status"], "pending_review")
        out = Path(result["output"])
        self.assertEqual(evidence.verify_seal(out), [])
        transcript = out / "transcript.md"
        original = transcript.read_text()
        transcript.write_text("replacement account of the trial")
        self.assertTrue(evidence.verify_seal(out))
        transcript.write_text(original)
        self.assertEqual(evidence.verify_seal(out), [])
        # A file named progress.html is still part of a product's evidence.
        (out / "work/progress.html").write_text("changed product")
        self.assertTrue(evidence.verify_seal(out))
        destination = self.tmp / "copy"
        destination.mkdir()
        with self.assertRaisesRegex(SystemExit, "evidence changed"):
            run.continue_from(out, destination)

    def test_launch_exception_retains_incomplete_receipt(self):
        with mock.patch.object(run, "launch", side_effect=OSError("host unavailable")):
            code, result = self.invoke("grok", "done")
        self.assertEqual(code, 2)
        self.assertFalse(result["pass"])
        receipt = evidence.read_json(Path(result["output"]) / "attempt.json")
        self.assertEqual(receipt["status"], "incomplete")
        self.assertIn("host unavailable", receipt["reason"])

    def test_manual_resume_preserves_failed_attempt_and_records_budget_extension(self):
        _, stopped = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(stopped["output"])
        original = (out / "result.json").read_bytes()
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", "codex", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(code, 0)
        archives = list((out / "attempts").glob("*/result.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), original)
        self.assertTrue(evidence.read_json(out / "attempt.json")["budget"]["explicit_extension"])
        self.assertEqual(len(evidence.read_json(out / "result.json")["process"]["sessions"]), 2)
        self.assertEqual(evidence.verify_seal(out), [])
        archives[0].write_text("changed history")
        self.assertTrue(evidence.verify_seal(out))

    def test_subject_drift_is_incomplete_even_when_fake_product_passes(self):
        original_launch = run.launch
        def change_package(*args, **kwargs):
            result = original_launch(*args, **kwargs)
            (self.plugin / "changed.txt").write_text("new subject")
            return result
        with mock.patch.object(run, "launch", side_effect=change_package):
            code, result = self.invoke("grok", "done")
        self.assertEqual(code, 1)
        self.assertEqual(result["evidence"]["status"], "incomplete")
        self.assertIn("installed package changed during run", result["evidence"]["reasons"])


class BatchTests(base.HarnessCase):
    use_catalog = base.SuiteTest.use_catalog
    run_suite = base.SuiteTest.run_suite

    def test_batch_refuses_changed_package_before_next_case(self):
        cases = {"gate": {"prompt": "p", "checks": ["test -f hello.py"]},
                 "next": {"prompt": "p", "checks": ["test -f hello.py"]}}
        self.use_catalog(cases, {"batch": {"gate": ["gate"], "cases": ["next"]}})
        original = run.main
        def changing(argv=None):
            code = original(argv)
            if argv and "--case" in argv and argv[argv.index("--case") + 1] == "gate":
                (self.plugin / "changed").write_text("new release")
            return code
        with mock.patch.object(run, "main", side_effect=changing):
            code, result = self.run_suite("batch")
        self.assertEqual(code, 1)
        self.assertTrue(result["cases"][0]["pass"])
        self.assertFalse(result["cases"][1]["pass"])
        self.assertEqual(result["cases"][1]["status"], "blocked_preflight")

    def test_shared_temporary_writes_invalidate_affected_suite_rows(self):
        self.use_catalog({name: {"prompt": "p", "checks": ["test -f hello.py"]} for name in ("a", "b")},
                         {"wide": {"cases": ["a", "b"]}})
        with mock.patch.object(run, "shared_tmp_writes", return_value={"/tmp/shared": ["a", "b"]}):
            code, result = self.run_suite("wide")
        self.assertEqual(code, 1)
        self.assertTrue(all(row["status"] == "incomplete" for row in result["cases"]))
        self.assertTrue(all(row["pass_mechanical_before_collision"] for row in result["cases"]))


if __name__ == "__main__":
    unittest.main()
