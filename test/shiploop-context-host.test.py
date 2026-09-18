#!/usr/bin/env python3
"""Real Navigator/CLI integration with a fake model transport; no real Improve."""
from argparse import Namespace
from copy import deepcopy
import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"))
import shiploop_context_host as session_driver

from shiploop_host import HostError as TransportError
from shiploop_context_host import CLI, navigator, store
from shiploop_context_host import DriverError, drive, owner_lock, owner_transition, selected_policy


def _result(stage, outcome="done", **extra):
    return {"outcome": outcome, "summary": "Synthetic setup only: " + stage, "evidence_refs": [], **extra}


def _receipt(stage):
    return {"kind": "synthetic-context-host-test/v1", "summary": "No real Improve: " + stage,
            "review_refs": [], "check_refs": [], "lessons": "Synthetic fixture only."}


def _at_first_carry_forward(repo, run, *, work_items):
    state = navigator.new_state(str(repo), "Context host test", protocol_version=3, improve_skill="")
    for stage in navigator.graph(state)[0] + navigator.graph(state)[1][:-1]:
        action = navigator.current_action(state)["id"]
        result = _result(stage, **({"work_items": work_items} if stage == "plan" else {}))
        state = navigator.finish_improve(navigator.apply(state, action, result), action, _receipt(stage))
    return state


class FakeTransport:
    def __init__(self, test, **_):
        self.test = test
        self.ids = []
        self.prompts = []
        self.resumed = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def start_thread(self, repo):
        task = 'task-' + str(len(self.ids) + 1)
        self.ids.append(task)
        return task

    def resume_thread(self, task):
        self.resumed.append(task)
        return task

    def run_turn(self, task, prompt):
        self.prompts.append((task, prompt))
        state = store.read_record(self.test.run / 'state.md')
        stage = navigator.current_stage(state)
        action = navigator.current_action(state)['id']
        if self.test.mode == 'failure':
            raise TransportError('synthetic disconnect after claim')
        if self.test.mode == 'no-progress':
            return {'status': 'completed', 'text': 'no action', 'usage': None}
        if state['active_improve']:
            # Simulate the extra revision used by real Improve binding, then
            # complete through the real pure API with a labelled fake receipt.
            if self.test.extra_revision:
                state['revision'] += 1
            after = navigator.finish_improve(state, action, _receipt(stage))
        else:
            after = navigator.apply(state, action, _result(stage))
        navigator.save(self.test.run, after)
        return {'status': 'completed', 'thread_id': task,
                'text': 'Synthetic fixture owner, no real Improve.', 'usage': None}


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.run = self.root / 'run'
        self.run.mkdir()
        self.mode = 'normal'
        self.extra_revision = False
        self.state = _at_first_carry_forward(self.repo, self.run,
            work_items=[{'id': 'W1', 'title': 'one'}, {'id': 'W2', 'title': 'two'}])
        navigator.save(self.run, self.state)
        self.args = Namespace(cli=str(CLI), run_dir=str(self.run), host='codex',
                              context_reset=None, max_turns=3, allow_network=False)
        self.host = FakeTransport(self)

    def tearDown(self):
        self.temp.cleanup()

    def run_driver(self):
        return drive(self.args, transport_factory=lambda *a, **kw: self.host, environ={})

    def receipt(self):
        return store.read_record(self.run / 'context-host.md')

    def test_native_host_selection_and_no_nested_controller(self):
        for host in ('grok', 'claude'):
            self.args.host = host
            # Separate receipts per selected host, with no model calls needed
            # to test the environment guard.
            with self.assertRaisesRegex(DriverError, 'already supervised'):
                drive(self.args, transport_factory=lambda *a, **kw: self.host,
                      environ={'SHIPLOOP_CONTEXT_HOST_WORKER': '1'})
        self.assertEqual(self.host.ids, [])
        self.args.host = 'claude'
        self.args.allow_network = True
        with self.assertRaisesRegex(DriverError, 'Codex sandbox option'):
            self.run_driver()

    def test_packaged_cli_is_portable_and_rejects_invalid_policy_before_host(self):
        package = self.root / 'installed skill'
        shutil.copytree(CLI.parent.parent, package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        cli = package / 'scripts' / 'shiploop'
        env = {**os.environ, 'SHIPLOOP_CONTEXT_RESET': 'invalid'}
        env.pop('SHIPLOOP_CONTEXT_HOST_WORKER', None)
        result = subprocess.run([sys.executable, '-B', str(cli), 'drive', '--run-dir', str(self.run),
                                 '--host', 'codex'], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('must be off or inner-loop', result.stderr)
        self.assertFalse((self.run / 'context-host.md').exists())
        help_result = subprocess.run([sys.executable, '-B', str(cli), 'drive', '--help'],
                                     text=True, capture_output=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn('--context-reset', help_result.stdout)
        self.assertIn('codex,grok,claude', help_result.stdout)

    def test_public_cli_runs_packaged_controller_across_boundary(self):
        package = self.root / 'selected installed package'
        shutil.copytree(CLI.parent.parent, package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        cli = package / 'scripts' / 'shiploop'
        bins = self.root / 'bin'
        bins.mkdir()
        executable = bins / 'codex'
        executable.write_text("#!" + sys.executable + "\n" + r'''
import json, os, pathlib, sys
sys.path.insert(0, os.environ['SHIPLOOP_TEST_SCRIPTS'])
import shiploop_navigator as nav
import shiploop_store as store
assert os.environ['SHIPLOOP_CONTEXT_HOST_WORKER'] == '1'
root = pathlib.Path(os.environ['SHIPLOOP_TEST_RUN'])
sessions = 0
turns = 0
def emit(x):
    print(json.dumps(x), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    method = request.get('method')
    rid = request.get('id')
    params = request.get('params', {})
    if method == 'initialize':
        emit({'id': rid, 'result': {}})
    elif method == 'thread/start':
        sessions += 1
        emit({'id': rid, 'result': {'thread': {'id': 'fixture-' + str(sessions)}}})
    elif method == 'turn/start':
        turns += 1
        tid = 'owner-' + str(turns)
        thread = params['threadId']
        assert os.environ['SHIPLOOP_TEST_CLI'] in params['input'][0]['text']
        emit({'id': rid, 'result': {'turn': {'id': tid}}})
        state = store.read_record(root / 'state.md')
        action = nav.current_action(state)['id']
        if state['active_improve'] is None:
            state = nav.apply(state, action, {'outcome': 'done', 'summary': 'Synthetic CLI fixture', 'evidence_refs': []})
        else:
            state = nav.finish_improve(state, action, {'kind': 'synthetic-cli-fixture', 'summary': 'No actual Improve executed'})
        nav.save(root, state)
        emit({'method': 'turn/completed', 'params': {'threadId': thread,
              'turn': {'id': tid, 'status': 'completed', 'error': None}}})
''')
        executable.chmod(0o755)
        env = {**os.environ, 'PATH': str(bins) + os.pathsep + os.environ['PATH'],
               'SHIPLOOP_TEST_SCRIPTS': str(cli.parent), 'SHIPLOOP_TEST_RUN': str(self.run),
               'SHIPLOOP_TEST_CLI': str(cli)}
        env.pop('SHIPLOOP_CONTEXT_RESET', None)
        env.pop('SHIPLOOP_CONTEXT_HOST_WORKER', None)
        result = subprocess.run([sys.executable, '-B', str(cli), 'drive', '--run-dir', str(self.run),
                                 '--host', 'codex', '--max-turns=3'], text=True, capture_output=True,
                                env=env, timeout=30)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        receipt = self.receipt()
        self.assertEqual(receipt['cli'], str(cli))
        self.assertEqual([x['thread_id'] for x in receipt['turns']], ['fixture-1', 'fixture-1', 'fixture-2'])
        self.assertEqual(len(receipt['reset_boundaries']), 1)
        self.assertEqual(receipt['status'], 'ready')

    def test_completed_run_returns_report_packet_without_starting_host(self):
        state = self.state
        for _ in range(100):
            if state['status'] == 'done':
                break
            stage = navigator.current_stage(state)
            action = navigator.current_action(state)['id']
            state = navigator.finish_improve(navigator.apply(state, action, _result(stage)),
                                             action, _receipt(stage))
        self.assertEqual(state['status'], 'done')
        navigator.save(self.run, state)
        result = self.run_driver()
        self.assertEqual(result['status'], 'done')
        self.assertIn(str(self.run / 'report.html'), result['packet'])
        self.assertEqual(self.host.ids, [])

    def test_policy_precedence_and_strict_values(self):
        self.assertEqual(selected_policy(None, {}), 'inner-loop')
        self.assertEqual(selected_policy(None, {}, 'inner-loop'), 'inner-loop')
        self.assertEqual(selected_policy(None, {}, 'off'), 'off')
        self.assertEqual(selected_policy('off', {'SHIPLOOP_CONTEXT_RESET': 'inner-loop'}), 'off')
        self.assertEqual(selected_policy(None, {'SHIPLOOP_CONTEXT_RESET': 'off'}), 'off')
        self.assertEqual(selected_policy(None, {'SHIPLOOP_CONTEXT_RESET': 'inner-loop'}), 'inner-loop')
        for value in ('', 'INNER-LOOP', 'inner-loop '):
            with self.assertRaises(DriverError):
                selected_policy(None, {'SHIPLOOP_CONTEXT_RESET': value})
        with self.assertRaises(DriverError):
            selected_policy('off', {}, 'inner-loop')

    def test_boundary_keeps_producer_then_clears_after_improve(self):
        self.extra_revision = True
        self.assertEqual(self.run_driver()['status'], 'turn-limit')
        self.assertEqual([t for t, _ in self.host.prompts], ['task-1', 'task-1', 'task-2'])
        self.assertEqual(len(self.receipt()['reset_boundaries']), 1)
        self.assertEqual(self.receipt()['status'], 'ready')
        self.assertTrue(self.host.closed)
        self.assertIn('W2', self.host.prompts[-1][1])
        self.assertNotIn('Synthetic fixture owner, no real Improve.', self.host.prompts[-1][1])

    def test_off_retains_thread_across_same_boundary(self):
        self.args.context_reset = 'off'
        self.run_driver()
        self.assertEqual([t for t, _ in self.host.prompts], ['task-1'] * 3)
        self.assertEqual(self.receipt()['reset_boundaries'], [])

    def test_pending_boundary_survives_exit_and_resets_once(self):
        self.args.max_turns = 2
        self.run_driver()
        self.assertTrue(self.receipt()['need_fresh'])
        self.args.context_reset = None  # saved policy survives environment loss
        self.args.max_turns = 1
        self.run_driver()
        self.assertEqual(self.host.ids, ['task-1', 'task-2'])
        self.assertEqual(len(self.receipt()['reset_boundaries']), 1)
        self.assertFalse(self.receipt()['need_fresh'])
        self.assertEqual(self.receipt()['policy'], 'inner-loop')

    def test_saved_off_policy_survives_default_on_resume(self):
        self.args.context_reset = 'off'
        self.args.max_turns = 2
        self.run_driver()
        self.args.context_reset = None
        self.args.max_turns = 1
        self.run_driver()
        self.assertEqual(self.receipt()['policy'], 'off')
        self.assertEqual(self.receipt()['reset_boundaries'], [])
        self.assertEqual(self.host.ids, ['task-1'])
        self.assertEqual(self.host.resumed, ['task-1'])
        self.assertEqual([task for task, _ in self.host.prompts], ['task-1'] * 3)

    def test_safe_restart_resumes_same_task(self):
        self.args.max_turns = 1
        self.run_driver()
        self.run_driver()
        self.assertEqual(self.host.resumed, ['task-1'])
        self.assertEqual(self.host.ids, ['task-1'])

    def test_failure_claim_refuses_replay_and_closes_transport(self):
        self.mode = 'failure'
        with self.assertRaises(TransportError):
            self.run_driver()
        self.assertTrue(self.host.closed)
        self.assertEqual(self.receipt()['status'], 'uncertain')
        self.assertEqual(self.receipt()['thread_id'], 'task-1')
        with self.assertRaisesRegex(DriverError, 'Uncertain prior owner'):
            self.run_driver()
        self.assertEqual(len(self.host.prompts), 1)

    def test_receipt_failure_after_task_creation_never_starts_owner(self):
        original = session_driver.save_receipt
        calls = []
        def fail_on_identity(run, receipt):
            calls.append(receipt['status'])
            if receipt.get('thread_id') and receipt['status'] == 'running':
                raise OSError('injected receipt persistence failure')
            return original(run, receipt)
        with patch.object(session_driver, 'save_receipt', side_effect=fail_on_identity):
            with self.assertRaises(OSError):
                self.run_driver()
        self.assertEqual(self.host.ids, ['task-1'])
        self.assertEqual(self.host.prompts, [])
        self.assertEqual(self.receipt()['status'], 'uncertain')
        self.assertTrue(self.host.closed)

    def test_pending_receipt_write_failure_does_not_start_model(self):
        original = session_driver.save_receipt
        def fail_on_claim(run, receipt):
            if receipt['status'] == 'running':
                raise OSError('injected claim failure')
            return original(run, receipt)
        with patch.object(session_driver, 'save_receipt', side_effect=fail_on_claim):
            with self.assertRaises(OSError):
                self.run_driver()
        self.assertEqual(self.host.ids, [])
        self.assertEqual(self.host.prompts, [])
        self.assertEqual(self.receipt()['status'], 'ready')
        self.assertTrue(self.host.closed)

    def test_malformed_saved_receipt_rejected_before_model(self):
        self.args.max_turns = 1
        self.run_driver()
        receipt = self.receipt()
        del receipt['turns']
        session_driver.save_receipt(self.run, receipt)
        with self.assertRaisesRegex(DriverError, 'missing or unknown'):
            self.run_driver()
        self.assertEqual(len(self.host.prompts), 1)

    def test_no_progress_is_not_silently_retried(self):
        self.mode = 'no-progress'
        with self.assertRaisesRegex(DriverError, 'did not advance'):
            self.run_driver()
        self.assertEqual(self.receipt()['status'], 'uncertain')
        self.assertEqual(len(self.host.prompts), 1)

    def test_external_state_change_and_policy_change_rejected(self):
        self.args.max_turns = 1
        self.run_driver()
        self.args.context_reset = 'off'
        with self.assertRaisesRegex(DriverError, 'Policy differs'):
            self.run_driver()
        self.args.context_reset = 'inner-loop'
        state = store.read_record(self.run / 'state.md')
        navigator.save(self.run, navigator.control(state, 'pause', 'External owner'))
        with self.assertRaisesRegex(DriverError, 'outside the launcher'):
            self.run_driver()

    def test_other_host_cli_and_symlinks_fail_before_model(self):
        self.args.host = 'unknown'
        with self.assertRaisesRegex(DriverError, 'Unsupported context host'):
            self.run_driver()
        self.args.host = 'codex'
        self.args.cli = '/bin/echo'
        with self.assertRaisesRegex(DriverError, 'bundled ShipLoop CLI'):
            self.run_driver()
        self.args.cli = str(CLI)
        target = self.root / 'target'
        target.write_text('untouched')
        (self.run / 'context-host.md').symlink_to(target)
        with self.assertRaisesRegex(DriverError, 'symlink'):
            self.run_driver()
        self.assertEqual(target.read_text(), 'untouched')
        self.assertEqual(self.host.ids, [])

    def test_logical_cli_symlink_preserved(self):
        link = self.root / 'selected-package' / 'shiploop'
        link.parent.mkdir()
        link.symlink_to(CLI)
        self.args.cli = str(link)
        self.args.max_turns = 1
        # A bare CLI symlink changes PACKAGE_ROOT unless linked at a full package;
        # use a directory symlink so this verifies the actual supported locator.
        link.unlink()
        link.parent.rmdir()
        link.parent.symlink_to(CLI.parent, target_is_directory=True)
        self.run_driver()
        self.assertEqual(self.receipt()['cli'], str(link))
        self.assertIn(str(link), self.host.prompts[0][1])

    def test_exclusive_lock(self):
        with owner_lock(self.run):
            with self.assertRaisesRegex(DriverError, 'Another context host'):
                self.run_driver()
        self.assertEqual(self.host.ids, [])

    def test_last_item_boundary_resets_before_outer_work(self):
        state = _at_first_carry_forward(self.repo, self.run,
            work_items=[{'id': 'W1', 'title': 'last item'}])
        action = navigator.current_action(state)['id']
        waiting = navigator.apply(state, action, _result('carry-forward'))
        after = navigator.finish_improve(waiting, action, _receipt('carry-forward'))
        self.assertEqual(navigator.current_stage(after), 'system-test-author')
        self.assertEqual(owner_transition(waiting, after), state['run_id'] + ':' + action)

    def test_inconsistent_history_cannot_request_reset(self):
        action = navigator.current_action(self.state)['id']
        waiting = navigator.apply(self.state, action, _result('carry-forward'))
        after = navigator.finish_improve(waiting, action, _receipt('carry-forward'))
        for key, value in [('stage', 'select-work'), ('outcome', 'repeat')]:
            malformed = deepcopy(after)
            malformed['history'][-1][key] = value
            try:
                decision = owner_transition(waiting, malformed)
            except (DriverError, navigator.NavigatorError):
                decision = None
            self.assertIsNone(decision)

    def test_no_reset_for_producer_pause_repeat_or_other_stage(self):
        action = navigator.current_action(self.state)['id']
        waiting = navigator.apply(self.state, action, _result('carry-forward'))
        self.assertIsNone(owner_transition(self.state, waiting))
        self.assertIsNone(owner_transition(waiting, navigator.control(waiting, 'pause', 'Wait')))
        repeat = navigator.finish_improve(waiting, action, _receipt('carry-forward'),
                                          _result('carry-forward', 'repeat'))
        self.assertIsNone(owner_transition(waiting, repeat))
        with self.assertRaises(DriverError):
            owner_transition(waiting, waiting)
        done = navigator.finish_improve(waiting, action, _receipt('carry-forward'))
        action2 = navigator.current_action(done)['id']
        waiting2 = navigator.apply(done, action2, _result('select-work'))
        done2 = navigator.finish_improve(waiting2, action2, _receipt('select-work'))
        self.assertIsNone(owner_transition(waiting2, done2))
        with self.assertRaises(DriverError):
            owner_transition(waiting, done2)


if __name__ == '__main__':
    unittest.main()
