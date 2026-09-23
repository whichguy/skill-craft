#!/usr/bin/env python3
"""Navigator graph acceptance: actual routes and packets without project work."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/shiploop/scripts'
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator_dry_run as driver  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class NavigatorDryRunTests(unittest.TestCase):
    def test_access_policy_is_reachable_through_actual_graph_and_recovery(self):
        # A routing/locator contract, not proof that a host follows auth advice.
        policy = ROOT / 'skills/shiploop/references/research-loop.md'
        for name in ('delivery', 'blocked-resume', 'pause-resume'):
            report = driver.run_scenario(name, driver.scenarios()[name])
            self.assertTrue(report['ok'], report.get('error'))
            for event in report['events']:
                with self.subTest(scenario=name, stage=event['from']):
                    self.assertEqual(event['prompt'].count(
                        f'Access-readiness policy: {policy}#early-access-readiness'
                    ), 1)
                    self.assertEqual(event['prompt'].count(
                        'Cross-run knowledge policy: '
                        + str(policy.parent / 'project-knowledge.md')
                    ), 1)
                    self.assertIn(
                        'Repository knowledge index (host-authored, if present): ',
                        event['prompt'],
                    )
                    self.assertEqual(event['prompt'].count(
                        'Consumer testing guide: '
                        + str(policy.parent / 'testing-and-documentation.md')
                        + '#lightweight-and-browser-checks'
                    ), 1)
                    self.assertEqual(event['prompt'].count(
                        'Worktree and artifact policy: '
                        + str(policy.parent / 'workspace-lifecycle.md')
                    ), 1)

    def test_expected_paths_and_full_packets(self):
        expected = {'delivery': (25, 'done'), 'two-work-items': (35, 'done'),
                    'skill': (26, 'done'), 'repeat-improve': (26, 'done'),
                    'blocked-resume': (27, 'done'), 'pause-resume': (27, 'done'),
                    'halted': (1, 'halted'), 'corrective-work': (35, 'done')}
        self.assertEqual(set(driver.scenarios()), set(expected))
        for name, scenario in driver.scenarios().items():
            with self.subTest(name=name):
                report = driver.run_scenario(name, scenario)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertEqual((len(report['events']), report['simulated_status']), expected[name])
                for event in report['events']:
                    self.assertTrue(event['simulation_only'])
                    self.assertIn('owner', event)
                    self.assertIn('next_owner', event)
                    self.assertIn('completed_instances', event)
                    self.assertIn('Inspect the SDLC graph', event['prompt'])
                    self.assertIn(event['from'], event['prompt'])
                    self.assertFalse(
                        {'phase', 'subphase', 'counter', 'review_count'} & set(event)
                    )

        two_items = driver.run_scenario('two-work-items', driver.scenarios()['two-work-items'])
        self.assertTrue(two_items['ok'], two_items.get('error'))
        inner_owners = {
            event['owner'] for event in two_items['events'] if event['owner'] != 'root'
        }
        self.assertEqual(inner_owners, {'W1', 'W2'})
        w1_carry = next(
            event
            for event in two_items['events']
            if event['owner'] == 'W1' and event['from'] == 'carry-forward'
        )
        self.assertEqual(w1_carry['next_owner'], 'W2')
        self.assertEqual(w1_carry['completed_instances'], ['W1'])
        self.assertEqual(two_items['completed_instances'], ['W1', 'W2'])

    def test_v3_dry_run_simulates_actual_improve_handoffs_without_starting_them(self):
        expected = {'delivery': 68, 'two-work-items': 104, 'blocked-resume': 71,
                    'repeat-improve': 70, 'pause-resume': 70, 'halted': 1}
        scenarios = driver.scenarios(3)
        self.assertEqual(set(scenarios), set(expected))
        for name, scenario in scenarios.items():
            with self.subTest(name=name):
                report = driver.run_scenario(name, scenario, protocol_version=3)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertEqual(len(report['events']), expected[name])
                self.assertEqual(report['simulated_status'],
                                 'halted' if name == 'halted' else 'done')
                produces = [event for event in report['events'] if event['command'] == 'produce']
                finishes = [event for event in report['events'] if event['command'] == 'finish-improve']
                self.assertEqual(len(produces), len(finishes))
                self.assertEqual([event['from'] for event in produces],
                                 [event['from'] for event in finishes])
                self.assertTrue(all(event['simulation_only'] for event in report['events']))

        two_items = driver.run_scenario(
            'two-work-items', scenarios['two-work-items'], protocol_version=3)
        self.assertEqual(two_items['completed_instances'], ['W1', 'W2'])
        for command in ('produce', 'finish-improve'):
            inner = [event for event in two_items['events']
                     if event['from'] in ('select-work', 'implement', 'carry-forward')
                     and event['command'] == command]
            self.assertEqual([event['owner'] for event in inner],
                             ['W1', 'W1', 'W1', 'W2', 'W2', 'W2'])
        w1_finish = next(event for event in two_items['events']
                         if event['owner'] == 'W1' and event['from'] == 'carry-forward'
                         and event['command'] == 'finish-improve')
        self.assertEqual(w1_finish['next_owner'], 'W2')

    def test_wrong_edge_and_unknown_command_fail(self):
        wrong = copy.deepcopy(driver.scenarios()['delivery'])
        wrong['steps'][0]['expect'] = 'release'
        self.assertFalse(driver.run_scenario('skip', wrong)['ok'])
        wrong['steps'][0]['expect'] = 'discovery'
        wrong['steps'][0]['command'] = 'execute-shell'
        self.assertIn('unknown synthetic command', driver.run_scenario('shell', wrong)['error'])

    def test_no_live_run_or_engine_calls(self):
        class ForbiddenCore:
            def __getattr__(self, name):
                raise AssertionError(f'Unexpected live core access: {name}')
        def forbidden(*args, **kwargs):
            raise AssertionError('Navigator dry-run attempted project execution or persistence')
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with (patch.object(subprocess, 'run', side_effect=forbidden),
              patch.object(store, 'transaction', side_effect=forbidden),
              patch.object(navigator, 'save', side_effect=forbidden),
              redirect_stdout(output)):
            self.assertEqual(
                protocol.main(ForbiddenCore(), ['graph-dry-run', '--protocol-version', '2']),
                0,
            )
        self.assertEqual(output.getvalue().count('PASS '), 8)

    def test_cli_custom_json_and_markdown_without_state_changes(self):
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-') as temporary:
            root = Path(temporary)
            sentinel = root / '.shiploop'
            sentinel.mkdir()
            state = sentinel / 'state.md'
            state.write_text('Unrelated incomplete run')
            before = state.read_bytes()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                   '--protocol-version', '2']
            result = subprocess.run(cli + ['--format', 'json'], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['simulation_only'])
            self.assertEqual(len(data['scenarios']), 8)
            custom = subprocess.run(cli + ['--script', str(ROOT / 'skills/shiploop/references/navigator-dry-run-example.json'), '--format', 'markdown'], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(custom.returncode, 0, custom.stdout + custom.stderr)
            self.assertIn('intake -> discovery', custom.stdout)
            self.assertEqual(state.read_bytes(), before)
            self.assertEqual([p.name for p in sentinel.iterdir()], ['state.md'])

    def test_cli_defaults_to_protocol_v3_without_touching_saved_state(self):
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-v3-') as temporary:
            root = Path(temporary)
            sentinel = root / '.shiploop'
            sentinel.mkdir()
            state = sentinel / 'state.md'
            state.write_text('Unrelated incomplete run')
            before = state.read_bytes()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                   '--format', 'json']
            result = subprocess.run(cli, cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['simulation_only'])
            self.assertEqual(data['protocol_version'], 3)
            self.assertEqual(set(item['name'] for item in data['scenarios']),
                             {'delivery', 'two-work-items', 'blocked-resume',
                              'repeat-improve', 'pause-resume', 'halted'})
            self.assertEqual(state.read_bytes(), before)

    def test_every_listed_scenario_runs_for_its_protocol(self):
        # Regression: --list printed protocol-2 names while the v3 default
        # lacked five of them, so --scenario crashed with a bare KeyError (exit 1).
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-list-') as temporary:
            for version in ('2', '3', '4'):
                listed = subprocess.run(base + ['--list', '--protocol-version', version],
                                        cwd=temporary, env=env, capture_output=True, text=True)
                self.assertEqual(listed.returncode, 0, listed.stderr)
                names = listed.stdout.split()
                self.assertEqual(names, list(driver.scenarios(int(version))))
                for name in names:
                    with self.subTest(protocol=version, scenario=name):
                        result = subprocess.run(
                            base + ['--scenario', name, '--protocol-version', version],
                            cwd=temporary, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertNotIn('Traceback', result.stderr)

    def test_scenario_missing_from_protocol_is_an_input_error(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-missing-') as temporary:
            for name in ('skill', 'corrective-work'):
                with self.subTest(scenario=name):
                    result = subprocess.run(
                        [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                         '--scenario', name], cwd=temporary, env=env,
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn(f"scenario '{name}' is not available for protocol 3",
                                  result.stdout)
                    self.assertNotIn('Traceback', result.stderr)

    def test_v3_example_script_passes_on_default_protocol(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        example = ROOT / 'skills/shiploop/references/navigator-v3-dry-run-example.json'
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-v3-example-') as temporary:
            result = subprocess.run(
                [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run',
                 '--script', str(example), '--format', 'json'],
                cwd=temporary, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            events = json.loads(result.stdout)['scenarios'][0]['events']
            self.assertEqual([event['to'] for event in events],
                             ['intake', 'discovery', 'discovery', 'research'])


if __name__ == '__main__':
    unittest.main()
