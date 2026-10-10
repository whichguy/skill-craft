#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fixture
import operations

class SetupBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ask-agent-batch-test-');self.addCleanup(self.tmp.cleanup)
        self.run=Path(self.tmp.name)/'run'
        self.manifest=fixture.prepare_fixture(self.run,3,'parallel')

    def _is_helper_command(self, args, command):
        helper=Path(self.manifest['paths']['package'])/'scripts/ask_agent_workspace.py'
        return len(args)>=4 and Path(args[2]).resolve()==helper.resolve() and args[3]==command

    def _prepare_synthetic_workers(self):
        """Prepare real helper worktrees, then supply deterministic test-only results."""
        setup=operations.prepare_batch(self.run)
        setup_by_id={worker['worker_id']:worker for worker in setup['workers']}
        for task in self.manifest['task_assignments']:
            worker_id=task['worker_id']
            child=Path(setup_by_id[worker_id]['worktree'])
            fixture.probe_run(self.run,worker_id,'start',cwd=child)
            (child/task['path']).write_text(
                'def transform(x):\n'
                f'    return ({int(worker_id)} + 1) * x + {int(worker_id)} * {int(worker_id)}\n',
                encoding='utf-8',
            )
            fixture.probe_run(self.run,worker_id,'finish',cwd=child)
        return setup

    def test_prepares_distinct_exact_snapshots_and_refuses_duplicate_attempt(self):
        result=operations.prepare_batch(self.run)
        self.assertEqual(result['status'],'PREPARED')
        self.assertEqual(result['operations_script_sha256'],fixture.sha256_file(Path(operations.__file__)))
        self.assertEqual(result['frozen_package_tree_sha256_before_preparation'],self.manifest['source']['package_tree_sha256'])
        self.assertEqual(result['frozen_package_tree_sha256_after_preparation'],self.manifest['source']['package_tree_sha256'])
        self.assertTrue(all(w['package_identity']==result['package_identity'] for w in result['workers']))
        self.assertEqual(len({w['worktree'] for w in result['workers']}),3)
        for worker in result['workers']:
            state=fixture.capture_repo_state(Path(worker['worktree']))
            self.assertEqual(state['index_entries'],self.manifest['caller_snapshot']['index_entries'])
            self.assertEqual(state['working_tree'],self.manifest['caller_snapshot']['working_tree'])
            inspected=worker['prepared_inspection']
            self.assertEqual(inspected['status'],'prepared')
            self.assertEqual(inspected['phase'],'prepared')
            self.assertEqual(inspected['receipt'],worker['receipt'])
            self.assertEqual(inspected['worktree'],worker['worktree'])
            self.assertEqual(inspected['branch'],worker['branch'])
            self.assertEqual(inspected['changed_paths'],[])
            self.assertEqual(inspected['contribution_paths'],[])
        original=(self.run/'operator/setup-result.json').read_bytes()
        with self.assertRaises(fixture.FixtureError):operations.prepare_batch(self.run)
        self.assertEqual(original,(self.run/'operator/setup-result.json').read_bytes())

    def test_source_drift_refuses_before_workers_exist(self):
        (self.run/'caller/notes.txt').write_text('drift\n')
        with self.assertRaises(fixture.FixtureError):operations.prepare_batch(self.run)
        result=json.loads((self.run/'operator/setup-result.json').read_text())
        self.assertEqual(result['status'],'FAILED');self.assertEqual(result['workers'],[])
        self.assertEqual(result['error_code'],'SETUP_FAILED')
        self.assertEqual(result['failure']['phase'],'caller_snapshot_before_setup')

    def test_missing_or_duplicate_collection_assertions_write_nothing(self):
        for worker_ids in (['1','2'],['1','1','3']):
            with self.subTest(worker_ids=worker_ids):
                with self.assertRaisesRegex(fixture.FixtureError,'PARENT_COLLECTION_ASSERTION_INVALID'):
                    operations.integrate_batch(self.run,worker_ids)
                self.assertFalse((self.run/'operator/integration-result.json').exists())
                self.assertFalse((self.run/'operator/integration-calls').exists())

    def test_noncompact_delivery_has_no_compact_return_records(self):
        self.assertEqual(
            operations._require_compact_returns(
                self.run, {'treatment': 'scripted'}, ['1', '2', '3']),
            [],
        )

    def test_parent_result_writer_rejects_missing_duplicate_worker_handles(self):
        invalid_handles = (
            ['1=child-1', '2=child-2'],
            ['1=child-1', '1=child-duplicate', '3=child-3'],
            ['1=child-1', '2=child-1', '3=child-3'],
            ['1=child-1', '2=', '3=child-3'],
            ['1=child-1', '2=child-2', '4=child-4'],
        )
        for handles in invalid_handles:
            with self.subTest(handles=handles), self.assertRaisesRegex(
                    fixture.FixtureError, 'PARENT_RESULT_INVALID'):
                operations.write_parent_result(self.run, handles, 'a' * 64, 'b' * 64)
            self.assertFalse((self.run / 'operator' / 'parent-result.json').exists())

    def test_parent_result_writer_requires_lowercase_sha256_inputs(self):
        for verification_hash, integration_hash in (
                ('bad', 'b' * 64), ('A' * 64, 'b' * 64), ('a' * 64, 'b' * 63)):
            with self.subTest(verification_hash=verification_hash, integration_hash=integration_hash), self.assertRaisesRegex(
                    fixture.FixtureError, 'PARENT_RESULT_INVALID'):
                operations.write_parent_result(
                    self.run, ['1=child-1', '2=child-2', '3=child-3'],
                    verification_hash, integration_hash,
                )

    def test_cli_emits_contract_diagnostic_for_invalid_collection_assertion(self):
        completed=subprocess.run(
            [sys.executable,'-B',str(Path(operations.__file__)),'integrate-batch','--run',str(self.run)],
            capture_output=True,text=True,
        )
        self.assertEqual(completed.returncode,2)
        diagnostic=json.loads(completed.stderr)
        self.assertEqual(diagnostic['schema'],'ask-agent-diagnostic/v1')
        self.assertEqual(diagnostic['code'],'PARENT_COLLECTION_ASSERTION_INVALID')
        self.assertEqual(diagnostic['severity'],'error')
        self.assertEqual(diagnostic['phase'],'argument_validation')
        self.assertEqual(diagnostic['rationale_ref'],'CONTRACT.md#retry-safety')
        self.assertEqual(diagnostic['expected'],{'manifest_worker_ids_exactly_once':['1','2','3']})
        self.assertEqual(diagnostic['observed'],{'collected_worker_ids':[]})
        integration_evidence=next(
            row for row in diagnostic['evidence']
            if Path(row['path']).resolve()==(self.run/'operator/integration-result.json').resolve()
        )
        self.assertEqual(integration_evidence['hash_status'],'missing')
        self.assertTrue((self.run/'operator/diagnostics.jsonl').is_file())

    def test_compact_result_cannot_claim_unaccepted_integration(self):
        with self.assertRaises(fixture.FixtureError):
            operations.integration_summary(self.run,{'status':'INTEGRATED','fixture_verification':{'passed':False}})

    def test_commit_summary_requires_and_retains_exact_worker_commit_records(self):
        workers=['1','2','3']
        records=[{'worker_id':worker,'commit_base':f'{worker}0'*20,
                  'commits':[f'{worker}1'*20],'patch_sha256':f'{worker}2'*32}
                 for worker in workers]
        result={'status':'INTEGRATED','fixture_verification':{'passed':True},
                'delivery_mode':'commits','integration_strategy':'preserve-parent patch from commits',
                'integration_worker_ids':workers,'applied_worker_ids':workers,
                'commit_records':records,'elapsed_s':1.0,'patches':[],
                'native_lifecycle_note':'Native audit is independent.'}
        summary=operations.integration_summary(self.run,result)
        self.assertEqual(summary['delivery_mode'],'commits')
        self.assertEqual(summary['integration_strategy'],'preserve-parent patch from commits')
        self.assertEqual(summary['worker_ids'],workers)
        self.assertEqual(summary['commit_records'],records)
        for mutate in (
            lambda value: value.update(commit_records=records[:2]),
            lambda value: value.update(commit_records=[*records, 'unbound']),
            lambda value: value['commit_records'][0].update(commit_base='not-a-full-sha'),
            lambda value: value['commit_records'][0].update(commits=[value['commit_records'][0]['commit_base']]),
            lambda value: value.update(integration_strategy='eligible cherry-pick'),
        ):
            mutated=json.loads(json.dumps(result))
            mutate(mutated)
            with self.subTest(result=mutated), self.assertRaisesRegex(
                    fixture.FixtureError,'incomplete worker commit records'):
                operations.integration_summary(self.run,mutated)

    def test_patch_summary_binds_delivery_mode_and_result_path(self):
        worker_ids = ['1', '2', '3']
        result = {
            'status': 'INTEGRATED',
            'fixture_verification': {'passed': True},
            'applied_worker_ids': worker_ids,
            'integration_worker_ids': worker_ids,
            'delivery_mode': 'patch',
            'elapsed_s': 1.0,
            'patches': [],
            'native_lifecycle_note': 'Native audit is independent.',
        }
        summary = operations.integration_summary(self.run, result)
        self.assertEqual(summary['delivery_mode'], 'patch')
        self.assertEqual(summary['applied_worker_ids'], worker_ids)
        self.assertEqual(summary['result_path'], str(self.run.resolve() / 'operator/integration-result.json'))

    def test_cli_advertises_shared_delivery_and_ephemeral_finalizer(self):
        completed=subprocess.run(
            [sys.executable,'-B',str(Path(operations.__file__)),'--help'],
            capture_output=True,text=True,
        )
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertIn('finish-ephemeral',completed.stdout)
        self.assertIn('--delivery-mode {patch,commits}',completed.stdout)

    def test_compact_commit_return_requires_complete_worker_only_range_and_dirty_parent_diff(self):
        task_path='src/step_1.py'
        base='a'*40
        commit='b'*40
        patch_path=str(self.run/'workspace-store'/'contribution.patch')
        snapshot={'source_dirty':True}
        worker={'worker_id':'1','path':task_path,'receipt':'receipt-1','worktree':'/worker-1',
                'branch':'ask-agent/worker-1','commit_base':base,'snapshot':snapshot,
                'prepared_inspection':{'fingerprint':'prepared-fingerprint'}}
        binding={'binding_sha256':'binding-digest'}
        delivery={'mode':'commits','base':base,'commits':[commit],
                  'commit_paths':[task_path],
                  'per_commit_paths':[{'commit':commit,'paths':[task_path]}],
                  'residual_paths':[],'contribution_patch':patch_path}
        result={'status':'READY_FOR_PARENT_ACCEPTANCE','command':'verify-return','binding_sha256':'binding-digest',
                'workspace_evidence':{'inspection':{'status':'returned','receipt':'receipt-1',
                    'worktree':'/worker-1','contribution_paths':[task_path],'delivery':delivery}},
                'integration_strategy':{'strategy':'preserve-parent patch from commits',
                    'source_dirty':True,'commit_base':base,'commits':[commit],
                    'parent_target_revalidation_required':True}}
        manifest={'delivery_mode':'commits','caller_snapshot':{'head':'c'*40}}
        self.assertTrue(operations._compact_return_result_valid(result,manifest,{},worker,binding))
        for mutate in (
            lambda value: value['workspace_evidence']['inspection']['delivery'].update(base='d'*40),
            lambda value: value['workspace_evidence']['inspection']['delivery'].update(residual_paths=['other.py']),
            lambda value: value['workspace_evidence']['inspection']['delivery'].update(commits=[base]),
            lambda value: value['workspace_evidence']['inspection']['delivery'].update(
                per_commit_paths=[{'commit':commit,'paths':['other.py']}]),
            lambda value: value['integration_strategy'].update(strategy='eligible cherry-pick'),
        ):
            mutated=json.loads(json.dumps(result))
            mutate(mutated)
            self.assertFalse(operations._compact_return_result_valid(mutated,manifest,{},worker,binding))

    def test_compact_ephemeral_return_requires_findings_only_audit_without_delivery(self):
        worker={'worker_id':'1','path':'src/step_1.py','receipt':'receipt-1','worktree':'/worker-1',
                'branch':'ask-agent/worker-1','prepared_inspection':{'fingerprint':'baseline-fingerprint'}}
        binding={'binding_sha256':'binding-digest'}
        audit={'status':'ephemeral-audit','findings_only':True,
               'changed_paths':['src/step_1.py','.experiment-local/owner.txt'],
               'baseline_fingerprint':'baseline-fingerprint','fingerprint':'current-fingerprint',
               'head':'a'*40,'branch':'ask-agent/worker-1','scratch_retained':True}
        result={'status':'READY_FOR_PARENT_ACCEPTANCE','command':'verify-return','binding_sha256':'binding-digest',
                'workspace_evidence':{'ephemeral_audit':audit}}
        manifest={'delivery_mode':'ephemeral','caller_snapshot':{'head':'a'*40}}
        self.assertTrue(operations._compact_return_result_valid(result,manifest,{},worker,binding))
        forged=json.loads(json.dumps(result))
        forged['workspace_evidence']['delivery']={'mode':'patch'}
        self.assertFalse(operations._compact_return_result_valid(forged,manifest,{},worker,binding))

    def test_ephemeral_finalization_requires_manifest_ordered_collection(self):
        with self.assertRaisesRegex(fixture.FixtureError,'PARENT_COLLECTION_ASSERTION_INVALID'):
            operations._assert_collected_ids(self.manifest,['2','1','3'])

    def test_cli_failure_diagnostic_points_to_structured_failure(self):
        result_path=self.run/'operator/integration-result.json'
        action_path=self.run/'operator/integration-calls/001-patch-check-1.json'
        result_path.write_text(json.dumps({
            'status':'FAILED','phase':'patch-check-1',
            'failure':{
                'code':'PATCH_CONFLICT','phase':'patch-check-1',
                'expected':'exit_code == 0',
                'observed':{'exit_code':1,'stderr':'patch does not apply'},
                'evidence_path':str(action_path),
                'retry_semantics':'Preserve this run and reconcile before a fresh attempt.',
            },
        }),encoding='utf-8')
        diagnostic=operations._cli_failure_diagnostic(
            self.run,'integrate-batch',fixture.FixtureError('patch check failed')
        )
        result_evidence=next(
            row for row in diagnostic['evidence']
            if Path(row['path']).resolve()==result_path.resolve()
        )
        self.assertEqual(result_evidence['json_pointer'],'/failure')
        self.assertEqual(diagnostic['expected'],'exit_code == 0')
        self.assertEqual(diagnostic['observed'],{'exit_code':1,'stderr':'patch does not apply'})
        self.assertEqual(diagnostic['retry_safety'],'Preserve this run and reconcile before a fresh attempt.')
        self.assertIn(
            str(action_path.resolve()),
            [str(Path(row['path']).resolve()) for row in diagnostic['evidence']],
        )

    def test_real_helper_patch_integration_preserves_index_and_dirty_inputs(self):
        self._prepare_synthetic_workers()
        worker_ids=[task['worker_id'] for task in self.manifest['task_assignments']]
        result=operations.integrate_batch(self.run,worker_ids)
        self.assertEqual(result['status'],'INTEGRATED')
        compact=operations.integration_summary(self.run,result)
        self.assertEqual(compact['applied_worker_ids'],worker_ids)
        self.assertNotIn('actions',compact)
        self.assertTrue(Path(compact['result_path']).is_file())
        self.assertEqual(result['applied_worker_ids'],worker_ids)
        self.assertEqual(result['fixture_verification']['passed'],True)
        self.assertIn('parent-supplied worker ids are assertions',result['native_lifecycle_note'].lower())
        caller=Path(self.manifest['paths']['caller'])
        current=fixture.capture_repo_state(caller)
        baseline=self.manifest['caller_snapshot']
        self.assertEqual(current['head'],baseline['head'])
        self.assertEqual(current['index_entries'],baseline['index_entries'])
        self.assertEqual(current['index_tree'],baseline['index_tree'])
        self.assertEqual(current['cached_diff_sha256'],baseline['cached_diff_sha256'])
        self.assertEqual(current['unstaged_dirty_diffs'],baseline['unstaged_dirty_diffs'])
        for task in self.manifest['task_assignments']:
            self.assertEqual(
                current['working_tree']['files'][task['path']],
                'sha256:'+fixture.sha256_file(Path(result['patches'][int(task['worker_id'])-1]['worktree'])/task['path']),
            )
        self.assertTrue((self.run/'operator/integration-result.json').is_file())
        self.assertTrue((self.run/'operator/integration-calls').is_dir())

    def test_unexpected_returned_contribution_path_refuses_before_apply(self):
        setup=self._prepare_synthetic_workers()
        caller=Path(self.manifest['paths']['caller'])
        before=fixture.capture_repo_state(caller)
        original_run=subprocess.run

        def add_unowned_contribution(args, **kwargs):
            if self._is_helper_command(args,'inspect') and '--phase' in args and args[args.index('--phase')+1]=='returned':
                completed=original_run(args,**kwargs)
                payload=json.loads(completed.stdout)
                payload['contribution_paths']=[payload['contribution_paths'][0],'src/step_3.py']
                return subprocess.CompletedProcess(args,completed.returncode,json.dumps(payload),completed.stderr)
            return original_run(args,**kwargs)

        with mock.patch('operations.subprocess.run',side_effect=add_unowned_contribution):
            with self.assertRaises(fixture.FixtureError) as raised:
                operations.integrate_batch(self.run,[task['worker_id'] for task in self.manifest['task_assignments']])
        result=json.loads((self.run/'operator/integration-result.json').read_text())
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['failure']['code'],'RETURNED_INSPECTION_INVALID')
        self.assertEqual(result['failure']['expected'],{
            'status':'returned','phase':'returned',
            'receipt':setup['workers'][0]['receipt'],
            'worktree':setup['workers'][0]['worktree'],
            'branch':setup['workers'][0]['branch'],
            'contribution_paths':['src/step_1.py'],'artifacts':[operations.OWNER_MARKER],
        })
        self.assertEqual(
            result['failure']['observed']['inspection']['contribution_paths'],
            ['src/step_1.py','src/step_3.py'],
        )
        self.assertIn('sole owned contribution',str(raised.exception))
        self.assertEqual(result['applied_worker_ids'],[])
        self.assertEqual(len(setup['workers']),3)
        after=fixture.capture_repo_state(caller)
        self.assertEqual(after['working_tree'],before['working_tree'])
        self.assertEqual(after['index_entries'],before['index_entries'])

    def test_source_drift_before_integration_preserves_dirty_input(self):
        self._prepare_synthetic_workers()
        caller=Path(self.manifest['paths']['caller'])
        notes=caller/'notes.txt'
        notes.write_text('preserve external drift\n',encoding='utf-8')
        with self.assertRaisesRegex(fixture.FixtureError,'drifted from the frozen input'):
            operations.integrate_batch(self.run,[task['worker_id'] for task in self.manifest['task_assignments']])
        result=json.loads((self.run/'operator/integration-result.json').read_text())
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['failure']['code'],'FROZEN_SOURCE_DRIFT')
        self.assertEqual(result['applied_worker_ids'],[])
        self.assertEqual(notes.read_text(encoding='utf-8'),'preserve external drift\n')

    def test_patch_conflict_after_first_apply_preserves_partial_progress_and_drift(self):
        self._prepare_synthetic_workers()
        caller=Path(self.manifest['paths']['caller'])
        step_two=caller/'src/step_2.py'
        conflict='def transform(x):\n    return 987654321\n'
        original_run=subprocess.run
        worker_two_checks=0

        def conflict_during_second_check(args, **kwargs):
            nonlocal worker_two_checks
            if (args and args[0]=='git' and 'apply' in args and '--check' in args
                    and Path(args[-1]).name=='worker-2.patch'):
                worker_two_checks+=1
                if worker_two_checks==2:
                    step_two.write_text(conflict,encoding='utf-8')
            return original_run(args,**kwargs)

        with mock.patch('operations.subprocess.run',side_effect=conflict_during_second_check):
            with self.assertRaises(fixture.FixtureError):
                operations.integrate_batch(self.run,[task['worker_id'] for task in self.manifest['task_assignments']])
        result=json.loads((self.run/'operator/integration-result.json').read_text())
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['failure']['code'],'PATCH_CONFLICT')
        self.assertEqual(result['failure']['phase'],'patch-check-2')
        self.assertEqual(result['failure']['expected'],'exit_code == 0')
        self.assertNotEqual(result['failure']['observed']['exit_code'],0)
        self.assertIn('patch does not apply',result['failure']['observed']['stderr'].lower())
        self.assertEqual(result['applied_worker_ids'],['1'])
        self.assertEqual(step_two.read_text(encoding='utf-8'),conflict)
        self.assertEqual(
            fixture.sha256_file(caller/'src/step_1.py'),
            result['patches'][0]['module_sha256'],
        )
        self.assertTrue(Path(result['failure']['evidence_path']).is_file())

    def test_second_prepare_failure_retains_first_receipt_and_refuses_rerun(self):
        original_run=subprocess.run
        prepare_count=0

        def fail_second_prepare(args, **kwargs):
            nonlocal prepare_count
            if self._is_helper_command(args,'prepare'):
                prepare_count+=1
                if prepare_count==2:
                    return subprocess.CompletedProcess(args,1,'','synthetic second prepare failure')
            return original_run(args,**kwargs)

        with mock.patch('operations.subprocess.run',side_effect=fail_second_prepare):
            with self.assertRaisesRegex(fixture.FixtureError,'helper failed at prepare-2'):
                operations.prepare_batch(self.run)
        result_path=self.run/'operator/setup-result.json'
        result=json.loads(result_path.read_text())
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(len(result['workers']),1)
        retained=result['workers'][0]['receipt']
        self.assertTrue(Path(retained).is_file())
        original=result_path.read_bytes()
        with self.assertRaisesRegex(fixture.FixtureError,'SETUP_ALREADY_ATTEMPTED'):
            operations.prepare_batch(self.run)
        self.assertEqual(result_path.read_bytes(),original)

    def test_semantically_failed_inspection_retains_receipts_and_refuses_rerun(self):
        original_run=subprocess.run

        def fail_inspection(args, **kwargs):
            if self._is_helper_command(args,'inspect'):
                completed=original_run(args,**kwargs)
                payload=json.loads(completed.stdout)
                payload['contribution_paths']=['unexpected.txt']
                return subprocess.CompletedProcess(
                    args,completed.returncode,json.dumps(payload),completed.stderr
                )
            return original_run(args,**kwargs)

        with mock.patch('operations.subprocess.run',side_effect=fail_inspection):
            with self.assertRaisesRegex(fixture.FixtureError,'unexpected changes'):
                operations.prepare_batch(self.run)
        result_path=self.run/'operator/setup-result.json'
        result=json.loads(result_path.read_text())
        self.assertEqual(result['status'],'FAILED')
        self.assertEqual(len(result['workers']),3)
        self.assertTrue(all(Path(worker['receipt']).is_file() for worker in result['workers']))
        self.assertEqual(
            result['workers'][0]['prepared_inspection']['contribution_paths'],
            ['unexpected.txt'],
        )
        original=result_path.read_bytes()
        with self.assertRaisesRegex(fixture.FixtureError,'SETUP_ALREADY_ATTEMPTED'):
            operations.prepare_batch(self.run)
        self.assertEqual(result_path.read_bytes(),original)

if __name__=='__main__':unittest.main()
