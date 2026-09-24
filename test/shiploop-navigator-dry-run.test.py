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
import shiploop_navigator_v3_prompts as guidance3  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class NavigatorDryRunTests(unittest.TestCase):
    def test_access_policy_is_reachable_through_actual_graph_and_recovery(self):
        # A routing/locator contract, not proof that a host follows auth advice.
        references = ROOT / 'skills/shiploop/references'
        policy = references / 'research-loop.md'
        lifecycle = references / 'environment-lifecycle.md'
        self.assertTrue(lifecycle.is_file())
        self.assertTrue((references / 'delivery-authority.md').is_file())
        policy_text = policy.read_text(encoding='utf-8')
        self.assertIn('## Recursive discovery and experiments', policy_text)
        self.assertIn('## Navigator execution mode adapter', policy_text)
        requirements = guidance3.ENVIRONMENT_DISCOVERY_REQUIREMENTS
        self.assertEqual(set(requirements), {'discovery', 'research'})
        discovery_lines = (
            'One investigation allowance spans applicable discovery and research review stages; '
            'a stage boundary does not refill it.',
            f'Recursive discovery policy: {policy}#recursive-discovery-and-experiments',
            f'Navigator adapter: {policy}#navigator-execution-mode-adapter',
        )
        for name in ('delivery', 'blocked-resume', 'pause-resume'):
            report = driver.run_scenario(name, driver.scenarios()[name], protocol_version=3)
            self.assertTrue(report['ok'], report.get('error'))
            for event in report['events']:
                with self.subTest(scenario=name, stage=event['from'], command=event['command']):
                    prompt = event['prompt']
                    self.assertEqual(prompt.count(
                        f'Access-readiness policy: {policy}#early-access-readiness'
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Cross-run knowledge policy: '
                        + str(policy.parent / 'project-knowledge.md')
                    ), 1)
                    self.assertIn(
                        'Repository knowledge index (host-authored, if present): ',
                        prompt,
                    )
                    self.assertEqual(prompt.count(
                        'Consumer testing guide: '
                        + str(policy.parent / 'testing-and-documentation.md')
                        + '#lightweight-and-browser-checks'
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Worktree and artifact policy: '
                        + str(policy.parent / 'workspace-lifecycle.md')
                    ), 1)
                    self.assertEqual(prompt.count(
                        'Delivery-authority policy: ' + str(references / 'delivery-authority.md')
                    ), 1)
                    self.assertEqual(prompt.count(f'Environment lifecycle policy: {lifecycle}'), 1)
                    self.assertEqual(prompt.count(
                        'Environment lifecycle note (host-authored, if present): '
                        + str(driver.RUN / 'notes' / 'environment-lifecycle.md')
                    ), 1)
                    # Only the discovery and research producers carry the
                    # environment discovery requirement and its locators.
                    discovery = event['from'] in requirements
                    self.assertEqual(prompt.count('Environment discovery requirement: '),
                                     int(discovery))
                    if discovery:
                        self.assertIn('Environment discovery requirement: '
                                      + requirements[event['from']], prompt)
                    for line in discovery_lines:
                        self.assertEqual(prompt.count(line), int(discovery), line)

    def test_v3_dry_run_simulates_actual_improve_handoffs_without_starting_them(self):
        expected = {'delivery': 42, 'two-work-items': 62, 'blocked-resume': 44,
                    'repeat-improve': 44, 'pause-resume': 44, 'halted': 1}
        scenarios = driver.scenarios()
        self.assertEqual(set(scenarios), set(expected))
        for name, scenario in scenarios.items():
            with self.subTest(name=name):
                report = driver.run_scenario(name, scenario, protocol_version=3)
                self.assertTrue(report['ok'], report.get('error'))
                self.assertEqual(len(report['events']), expected[name])
                self.assertEqual(report['simulated_status'],
                                 'halted' if name == 'halted' else 'done')
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
                produces = [event for event in report['events'] if event['command'] == 'produce']
                finishes = [event for event in report['events'] if event['command'] == 'finish-improve']
                # An actual Improve child starts only for a planning/contract
                # stage result or the end-of-work carry-forward; every other
                # produce advances directly with no paired finish-improve.
                checkpoint_stages = guidance3.PLANNING_REVIEW_STAGES | {'carry-forward'}
                self.assertTrue({event['from'] for event in finishes} <= checkpoint_stages)
                planning_produces = sorted(event['from'] for event in produces
                                           if event['from'] in guidance3.PLANNING_REVIEW_STAGES)
                planning_finishes = sorted(event['from'] for event in finishes
                                           if event['from'] in guidance3.PLANNING_REVIEW_STAGES)
                self.assertEqual(planning_produces, planning_finishes)
                self.assertTrue(all(event['simulation_only'] for event in report['events']))

        two_items = driver.run_scenario(
            'two-work-items', scenarios['two-work-items'], protocol_version=3)
        self.assertEqual(two_items['completed_instances'], ['W1', 'W2'])
        self.assertEqual({event['owner'] for event in two_items['events']
                          if event['owner'] != 'root'}, {'W1', 'W2'})
        produce_inner = [event for event in two_items['events']
                         if event['from'] in ('select-work', 'implement', 'carry-forward')
                         and event['command'] == 'produce']
        self.assertEqual([event['owner'] for event in produce_inner],
                         ['W1', 'W1', 'W1', 'W2', 'W2', 'W2'])
        # select-work/implement are not planning stages and W1's carry-forward
        # leaves W2 pending, so only W2's end-of-work carry-forward gets a
        # review; W1's carry-forward advances straight to W2 without one.
        finish_inner = [event for event in two_items['events']
                        if event['from'] in ('select-work', 'implement', 'carry-forward')
                        and event['command'] == 'finish-improve']
        self.assertEqual([event['owner'] for event in finish_inner], ['W2'])
        w1_produce = next(event for event in two_items['events']
                          if event['owner'] == 'W1' and event['from'] == 'carry-forward'
                          and event['command'] == 'produce')
        self.assertEqual(w1_produce['next_owner'], 'W2')
        self.assertEqual(w1_produce['completed_instances'], ['W1'])

    def test_wrong_edge_and_unknown_command_fail(self):
        wrong = copy.deepcopy(driver.scenarios()['delivery'])
        wrong['steps'][0]['expect'] = 'release'
        self.assertFalse(driver.run_scenario('skip', wrong)['ok'])
        wrong['steps'][0]['expect'] = 'discovery'
        wrong['steps'][0]['command'] = 'execute-shell'
        self.assertIn('unknown synthetic command', driver.run_scenario('shell', wrong)['error'])

    def test_unknown_top_level_script_field_is_refused_by_name(self):
        """A retired setting such as improve_cadence is refused, not ignored."""
        retired = copy.deepcopy(driver.scenarios()['delivery'])
        retired['improve_cadence'] = 'every-stage'
        report = driver.run_scenario('custom', retired)
        self.assertFalse(report['ok'])
        self.assertIn('scenario has unsupported fields: improve_cadence', report['error'])
        self.assertEqual(report['events'], [])

    def test_no_live_run_or_engine_calls(self):
        class ForbiddenCore:
            def __getattr__(self, name):
                raise AssertionError(f'Unexpected live core access: {name}')
        def forbidden(*args, **kwargs):
            raise AssertionError('Navigator dry-run attempted project execution or persistence')
        from contextlib import redirect_stdout
        from io import StringIO
        for version in ('3', '4'):
            with self.subTest(protocol=version):
                output = StringIO()
                with (patch.object(subprocess, 'run', side_effect=forbidden),
                      patch.object(store, 'transaction', side_effect=forbidden),
                      patch.object(navigator, 'save', side_effect=forbidden),
                      redirect_stdout(output)):
                    self.assertEqual(
                        protocol.main(ForbiddenCore(),
                                      ['graph-dry-run', '--protocol-version', version]),
                        0,
                    )
                self.assertEqual(output.getvalue().count('PASS '), 6)

    def test_cli_custom_json_and_markdown_without_state_changes(self):
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-') as temporary:
            root = Path(temporary)
            sentinel = root / '.shiploop'
            sentinel.mkdir()
            state = sentinel / 'state.md'
            state.write_text('Unrelated incomplete run')
            before = state.read_bytes()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
            result = subprocess.run(cli + ['--format', 'json'], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['simulation_only'])
            self.assertEqual(len(data['scenarios']), 6)
            example = ROOT / 'skills/shiploop/references/navigator-v3-dry-run-example.json'
            custom = subprocess.run(cli + ['--script', str(example), '--format', 'markdown'],
                                    cwd=root, env=env, capture_output=True, text=True)
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
        # Regression: --list once printed names the selected protocol lacked,
        # so --scenario crashed with a bare KeyError (exit 1).
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        base = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
        with tempfile.TemporaryDirectory(prefix='navigator-dry-run-list-') as temporary:
            for version in ('3', '4'):
                listed = subprocess.run(base + ['--list', '--protocol-version', version],
                                        cwd=temporary, env=env, capture_output=True, text=True)
                self.assertEqual(listed.returncode, 0, listed.stderr)
                names = listed.stdout.split()
                self.assertEqual(names, list(driver.scenarios()))
                for name in names:
                    with self.subTest(protocol=version, scenario=name):
                        result = subprocess.run(
                            base + ['--scenario', name, '--protocol-version', version],
                            cwd=temporary, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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
                             ['discovery', 'research', 'spec', 'spec', 'test-strategy'])


if __name__ == '__main__':
    unittest.main()
