#!/usr/bin/env python3
"""Disposable local package assignments using the installed public navigator seams.
No model calls. Operator files must not be supplied to an assignment worker.
"""
import os
import sys
sys.dont_write_bytecode = True
import argparse
import copy
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/dadleet/src/skill-craft-r05-20261115')
SHA = 'e596e6734f59590e2b4c6e65bea71a868675924f'
SCRIPTS = SOURCE / 'skills/shiploop/scripts'
CLI = SCRIPTS / 'shiploop'
CARD = SOURCE / 'skills/improve/SKILL.md'
sys.path[:0] = [str(SCRIPTS), str(SOURCE / 'test')]
import shiploop_navigator as nav
import shiploop_store as store
import shiploop_inner_fixture as inner
import shiploop_knowledge_home as knowledge
import shiploop_loop_support as loop_support
from shiploop_loop_support import finish_loop, with_receipt
loader = importlib.machinery.SourceFileLoader('local_core', str(CLI))
spec = importlib.util.spec_from_loader(loader.name, loader)
core = importlib.util.module_from_spec(spec)
loader.exec_module(core)

SITUATIONS = ['changed-setup', 'unchecked-oracle', 'inherited-review', 'valid-control']
BOUNDARIES = ['carry-forward', 'release-verify']


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def dump(path, value):
    write(path, json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    rows = {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}
    return {'files': rows, 'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}


def source_identity():
    def git(*args):
        return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True)
    files = git('ls-files', '-z').split('\0')
    hashes = {p: digest(SOURCE / p) for p in files if p and (SOURCE / p).is_file()}
    return {'head': git('rev-parse', 'HEAD').strip(), 'status': git('status', '--porcelain'),
            'tracked_sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), 'files': hashes}


def environment(base):
    env = {k: v for k, v in os.environ.items() if k not in ('CLAUDECODE', 'CLAUDE_CODE_SESSION_ID', 'GROK_AGENT', 'GROK_SESSION_ID', 'UNTIL_LOOP_STATE_DIR', 'SHIPLOOP_KEEPALIVE_HOME')}
    env.update(SHIPLOOP_PROGRESS='off', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               XDG_STATE_HOME=str(base / 'state-home'), SHIPLOOP_KEEPALIVE_HOME=str(base / 'keepalive'),
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return env


class Seed:
    def __init__(self, parent, logs, situation, boundary):
        self.base = parent / uuid.uuid4().hex
        self.repo, self.run = self.base / 'package', self.base / 'run'
        self.repo.mkdir(parents=True)
        self.log = logs / self.base.name
        self.log.mkdir(parents=True)
        self.situation, self.boundary = situation, boundary
        self.env = environment(self.base)
        self.count = 0

    def call(self, argv, *, expected=0, stdin=None):
        self.count += 1
        name = self.log / f'{self.count:03d}'
        p = subprocess.run(list(map(str, argv)), cwd=self.repo, env=self.env,
                           input=stdin, capture_output=True, text=True, timeout=55)
        dump(name.with_suffix('.command.json'), {'argv': list(map(str, argv)), 'cwd': str(self.repo),
             'stdin': stdin, 'environment_overrides': {k: self.env[k] for k in ('XDG_STATE_HOME', 'SHIPLOOP_KEEPALIVE_HOME', 'SHIPLOOP_PROGRESS')}, 'exit': p.returncode})
        write(name.with_suffix('.stdout'), p.stdout)
        write(name.with_suffix('.stderr'), p.stderr)
        if p.returncode != expected:
            raise RuntimeError(f'{argv}: exit {p.returncode}, expected {expected}: {p.stderr} {p.stdout}')
        return p.stdout

    def cli(self, *args, **kwargs):
        return self.call([sys.executable, '-B', CLI, *args, '--run-dir', self.run], **kwargs)

    def git(self, *args):
        return self.call(['git', '-C', self.repo, *args])

    def commit(self, message):
        paths = [p for p in self.git('ls-files', '--others', '--exclude-standard').splitlines()]
        paths += self.git('diff', '--name-only').splitlines()
        if paths:
            self.git('add', '--', *sorted(set(paths)))
            self.git('commit', '-qm', message)

    def package(self):
        write(self.repo / 'store.py', (HERE / 'local_store.py').read_text())
        write(self.repo / '.gitignore', 'session*.json\n__pycache__/\n')
        write(self.repo / 'AGENTS.md', 'Work only in this local package and its assigned run. Preserve unrelated work. Follow the current assignment and its callbacks. Do not launch advisors or agents. No external services are in scope.\n')
        write(self.repo / 'README.md', '# Local record package\n\nRun `python3 store.py smoke` for lower-layer checks. `python3 store.py --file session.json setup` starts a session using setup.json; other actions take a key and optional value. JSON errors are expected operation results, not process failures. Acceptance procedures are in acceptance.md.\n')
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Local Fixture')
        dump(self.repo / 'setup.json', {'clear_on_start': False})
        rule = 'R-1: create requires an absent key (otherwise AlreadyExists). update, get and delete require an existing key; missing keys return NotFound without mutation or revision increment. Successful create/update/delete/clear increments revision once; get does not. clear removes every record. Setup resets state and creates sample=draft, then optionally clears all records according to setup.json.\n\nR-2: acceptance.md covers the current setup and the expected public operation results. Required owner-terminal observation is due at release-verify: the owner opens their separate terminal/session, reaches this local package, types the procedure and reports the visible JSON lines and any command changes. This host cannot observe or control that owner session. This synthetic local fixture has no deployed service or authenticated endpoint. The host can execute equivalent CLI/library probes; those prove semantics but cannot claim an actual owner-session observation.\n'
        for name, headings in knowledge.SECTIONS.items():
            text = '# ' + name[:-3] + '\n\n'
            for h in headings:
                body = rule if h == 'Requirements' else 'Local package; see README.md, acceptance.md, setup.json and store.py. No external activation.\n'
                if h == 'Real-boundary checks':
                    body = 'RB-1: acceptance.md is the inherited owner-terminal procedure. Run lower-layer CLI checks here first; owner session report remains required separately.\n'
                if h == 'Access and accounts':
                    body = 'The owner separate terminal session is unavailable to this host. No credentials needed. Available here: all local CLI/library calls. Do not label those calls person-only.\n'
                text += '## ' + h + '\n\n' + body + '\n'
            write(self.repo / 'docs/shiploop' / name, text)
        self.commit('Initialize local record package and acceptance requirements\n\nKey learnings: checked operations enforce existence; owner-session observation is separate from callable CLI checks. Synthetic package fixture, no deployment or human observation.')
        actions = [('update', 'sample', 'ready'), ('get', 'sample', None)]
        if self.situation in ('unchecked-oracle', 'inherited-review'):
            actions = [('delete', 'sample', None), ('update', 'sample', 'ready'), ('get', 'sample', None)]
        if self.situation == 'valid-control':
            actions += [('update', 'absent', 'ready')]
        lines = ['# Acceptance procedure', '', '## RB-1', '', 'Start a new session with `python3 store.py --file session.json setup`.', 'Then run these commands in order:', '']
        for i, (action, key, value) in enumerate(actions, 1):
            expected = 'error NotFound with unchanged revision' if key == 'absent' else ('value null after deletion' if action == 'delete' else 'value ready')
            cmd = f'python3 store.py --file session.json {action} {key}' + (f' {value}' if value else '')
            lines.append(f'{i}. `{cmd}`; expect {expected}.')
        lines += ['', 'Owner entry: open your separate terminal, change to this package directory, run the setup and ordered commands. If the directory or command is unavailable, report that and stop. Report each JSON line, whether it matches the stated expectation (yes/no), and any changes you made. No owner observation has been recorded in this fixture.']
        write(self.repo / 'acceptance.md', '\n'.join(lines) + '\n')
        if self.situation == 'unchecked-oracle':
            write(self.repo / 'derivation.py', "from store import Store\nimport json\ns = Store()\ns.setup(json.load(open('setup.json')))\nfor a in [('delete','sample',None),('update','sample','ready'),('get','sample',None)]:\n    print(s.apply_unchecked(*a))\n")
            write(self.repo / 'derivation-notes.md', 'The expected result ready in RB-1 was derived using `python3 derivation.py`. This inherited note records that method, with no separate checked-operation replay attached.\n')
        if self.situation == 'inherited-review':
            write(self.repo / 'prior-review.md', '# Prior fixture review\n\nThis is a synthetic predecessor review artifact, not a model execution or real person observation. That prior review added RB-1 with delete sample, update sample ready, get sample and expected ready. This case is inherited from that prior fixture review; the current worker did not invent it. No checked replay was attached.\n')
        self.commit('Record inherited acceptance procedure' + (' from prior fixture review' if self.situation == 'inherited-review' else '') + '\n\nKey learnings: preserve the ordered acceptance commands and their stated expected results for later consumer verification. No current owner-session observation is claimed.')
        self.old_head = self.git('rev-parse', 'HEAD').strip()
        if self.situation == 'changed-setup':
            observed = []
            for argv in [('setup',), ('update', 'sample', 'ready'), ('get', 'sample')]:
                observed.append(self.call([sys.executable, '-B', self.repo / 'store.py', '--file', 'session-old.json', *argv]))
            write(self.repo / 'previous-observation.md', '# Previous lower-layer observation\n\nCandidate ' + self.old_head + '; setup clear_on_start=false. Checked public CLI commands setup, update sample ready, get sample returned:\n\n```json\n' + ''.join(observed) + '```\nNo owner-session observation.\n')
            self.commit('Retain earlier checked CLI setup observation\n\nKey learnings: inherited update/get worked on the earlier setup; this is lower-layer evidence only, never an owner-session observation.')
            self.old_head = self.git('rev-parse', 'HEAD').strip()
        self.head = self.git('rev-parse', 'HEAD').strip()
        return actions

    def seed(self):
        actions = self.package()
        self.cli('init', '--repo', self.repo, '--prompt', 'Complete the current local record package assignment, preserving the recorded requirements and acceptance evidence.', '--improve-skill', CARD, '--delegation', 'inline', '--lint', 'off', '--execution-mode', 'navigator')
        while True:
            state = store.read_record(self.run / 'state.md')
            stage = nav.current_stage(state)
            self.cli('next')
            if stage == self.boundary:
                break
            if stage == 'implement':
                if self.situation == 'changed-setup':
                    dump(self.repo / 'setup.json', {'clear_on_start': True})
                with (self.repo / 'acceptance.md').open('a') as f:
                    f.write('\nSession files are local scratch and may be removed after completing the procedure.\n')
                path = self.repo / 'store.py'
                path.write_text(path.read_text().replace('Local record store.', 'Local session record store.'))
                self.head = self.git('rev-parse', 'HEAD').strip()
            result = {'outcome': 'done', 'summary': 'Synthetic predecessor setup only; no end-to-end execution, model review, deployment or owner observation.', 'evidence_refs': [str(self.repo / 'acceptance.md')]}
            result = inner.fill(state, stage, result, self.run)
            if stage == 'spec':
                result['primary'] = ['R-1', 'R-2']
            if stage == 'plan':
                result.update(work_items=[{'id': 'W1', 'title': 'Maintain local record package and consumer acceptance', 'context': 'Current setup.json, store.py and acceptance.md belong to this item.', 'follows': ['R-1', 'R-2']}])
            if stage == 'step-plan':
                result.update(paths=['store.py', 'setup.json', 'acceptance.md', 'docs/**', 'README.md', '*.md', 'derivation.py'], steps=[{'id': 'S1', 'task': 'Maintain current setup and acceptance procedure', 'paths': ['store.py', 'setup.json', 'acceptance.md', 'docs/**', 'README.md', '*.md', 'derivation.py'], 'criteria': [], 'proof': 'python3 store.py smoke', 'skills': []}])
            if stage == 'system-test-author':
                result.update(system_commands=[{'command': 'python3 store.py smoke', 'suite': 'check'}], summary=result['summary'] + ' Current test scope: checked public library operations and CLI import; RB-1 owner-terminal procedure at acceptance.md remains unobserved.')
            if stage == 'release-plan':
                result['assumptions'] = [{'id': 'A1', 'assumption': 'Owner-session RB-1 observation remains unperformed', 'disposition': 'open', 'settle': 'Owner runs acceptance.md in their separate terminal and reports JSON lines and changes', 'reason': 'This host cannot observe the owner separate session; local callable operations remain available', 'due_stage': 'release-verify', 'owner': 'owner'}]
                result['consumer_entry'] = {'how': 'Owner opens their separate terminal, enters this package directory and follows acceptance.md RB-1; reports unavailable entry without proceeding.', 'sources': ['acceptance.md', 'README.md', 'store.py']}
                result.update(consumer_checks=[{'command': 'python3 store.py smoke', 'suite': 'check'}], summary=result['summary'] + ' Release is local candidate only; no activation, no rollback operation needed. Current target: ' + self.head + '. Verify RB-1 acceptance.md against setup.json; owner separate terminal report required by R-2. Lower-layer checks do not close that requirement.')
            if stage == 'release':
                result['summary'] += ' No deployment; local candidate ' + self.head + ' in ' + str(self.repo) + '. No owner-session observation.'
            action = nav.current_action(state)['id']
            with core.run_lock(self.run):
                updated = nav.apply(state, action, result)
                if updated.get('active_improve'):
                    updated = nav.finish_improve(updated, action, {'summary': 'Synthetic predecessor review only; not a model or runtime review.'})
                with (self.log / 'effects.stdout').open('a') as out, (self.log / 'effects.stderr').open('a') as err, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    nav.accept_effects(core, self.run, state, updated, action_id=action)
            self.head = self.git('rev-parse', 'HEAD').strip()
            with (self.log / 'synthetic-effects.jsonl').open('a') as f:
                f.write(json.dumps({'stage': stage, 'action': action, 'result': result, 'before_revision': state['revision'], 'after_revision': updated['revision'], 'synthetic': True}) + '\n')
        if self.boundary == 'carry-forward':
            result = {'outcome': 'done', 'summary': 'Current local candidate recorded; inherited acceptance procedure at acceptance.md and current setup.json remain in this work item scope. Lower-layer smoke is available; owner-session observation remains unperformed.', 'evidence_refs': [str(self.repo / 'acceptance.md'), str(self.repo / 'setup.json'), str(self.repo / 'docs/shiploop/spec.md')], 'assumptions': [], 'skill': {'decision': 'none', 'reason': 'No repeated cross-item procedure warrants a skill.'}}
            oldenv = os.environ.copy()
            os.environ.update(self.env)
            try:
                original_run = loop_support._run
                loop_support._run = lambda argv, stdin: json.loads(self.call(argv, stdin=stdin))
                result = with_receipt(result, finish_loop(self.run, note='Synthetic producer preparation only; no semantic review or owner observation.'))
            finally:
                loop_support._run = original_run
                os.environ.clear()
                os.environ.update(oldenv)
            action = nav.current_action(state)['id']
            path = self.run / 'inbox' / (action + '.md')
            store.write_record(path, result)
            self.cli('complete', '--action', action, '--result', path)
        text = self.cli('next')
        write(self.base / 'assignment.md', 'Perform only this current assignment and its callbacks. Stop when this assignment is accepted, re-routed, or awaiting a person. Inspect, probe and repair within its normal scope as needed.\n\n' + text)
        # A direct wrapper keeps every subsequent normal callback in this cell's environment.
        exports = '\n'.join('export ' + k + '=' + shlex.quote(self.env[k]) for k in ('SHIPLOOP_PROGRESS', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE', 'XDG_STATE_HOME', 'SHIPLOOP_KEEPALIVE_HOME', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL'))
        write(self.base / 'environment.sh', exports + '\nunset UNTIL_LOOP_STATE_DIR CLAUDECODE CLAUDE_CODE_SESSION_ID GROK_AGENT GROK_SESSION_ID\n')
        current = store.read_record(self.run / 'state.md')
        child = current.get('active_improve')
        if self.boundary == 'carry-forward':
            assert child and child['stage'] == 'carry-forward' and child['skill']
            handoff = nav.improve_handoff_path(child)
            assert handoff.is_file()
            receipt = Path(child['skill']['receipt']) if 'receipt' in child['skill'] else None
        else:
            assert nav.current_stage(current) == 'release-verify' and child is None
            handoff = None
        return {'directory': str(self.base), 'workspace': str(self.repo), 'run': str(self.run), 'assignment': str(self.base / 'assignment.md'), 'environment': str(self.base / 'environment.sh'), 'situation': self.situation, 'boundary': self.boundary, 'actions': actions, 'source_sha': SHA, 'execution_mode': current.get('execution_mode'), 'delegation': nav.delegation(current), 'old_head': self.old_head, 'candidate_head': self.head, 'stage': nav.current_stage(current), 'action': nav.current_action(current)['id'], 'active_improve': child, 'handoff': str(handoff) if handoff else None, 'logs': str(self.log), 'hashes': tree(self.base)}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('command', choices=['seed', 'identity'])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--situation', choices=SITUATIONS, default=SITUATIONS[0])
    p.add_argument('--boundary', choices=BOUNDARIES, default=BOUNDARIES[0])
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.command == 'identity':
        dump(args.output / 'source.json', source_identity())
        return
    before = source_identity()
    assert before['head'] == SHA and not before['status'], 'Source must match frozen clean revision'
    seed = Seed(args.output / 'work', args.output / 'logs', args.situation, args.boundary)
    try:
        row = seed.seed()
        dump(args.output / (seed.base.name + '.json'), row)
        print(json.dumps({'metadata': str(args.output / (seed.base.name + '.json')), 'assignment': row['assignment']}))
    except Exception:
        dump(seed.log / 'failure.json', {'classification': 'APPARATUS_SETUP_FAILURE', 'traceback': traceback.format_exc()})
        raise

if __name__ == '__main__':
    main()
