"""Validate retained R05 evidence and current code anchors; execute no model or runtime tests."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from urllib.parse import unquote

repo = Path(sys.argv[1]).resolve()
evidence = repo / 'docs/shiploop-implement-prompt-audit-evidence/r05-20261115'
plan = repo / 'docs/shiploop-implement-step-fix-plan-2026-10-17.md'


def read(name):
    return json.loads((evidence / name).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


source, acceptance = read('source-map.json'), read('acceptance.json')
assert acceptance['status'] == 'QUALIFIED_SCOPED_NO_REPAIR'
assert not acceptance['production_delta'] and acceptance['new_production_regressions'] == 0
assert source['source_head'] == acceptance['current_source']
assert source['qualification_source_head'] == acceptance['qualification_source']
assert [r['id'] for r in source['recommendations']] == [f'R{i:02}' for i in range(1, 23)]
assert {r['id'] for r in source['considerations_and_rules']} == (
    {f'C{i}' for i in range(1, 9)} | {f'CC{i}' for i in range(1, 15)})
anchors = [a for r in [*source['recommendations'], source['schedule'], source['qualification_transport']]
           for a in r['anchors']]
anchors += [r['anchor'] for r in source['considerations_and_rules']]
files = {}
for anchor in anchors:
    path = anchor['path']
    if path not in files:
        raw = (repo / path).read_bytes()
        assert raw == subprocess.check_output(['git', '-C', str(repo), 'show', source['source_head'] + ':' + path]), path
        qualified = subprocess.check_output(['git', '-C', str(repo), 'show', source['qualification_source_head'] + ':' + path])
        if raw != qualified:
            assert path == 'docs/experiments/parallel-plan-execution-20261114/README.md', path
            assert qualified.count(anchor['excerpt'].encode()) == 1, path
        files[path] = raw
    raw = files[path]
    lines = raw.decode().splitlines(keepends=True)
    assert 1 <= anchor['start'] <= anchor['end'] <= len(lines), path
    excerpt = ''.join(lines[anchor['start'] - 1:anchor['end']])
    assert excerpt == anchor['excerpt'] and sha(excerpt.encode()) == anchor['excerpt_sha256'], path
    assert sha(raw) == anchor['source_sha256'] and anchor['revision'] == source['source_head'], path
assert len(anchors) == 211 and len(files) == 46
assert not subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only',
                                   acceptance['qualification_source'], 'HEAD', '--',
                                   'skills/shiploop', 'skills/improve', 'skills/until-loop'])

body = plan.read_text()
assert body.startswith('Execute: ask\n')
assert re.findall(r'^### (R\d\d) —', body, re.M) == [f'R{i:02}' for i in range(1, 23)]
assert re.findall(r'^\| (T\d+) \|', body, re.M) == [f'T{i}' for i in range(1, 53)]
assert '| P1 | R19 |' in body and '| P1 | R05 |' not in body
links = 0
for doc in (plan, evidence / 'README.md'):
    text = doc.read_text()
    assert 'FOLLOWUP_' not in text
    assert len(re.findall(r'^```', text, re.M)) % 2 == 0, doc
    for target in re.findall(r'\]\(([^\s)]+)\)', text):
        if target.startswith(('https://', 'http://', 'mailto:')):
            continue
        path, _, fragment = unquote(target).partition('#')
        dest = (doc.parent / path).resolve() if path else doc
        assert dest.is_file(), (doc.name, target)
        if re.fullmatch(r'L\d+', fragment):
            assert 1 <= int(fragment[1:]) <= len(dest.read_text().splitlines()), target
        elif fragment and dest.suffix == '.md':
            headings = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-')
                        for h in re.findall(r'^#+ (.+)$', dest.read_text(), re.M)}
            assert fragment in headings, target
        links += 1

registrations = {
    'interrupted-001': read('registration/registration.json'),
    'primary-002': read('registration/registration-002.json'),
    'followup-003': read('registration/registration-003.json'),
}
records = read('native-results.json')
for bank, count in [('interrupted-001', 16), ('primary-002', 16), ('followup-003', 4)]:
    selected = [r for r in records if r['bank'] == bank]
    assert len(selected) == count == len(registrations[bank]['cells'])
    assert {r['id'] for r in selected} == {c['id'] for c in registrations[bank]['cells']}
    for row in selected:
        if row['receipt'] is None:
            assert bank == 'interrupted-001'
            continue
        receipt = row['receipt']
        assert receipt['exit_code'] == 0 and receipt['execution_status'] == 'COMPLETED'
        assert row['native_final'] and sha(row['input'].encode()) == receipt['input_sha256']
        args = row['launch']['argv']
        assert args[args.index('--model') + 1] == 'gpt-6.1-sol'
        assert 'model_reasoning_effort="medium"' in args
        if bank == 'followup-003':
            assert args[args.index('--sandbox') + 1] == 'danger-full-access'
            assert 'approval_policy="never"' in args
        if bank != 'interrupted-001':
            assert receipt['environment']['SHIPLOOP_KEEPALIVE'] == 'off'
assert Counter(r['collection_status'] for r in records if r['bank'] == 'interrupted-001') == {
    'COMPLETED': 3, 'INTERRUPTED': 3, 'NOT_LAUNCHED': 10}

judgments = read('judgments.json')
for group in judgments:
    assert group['exit']['exit_code'] == 0 and group['exit']['evidence_files_unchanged']
    assert group['pre_file_sha256'] == group['post_file_sha256']
    argv = group['launch']['argv']
    assert argv[argv.index('--model') + 1] == 'gpt-6-astra'
    assert 'model_reasoning_effort="high"' in argv
    assert argv[argv.index('--sandbox') + 1] == 'read-only'
    assert set(group['launch']['cells']) == {c['id'] for c in group['judgment']['cells']}
    assert all(c['evidence'] and c['contamination'] == 'none-observed' for c in group['judgment']['cells'])
for bank, expected in [('primary-002', 16), ('followup-003', 4)]:
    cells = [c for group in judgments if group['bank'] == bank for c in group['judgment']['cells']]
    assert len(cells) == len({c['id'] for c in cells}) == expected
    assert all(c['diagnosis'] == c['disposition'] == 'PASS' for c in cells)
    if bank == 'primary-002':
        assert Counter(c['protocol'] for c in cells) == {'PASS': 12, 'INCOMPLETE': 4}
        assert sorted(c['id'] for c in cells if c['protocol'] == 'INCOMPLETE') == [
            'cell-05', 'cell-09', 'cell-10', 'cell-14']
    else:
        assert all(c['protocol'] == c['verdict'] == 'PASS' for c in cells)
assert acceptance['primary']['protocol'] == {'PASS': 12, 'INCOMPLETE': 4}
assert acceptance['followups']['protocol'] == {'PASS': 4} and acceptance['followups']['not_a_regrade']

for row in read('source-stability.json'):
    assert row['head'] == acceptance['qualification_source']
    assert row['tracked_files'] == 13337 and row['identical_pre_post'] and not row['ordinary_status']
    assert row['pre_inventory_sha256'] == row['post_inventory_sha256']
transport = read('transport.json')
assert all(r['initial_bind_in_frozen_inventory'] and r['bind_still_exists']
           for r in transport['initial_binding'])
for row in transport['permission_probes']:
    assert row['receipt']['exit'] == 0
    result = json.loads(row['receipt']['final'])
    assert result['initial_bind_exists']
    if row['mode'] == 'workspace-write':
        assert result['status'] == 'BLOCKED' and 'Operation not permitted' in result['error']
    else:
        assert result['status'] == 'PASS' and result['tree']
assert len(transport['permission_probes']) == 4
trace = read('trace-audit.json')
assert len(trace['screens']) == 20 and not any(r['input_locator_flags'] for r in trace['screens'])
integration = read('integration.json')
assert integration['all_existing_skill_bytes_unchanged']
assert integration['plan_source_files_changed'] == ['docs/experiments/parallel-plan-execution-20261114/README.md']
assert all(r['excerpt_unchanged'] for r in integration['background_file_changes'])
assert len(integration['upstream_added_skill_files']) == 10 and not integration['relevant_skill_delta']
assert acceptance['closure_review']['status'] == 'APPROVE'
assert (evidence / 'closure-review.md').read_text().startswith('APPROVE')
assert read('closure-review-exit.json')['source_files_unchanged']

# Copied registration/freeze bytes must match the external original manifest.
external = {r['path']: r for r in read('external-evidence.json')['files']}
root = Path(read('external-evidence.json')['root'])
for p in (evidence / 'registration').iterdir():
    assert sha(p.read_bytes()) == external[str(root / p.name)]['sha256'], p.name
for name in ['registration-freeze.json', 'registration-002-freeze.json', 'registration-003-freeze.json']:
    for rel, digest in read('registration/' + name)['sha256'].items():
        assert external[str(root / rel)]['sha256'] == digest, (name, rel)
        options = [evidence / 'registration' / rel, evidence / 'apparatus' / rel,
                   evidence / 'preflight' / rel.replace('/', '--')]
        for p in options:
            if p.is_file():
                assert sha(p.read_bytes()) == digest, (name, rel)
print(json.dumps({'status': 'PASS', 'source_head': source['source_head'],
                  'qualification_source': acceptance['qualification_source'],
                  'recommendations': 22, 'considerations': 8, 'craft_rules': 14,
                  'acceptance_references': 52, 'anchors': len(anchors), 'files': len(files),
                  'primary_semantic_passes': 16, 'primary_protocol_passes': 12,
                  'primary_protocol_incomplete': 4, 'separate_followup_passes': 4,
                  'local_links': links, 'visual_render_checked': False,
                  'scope': 'Retained evidence and source consistency; no runtime test execution'}, indent=2))
