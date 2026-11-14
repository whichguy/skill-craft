#!/usr/bin/env python3
"""Public recovery inspection against real hello-family workspace lifecycles."""
import fcntl
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
fixture = runpy.run_path(str(ROOT / 'test/shiploop-workspace.test.py'))
workspace, store = fixture['workspace'], fixture['store']
sys.path.insert(0, str(ROOT / 'test/shiploop_e2e'))
import recovery


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.f = fixture['ShipLoopWorkspaceTests']()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.env["SHIPLOOP_PROGRESS"] = "off"
        self.out = self.f.base.resolve()
        self.root = self.out / 'hello-workspace'
        self.f.cli('workspace', 'start', '--repo', str(self.f.repo), '--workspace-root',
                   str(self.root), '--prompt', 'Build a hello CLI that prints Hello, world.')
        self.manifest = store.read_record(self.root / 'workspace.md')
        self.tree = Path(self.manifest['worktree'])
        (self.out / 'invocation.json').write_text(json.dumps({
            'case': 'hello', 'host': 'fixture', 'cwd': str(self.f.repo.resolve()),
            'versions': {'source_commit': 'frozen-apparatus'},
        }))
        (self.out / 'result.json').write_text('{"pass":false,"failed":"original"}\n')

    def inventory(self):
        return {str(p.relative_to(self.out)): (p.lstat().st_mode, p.lstat().st_mtime_ns,
                os.readlink(p) if p.is_symlink() else p.read_bytes())
                for p in self.out.rglob('*') if p.is_symlink() or p.is_file()}

    def inspect(self, phase='builder', code=0):
        before = self.inventory()
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'test/shiploop_e2e/run.py'),
            '--inspect-recovery', str(self.out), '--recovery-phase', phase, '--json'],
            text=True, capture_output=True, timeout=15, env=self.f.env)
        after = self.inventory()
        changed = [key for key in before.keys() | after.keys() if before.get(key) != after.get(key)]
        self.assertEqual(changed, [], 'inspection changed retained inputs or Git metadata')
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_dirty_active_hello_and_verified_return(self):
        (self.tree / 'hello.txt').write_text('Hello, world.\n')
        active = self.inspect()
        self.assertEqual(active['source']['repo'], str(self.tree))
        self.assertEqual(active['selected_run']['run_dir'], self.manifest['run_dir'])
        self.f._plan(self.root)
        self.f._resolve_plan(self.root)
        self.f._execute(self.root)
        final = self.inspect('final')
        self.assertEqual(final['source']['repo'], str(self.f.repo.resolve()))
        self.assertEqual(final['binding']['kind'], 'verified-return')

    def test_foreign_sibling_is_not_execution_worktree(self):
        sibling = self.out / 'sibling'
        self.f.git('worktree', 'add', '-q', '-b', 'foreign', str(sibling))
        state_path = self.root / 'run/state.md'
        state = store.read_record(state_path)
        state['repo'] = str(sibling)
        store.write_record(state_path, state)
        self.assertEqual(self.inspect(code=2)['status'], 'UNKNOWN')

    def test_final_inspection_rechecks_return_after_tracked_source_edit(self):
        self.f._plan(self.root)
        self.f._resolve_plan(self.root)
        self.f._execute(self.root)
        self.inspect('final')
        before = self.inventory()
        observed = self.f._call(workspace.binding_snapshot, self.root, self.tree)
        snapshot = workspace.completed_receipt_snapshot
        validated = []
        source = self.f.repo.resolve() / 'tracked-staged.txt'

        def edit_after_validation(*args):
            receipt = snapshot(*args)
            if not validated:
                self.assertIsNotNone(receipt, 'race must start from a valid return')
                validated.append(receipt)
                source.write_text('changed after receipt validation\n')
            return receipt

        with mock.patch.object(workspace, 'completed_receipt_snapshot', side_effect=edit_after_validation):
            result = self.f._call(recovery.inspect_context, self.out, 'final')
        self.assertEqual(len(validated), 1)
        # HEAD and ownership still match: only the completed-return validator can reject this edit.
        self.assertEqual(self.f._call(workspace.binding_snapshot, self.root, self.tree), observed)
        after = self.inventory()
        self.assertEqual([key for key in before.keys() | after.keys() if before.get(key) != after.get(key)],
                         [str(source.relative_to(self.out))])
        self.assertEqual(result['status'], 'UNKNOWN', result)
        self.assertIsNone(result['source'])
        self.assertIsNone(result['binding'])

    def test_fifo_workspace_lock_is_promptly_unresolved_without_writes(self):
        lock = self.root / '.workspace.lock'
        lock.unlink()
        os.mkfifo(lock)
        metadata = lock.lstat()
        # subprocess.run kills and reaps the inspector if opening the FIFO blocks.
        self.assertEqual(self.inspect(code=2)['status'], 'UNKNOWN')
        self.assertEqual(lock.lstat(), metadata)

    def test_ambiguous_and_unreadable_launches_are_visible(self):
        other = self.out / 'another'
        self.f.cli('workspace', 'start', '--repo', str(self.f.repo), '--workspace-root',
                   str(other), '--prompt', 'Another hello.')
        self.assertEqual(self.inspect(code=2)['reason'], 'ambiguous-runs')
        (self.out / 'shiploop-run.json').write_text(json.dumps({'run_dir': self.manifest['run_dir']}))
        (self.out / 'invocation-resume-fixture-1.json').write_text('{')
        result = self.inspect(code=2)
        self.assertEqual(result['unreadable_launches'], ['invocation-resume-fixture-1.json'])

    def test_missing_busy_lock_and_pending_transaction_do_not_recover(self):
        self.f._plan(self.root)
        self.f._resolve_plan(self.root)
        self.f._execute(self.root)
        self.inspect('final')
        lock = self.root / '.workspace.lock'
        with lock.open('r') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.inspect(code=2)
            self.inspect('final', code=2)
        original = lock.read_bytes()
        lock.unlink()
        self.inspect(code=2)
        self.inspect('final', code=2)
        lock.write_bytes(original)
        def fault(phase, index):
            if phase == 'after-target' and index == 1:
                raise RuntimeError('interrupt')
        with self.assertRaises(RuntimeError):
            store.transaction(self.root, {'pending.md': 'pending\n'}, fault=fault)
        self.inspect(code=2)
        self.inspect('final', code=2)
        self.assertTrue((self.root / store.JOURNAL_NAME).exists())

    def test_malformed_and_symlink_git_metadata_refused(self):
        gitfile = self.tree / '.git'
        raw = gitfile.read_bytes()
        gitfile.write_text('gitdir: missing\n')
        self.inspect(code=2)
        gitfile.unlink()
        alternate = self.out / 'git-pointer'
        alternate.write_bytes(raw)
        gitfile.symlink_to(alternate)
        self.inspect(code=2)
        gitfile.unlink()
        gitfile.write_bytes(raw)
        gitdir = Path(raw.decode().strip().split('gitdir: ', 1)[1])
        common = gitdir / 'commondir'
        pointer = common.read_bytes()
        common.unlink()
        target = self.out / 'common-pointer'
        target.write_bytes(pointer)
        common.symlink_to(target)
        self.inspect(code=2)


    def test_foreign_launch_and_final_without_return_refused(self):
        self.inspect('final', code=2)
        launch = self.out / 'invocation.json'
        value = json.loads(launch.read_text())
        value['cwd'] = str(self.tree)
        launch.write_text(json.dumps(value))
        self.inspect(code=2)


if __name__ == '__main__':
    unittest.main()
