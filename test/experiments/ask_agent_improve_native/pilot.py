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
parser.add_argument('operation', choices=['setup', 'finalize', 'snapshot', 'verify-delivery'])
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

def scoped_delivery_manifest(info):
    rows = []
    for name in info['scope']:
        caller_path, candidate_path = source / name, candidate / name
        caller_digest = digest(caller_path) if caller_path.is_file() and not caller_path.is_symlink() else None
        candidate_digest = digest(candidate_path) if candidate_path.is_file() and not candidate_path.is_symlink() else None
        rows.append({'path': name, 'caller_sha256': caller_digest,
            'candidate_sha256': candidate_digest,
            'result': 'match' if caller_digest and caller_digest == candidate_digest else 'mismatch'})
    return {'scoped_delivery': 'PASS' if all(row['result'] == 'match' for row in rows) else 'FAIL',
        'delivery_paths': rows}

def persist_scoped_delivery(manifest):
    record = {'git_delivery': 'INCOMPLETE', 'workspace_return': 'completed',
        'parent_import': 'not-run' if manifest['scoped_delivery'] == 'PASS' else 'blocked',
        'parent_advancement': 'incomplete' if manifest['scoped_delivery'] == 'PASS' else 'blocked',
        'record_phase': 'after-workspace-return-before-parent-import',
        'scoped_delivery_basis': 'per-path caller/candidate digests only; not semantic or caller-test proof',
        **manifest}
    (case / 'scoped-delivery.json').write_text(json.dumps(record, indent=2)+'\n')
    return record

def require_scoped_delivery(info):
    manifest = scoped_delivery_manifest(info)
    persist_scoped_delivery(manifest)
    mismatches = [row['path'] for row in manifest['delivery_paths'] if row['result'] != 'match']
    if mismatches:
        raise AssertionError('Scoped delivery mismatch: '+', '.join(mismatches))
    return manifest

def snapshot():
    return {'head': git('snapshot-head', 'rev-parse', 'HEAD').decode().strip(),
        'index': digest(source / '.git/index'),
        'cached_diff': git('snapshot-index-diff', 'diff', '--cached', '--binary').decode(),
        'preserved_files': {name: digest(source / name) for name in ['user-intent.txt', 'loose-note.txt']},
        'calculator': digest(source / 'calculator.py')}

def load_pilot():
    """Read this case's pilot.json; only the current scoped-required policy is accepted."""
    path = case / 'pilot.json'
    info = json.loads(path.read_text())
    policy = info.get('commit_policy')
    if policy != 'scoped-required':
        raise SystemExit(f"Refusing {path}: commit_policy must be 'scoped-required', found {policy!r}. "
                         'Run setup for a new case; this pilot does not re-verify other policies.')
    return info

def verify_worker_commits(info, terminal):
    """Require scoped worker commits whose exact SHAs appear in the terminal handoff."""
    def candidate_git(label, *argv):
        return command(['git', *argv], candidate, label).decode().strip()
    baseline = info['candidate_initial_head']
    head = candidate_git('worker-head', 'rev-parse', 'HEAD')
    candidate_git('worker-ancestor', 'merge-base', '--is-ancestor', baseline, head)
    commits = candidate_git('worker-commits', 'rev-list', '--reverse', baseline+'..'+head).splitlines()
    assert commits, 'Required worker commit is missing'
    handoff = terminal.get('last_report', {}).get('handoff', '')
    assert all(sha in handoff for sha in commits), 'Terminal handoff lacks exact worker commit provenance'
    records = []
    for sha in commits:
        paths = candidate_git('worker-paths-'+sha, 'diff-tree', '--no-commit-id', '--name-only', '-r', sha).splitlines()
        assert paths and set(paths) <= set(info['scope']), 'Worker commit includes empty or out-of-scope change'
        body = candidate_git('worker-message-'+sha, 'show', '-s', '--format=%B', sha)
        sections = ['Review', 'Plan', 'Changes', 'Validation', 'Key learnings', 'Remaining work']
        assert all(section.lower() in body.lower() for section in sections), 'Missing learning-oriented commit sections'
        records.append({'sha': sha, 'paths': paths})
    dirty = candidate_git('worker-uncommitted-scope', 'status', '--porcelain', '--untracked-files=all', '--', *info['scope'])
    assert not dirty, 'Scoped worker changes remain uncommitted'
    evidence = {'status': 'PASS', 'baseline': baseline, 'head': head, 'commits': records,
        'caller_history_integration': False, 'delivery_mode': 'working-tree-return',
        'basis': 'Actual Git ancestry, commit paths/messages and scoped worktree status; native execution is separately attested'}
    (case / 'worker-commits.json').write_text(json.dumps(evidence, indent=2)+'\n')
    return evidence

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
    caller_markers = ['# staged caller context: preserve this note',
                      '# unstaged caller context: preserve this note too']
    with (source / 'calculator.py').open('a') as handle:
        handle.write(caller_markers[0]+'\n')
    git('git-stage-scoped-dirty', 'add', 'calculator.py')
    with (source / 'calculator.py').open('a') as handle:
        handle.write(caller_markers[1]+'\n')
    (case / 'caller-before.json').write_text(json.dumps(snapshot(), indent=2)+'\n')
    card = package / 'skills/improve/SKILL.md'
    ship('workspace-start', 'workspace', 'start', '--repo', source,
         '--workspace-root', workspace, '--prompt', 'Bound native Improve delivery pilot; synthetic predecessor setup only.',
         '--include-untracked', 'loose-note.txt', '--improve-skill', card)
    state = store.read_record(run / 'state.md')
    while nav.current_stage(state) != 'handoff':
        action = nav.current_action(state)['id']
        state = nav.apply(state, action, {'outcome': 'done', 'summary': 'Synthetic predecessor setup; no work or review execution claim.'})
        if state['active_improve'] is not None:  # Only planning checkpoints and the last carry-forward park an Improve child.
            state = nav.finish_improve(state, action, {'summary': 'Synthetic predecessor marker only.'})
    nav.save(run, state)
    action = nav.current_action(state)['id']
    producer = run / 'inbox' / (action + '.md')
    store.write_record(producer, {'outcome': 'done', 'summary': 'Review the bounded calculator candidate and preserve caller inputs.',
        'evidence_refs': [str(candidate / 'calculator.py'), str(candidate / 'test_calculator.py')]})
    ship('producer-complete', 'complete', '--run-dir', run, '--action', action, '--result', producer)
    ship('improve-bind', 'improve-bind', '--run-dir', run, '--action', action, '--skill-card', card)
    bound = store.read_record(run / 'state.md')['active_improve']
    receipt = bridge.receipt_path(bound)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    info = {'case': str(case), 'package': str(package), 'source': str(source), 'candidate': str(candidate),
        'workspace': str(workspace), 'run': str(run), 'action': action, 'bound': bound,
        'receipt': str(receipt), 'owner_record': str(receipt.with_name('host-owner.md')),
        'completion': str(run / 'inbox' / (action + '-improve.md')),
        'scope': ['calculator.py', 'test_calculator.py'],
        'commit_policy': 'scoped-required',
        'caller_scope_markers': {'calculator.py': caller_markers},
        'candidate_initial_head': command(['git', 'rev-parse', 'HEAD'], candidate, 'candidate-baseline').decode().strip(),
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
elif args.operation == 'verify-delivery':
    manifest = scoped_delivery_manifest(load_pilot())
    print(json.dumps(manifest, indent=2))
    if manifest['scoped_delivery'] != 'PASS':
        raise SystemExit('Scoped delivery mismatch: '+', '.join(
            row['path'] for row in manifest['delivery_paths'] if row['result'] != 'match'))
else:
    info = load_pilot()
    collected = json.loads((case / 'parent-collected.json').read_text())
    assert collected['worker_stopped'] and collected['delegates_stopped']
    owner_record = Path(info['owner_record'])
    assert owner_record.is_file(), 'Retain actual parent native-lifecycle evidence first'
    assert collected['owner_record_sha256'] == digest(owner_record), 'Parent attestation no longer matches owner record'
    terminal = json.loads(Path(info['receipt']).read_text())
    assert terminal['status'] == 'complete'
    assert digest(run / 'state.md') == (case / 'parent-before.sha256').read_text().strip()
    worker_commits = verify_worker_commits(info, terminal)
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
    scoped_delivery = require_scoped_delivery(info)
    command(info['parent_import'], case, 'parent-import')
    after, before = snapshot(), json.loads((case / 'caller-before.json').read_text())
    assert all(after[key] == before[key] for key in ['head', 'index', 'cached_diff', 'preserved_files'])
    assert after['calculator'] != before['calculator']
    for name, markers in info['caller_scope_markers'].items():
        for marker in markers:
            assert (source / name).read_text().count(marker) == 1, 'Inherited scoped caller content changed'
    assert not (source / '.shiploop-improve').exists()
    assert store.read_record(run / 'state.md')['status'] == 'done'
    (case / 'caller-after.json').write_text(json.dumps(after, indent=2)+'\n')
    (case / 'delivery.json').write_text(json.dumps({'git_delivery': 'PASS', 'caller': str(source),
        'candidate': str(candidate), 'dirty_inputs_and_index_preserved': True,
        'scoped_delivery_basis': 'per-path caller/candidate digests only; not semantic or caller-test proof',
        'scoped_delivery_record': str(case / 'scoped-delivery.json'),
        'parent_status': 'done', 'synthetic_predecessor_setup': True,
        'worker_commits': worker_commits,
        'native_lifecycle': 'parent-attested; not independently verified by this fixture',
        'owner_record': str(owner_record), 'owner_record_sha256_at_acceptance': collected['owner_record_sha256'],
        **scoped_delivery}, indent=2)+'\n')
    print('Git delivery PASS: all scoped candidate paths delivered; caller HEAD/index and inherited dirty inputs preserved. Native evidence is separately parent-attested.')
