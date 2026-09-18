"""Launcher evidence boundaries using a local fake CLI, never a model call."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from run import launch


class LaunchEvidenceTests(unittest.TestCase):
    def run_fake(self, events):
        temporary = tempfile.TemporaryDirectory(prefix='repeatable-launch-check-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        repo = root / 'repo'
        repo.mkdir()
        (repo / 'source.txt').write_text('unchanged')
        binary = root / 'bin'
        binary.mkdir()
        cli = binary / 'codex'
        cli.write_text('#!/usr/bin/env python3\nimport sys\n'
                       'if "--version" in sys.argv: print("codex fake-test"); sys.exit(0)\n'
                       'sys.stdin.read()\n'
                       + ''.join('print(' + repr(json.dumps(e)) + ')\n' for e in events))
        cli.chmod(0o755)
        with patch.dict(os.environ, {'PATH': str(binary) + os.pathsep + os.environ['PATH']}):
            record = launch(repo, root / 'observer', 'bounded fixture job', timeout=10)
        return root, repo, record

    def test_cli_exit_is_not_improve_or_product_success(self):
        root, repo, record = self.run_fake([
            {'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 3}},
        ])
        self.assertEqual(record['status'], 'exited')
        self.assertEqual(record['improve']['status'], 'unobserved')
        self.assertEqual(record['terminal_usage'], [{'input_tokens': 12, 'output_tokens': 3}])
        self.assertEqual(record['before'], record['after'])
        with self.assertRaises(FileExistsError):
            launch(repo, root / 'observer', 'retry must not erase the attempt')

    def test_zero_process_exit_does_not_hide_event_failure(self):
        root, _, record = self.run_fake([
            {'type': 'turn.failed', 'error': {'message': 'fixture transport failure'}},
        ])
        self.assertEqual(record['returncode'], 0)
        self.assertEqual(record['status'], 'event-error')
        saved = json.loads((root / 'observer/result.json').read_text())
        self.assertEqual(saved['errors'][0]['type'], 'turn.failed')

    def test_observer_cannot_be_inside_worker_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with patch('run.subprocess.run', side_effect=AssertionError('unexpected CLI call')):
                with self.assertRaises(ValueError):
                    launch(repo, repo / 'observer', 'no model should be launched')


if __name__ == '__main__':
    unittest.main()
