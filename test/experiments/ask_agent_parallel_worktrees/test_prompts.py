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

    def test_compact_prompt_uses_small_audit_index_and_preserves_all_gates(self):
        run=Path('/compact-prompt-baseline-fixture')
        with patch.object(prompts.Path,'resolve',return_value=run):
            compact=prompts.make_prompt(run,3,'parallel','compact')
            baseline=prompts.make_prompt(run,3,'parallel','baseline')
        self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(),
                         'd4ff6a4cc5e932a0ba14930690cb7db874050cf801131b8fdf32b2a6c06a08ed')
        self.assertNotIn(f"Read that card and {run/'manifest.json'} once",compact)
        self.assertIn('scripts and independent auditor validate frozen run metadata',compact)
        self.assertIn('do not read the full manifest',compact)
        self.assertNotIn("every worker's native handle, task, actual root, branch",compact)
        self.assertIn("small audit index with overall status",compact)
        self.assertIn("ID, status, native handle, binding digest, and exact retained evidence record references",compact)
        self.assertIn('Keep full raw records in their existing files',compact)
        for gate in ('parent oracle', '--parent-oracle', 'prepare-batch', '--emit-worker ID',
                     'native background worker spawn and terminal collection tools',
                     'After collecting all actual native terminal results',
                     'worker-start', 'worker-finish',
                     'checks.py --worker ID', 'verify-return', 'integrate-batch',
                     'operator/fixture.py verify --run',
                     'independent native auditor'):
            self.assertIn(gate,compact)

    def test_manifest_count_mismatch_cannot_freeze_prompt(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'operator').mkdir();(p/'manifest.json').write_text(json.dumps({'workers':3,'mode':'parallel'}))
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                prompts.main(['--run',t,'--workers','5'])
            self.assertFalse((p/'operator/parent-prompt.txt').exists())

    def test_freezes_contract_and_auditor_and_refuses_launched_run(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);op=p/'operator';op.mkdir();(p/'manifest.json').write_text(json.dumps({'workers':3,'mode':'parallel'}))
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(prompts.main(['--run',t,'--workers','3']),0)
            self.assertTrue((op/'CONTRACT.md').is_file());self.assertTrue((op/'native_trace.py').is_file())
            before=(op/'parent-prompt.txt').read_bytes();(op/'launch.json').write_text('{}')
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):prompts.main(['--run',t,'--workers','3'])
            self.assertEqual(before,(op/'parent-prompt.txt').read_bytes())

if __name__=='__main__':unittest.main()
