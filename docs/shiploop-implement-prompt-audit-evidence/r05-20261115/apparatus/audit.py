#!/usr/bin/env python3
"""Read-only final inventory checks; does not advance subject assignments."""
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path
import re
import seed
from preflight import Reference


def audit(run):
    cells = json.loads((run / 'cells.json').read_text())
    evidence = []
    states = set()
    for row in cells:
        base, repo = Path(row['directory']), Path(row['workspace'])
        assert seed.tree(base) == row['hashes']
        assignment = Path(row['assignment']).read_text()
        for word in ('planted flaw', 'procedure audit', 'detect first invalid transition', 'R05 verdict', 'private oracle', 'reference-proof.json', 'proposed-registration.json'):
            assert word not in assignment, (base, word)
        # Last normal next stdout must be reproduced byte-for-byte after the neutral boundary.
        command_files = sorted(Path(row['logs']).glob('*.command.json'))
        last = next(p for p in reversed(command_files) if json.loads(p.read_text())['argv'][3:4] == ['next'])
        raw = last.with_name(last.name.replace('.command.json', '.stdout')).read_text()
        assert assignment.endswith(raw)
        state = seed.store.read_record(Path(row['run']) / 'state.md')
        assert seed.nav.current_stage(state) == row['boundary']
        assert seed.nav.delegation(state) == 'inline'
        assert state.get('execution_mode') == 'navigator'
        if row['boundary'] == 'carry-forward':
            d = Path(row['handoff']).parent
            packet = json.loads((d / 'packet.json').read_text())
            assert packet['status'] == 'active'
            assert not list((d / 'reviews').glob('review-*.md'))
            assert packet['state_file'] not in states
            states.add(packet['state_file'])
        else:
            assert not state['active_improve']
        assert not (repo / '.git/objects/info/alternates').exists()
        for f in repo.rglob('*'):
            if not f.is_file() or '.git' in f.parts or '.shiploop-improve' in f.parts:
                continue
            if f.suffix in ('.md', '.py', '.json'):
                text = f.read_text()
                for key in ('private_fault_label', 'earliest_invalid_action', 'private_reference_proof', 'reference-proof.json', 'proposed-registration.json'):
                    assert key not in text, (f, key)
        old = None
        if row['situation'] == 'changed-setup':
            text = (repo / 'previous-observation.md').read_text()
            block = text.split('```json\n', 1)[1].split('```', 1)[0]
            observed = [json.loads(line) for line in block.splitlines() if line.strip()]
            ref = Reference()
            checked = [ref.step('setup', value=False), ref.step('update', 'sample', 'ready'), ref.step('get', 'sample')]
            assert observed == checked
            old = {'actual_old_cli_matches_independent_reference': True, 'observed': observed, 'note': str(repo / 'previous-observation.md')}
        evidence.append({'directory': str(base), 'hashes_unchanged': True, 'actual_next_assignment_byte_match': True, 'fresh_runtime_unconsumed': True, 'no_private_answer_locators_in_product_files': True, 'old_setup_proof': old})
    source = seed.source_identity()
    assert source == json.loads((run / 'source-before.json').read_text())
    result = {'outcome': 'PASS', 'cells': evidence, 'distinct_active_improve_runtime_states': len(states), 'source_unchanged': True, 'os_level_isolation': 'NOT_VERIFIED; these are workspace hygiene checks, not permission/access enforcement'}
    output = run / 'final-audit.json'
    assert not output.exists(), 'Preserve earlier audit; use a new output if another attempt is needed'
    seed.dump(output, result)
    print(json.dumps({'outcome': 'PASS', 'cells': len(evidence), 'output': str(output)}))

if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--run', required=True, type=Path)
    audit(p.parse_args().run)
