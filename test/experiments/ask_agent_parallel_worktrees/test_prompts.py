"""Generated command paths and manifest binding are deterministic."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch
import prompts

class PromptContract(unittest.TestCase):
    def test_scripted_commands_quote_spaces_and_include_collection_gate(self):
        run=Path('/temporary/experiment with spaces')
        result=prompts.make_prompt(run,5,'parallel','scripted')
        self.assertIn(shlex.quote(str(run/'operator/operations.py'))+' integrate-batch',result)
        self.assertIn('--run '+shlex.quote(str(run)),result)
        self.assertIn('--collected-worker 5',result)
        self.assertIn('independent native auditor',result)

    def test_treatments_do_not_leak_scripted_instructions_into_baseline(self):
        baseline=prompts.make_prompt('/temporary/run',3,'parallel','baseline')
        self.assertNotIn('integrate-batch',baseline)
        self.assertNotIn('Experimental scripted',baseline)
        scripted=prompts.make_prompt('/temporary/run',3,'parallel','scripted')
        self.assertEqual(scripted.count('integrate-batch'),1)
        self.assertNotIn('using git -C TARGET',scripted)

    def test_baseline_artifacts_match_exact_snapshot_exemption(self):
        text=prompts.make_prompt('/temporary/run',3,'parallel','baseline')
        self.assertIn('Declare only .experiment-local/owner.txt as the probe artifact',text)
        self.assertIn('no other ignored worker artifacts are allowed',text)
        self.assertIn('inline self-contained native handoff',text)
        self.assertIn('Do not write a handoff file',text)
        self.assertIn('After the finish probe, make no further worker filesystem writes',text)
        self.assertNotIn('Declare .experiment-local as an artifact',text)

    def test_baseline_and_batched_verify_summary_in_separate_tool_call(self):
        run = Path('/temporary/run')
        for treatment in ('baseline', 'batched'):
            with self.subTest(treatment=treatment):
                text = prompts.make_prompt(run, 3, 'parallel', treatment)
                self.assertIn('In a separate native tool call, run python3 ', text)
                self.assertIn('verify --run ' + shlex.quote(str(run)) + ' --summary', text)
                self.assertTrue('exit code 0' in text or 'exit status 0' in text, text)
                self.assertIn('untruncated stdout', text)
                self.assertIn('only one JSON object', text)
                self.assertIn('schema ask-agent-fixture-verification-summary/v1', text)
                self.assertIn('passed true, errors empty', text)
                self.assertIn('Do not chain the verification with checks.py --all', text)
                self.assertIn('The full verification.json remains retained', text)

    def test_packet_uses_exact_native_briefs_and_retains_native_collection(self):
        text=prompts.make_prompt('/temporary/run',5,'parallel','packet')
        self.assertIn('operator/briefs.py',text)
        self.assertIn('Pass each native_arguments object directly to spawn_subagent',text)
        self.assertIn('After all actual native terminal results',text)
        self.assertIn('integrate-batch',text)

    def test_compact_commands_keep_machine_json_outputs_separate(self):
        text=prompts.make_prompt('/temporary/run',3,'parallel','compact')
        self.assertIn('gets its own tool call and unmodified tool result',text)
        self.assertIn("stdout must contain only that command's single JSON object",text)
        self.assertIn('Never chain a command or append shell/Python debug or inspection output',text)
        self.assertIn('Trust the complete generated JSON',text)
        self.assertIn('Do not create temporary prompt copies or perform manual serialization audits',text)
        self.assertIn('verify --run /temporary/run --summary', text)
        self.assertIn('schema ask-agent-fixture-verification-summary/v1', text)

    def test_compact_prompt_uses_small_audit_index_and_preserves_all_gates(self):
        run=Path('/compact-prompt-baseline-fixture')
        with patch.object(prompts.Path,'resolve',return_value=run):
            compact=prompts.make_prompt(run,3,'parallel','compact')
            baseline=prompts.make_prompt(run,3,'parallel','baseline')
        self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(),
                         'a2c2d6ec09e84f00aaf5fa1a353ad19d2c5e128d95838eb0ee5555eb078d5be1')
        self.assertNotIn(f"Read that card and {run/'manifest.json'} once",compact)
        self.assertIn('scripts and independent auditor validate frozen run metadata',compact)
        self.assertIn('do not read the full manifest',compact)
        self.assertNotIn("every worker's native handle, task, actual root, branch",compact)
        self.assertIn("small audit index",compact)
        self.assertIn("worker IDs, parent-asserted native handles, binding digests, and exact retained evidence references with hashes",compact)
        self.assertIn('Keep full raw records in their existing files',compact)
        self.assertIn('SUCCESS TERMINAL BOUNDARY',compact)
        self.assertIn('The successful fixture verification summary is the compact parent\'s final gate',compact)
        self.assertIn('Run compact v4 of the Ask Agent interface experiment',compact)
        self.assertTrue('exit code 0' in compact or 'exit status 0' in compact, compact)
        self.assertIn('untruncated stdout', compact)
        self.assertIn('only one JSON object', compact)
        self.assertIn('passed true, errors empty, positive check_count, and empty failed_checks', compact)
        self.assertIn('nonempty run_id', compact)
        self.assertIn('with the exact values already received',compact)
        self.assertIn('Then return the native final response immediately',compact)
        self.assertIn('the only remaining actions are that one parent-result writer call and the native final response',compact)
        self.assertIn('Make no other successful-path read, grep, list, verification, trace, usage, or performance calls',compact)
        self.assertIn('do not reopen retained records or search for external native audits, run records, or campaign metrics',compact)
        self.assertIn('external controller performs post-exit native-history, usage, and performance analysis after the parent exits',compact)
        self.assertIn('retain the existing evidence-based diagnosis and stop behavior',compact)
        self.assertIn('does not remove or bypass any lifecycle, worker, semantic-test, return, integration, or fixture gate',compact)
        for gate in ('parent oracle', '--parent-oracle', 'prepare-batch', '--emit-worker ID',
                     'native background worker spawn and terminal collection tools',
                     'After collecting all actual native terminal results',
                     'worker-start', 'worker-finish',
                     'checks.py --worker ID', 'verify-return', 'integrate-batch',
                     'operator/fixture.py verify --run',
                     'independent native auditor'):
            self.assertIn(gate,compact)

    def test_compact_delivery_prompts_select_only_the_matching_finalizer(self):
        run=Path('/temporary/delivery run')
        commits=prompts.make_prompt(run,3,'parallel','compact','commits')
        self.assertIn('Only the assigned worker may make its task commit',commits)
        self.assertIn('parent must not commit worker contributions',commits)
        self.assertIn('integrate-batch --run',commits)
        self.assertIn('--delivery-mode commits',commits)
        self.assertNotIn('integrate-commits',commits)
        self.assertIn('Do not claim the harness proves production-scale speedup',commits)

        ephemeral=prompts.make_prompt(run,3,'parallel','compact','ephemeral')
        self.assertIn('scoped scratch edits, findings-only return',ephemeral)
        self.assertIn('finish-ephemeral --run',ephemeral)
        self.assertIn('NO_INTEGRATION',ephemeral)
        self.assertIn('must not import, patch, cherry-pick, or otherwise apply worker files',ephemeral)
        self.assertNotIn('integrate-batch --run',ephemeral)
        self.assertNotIn('integrate-commits',ephemeral)

    def test_compact_delivery_replacement_preserves_one_mode_specific_block_and_tail(self):
        run=Path('/temporary/delivery run')
        for delivery_mode, finalizer, opposite_marker in (
                ('patch','integrate-batch --run','After ephemeral finalization, in a separate native tool call,'),
                ('commits','--delivery-mode commits','After ephemeral finalization, in a separate native tool call,'),
                ('ephemeral','finish-ephemeral --run','After integration, in a separate native tool call,')):
            with self.subTest(delivery_mode=delivery_mode):
                text=prompts.make_prompt(run,3,'parallel','compact',delivery_mode)
                tail_marker=('After ephemeral finalization, in a separate native tool call,'
                             if delivery_mode=='ephemeral'
                             else 'After integration, in a separate native tool call,')
                self.assertEqual(text.count('After collecting all actual native terminal results, run'),1)
                self.assertEqual(text.count(tail_marker),1)
                self.assertNotIn(opposite_marker,text)
                block_start=text.index('After collecting all actual native terminal results, run')
                block_end=text.index(tail_marker,block_start)
                block=text[block_start:block_end]
                self.assertEqual(block.count(finalizer),1)
                self.assertEqual(block.count('verify-return --run'),1)
                if delivery_mode!='patch':
                    self.assertNotIn('The script applies only inspected immutable worker patches in ID order',block)
                self.assertEqual(text.count('schema ask-agent-fixture-verification-summary/v1'),1)
                self.assertIn('verify --run '+shlex.quote(str(run))+' --summary',text[block_end:])

    def test_manifest_count_mismatch_cannot_freeze_prompt(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'operator').mkdir();(p/'manifest.json').write_text(json.dumps({'workers':3,'mode':'parallel'}))
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                prompts.main(['--run',t,'--workers','5'])
            self.assertFalse((p/'operator/parent-prompt.txt').exists())

    def test_treatment_metadata_versions_summary_and_legacy_outputs(self):
        expected = {
            'compact': (4, 'summary-v1'),
            'baseline': (5, 'summary-v1'),
            'batched': (5, 'summary-v1'),
            'packet': (4, 'legacy'),
            'scripted': (4, 'legacy'),
        }
        for treatment, (version, output_mode) in expected.items():
            with self.subTest(treatment=treatment), tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                operator = run / 'operator'
                operator.mkdir()
                (run / 'manifest.json').write_text(json.dumps({'workers': 3, 'mode': 'parallel'}))
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        prompts.main(['--run', str(run), '--workers', '3', '--treatment', treatment]),
                        0,
                    )
                metadata = json.loads((operator / 'treatment.json').read_text())
                self.assertEqual(metadata['version'], version)
                self.assertEqual(metadata['verification_output'], output_mode)

    def test_compact_v4_freezes_one_versioned_summary_contract_for_every_delivery_mode(self):
        for delivery_mode in ('patch', 'commits', 'ephemeral'):
            with self.subTest(delivery_mode=delivery_mode), tempfile.TemporaryDirectory() as temporary:
                run=Path(temporary)
                operator=run/'operator'
                operator.mkdir()
                (run/'manifest.json').write_text(json.dumps({
                    'workers':3,'mode':'parallel','delivery_mode':delivery_mode,
                }))
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(prompts.main([
                        '--run',str(run),'--workers','3','--treatment','compact',
                        '--delivery-mode',delivery_mode,
                    ]),0)
                metadata=json.loads((operator/'treatment.json').read_text())
                self.assertEqual(metadata['version'],4)
                self.assertEqual(metadata['verification_output'],'summary-v1')
                self.assertEqual(metadata['delivery_mode'],delivery_mode)

    def test_freezes_contract_and_auditor_and_refuses_launched_run(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);op=p/'operator';op.mkdir();(p/'manifest.json').write_text(json.dumps({'workers':3,'mode':'parallel'}))
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(prompts.main(['--run',t,'--workers','3']),0)
            self.assertTrue((op/'CONTRACT.md').is_file());self.assertTrue((op/'native_trace.py').is_file())
            treatment=json.loads((op/'treatment.json').read_text())
            self.assertEqual(treatment['version'],5)
            self.assertEqual(treatment['verification_output'],'summary-v1')
            before=(op/'parent-prompt.txt').read_bytes();(op/'launch.json').write_text('{}')
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):prompts.main(['--run',t,'--workers','3'])
            self.assertEqual(before,(op/'parent-prompt.txt').read_bytes())

if __name__=='__main__':unittest.main()
