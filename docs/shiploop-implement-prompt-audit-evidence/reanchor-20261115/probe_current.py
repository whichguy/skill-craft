"""Read-only committed-source probes; helper evidence, not CLI or live acceptance."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--repo', required=True)
parser.add_argument('--revision', required=True)
args = parser.parse_args()
archive = subprocess.check_output(['git', '-C', args.repo, 'archive', args.revision, 'skills/shiploop/scripts'])
with tempfile.TemporaryDirectory(prefix='shiploop-reanchor-') as directory:
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(directory, filter='data')
    sys.path.insert(0, str(Path(directory) / 'skills/shiploop/scripts'))
    import shiploop_test_loop as tests
    import shiploop_check as check
    import shiploop_navigator as navigator
    import shiploop_loops as loops

    outputs = {
        'masked_failed': 'test_value.py::test_value[CASE-1] FAILED\n=== 1 failed in 0.01s ===\n',
        'mixed_pass_error': 'test_value.py::test_value[CASE-1] PASSED\n=== 1 passed, 1 error in 0.01s ===\n',
        'passing_FAILED_title': 'test_value.py::test_FAILED_value[CASE-1] PASSED\n=== 1 passed in 0.01s ===\n',
    }
    cases = []
    for label, output in outputs.items():
        for suite in ['focused', 'check']:
            row = {'command': 'wrapped-test', 'suite': suite}
            if suite == 'focused':
                row['ids'] = ['CASE-1']
            cases.append({'scenario': label, 'suite': suite, 'exit': 0, 'output': output,
                          'verdict': tests.judge(row, 0, output)})

    root = Path(directory) / 'run'
    root.mkdir()
    command = {'command': 'wrapped-test', 'suite': 'focused', 'ids': ['CASE-1']}
    legacy = {'schema': tests.SCHEMA, 'action': 'A1', 'stage': 'test', 'work_item': 'W1',
              'passed': True, 'commands': [command], 'trees': ['unchanged-tree'],
              'runs': [{**command, 'exit': 0, 'status': 'passed',
                        'counts': {'ran': 1, 'failed': 1, 'runners': ['pytest']},
                        'stdout': outputs['masked_failed'], 'stderr': ''}]}
    tests.store.write_record(root / tests.check_path('A1'), legacy)
    with patch.object(tests, '_tree', return_value='unchanged-tree'):
        reused = tests._reused(root, 'A1', 'test', 'W1', [command], root, {})

    old_proof = {**legacy, 'kind': 'step-proof', 'stage': 'implement', 'step': 'S1',
                 'command': 'wrapped-test'}
    tests.store.write_record(root / tests.step_proof_check_path('A1'), old_proof)
    with patch.object(tests, '_tree', return_value='unchanged-tree'), patch.object(
        tests, 'step_command', return_value=({'id': 'S1'}, {'command': 'wrapped-test', 'suite': 'check'})
    ):
        writes, refusal, lines = tests.step_proof(root, {'repo': str(root)}, 'W1', 'A1')

    key = {'tree': 'unchanged-tree', 'draft': 'unchanged-draft', 'version': 'old-package'}
    check.record_answer(root, 'A2', 'test', key, yes=True)
    same_yes = check.matching_yes(root, 'A2', key) is not None
    new_version_yes = check.matching_yes(root, 'A2', {**key, 'version': 'new-package'}) is not None
    body = 'start\n' + 'long Unicode field: 雪\n' * 6000 + 'required final text\n'
    printed = navigator.printed_text(None, root, {}, root / 'packet.md', body)
    start = loops.start_command({'runtime_cli': '/example/until-loop.py'}, root / 'receipt.json', root / 'contract.md')
    result = {
        'revision': args.revision,
        'scope': 'direct committed helpers; no full callback, external target, live model or release acceptance',
        'cases': cases,
        'candidate_old_verdict': {'reused': reused is not None,
                                 'status': reused[0][0]['status'] if reused else None,
                                 'stub': 'only product-tree lookup'},
        'step_old_verdict': {'reused': bool(writes) and not refusal and any('reused' in line for line in lines),
                            'refusal': refusal,
                            'stubs': 'product-tree lookup and accepted-step selector; stored proof receipt is real'},
        'whole_answer': {'matching_key_reused': same_yes, 'changed_package_version_reused': new_version_yes,
                         'limit': 'tests key comparison only; external-state identity inspected separately in source'},
        'full_packet': {'input_characters': len(body), 'whole_body_preserved': printed == body + navigator.HEAD_END + '\n'},
        'loop_start_has_directory': '--directory' in start,
        'work_template_characters': len(loops.WORK_STEP),
    }
    print(json.dumps(result, indent=2))
