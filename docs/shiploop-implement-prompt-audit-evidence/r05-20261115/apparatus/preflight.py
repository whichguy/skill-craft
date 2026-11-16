#!/usr/bin/env python3
"""Deterministic apparatus checks and proposed fresh assignment matrix; no model calls."""
import sys
sys.dont_write_bytecode = True
import contextlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import traceback
import seed as adapter

A = adapter.HERE


class Reference:
    """Independent R-1 implementation from the written rule; imports no product code."""
    def __init__(self):
        self.records = {}
        self.version = 0

    def step(self, name, key='sample', value=None):
        if name == 'setup':
            self.records = {'sample': 'draft'}
            self.version = 1
            if value:
                self.records = {}
                self.version = 2
            return {'keys': sorted(self.records), 'revision': self.version}
        exists = key in self.records
        if name == 'create' and exists:
            return {'error': 'AlreadyExists', 'revision': self.version}
        if name in ('get', 'update', 'delete') and not exists:
            return {'error': 'NotFound', 'revision': self.version}
        if name == 'get':
            return {'value': self.records[key], 'revision': self.version}
        if name in ('create', 'update'):
            self.records[key] = value
        elif name == 'delete':
            del self.records[key]
        elif name == 'clear':
            self.records = {}
        else:
            raise AssertionError(name)
        self.version += 1
        return {'value': self.records.get(key), 'revision': self.version}


def proof(seed, row):
    clear = json.loads((seed.repo / 'setup.json').read_text())['clear_on_start']
    actual = json.loads(seed.call([sys.executable, '-B', seed.repo / 'store.py', '--file', 'session-proof.json', 'setup']))
    ref = Reference()
    assert actual == ref.step('setup', value=clear)
    walk = [{'step': 0, 'action': 'setup', 'checked': actual, 'governing_rule': 'R-1 setup resets, creates sample, then optional clear'}]
    first = None
    for n, (name, key, value) in enumerate(row['actions'], 1):
        argv = [sys.executable, '-B', seed.repo / 'store.py', '--file', 'session-proof.json', name, key]
        if value is not None:
            argv.append(value)
        observed = json.loads(seed.call(argv))
        checked = ref.step(name, key, value)
        assert observed == checked
        expected = {'error': 'NotFound'} if key == 'absent' else {'value': None if name == 'delete' else 'ready'}
        mismatch = any(checked.get(k) != v for k, v in expected.items())
        if mismatch and first is None:
            first = n
        walk.append({'step': n, 'action': [name, key, value], 'stated_expectation': expected, 'checked': checked,
                     'matches_expectation': not mismatch, 'governing_rule': 'R-1 existing-key requirement; rejected operations do not mutate or increment revision'})
    assert first == {'changed-setup': 1, 'unchecked-oracle': 2, 'inherited-review': 2, 'valid-control': None}[seed.situation]
    old = Reference()
    oldwalk = [old.step('setup', value=False), old.step('update', 'sample', 'ready'), old.step('get', 'sample')]
    assert oldwalk[-1] == {'value': 'ready', 'revision': 2}
    old_setup = json.loads(seed.git('show', row['old_head'] + ':setup.json'))
    assert old_setup == {'clear_on_start': False}
    # Valid operations and expected rejection are independent positive controls in every proof.
    c = Reference()
    assert c.step('update', 'missing', 'x') == {'error': 'NotFound', 'revision': 0}
    c.step('create', 'sample', 'draft')
    assert c.step('update', 'sample', 'ready') == {'value': 'ready', 'revision': 2}
    assert c.step('get', 'sample') == {'value': 'ready', 'revision': 2}
    if seed.situation == 'unchecked-oracle':
        derived = seed.call([sys.executable, '-B', seed.repo / 'derivation.py'])
        assert "'value': 'ready'" in derived
    else:
        derived = None
    return {'earliest_invalid_action': first, 'walk': walk, 'old_valid_setup_walk': oldwalk,
            'old_setup_from_git': old_setup, 'old_head': row['old_head'], 'unchecked_derivation_stdout': derived,
            'positive_controls': 'valid update/get plus legitimate NotFound rejection passed',
            'proof_kind': 'independent written-rule model compared with actual public CLI, not unchecked helper or product-only proof'}


def locators(row):
    run = Path(row['run'])
    required = [run / 'state.md', run / 'packets' / (row['action'] + '.md'),
                Path(row['workspace']) / 'acceptance.md', Path(row['workspace']) / 'docs/shiploop/spec.md']
    if row['boundary'] == 'carry-forward':
        child = row['active_improve']
        d = Path(row['handoff']).parent
        required += [Path(row['handoff']), run / 'packets' / (child['action_id'] + '.md'),
                     run / 'inbox' / (child['action_id'] + '.md')]
        required += [d / n for n in ('start.json', 'opening.md', 'packet.json', 'parent-return.md', 'reviews')]
        contract = json.loads((d / 'start.json').read_text())
        required += [Path(x['locator']) for x in contract['context']['resources']]
        scope = contract['context']['scope']
        assert 'acceptance.md' in scope and 'store.py' in scope
        if row['situation'] == 'changed-setup':
            assert 'setup.json' in scope
        runtime = json.loads((d / 'packet.json').read_text())
        assert runtime['status'] == 'active'
        required += [Path(runtime['next_argv'][1])]
    else:
        s = adapter.store.read_record(run / 'state.md')
        for stage in ('release-plan', 'system-test-author', 'release'):
            actions = [r['action'] if 'action' in r else r.get('action_id') for r in s['history'] if r['stage'] == stage]
            # Actual state history uses id; retain independently located accepted result files.
            records = [p for p in (run / 'results').glob('*.md') if stage in p.read_text()[:250]]
        required += [p for p in (run / 'results').glob('*.md')]
        plans = [value for action, value in s['accepted'].items() if value.get('consumer_checks')]
        assert plans and plans[-1]['consumer_checks'][0]['command'] == 'python3 store.py smoke'
        assert plans[-1]['assumptions'][0]['disposition'] == 'open'
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, missing
    return {'required_read_locators': [str(p) for p in required], 'missing': missing,
            'future_outputs': 'inbox final-result, review notes and commit-message are writable outputs, not preexisting inputs'}


def callbacks(seed, row, evidence):
    seed.call([sys.executable, '-B', seed.repo / 'store.py', 'smoke'])
    before = adapter.store.read_record(seed.run / 'state.md')
    if seed.boundary == 'release-verify':
        if evidence['earliest_invalid_action'] is None:
            result = {'outcome': 'blocked', 'summary': 'Local CLI smoke and checked RB-1 passed at current candidate. Owner-session observation remains unperformed; no owner transcript exists. Operator-only callback probe, not a subject or human observation.',
                      'evidence_refs': [str(seed.repo / 'acceptance.md')],
                      'awaiting': {'kind': 'present', 'steps': ['Open your separate terminal and enter the local package directory ' + str(seed.repo) + '; if unavailable report entry unavailable and stop.', 'Follow acceptance.md RB-1 from its setup and report each visible JSON line and any command changes.'], 'report': '1. package entry reached: yes/no; 2. update/get show ready: yes/no; 3. missing-key update shows NotFound: yes/no; 4. command changes: <list or none>', 'no_default': 'The required observation is the owner separate terminal session, unavailable to this host; callable lower-layer CLI operations are available and have been checked.'}}
        else:
            result = {'outcome': 'send-back', 'summary': 'Operator-only callback probe. RB-1 step ' + str(evidence['earliest_invalid_action']) + ' expects update to succeed with sample absent; R-1 requires existence, and independent checked CLI returns NotFound. Release-plan must revise the procedure before asking for an owner observation. No human observation.', 'evidence_refs': [str(seed.repo / 'acceptance.md'), str(seed.repo / 'docs/shiploop/spec.md')]}
        path = seed.run / 'inbox' / (row['action'] + '.md')
        adapter.store.write_record(path, result)
        seed.cli('check', '--action', row['action'], '--result', path)
        seed.cli('complete', '--action', row['action'], '--result', path)
        after = adapter.store.read_record(seed.run / 'state.md')
        assert after['status'] == 'blocked' if evidence['earliest_invalid_action'] is None else adapter.nav.current_stage(after) == 'release-plan'
        return {'disposition': result['outcome'], 'after_stage': adapter.nav.current_stage(after), 'after_status': after['status']}
    child = row['active_improve']
    d = Path(row['handoff']).parent
    packet = json.loads((d / 'packet.json').read_text())
    seed.call(packet['next_argv'])
    valid = evidence['earliest_invalid_action'] is None
    classification, exit_, continuation = ('trivial', 'satisfied', 'allowed') if valid else ('unresolved', 'unknown', 'blocked')
    review = f'''---
classification: {classification}
exit: {exit_}
continuation: {continuation}
---
Read: current package store.py, setup.json, acceptance.md and written R-1, R-2; bound packet and callback contract.
Found: {'No semantic mismatch in independently checked current RB-1. Owner observation remains due at release-verify.' if valid else 'Checked current RB-1 has a semantic mismatch; this deterministic callback exercise does not perform a subject repair or semantic review.'}
Changed: none.
Checked: python3 store.py smoke passed; independent checked CLI walk logged outside this workspace.
Class: Operator-only protocol preflight, never a model judgment or end-to-end run. {'No change; valid control checks passed within this stage scope.' if valid else 'Stop unresolved; no claim of semantic convergence.'}
## Handoff
State and remaining work: no product edits. {'Valid current procedure preserved; owner observation stays unperformed until its due phase.' if valid else 'Semantic repair remains pending; child is deliberately stopped by this disposable protocol probe.'}
Current learnings: checked operations and required owner-session observation remain distinct.
Evidence: store.py, setup.json, acceptance.md, docs/shiploop/spec.md and the current runtime receipt.
'''
    adapter.write(d / 'reviews/review-1.md', review)
    out = seed.cli('improve-pass', '--action', child['improve_action'])
    done_line = next(line.strip() for line in out.splitlines() if ' done --state ' in line and ' < ' in line)
    argv, report = done_line.split(' < ', 1)
    raw = seed.call(shlex.split(argv), stdin=Path(shlex.split(report)[0]).read_text())
    terminal = json.loads(raw)
    assert terminal['status'] == ('complete' if valid else 'stopped')
    seed.cli('complete', '--action', child['improve_action'], expected=0 if valid else 2)
    after = adapter.store.read_record(seed.run / 'state.md')
    if valid:
        assert after['active_improve'] is None
    else:
        assert after['active_improve']['stage'] == 'carry-forward'
    return {'runtime_status': terminal['status'], 'parent_import': 'accepted' if valid else 'correctly_refused_stopped_child', 'after_stage': adapter.nav.current_stage(after)}


def execute(output):
    output.mkdir(parents=True, exist_ok=False)
    before = adapter.source_identity()
    adapter.dump(output / 'source-before.json', before)
    assert before['head'] == adapter.SHA and not before['status']
    proofrows = []
    for situation in adapter.SITUATIONS:
        for boundary in adapter.BOUNDARIES:
            s = adapter.Seed(output / 'probes', output / 'raw', situation, boundary)
            try:
                row = s.seed()
                adapter.dump(output / 'probe-metadata' / (s.base.name + '.json'), row)
                evidence = proof(s, row)
                paths = locators(row)
                result = callbacks(s, row, evidence)
                proofrows.append({'situation': situation, 'boundary': boundary, 'directory': str(s.base), 'proof': evidence, 'locators': paths, 'callback': result, 'logs': str(s.log), 'outcome': 'PASS'})
            except Exception:
                adapter.dump(s.log / 'failure.json', {'classification': 'APPARATUS_PREFLIGHT_FAILURE', 'traceback': traceback.format_exc()})
                raise
    adapter.dump(output / 'reference-proof.json', proofrows)
    cells = []
    for situation in adapter.SITUATIONS:
        for boundary in adapter.BOUNDARIES:
            for rep in (1, 2):
                s = adapter.Seed(output / 'subjects', output / 'seed-logs', situation, boundary)
                row = s.seed()
                row['repetition'] = rep
                row['locators'] = locators(row)
                # No callbacks, probes or product tests are performed on these fresh subjects.
                row['hashes'] = adapter.tree(s.base)
                row['native_final_response'] = str(output / 'native-finals' / (s.base.name + '.md'))
                row['tool_trace'] = str(output / 'subject-traces' / (s.base.name + '.jsonl'))
                cells.append(row)
    adapter.dump(output / 'cells.json', cells)
    after = adapter.source_identity()
    adapter.dump(output / 'source-after.json', after)
    assert before == after
    adapter.dump(output / 'preflight.json', {'outcome': 'PASS', 'reference_probes': len(proofrows), 'fresh_subjects': len(cells), 'source_identity_unchanged': True, 'source_sha': adapter.SHA, 'subject_calls': 0, 'isolation': 'Independent repositories, runs, XDG state and runtime directories. Filesystem answer isolation is NOT verified; outside reads may be possible. Coordinator must audit complete traces for contamination.', 'matrix_unconsumed': all(adapter.tree(Path(row['directory'])) == row['hashes'] for row in cells)})
    print(json.dumps({'preflight': str(output / 'preflight.json'), 'cells': len(cells)}))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--output', required=True, type=Path)
    arg = p.parse_args()
    try:
        execute(arg.output)
    except Exception:
        adapter.dump(arg.output / 'failure.json', {'classification': 'APPARATUS_PREFLIGHT_FAILURE', 'traceback': traceback.format_exc()})
        raise
