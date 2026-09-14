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
                    self.assertIn('Inspect the SDLC graph', event['prompt'])
                    self.assertIn(event['from'], event['prompt'])

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
            self.assertEqual(protocol.main(ForbiddenCore(), ['graph-dry-run']), 0)
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
            cli = [sys.executable, '-B', str(SCRIPTS / 'shiploop'), 'graph-dry-run']
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


if __name__ == '__main__':
    unittest.main()
