"""Check the current source anchors and retained R07 acceptance, without running runtime tests."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys
from urllib.parse import unquote

repo = Path(sys.argv[1]).resolve()
evidence = repo / 'docs/shiploop-implement-prompt-audit-evidence/r07-20261115'
plan = repo / 'docs/shiploop-implement-step-fix-plan-2026-10-17.md'
source = json.loads((evidence / 'source-map.json').read_text())
acceptance = json.loads((evidence / 'acceptance.json').read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


assert [r['id'] for r in source['recommendations']] == [f'R{i:02}' for i in range(1, 23)]
assert {r['id'] for r in source['considerations_and_rules']} == (
    {f'C{i}' for i in range(1, 9)} | {f'CC{i}' for i in range(1, 15)})
anchors = [a for r in [*source['recommendations'], source['schedule']] for a in r['anchors']]
anchors += [r['anchor'] for r in source['considerations_and_rules']]
files = {}
for a in anchors:
    path = a['path']
    if path not in files:
        raw = (repo / path).read_bytes()
        pinned = subprocess.check_output(['git', '-C', str(repo), 'show', source['source_head'] + ':' + path])
        assert raw == pinned, ('source drift', path)
        files[path] = raw
    raw = files[path]
    lines = raw.decode().splitlines(keepends=True)
    assert 1 <= a['start'] <= a['end'] <= len(lines), (path, a['symbol'])
    excerpt = ''.join(lines[a['start'] - 1:a['end']])
    assert excerpt == a['excerpt'] and sha(excerpt.encode()) == a['excerpt_sha256'], path
    assert sha(raw) == a['source_sha256'] and a['revision'] == source['source_head'], path

body = plan.read_text()
assert body.startswith('Execute: ask\n')
assert re.findall(r'^### (R\d\d) —', body, re.M) == [f'R{i:02}' for i in range(1, 23)]
assert re.findall(r'^\| (T\d+) \|', body, re.M) == [f'T{i}' for i in range(1, 53)]
links = 0
for doc in (plan, evidence / 'README.md'):
    text = doc.read_text()
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

assert acceptance['status'] == 'PASS' and acceptance['source_head'] == source['source_head']
assert acceptance['qualification']['valid_terminal_omission_reproductions'] == 3
assert acceptance['qualification']['runtime_unchanged']
methods = json.loads((evidence / 'new-regression-methods.json').read_text())
assert acceptance['new_regression_methods'] == len(methods) == len(set(methods))
for entry in methods:
    path, identifier = entry.split(':')
    owner, name = identifier.split('.')
    tree = ast.parse((repo / path).read_text())
    assert any(isinstance(node, ast.ClassDef) and node.name == owner and any(
        isinstance(method, ast.FunctionDef) and method.name == name for method in node.body)
        for node in ast.walk(tree)), entry
for check in acceptance['checks']:
    assert check['status'] == 'PASS' and check['exit_code'] == 0, check['name']
    output = (evidence / check['stdout']).read_text() + (evidence / check['stderr']).read_text()
    if check['kind'] == 'unittest-command':
        counts = [int(n) for n in re.findall(r'^Ran (\d+) tests? in', output, re.M)]
        receipt = json.loads((evidence / check['receipt']).read_text())
        assert counts == [check['test_count']] and counts[0] > 0, check['name']
        assert re.search(r'^OK$', output, re.M) and not re.search(r'^FAILED\b|\bskipped[= ]', output, re.M), check['name']
        assert receipt['status'] == 'PASS' and receipt['exit_code'] == 0, check['name']
        assert receipt['test_count'] == check['test_count'], check['name']
        assert not receipt['private_xdg_leftovers'], check['name']
    if check.get('required_text'):
        assert check['required_text'] in output, check['name']
for bank in acceptance['validation_banks']:
    selected = [row for row in acceptance['checks'] if row['bank'] == bank['id']]
    suites = [row for row in selected if row['kind'] == 'unittest-command']
    assert len(suites) == bank['unittest_commands']
    assert sum(row['full_module'] for row in suites) == bank['full_modules']
    assert sum(row['test_count'] for row in suites) == bank['test_executions']
    assert all(row['source_head'] == bank['source_head'] for row in selected)
    before = json.loads((evidence / bank['directory'] / 'pre-identity.json').read_text())
    after = json.loads((evidence / bank['directory'] / 'post-identity.json').read_text())
    assert before['head'] == after['head'] == bank['source_head']
    assert before['fingerprint'] == after['fingerprint'] and before['tracked_count'] == after['tracked_count']
    for identity in (before, after):
        assert not identity['ordinary_status'] and not identity['ignored_inclusive_status']
        assert all(identity['parent_file_hashes'].values())
assert acceptance['validation_banks'][0]['full_modules'] == 13
assert acceptance['validation_banks'][0]['test_executions'] == 1204
assert acceptance['validation_banks'][1]['full_modules'] == 6
assert acceptance['validation_banks'][1]['source_head'] == source['source_head']
integration = [row for row in acceptance['checks'] if row['bank'] == 'integration' and
               row['kind'] == 'unittest-command' and not row['full_module']]
assert sorted(row['argv'][2] + ':' + name for row in integration for name in row['argv'][3:]) == sorted(methods)

for r in json.loads((evidence / 'retained-attempts.json').read_text()):
    output = (evidence / r['stdout']).read_text() + (evidence / r['stderr']).read_text()
    assert [int(n) for n in re.findall(r'Ran (\d+) tests? in', output)] == r['observed_test_counts'], r['id']
    assert r['source_unchanged'], r['id']
    assert ('FAILED (' in output) if r['exit_code'] else bool(re.search(r'^OK$', output, re.M)), r['id']

assert acceptance['review']['status'] == 'APPROVE'
assert (evidence / acceptance['review']['path']).read_text().startswith('**APPROVE**')
review_exit = json.loads((evidence / 'integration-review-exit.json').read_text())
assert review_exit['exit_code'] == 0 and review_exit['source_files_unchanged']
assert acceptance['tracked_source_stable'] and not acceptance['unexpected_outputs']
assert acceptance['qualification']['initial_errors'] == 0
assert acceptance['scope'] == 'Explicit continuity of recorded outcomes; references remain host declarations'
print(json.dumps({'status': 'PASS', 'source_head': source['source_head'], 'recommendations': 22,
                  'considerations': 8, 'craft_rules': 14, 'acceptance_references': 52,
                  'anchors': len(anchors), 'files': len(files), 'local_links': links,
                  'new_regression_methods': acceptance['new_regression_methods'],
                  'visual_render_checked': False,
                  'scope': 'Source and retained evidence consistency; no runtime test execution'}, indent=2))
