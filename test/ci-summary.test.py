#!/usr/bin/env python3
"""Receipt reporting uses real catalog selections and rejects false pass evidence."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import ci_summary

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


class SummaryTests(unittest.TestCase):
    def receipt(self, group="smoke", changed=()):
        ids = ci_summary.selection_ids([group], changed)
        return {
            'schema': 'skill-craft-hermetic-receipt/1', 'source': {'head': SHA, 'status': []},
            'groups': [group], 'changed_from': None, 'changed': list(changed), 'selected': [{'id': i} for i in ids],
            'completed': [{'id': i, 'status': 'passed', 'returncode': 0, 'duration_seconds': n + 0.25}
                          for n, i in enumerate(ids)],
            'status': 'passed', 'wall_seconds': 12.5, 'runtimes': {'node': 'v26.0.0', 'python3': 'Python 3.15.1'},
        }

    def test_complete_receipt_reports_scope_counts_slowest_and_versions(self):
        receipt = self.receipt()
        report, passed = ci_summary.render(receipt, SHA, 'smoke', 'success')
        self.assertTrue(passed)
        self.assertIn(f"selected/completed: {len(receipt['selected'])}/{len(receipt['selected'])}", report)
        self.assertIn(SHA, report)
        self.assertIn('12.5 seconds', report)
        self.assertIn('v26', report)
        self.assertIn('live acceptance', report)
        self.assertLess(report.index(ci_summary.escape(receipt['completed'][-1]['id']) + ':'),
                        report.index(ci_summary.escape(receipt['completed'][-2]['id']) + ':'))

    def test_partial_failed_cancelled_and_premature_pass_never_pass(self):
        for status in ('running', 'failed', 'passed'):
            receipt = self.receipt()
            receipt['status'] = status
            missing = receipt['completed'].pop()['id']
            report, passed = ci_summary.render(receipt, SHA, 'smoke', 'success')
            self.assertFalse(passed)
            self.assertIn(ci_summary.escape(missing), report)
        for job in ('failure', 'cancelled', 'skipped', ''):
            self.assertFalse(ci_summary.render(self.receipt(), SHA, 'smoke', job)[1])
        for status, code in (('failed', 1), ('timed_out', None), ('passed', 1)):
            receipt = self.receipt()
            receipt['completed'][0].update(status=status, returncode=code)
            self.assertFalse(ci_summary.render(receipt, SHA, 'smoke', 'success')[1])

    def test_stale_malformed_duplicate_and_wrong_selection_rejected(self):
        original = self.receipt()
        variants = [None, {}, dict(original, schema='other'), dict(original, source={'head': 'b' * 40}),
                    dict(original, groups=['quick']), dict(original, selected=[]),
                    dict(original, completed=original['completed'] * 2),
                    dict(original, selected=original['selected'][:-1]), dict(original, changed='bad'),
                    dict(original, wall_seconds=float('nan')),
                    dict(original, source={'head': SHA, 'status': [' M file']})]
        for variant in variants:
            with self.subTest(receipt=variant), self.assertRaises((ValueError, KeyError, TypeError)):
                ci_summary.render(variant, SHA, 'smoke', 'success')
        receipt = copy.deepcopy(original)
        receipt['completed'][0]['duration_seconds'] = -1
        with self.assertRaises(ValueError):
            ci_summary.render(receipt, SHA, 'smoke', 'success')

    def test_missing_objects_boolean_returncodes_and_unemitted_statuses_are_rejected(self):
        for field in ("selected", "completed"):
            for value in (None, {}, [None], [False], ["suite"]):
                receipt = self.receipt()
                receipt[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ci_summary.render(receipt, SHA, "smoke", "success")
            receipt = self.receipt()
            del receipt[field]
            with self.assertRaises(ValueError):
                ci_summary.render(receipt, SHA, "smoke", "success")
        for code in (False, True):
            receipt = self.receipt()
            receipt["completed"][0]["returncode"] = code
            with self.assertRaises(ValueError):
                ci_summary.render(receipt, SHA, "smoke", "success")
        for status in ("error", "interrupted", "cancelled", "not_started"):
            receipt = self.receipt()
            receipt["completed"][0]["status"] = status
            with self.assertRaises(ValueError):
                ci_summary.render(receipt, SHA, "smoke", "success")

    def test_shard_receipts_are_validated_against_their_own_changed_paths(self):
        changed = ["test/shiploop_e2e/run.py"]
        for group in ("quick-1", "quick-2"):
            receipt = self.receipt(group, changed)
            self.assertTrue(ci_summary.render(receipt, SHA, group, "success")[1])
            counts = ci_summary.selection_counts([group], changed)
            self.assertGreater(counts["not_in_this_shard"], 0)
            self.assertGreater(counts["deferred_policy"], 0)
            receipt["changed"] = ["README.md"]
            with self.assertRaises(ValueError):
                ci_summary.render(receipt, SHA, group, "success")
        full = ci_summary.selection_counts(["all"], changed)
        targeted = ci_summary.targeted_ids(changed)
        smoke = set(ci_summary.selection_ids(["smoke"]))
        self.assertEqual(full["affected"], len(targeted - smoke))
        self.assertEqual(full["deferred_policy"], 0)
        self.assertEqual(full["not_in_this_shard"], 0)
        self.assertEqual(full["deferred_targeted"], 0)

    def test_consistently_forged_narrower_range_is_rejected(self):
        receipt = self.receipt("quick", ["README.md"])
        receipt["changed_from"] = "narrower-base"
        with self.assertRaisesRegex(ValueError, "planned base"):
            ci_summary.render(receipt, SHA, "quick", "success", expected_base="planner-base",
                              expected_changes=["test/shiploop_e2e/run.py"])
        receipt["changed_from"] = "planner-base"
        with self.assertRaisesRegex(ValueError, "independently derived"):
            ci_summary.render(receipt, SHA, "quick", "success", expected_base="planner-base",
                              expected_changes=["test/shiploop_e2e/run.py"])
        full = self.receipt("core")
        report, passed = ci_summary.render(full, SHA, "core", "success", expected_base="",
                                          expected_changes=[])
        self.assertTrue(passed)
        self.assertIn("affected: UNAVAILABLE", report)

    def test_cli_independently_checks_planner_range_for_consistent_forgery(self):
        receipt = self.receipt("quick", ["README.md"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, summary = root / "receipt.json", root / "summary.md"
            for claimed_base in ("narrower-base", "planner-base"):
                receipt["changed_from"] = claimed_base
                path.write_text(json.dumps(receipt))
                with mock.patch.object(ci_summary, "independent_changes",
                                       return_value=("test/shiploop_e2e/run.py",)) as derive, \
                        mock.patch.dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)), \
                        mock.patch("builtins.print"):
                    code = ci_summary.main(["--receipt", str(path), "--expected-sha", SHA,
                                            "--group", "quick", "--job-status", "success",
                                            "--base", "planner-base"])
                derive.assert_called_once_with("planner-base")
                self.assertEqual(code, 1)
                self.assertIn("FAILED / INCOMPLETE", summary.read_text())
                summary.unlink()

    def test_markdown_data_is_escaped(self):
        value = '[click](https://example.invalid)|<script>\n# heading `code` @owner'
        rendered = ci_summary.escape(value)
        for raw in ('[', ']', '|', '<script>', '\n', '`', '@'):
            self.assertNotIn(raw, rendered)

    def test_counts_partition_selection_and_keep_indirect_heavy_deferred(self):
        changed = ['test/shiploop_e2e/run.py']
        counts = ci_summary.selection_counts(['quick'], changed)
        self.assertGreater(counts['deferred_targeted'], 0)
        self.assertEqual(counts['smoke'], len(ci_summary.selection_ids(['smoke'])))
        self.assertEqual(counts['selected'], counts['smoke'] + counts['affected'] + counts['other_selected'])
        self.assertEqual(ci_summary.selection_counts(['all'], changed)['deferred_targeted'], 0)

    def test_cli_writes_failure_summary_even_when_no_receipt_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, summary = root / 'receipt.json', root / 'summary.md'
            command = [sys.executable, '-B', str(ROOT / 'test/ci_summary.py'), '--receipt', str(receipt),
                       '--base', '', '--expected-sha', SHA, '--group', 'smoke', '--job-status', 'success']
            for content in (None, '{', '{}', json.dumps(dict(self.receipt(), source={'head': 'b' * 40})),
                            json.dumps(self.receipt())):
                if content is not None:
                    receipt.write_text(content)
                result = subprocess.run(command, env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, content == json.dumps(self.receipt()), result.stderr)
                self.assertIn('PASSED' if result.returncode == 0 else 'FAILED / INCOMPLETE', summary.read_text())
                summary.unlink()

    def test_workflow_reports_always_with_source_and_job_status(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        step = workflow.split('      - name: Summarize suite evidence\n', 1)[1].split('      - name:', 1)[0]
        self.assertIn('if: ${{ always() }}', step)
        self.assertIn('EXPECTED_SHA: ${{ needs.plan.outputs.source_sha }}', step)
        self.assertIn('JOB_STATUS: ${{ job.status }}', step)
        self.assertIn('--expected-sha "$EXPECTED_SHA"', step)
        self.assertIn('BASE: ${{ needs.plan.outputs.base }}', step)
        self.assertIn('--base "$BASE"', step)
        self.assertIn('--job-status "$JOB_STATUS"', step)
        self.assertLess(workflow.index('      - name: Checkout unchanged'),
                        workflow.index('      - name: Summarize suite evidence'))


if __name__ == '__main__':
    unittest.main()
