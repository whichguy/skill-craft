#!/usr/bin/env python3
"""Offline real-Git conflict and partial-result retention controls; no model calls."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import fixture


class IntegrationControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ask-agent-parallel-controls-')
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)/'case'
        self.manifest = fixture.prepare_fixture(self.run,3,'parallel')
        self.caller = self.run/'caller'
        self.helper = self.run/'package/ask-agent/scripts/ask_agent_workspace.py'

    def helper_call(self, *args):
        result = subprocess.run(['python3','-B',str(self.helper),*args],capture_output=True,text=True,check=True)
        return json.loads(result.stdout)

    def prepare(self, label):
        return self.helper_call('prepare','--source',str(self.caller),'--store',str(self.run/'store'),
                                '--label',label,'--writers-quiescent')

    def contribution(self, preparation, value):
        worktree = Path(preparation['worktree'])
        (worktree/'src/step_1.py').write_text(f'def transform(x):\n    return {value}\n')
        result = self.helper_call('inspect','--receipt',preparation['receipt'],'--phase','returned','--delivery-mode','patch')
        return Path(result['delivery']['contribution_patch'])

    def apply(self, patch, check=False):
        args=['git','-C',str(self.caller),'-c','core.autocrlf=false','apply','--binary','--whitespace=nowarn']
        if check: args.append('--check')
        return subprocess.run([*args,str(patch)],capture_output=True,text=True)

    def test_conflicting_contribution_is_refused_and_retained(self):
        first,second=self.prepare('first'),self.prepare('second')
        one,two=self.contribution(first,'2*x+1'),self.contribution(second,'2*x+2')
        before=fixture.capture_repo_state(self.caller)
        self.assertEqual(self.apply(one,check=True).returncode,0)
        self.assertEqual(self.apply(one).returncode,0)
        self.assertNotEqual(self.apply(two,check=True).returncode,0)
        self.assertEqual((self.caller/'src/step_1.py').read_text(),'def transform(x):\n    return 2*x+1\n')
        after=fixture.capture_repo_state(self.caller)
        self.assertEqual(before['index_entries'],after['index_entries'])
        self.assertEqual(before['cached_diff_sha256'],after['cached_diff_sha256'])
        self.assertEqual(before['unstaged_dirty_diffs'],after['unstaged_dirty_diffs'])
        self.assertTrue(one.is_file() and two.is_file())
        self.assertTrue(Path(first['worktree']).is_dir() and Path(second['worktree']).is_dir())

    def test_missing_worker_cannot_become_a_complete_batch(self):
        first,missing=self.prepare('successful'),self.prepare('missing')
        one=self.contribution(first,'2*x+1')
        self.assertEqual(self.apply(one).returncode,0)
        result=fixture.verify_fixture(self.run)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['worker_probe_completeness'])
        self.assertTrue(one.is_file())
        self.assertTrue(Path(first['worktree']).is_dir())
        self.assertTrue(Path(missing['worktree']).is_dir())
        self.assertEqual((self.caller/'src/step_1.py').read_text(),'def transform(x):\n    return 2*x+1\n')


if __name__ == '__main__':
    unittest.main()
