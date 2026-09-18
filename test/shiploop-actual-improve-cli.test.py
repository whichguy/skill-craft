#!/usr/bin/env python3
"""Real runtime/CLI composition; fixture judgments are synthetic, not a live review."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/shiploop/scripts'))
import shiploop_store as store  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

CLI = ROOT / 'skills/shiploop/scripts/shiploop'
CARD = ROOT / 'skills/improve/SKILL.md'
UNTIL = ROOT / 'skills/improve/runtime/until-loop/scripts/until-loop'


class ActualImproveCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='shiploop-child-cli-')
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / 'repo'
        self.run = self.base / 'run'
        # This hermetic real-Git fixture must not inherit a runner image's
        # global LFS or custom filter configuration. The workspace guard is
        # intentionally exercised by dedicated unsupported-configuration tests.
        self.environment = {
            **os.environ,
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': os.devnull,
        }
        self.repo.mkdir()
        self.product_contract = self.repo / 'product' / 'contracts' / 'cold-recovery.md'
        self.product_contract.parent.mkdir(parents=True)
        self.product_contract.write_text(
            '# Product contract\n\n## child-contract-transfer\n\nRetain the selected acceptance boundary.\n'
        )
        self.product_test = self.repo / 'test' / 'product_contract_test.py'
        self.product_test.parent.mkdir()
        self.product_test.write_text(
            'class ProductContractTests:\n'
            '    def test_child_contract_transfer(self):\n'
            '        pass\n'
        )
        self.invoke(CLI, 'init', '--repo', self.repo, '--run-dir', self.run,
                    '--prompt', 'Protocol composition fixture', '--improve-skill', CARD)
        self.run_note = self.run / 'notes' / 'parent-evidence.md'
        self.run_note.parent.mkdir()
        self.run_note.write_text(
            '# parent-evidence-transfer\n\nKeep this parent run note locatable after import.\n'
        )
        self.parent_evidence_refs = [
            str(self.product_contract) + '#child-contract-transfer',
            str(self.product_test) + '::ProductContractTests::test_child_contract_transfer',
            str(self.run_note) + '#parent-evidence-transfer',
        ]
        self.state = store.read_record(self.run / 'state.md')
        self.action = self.state['action']['id']
        self.producer = {
            'outcome': 'done', 'summary': 'Fixture intake evidence.',
            'evidence_refs': self.parent_evidence_refs,
        }
        self.input = self.run / 'inbox' / (self.action + '.md')
        store.write_record(self.input, self.producer)
        self.invoke(CLI, 'done', '--run-dir', self.run, '--action', self.action, '--result', self.input)
        self.invoke(CLI, 'improve-bind', '--run-dir', self.run, '--action', self.action, '--skill-card', CARD)
        self.bound = store.read_record(self.run / 'state.md')['active_improve']

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, executable, *args, status=0):
        result = subprocess.run([sys.executable, '-B', str(executable), *map(str, args)],
                                text=True, capture_output=True, cwd=self.base, timeout=30,
                                env=self.environment)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def initialize_child(self):
        parent_refs = self.bound['seed_result']['evidence_refs']
        # This fixture host deliberately transfers opaque parent locators into
        # fields the real v2 contract already permits. The runtimes preserve
        # those bytes, but do not enforce their semantic applicability.
        copied_refs = '\n'.join(parent_refs) if parent_refs else 'none'
        contract = {
            'version': 1, 'policy': 'decision-rubric/2',
            'original_request': (
                'Protocol-only fixture. No semantic review claim.\n'
                + self.bound['contract_marker']
                + '\nFixture host copied parent evidence references:\n'
                + copied_refs
            ),
            'interpretation': (
                'Test real runtime completion and parent callback composition. '
                'Fixture host copied parent evidence references into this existing '
                'contract field: ' + '; '.join(parent_refs or ['none'])
            ),
            'criteria': [{'id': 'C1', 'text': 'Fixture evidence exists',
                          'basis': {'kind': 'request', 'reference': 'protocol fixture'}}],
        }
        contract_path = self.base / 'contract.json'
        contract_path.write_text(json.dumps(contract))
        self.invoke(UNTIL, 'v2', 'init', '--repo', self.repo, '--contract-file', contract_path)
        child = json.loads((self.repo / '.until-loop/state.json').read_text())
        result = {'action_id': child['action']['id'], 'contract_revision': 1, 'decision': 'complete',
                  'criteria': [{'id': 'C1', 'status': 'satisfied', 'evidence': 'Synthetic protocol fixture'}],
                  'next_action': None, 'blocker': None}
        Path(child['action']['result_path']).write_text(json.dumps(result))
        return child

    def receipt(self):
        for name in ('working.md', 'review-a.md', 'review-b.md', 'checks.md'):
            (self.repo / '.until-loop' / name).write_text('Synthetic protocol evidence: ' + name)
        receipt = {'summary': 'Runtime mechanics complete; no actual review claim.',
                   'review_refs': ['.until-loop/review-a.md', '.until-loop/review-b.md'],
                   'check_refs': ['.until-loop/checks.md'], 'lessons': 'A runtime receipt is not semantic proof.'}
        path = self.run / 'inbox' / (self.action + '-improve.md')
        store.write_record(path, receipt)
        return path

    def test_current_child_completion_imports_once_and_cold_next_recovers(self):
        self.assertEqual(self.state['navigator_protocol_version'], 3)
        self.assertEqual(self.bound['seed_result']['evidence_refs'], self.parent_evidence_refs)
        child = self.initialize_child()
        frozen_contract = child['contract']
        self.assertEqual(set(frozen_contract), {
            'version', 'policy', 'original_request', 'interpretation', 'criteria', 'revision',
        })
        for reference in self.parent_evidence_refs:
            self.assertIn(reference, frozen_contract['original_request'])
            self.assertIn(reference, frozen_contract['interpretation'])
        child_state = self.repo / '.until-loop' / 'state.json'
        child_before_cold_next = child_state.read_bytes()
        child_cold = self.invoke(UNTIL, 'v2', 'next', '--repo', self.repo)
        for reference in self.parent_evidence_refs:
            self.assertIn(reference, child_cold.stdout)
        self.assertEqual(child_before_cold_next, child_state.read_bytes())
        receipt = self.receipt()
        before = (self.run / 'state.md').read_bytes()
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action,
                    '--result', receipt, status=2)
        self.assertEqual(before, (self.run / 'state.md').read_bytes())
        self.invoke(UNTIL, 'v2', 'submit', '--repo', self.repo, '--action-id', child['action']['id'])
        recovered = self.invoke(CLI, 'next', '--run-dir', self.run)
        normalized_packet = ' '.join(recovered.stdout.split())
        self.assertIn(self.bound['contract_marker'], normalized_packet)
        self.assertIn('Ordinary child review notes retain candidate and scope identity', normalized_packet)
        self.assertIn('independent reviewer availability, use, or permitted fallback', normalized_packet)
        self.assertIn('whether reused evidence still applies', normalized_packet)
        self.assertIn('short decision and reference locators for cold recovery', normalized_packet)
        for reference in self.parent_evidence_refs:
            self.assertIn(reference, recovered.stdout)
        self.assertEqual(before, (self.run / 'state.md').read_bytes())
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action, '--result', receipt)
        after = (self.run / 'state.md').read_bytes()
        state = store.read_record(self.run / 'state.md')
        self.assertEqual(state['stage'], 'discovery')
        self.assertIsNone(state['active_improve'])
        self.assertEqual(len(state['improve_results']), 1)
        self.assertTrue((self.run / 'improve' / self.action / 'working.md').is_file())
        self.assertEqual(state['accepted'][self.action]['evidence_refs'], self.parent_evidence_refs)
        self.assertEqual(state['improve_results'][self.action]['seed_result']['evidence_refs'],
                         self.parent_evidence_refs)
        archived_contract = json.loads(
            (self.run / 'improve' / self.action / 'state.json').read_text()
        )['contract']
        self.assertEqual(archived_contract, frozen_contract)
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action, '--result', receipt)
        self.invoke(CLI, 'done', '--run-dir', self.run, '--action', self.action, '--result', self.input)
        self.assertEqual(after, (self.run / 'state.md').read_bytes())
        record = store.read_record(receipt)
        record['summary'] = 'Conflicting callback'
        store.write_record(receipt, record)
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action,
                    '--result', receipt, status=2)
        self.assertEqual(after, (self.run / 'state.md').read_bytes())

    def test_linked_completion_inbox_cannot_be_read_or_advance(self):
        self.initialize_child()
        receipt = self.receipt()
        original = receipt.with_name('elsewhere.md')
        receipt.replace(original)
        receipt.symlink_to(original)
        before = (self.run / 'state.md').read_bytes()
        result = self.invoke(CLI, 'improve-complete', '--run-dir', self.run,
                             '--action', self.action, '--result', receipt, status=2)
        self.assertIn('non-symlink', result.stderr)
        self.assertEqual(before, (self.run / 'state.md').read_bytes())

    def test_relative_skill_selection_is_bound_to_initial_cwd_for_cold_recovery(self):
        selected = self.base / 'selected-improve.md'
        selected.symlink_to(CARD)
        run = self.base / 'relative-selection-run'
        self.invoke(CLI, 'init', '--repo', self.repo, '--run-dir', run,
                    '--prompt', 'Relative selection recovery fixture',
                    '--improve-skill', selected.name)
        state = store.read_record(run / 'state.md')
        self.assertEqual(state['improve_skill'], str(selected))
        action = state['action']['id']
        result = run / 'inbox' / (action + '.md')
        store.write_record(result, {'outcome': 'done', 'summary': 'Fixture producer'})
        self.invoke(CLI, 'done', '--run-dir', run, '--action', action, '--result', result)
        before = (run / 'state.md').read_bytes()
        cold = subprocess.run([sys.executable, '-B', str(CLI), 'next', '--run-dir', str(run)],
                              cwd='/', text=True, capture_output=True, timeout=30,
                              env=self.environment)
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertIn('--skill-card=' + str(selected), cold.stdout)
        bound = subprocess.run([sys.executable, '-B', str(CLI), 'improve-bind',
                                '--run-dir', str(run), '--action', action,
                                '--skill-card', state['improve_skill']],
                               cwd='/', text=True, capture_output=True, timeout=30,
                               env=self.environment)
        self.assertEqual(bound.returncode, 0, bound.stderr)
        self.assertNotEqual(before, (run / 'state.md').read_bytes())
        self.assertEqual(store.read_record(run / 'state.md')['active_improve']['skill']['skill_card'],
                         str(CARD.resolve()))

    def test_workspace_returns_only_after_final_child_then_imports_without_deadlock(self):
        source = self.base / 'source'
        source.mkdir()
        for args in [('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                     ('config', 'user.name', 'Fixture'), ('config', 'commit.gpgsign', 'false'),
                     ('config', 'core.hooksPath', '/dev/null')]:
            subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True,
                           env=self.environment)
        (source / 'product.txt').write_text('baseline\n')
        subprocess.run(['git', '-C', str(source), 'add', 'product.txt'], check=True,
                       env=self.environment)
        subprocess.run(['git', '-C', str(source), 'commit', '-qm', 'baseline'], check=True,
                       env=self.environment)
        workspace = self.base / 'isolated'
        self.invoke(CLI, 'workspace', 'start', '--repo', source, '--workspace-root', workspace,
                    '--prompt', 'Synthetic final return boundary fixture', '--improve-skill', CARD)
        self.repo = workspace / 'worktree'
        self.run = workspace / 'run'
        state = store.read_record(self.run / 'state.md')
        # Synthetic predecessors position the real CLI test at its final boundary.
        while navigator.current_stage(state) != 'handoff':
            if navigator.current_stage(state) == 'release':
                navigator.save(self.run, state)
                self.invoke(CLI, 'workspace', 'return', '--workspace-root', workspace, status=2)
            action = navigator.current_action(state)['id']
            state = navigator.apply(state, action, {'outcome': 'done', 'summary': 'Synthetic setup'})
            state = navigator.finish_improve(state, action, {'summary': 'Synthetic predecessor child'})
        navigator.save(self.run, state)
        self.invoke(CLI, 'workspace', 'return', '--workspace-root', workspace, status=2)
        self.action = navigator.current_action(state)['id']
        self.input = self.run / 'inbox' / (self.action + '.md')
        store.write_record(self.input, {'outcome': 'done', 'summary': 'Final fixture handoff'})
        self.invoke(CLI, 'done', '--run-dir', self.run, '--action', self.action, '--result', self.input)
        self.invoke(CLI, 'improve-bind', '--run-dir', self.run, '--action', self.action, '--skill-card', CARD)
        self.bound = store.read_record(self.run / 'state.md')['active_improve']
        child = self.initialize_child()
        receipt = self.receipt()
        (self.repo / 'product.txt').write_text('final child reviewed candidate\n')
        self.invoke(CLI, 'workspace', 'plan-return', '--workspace-root', workspace)
        plan = store.read_record(workspace / 'return-plan.md')
        for row in plan['paths']:
            self.assertNotIn('.until-loop', Path(row['path']).parts)
            row['disposition'] = 'keep'
        store.write_record(workspace / 'return-plan.md', plan)
        before = (self.run / 'state.md').read_bytes()
        self.invoke(CLI, 'workspace', 'return', '--workspace-root', workspace, status=2)
        self.assertEqual((source / 'product.txt').read_text(), 'baseline\n')
        self.invoke(UNTIL, 'v2', 'submit', '--repo', self.repo, '--action-id', child['action']['id'])
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action,
                    '--result', receipt, status=2)
        self.assertEqual((self.run / 'state.md').read_bytes(), before)
        submission = store.read_record(receipt)
        store.write_record(receipt, dict(submission, final_result={
            'outcome': 'blocked', 'summary': 'Review finished but delivery prerequisite is unresolved.'}))
        self.invoke(CLI, 'workspace', 'return', '--workspace-root', workspace, status=2)
        self.assertEqual((source / 'product.txt').read_text(), 'baseline\n')
        store.write_record(receipt, submission)
        self.invoke(CLI, 'workspace', 'return', '--workspace-root', workspace)
        self.assertEqual((source / 'product.txt').read_text(), 'final child reviewed candidate\n')
        self.assertFalse((source / '.until-loop').exists())
        self.assertEqual((self.run / 'state.md').read_bytes(), before)
        self.invoke(CLI, 'improve-complete', '--run-dir', self.run, '--action', self.action, '--result', receipt)
        self.assertEqual(store.read_record(self.run / 'state.md')['status'], 'done')


if __name__ == '__main__':
    unittest.main()
