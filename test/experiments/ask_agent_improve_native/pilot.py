"""Disposable real-CLI pilot fixture. No model launch or simulated child reviews.

Only predecessor navigation is synthetic setup. Native Improve and all final
delivery operations must run for real, with their evidence retained separately.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=['setup', 'finalize', 'snapshot'])
parser.add_argument('--package', type=Path, required=True)
parser.add_argument('--case', type=Path, required=True)
args = parser.parse_args()
package, case = args.package.resolve(), args.case.resolve()
pilot_checkout = Path(__file__).resolve().parents[3]
if case.is_relative_to(package) or case.is_relative_to(pilot_checkout):
    parser.error('--case must be outside the package and pilot source checkout')
scripts = package / 'skills/shiploop/scripts'
sys.path.insert(0, str(scripts))
import shiploop_navigator as nav
import shiploop_standalone_improve as bridge
import shiploop_store as store

env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
           GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
cli = scripts / 'shiploop'
source, workspace = case / 'caller', case / 'workspace'
candidate, run = workspace / 'worktree', workspace / 'run'

def command(argv, cwd, label, expected=0):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                            capture_output=True, timeout=60)
    logs = case / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    (logs / (label + '.stdout')).write_bytes(result.stdout)
    (logs / (label + '.stderr')).write_bytes(result.stderr)
    (logs / (label + '.json')).write_text(json.dumps({'argv': list(map(str, argv)),
        'cwd': str(cwd), 'exit_code': result.returncode}, indent=2)+'\n')
    if result.returncode != expected:
        raise RuntimeError(f'{label}: {result.returncode}: {result.stderr.decode(errors="replace")[-2000:]}')
    return result.stdout

def ship(label, *argv, expected=0):
    return command([sys.executable, '-B', cli, *argv], case, label, expected)

def git(label, *argv):
    return command(['git', *argv], source, label)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    return {'head': git('snapshot-head', 'rev-parse', 'HEAD').decode().strip(),
        'index': digest(source / '.git/index'),
        'cached_diff': git('snapshot-index-diff', 'diff', '--cached', '--binary').decode(),
        'preserved_files': {name: digest(source / name) for name in ['user-intent.txt', 'loose-note.txt']},
        'calculator': digest(source / 'calculator.py')}

if args.operation == 'setup':
    case.mkdir(parents=True, exist_ok=False)
    source.mkdir()
    for i, argv in enumerate([['init', '-q'], ['branch', '-M', 'main'],
            ['config', 'user.name', 'Native Improve Pilot'],
            ['config', 'user.email', 'pilot@example.invalid'],
            ['config', 'commit.gpgsign', 'false'], ['config', 'core.hooksPath', os.devnull]]):
        git(f'git-setup-{i}', *argv)
    (source / '.gitignore').write_text('__pycache__/\n*.pyc\n')
    (source / 'calculator.py').write_text('def total(values):\n    """Sum every supplied value, including the last one."""\n    return sum(values[:-1])\n')
    (source / 'test_calculator.py').write_text('import unittest\nfrom calculator import total\n\nclass TotalTests(unittest.TestCase):\n    def test_empty(self): self.assertEqual(total([]), 0)\n    def test_single(self): self.assertEqual(total([2]), 2)\n    def test_multiple(self): self.assertEqual(total([2, 3, 5]), 10)\n    def test_negative(self): self.assertEqual(total([-2, 1]), -1)\n\nif __name__ == "__main__": unittest.main()\n')
    (source / 'user-intent.txt').write_text('original user content\n')
    git('git-add-fixture', 'add', '.gitignore', 'calculator.py', 'test_calculator.py', 'user-intent.txt')
    git('git-commit-fixture', 'commit', '-qm', 'Fixture: totals must include every input; preserve unrelated caller inputs')
    (source / 'user-intent.txt').write_text('staged user intent\n')
    git('git-stage-dirty', 'add', 'user-intent.txt')
    (source / 'user-intent.txt').write_text('staged user intent\nadditional unstaged intent\n')
    (source / 'loose-note.txt').write_text('untracked caller note must survive exactly\n')
    (case / 'caller-before.json').write_text(json.dumps(snapshot(), indent=2)+'\n')
    card = package / 'skills/improve/SKILL.md'
    ship('workspace-start', 'workspace', 'start', '--repo', source,
         '--workspace-root', workspace, '--prompt', 'Bound native Improve delivery pilot; synthetic predecessor setup only.',
         '--include-untracked', 'loose-note.txt', '--improve-skill', card)
    state = store.read_record(run / 'state.md')
    while nav.current_stage(state) != 'handoff':
        action = nav.current_action(state)['id']
        state = nav.apply(state, action, {'outcome': 'done', 'summary': 'Synthetic predecessor setup; no work or review execution claim.'})
        state = nav.finish_improve(state, action, {'summary': 'Synthetic predecessor marker only.'})
    nav.save(run, state)
    action = nav.current_action(state)['id']
    producer = run / 'inbox' / (action + '.md')
    store.write_record(producer, {'outcome': 'done', 'summary': 'Review the bounded calculator candidate and preserve caller inputs.',
        'evidence_refs': [str(candidate / 'calculator.py'), str(candidate / 'test_calculator.py')]})
    ship('producer-done', 'done', '--run-dir', run, '--action', action, '--result', producer)
    ship('improve-bind', 'improve-bind', '--run-dir', run, '--action', action, '--skill-card', card)
    bound = store.read_record(run / 'state.md')['active_improve']
    receipt = bridge.receipt_path(bound)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    info = {'case': str(case), 'package': str(package), 'source': str(source), 'candidate': str(candidate),
        'workspace': str(workspace), 'run': str(run), 'action': action, 'bound': bound,
        'receipt': str(receipt), 'owner_record': str(receipt.with_name('host-owner.md')),
        'completion': str(run / 'inbox' / (action + '-improve.md')),
        'scope': ['calculator.py', 'test_calculator.py'],
        'excluded': ['user-intent.txt', 'loose-note.txt'],
        'check': ['python3', '-B', '-m', 'unittest', '-v', 'test_calculator.py'],
        'parent_import': [sys.executable, '-B', str(cli), 'improve-complete', '--run-dir', str(run), '--action', action,
                          '--result', str(run / 'inbox' / (action + '-improve.md'))]}
    (case / 'pilot.json').write_text(json.dumps(info, indent=2)+'\n')
    (case / 'packet.md').write_bytes(ship('parent-next', 'next', '--run-dir', run))
    (case / 'parent-before.sha256').write_text(digest(run / 'state.md')+'\n')
    print(json.dumps(info, indent=2))
elif args.operation == 'snapshot':
    print(json.dumps(snapshot(), indent=2))
else:
    info = json.loads((case / 'pilot.json').read_text())
    collected = json.loads((case / 'parent-collected.json').read_text())
    assert collected['worker_stopped'] and collected['delegates_stopped']
    owner_record = Path(info['owner_record'])
    assert owner_record.is_file(), 'Retain actual parent native-lifecycle evidence first'
    assert collected['owner_record_sha256'] == digest(owner_record), 'Parent attestation no longer matches owner record'
    terminal = json.loads(Path(info['receipt']).read_text())
    assert terminal['status'] == 'complete'
    assert digest(run / 'state.md') == (case / 'parent-before.sha256').read_text().strip()
    ship('plan-return', 'workspace', 'plan-return', '--workspace-root', workspace)
    plan_path = workspace / 'return-plan.md'
    plan = store.read_record(plan_path)
    for row in plan['paths']:
        if '.shiploop-improve' in Path(row['path']).parts:
            assert row['disposition'] == 'exclude'
        elif row['path'] in info['scope']:
            row['disposition'] = 'keep'
        else:
            raise AssertionError('Unexpected candidate change: '+row['path'])
    store.write_record(plan_path, plan)
    ship('workspace-return', 'workspace', 'return', '--workspace-root', workspace)
    command(info['parent_import'], case, 'parent-import')
    after, before = snapshot(), json.loads((case / 'caller-before.json').read_text())
    assert all(after[key] == before[key] for key in ['head', 'index', 'cached_diff', 'preserved_files'])
    assert after['calculator'] != before['calculator']
    assert digest(source / 'calculator.py') == digest(candidate / 'calculator.py')
    assert not (source / '.shiploop-improve').exists()
    assert store.read_record(run / 'state.md')['status'] == 'done'
    (case / 'caller-after.json').write_text(json.dumps(after, indent=2)+'\n')
    (case / 'delivery.json').write_text(json.dumps({'git_delivery': 'PASS', 'caller': str(source),
        'candidate': str(candidate), 'dirty_inputs_and_index_preserved': True,
        'parent_status': 'done', 'synthetic_predecessor_setup': True,
        'native_lifecycle': 'parent-attested; not independently verified by this fixture',
        'owner_record': str(owner_record), 'owner_record_sha256_at_acceptance': collected['owner_record_sha256']}, indent=2)+'\n')
    print('Git delivery PASS: exact candidate repair delivered; caller HEAD/index and inherited dirty inputs preserved. Native evidence is separately parent-attested.')
