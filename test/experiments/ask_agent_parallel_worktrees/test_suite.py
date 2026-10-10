#!/usr/bin/env python3
"""Safety and selection checks for the test operator, with no live model calls."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import suite


class SuiteControls(unittest.TestCase):
    def test_list_is_read_only(self):
        output=io.StringIO()
        with patch('suite.subprocess.run') as run, contextlib.redirect_stdout(output):
            self.assertEqual(suite.main(['--list']),0)
        run.assert_not_called()
        self.assertIn('compact-comparison',json.loads(output.getvalue()))

    def test_live_requires_explicit_opt_in(self):
        with patch('suite.subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                suite.main(['--suite','smoke'])
        self.assertEqual(error.exception.code,2)
        run.assert_not_called()

    def test_existing_output_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, patch('suite.subprocess.run') as run:
            with self.assertRaises(FileExistsError):
                suite.main(['--suite','smoke','--live','--output',tmp])
        run.assert_not_called()

    def test_failed_attempt_is_recorded_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'
            failure=subprocess.CompletedProcess([],1)
            with patch('suite.subprocess.run',return_value=failure) as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(['--suite','smoke','--live','--output',str(output)]),1)
            self.assertEqual(run.call_count,1)
            record=json.loads((output/'suite-result.json').read_text())
            self.assertEqual(record['cases'][0]['status'],'INCOMPLETE')

    def test_contradictory_verdict_cannot_persist_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'
            def command(argv,**kwargs):
                if 'native_trace.py' in ' '.join(argv):
                    op=output/'parallel3/operator';op.mkdir(parents=True,exist_ok=True)
                    (op/'native-verification.json').write_text(json.dumps({'status':'PASS','passed':False}))
                return subprocess.CompletedProcess(argv,0)
            with patch('suite.subprocess.run',side_effect=command),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(['--suite','smoke','--live','--output',str(output)]),1)
            saved=json.loads((output/'suite-result.json').read_text())
            self.assertEqual(saved['cases'][0]['status'],'FAIL')
            self.assertEqual(saved['status'],'FAIL')

    def test_missing_verdict_and_unrun_cases_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'
            with patch('suite.subprocess.run',return_value=subprocess.CompletedProcess([],0)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(['--suite','functional','--live','--output',str(output)]),1)
            saved=json.loads((output/'suite-result.json').read_text())
            self.assertEqual([c['status'] for c in saved['cases']],['INCOMPLETE','NOT_RUN'])
            self.assertIn('Missing or invalid',saved['cases'][0]['error'])

    def test_timing_suite_has_matched_repetitions(self):
        modes={}
        for name,n,mode,treatment,hold in suite.SUITES['timing']:
            self.assertEqual(hold,0)
            key=(n,mode,treatment)
            modes[key]=modes.get(key,0)+1
        self.assertEqual(set(modes.values()),{2})

    def test_compact_comparison_case_order_and_controls_match(self):
        self.assertEqual(
            suite.SUITES['compact-comparison'],
            [('compact3-a',3,'parallel','compact',0),
             ('baseline3-a',3,'parallel','baseline',0),
             ('baseline3-b',3,'parallel','baseline',0),
             ('compact3-b',3,'parallel','compact',0),
             ('compact5-a',5,'parallel','compact',0)],
        )

    def test_compact_comparison_applies_and_records_same_fixture_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'

            def command(argv, **kwargs):
                if any(str(arg).endswith('native_trace.py') for arg in argv):
                    run=Path(argv[argv.index('--run')+1])
                    operator=run/'operator'
                    operator.mkdir(parents=True,exist_ok=True)
                    (operator/'native-verification.json').write_text(
                        json.dumps({'status':'PASS','passed':True}),encoding='utf-8')
                return subprocess.CompletedProcess(argv,0)

            args=['--suite','compact-comparison','--live','--output',str(output),
                  '--seed-feedback-backlog']
            with patch('suite.subprocess.run',side_effect=command),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(args),0)

            campaign=json.loads((output/'suite-result.json').read_text())
            self.assertEqual(campaign['status'],'PASS')
            self.assertTrue(campaign['seed_compact_ignore_controls'])
            self.assertTrue(campaign['seed_feedback_backlog'])
            self.assertEqual(
                [(case['name'],case['treatment']) for case in campaign['cases']],
                [('compact3-a','compact'),('baseline3-a','baseline'),
                 ('baseline3-b','baseline'),('compact3-b','compact'),
                 ('compact5-a','compact')],
            )
            for case in campaign['cases']:
                self.assertEqual(case['hold_seconds'],0)
                self.assertTrue(case['seed_compact_ignore_controls'],case['name'])
                self.assertTrue(case['seed_feedback_backlog'],case['name'])
                prepare_argv=case['commands'][0]['argv']
                self.assertIn('--seed-compact-ignore-controls',prepare_argv,case['name'])
                self.assertIn('--seed-feedback-backlog',prepare_argv,case['name'])


    def test_delivery_suite_runs_default_commit_scale_then_findings_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'
            def command(argv, **kwargs):
                if any(str(arg).endswith('native_trace.py') for arg in argv):
                    run=Path(argv[argv.index('--run')+1]); operator=run/'operator'
                    operator.mkdir(parents=True,exist_ok=True)
                    (operator/'native-verification.json').write_text(json.dumps({'status':'PASS','passed':True}))
                return subprocess.CompletedProcess(argv,0)
            with patch('suite.subprocess.run',side_effect=command), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(['--suite','delivery-qualification','--live','--output',str(output)]),0)
            campaign=json.loads((output/'suite-result.json').read_text())
            self.assertTrue(campaign['seed_compact_ignore_controls'])
            self.assertEqual([(c['name'],c['workers'],c['delivery_mode']) for c in campaign['cases']],
                             [('commit3-a',3,'commits'),('commit5-a',5,'commits'),('ephemeral3-a',3,'ephemeral')])
            for case in campaign['cases']:
                self.assertEqual(case['treatment'],'compact')
                self.assertEqual(case['status'],'PASS')
                prepare=case['commands'][0]['argv']
                self.assertEqual(prepare[prepare.index('--delivery-mode')+1],case['delivery_mode'])
                self.assertIn('--seed-compact-ignore-controls',prepare)
                prompt=case['commands'][1]['argv']
                self.assertEqual(prompt[prompt.index('--delivery-mode')+1],case['delivery_mode'])

    def test_delivery_modes_reach_real_prompt_generation_before_model_launch(self):
        real_run = subprocess.run
        for case, mode in [('commit3-a', 'commits'), ('commit5-a', 'commits'),
                           ('ephemeral3-a', 'ephemeral')]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'campaign'
                observed = []
                def command(argv, **kwargs):
                    observed.append(argv)
                    if Path(argv[2]).name in {'fixture.py', 'prompts.py'}:
                        return real_run(argv, **kwargs)
                    # This offline regression must stop before any model is launched.
                    self.assertEqual(Path(argv[2]).name, 'controller.py')
                    self.assertIn('launch', argv)
                    return subprocess.CompletedProcess(argv, 1)
                with patch('suite.subprocess.run', side_effect=command), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    result = suite.main(['--suite', 'delivery-qualification', '--case', case,
                                         '--live', '--output', str(output)])
                self.assertEqual(result, 1)
                campaign = json.loads((output / 'suite-result.json').read_text())
                phases = campaign['cases'][0]['commands']
                self.assertEqual([row['exit_code'] for row in phases], [0, 0, 1])
                self.assertEqual(len(observed), 3)
                manifest = json.loads((output / case / 'manifest.json').read_text())
                self.assertEqual(manifest['delivery_mode'], mode)

    def test_delivery_suite_stops_before_later_cases_on_first_failed_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'campaign'
            with patch('suite.subprocess.run',return_value=subprocess.CompletedProcess([],1)) as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(suite.main(['--suite','delivery-qualification','--live','--output',str(output)]),1)
            self.assertEqual(run.call_count,1)
            cases=json.loads((output/'suite-result.json').read_text())['cases']
            self.assertEqual([c['status'] for c in cases],['INCOMPLETE','NOT_RUN','NOT_RUN'])


if __name__ == '__main__':
    unittest.main()
