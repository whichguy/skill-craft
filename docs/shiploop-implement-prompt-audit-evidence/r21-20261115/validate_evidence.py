"""Validate R21's source anchors and retained evidence, without executing runtime tests."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from urllib.parse import unquote

repo = Path(sys.argv[1]).resolve()
evidence = repo / 'docs/shiploop-implement-prompt-audit-evidence/r21-20261115'
plan = repo / 'docs/shiploop-implement-step-fix-plan-2026-10-17.md'
source = json.loads((evidence / 'source-map.json').read_text())
acceptance = json.loads((evidence / 'acceptance.json').read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


assert [row['id'] for row in source['recommendations']] == [f'R{i:02}' for i in range(1, 23)]
assert {row['id'] for row in source['considerations_and_rules']} == (
    {f'C{i}' for i in range(1, 9)} | {f'CC{i}' for i in range(1, 15)})
anchors = [a for row in [*source['recommendations'], source['schedule']] for a in row['anchors']]
anchors += [row['anchor'] for row in source['considerations_and_rules']]
files = {}
for anchor in anchors:
    path = anchor['path']
    if path not in files:
        current = (repo / path).read_bytes()
        pinned = subprocess.check_output(['git', '-C', str(repo), 'show', source['source_head'] + ':' + path])
        assert current == pinned, ('source drift', path)
        files[path] = current
    raw = files[path]
    lines = raw.decode().splitlines(keepends=True)
    assert 1 <= anchor['start'] <= anchor['end'] <= len(lines), path
    excerpt = ''.join(lines[anchor['start'] - 1:anchor['end']])
    assert excerpt == anchor['excerpt'] and digest(excerpt.encode()) == anchor['excerpt_sha256'], path
    assert digest(raw) == anchor['source_sha256'] and anchor['revision'] == source['source_head'], path

text = plan.read_text()
assert text.startswith('Execute: ask\n')
assert re.findall(r'^### (R\d\d) —', text, re.M) == [f'R{i:02}' for i in range(1, 23)]
assert re.findall(r'^\| (T\d+) \|', text, re.M) == [f'T{i}' for i in range(1, 53)]
links = 0
for doc in (plan, evidence / 'README.md'):
    body = doc.read_text()
    assert len(re.findall(r'^```', body, re.M)) % 2 == 0, doc
    for target in re.findall(r'\]\(([^\s)]+)\)', body):
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
assert acceptance['full_suite_tests'] == 484 and acceptance['new_regression_methods'] == 11
assert len(acceptance['checks']) == 6
for check in acceptance['checks']:
    assert check['status'] == 'PASS' and check['exit_code'] == 0
    raw = (evidence / check['stdout_path']).read_text() + (evidence / check['stderr_path']).read_text()
    counts = [int(n) for n in re.findall(r'Ran (\d+) tests? in', raw)]
    assert counts == check.get('observed_test_counts', []), check['name']
    if check['expected_tests'] is not None:
        assert counts == [check['expected_tests']] and re.search(r'^OK$', raw, re.M), check['name']

worker = json.loads((evidence / acceptance['original_worker_receipt']).read_text())
assert worker['aggregate_status'] == 'INCOMPLETE' and worker['required_tests_observed'] == 484
assert worker['tracked_source_stable'] and not worker['changed_tracked_files']
resolution = json.loads((evidence / acceptance['artifact_resolution']).read_text())
assert resolution['original_worker_status'] == 'INCOMPLETE' and resolution['cleanup_status'] == 'PASS'
assert resolution['original_receipt_sha256'] == digest((evidence / acceptance['original_worker_receipt']).read_bytes())
assert resolution['tracked_source_unchanged'] and resolution['tracked_count'] == 12636
assert resolution['post_status'] == '' and len(resolution['artifacts']) == 43 and not resolution['tests_rerun']
assert resolution['tracked_fingerprint_sha256'] == worker['pre']['tracked_fingerprint_sha256']

for run in json.loads((evidence / 'regressions.json').read_text()):
    raw = (evidence / run['stdout']).read_text() + (evidence / run['stderr']).read_text()
    assert [int(n) for n in re.findall(r'Ran (\d+) tests? in', raw)] == run['tests']
    assert run['identity_unchanged'] and run['tracked_fingerprint_before'] == run['tracked_fingerprint_after']
    assert ('FAILED (' in raw) if run['terminal']['exit'] else bool(re.search(r'^OK$', raw, re.M))

integration = json.loads((evidence / 'integration.json').read_text())
assert integration['integrated_source'] == source['source_head']
assert len(integration['r21_files']) == 7 and all(row['unchanged'] for row in integration['r21_files'])
for row in integration['r21_files'] + integration['unchanged_validation_inputs']:
    assert digest((repo / row['path']).read_bytes()) == row['sha256'], row['path']
review = json.loads((evidence / 'reviews.json').read_text())['final-review']
assert review['exit']['exit'] == 0 and review['exit']['source_unchanged']
assert 'Approve the scoped R21 change' in (evidence / 'final-review.md').read_text()
assert not any(row['new_findings'] for row in json.loads((evidence / 'lint-comparison.json').read_text()).values())
print(json.dumps({'status': 'PASS', 'source_head': source['source_head'], 'recommendations': 22,
                  'considerations': 8, 'craft_rules': 14, 'acceptance_references': 52,
                  'anchors': len(anchors), 'files': len(files), 'local_links': links,
                  'full_suite_tests': 484, 'new_regression_methods': 11,
                  'original_worker_audit': 'INCOMPLETE; retained', 'artifact_resolution': 'PASS',
                  'visual_render_checked': False,
                  'scope': 'Source and retained evidence consistency; no runtime test execution'}, indent=2))
