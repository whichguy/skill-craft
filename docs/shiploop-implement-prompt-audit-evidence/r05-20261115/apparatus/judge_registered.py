"""Collect one fresh read-only Astra judgment for completed registered subjects."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).parent


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def evidence_hashes(cells):
    found = {}
    for cell in cells:
        for p in Path(cell['workspace']).rglob('*'):
            if p.is_file() and '.git' not in p.parts and p.suffix in ('.md', '.py', '.json'):
                found[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path(cell['run']).rglob('*'):
            if p.is_file():
                found[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return found


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--group', required=True)
    p.add_argument('--registration', required=True, type=Path)
    p.add_argument('--execution', required=True, type=Path)
    p.add_argument('--judgments', required=True, type=Path)
    p.add_argument('--cells', nargs='+', required=True)
    args = p.parse_args()
    reg = json.loads(args.registration.read_text())
    cells = [row for row in reg['cells'] if row['id'] in args.cells]
    assert len(cells) == len(set(args.cells))
    target = args.judgments / args.group
    target.mkdir(parents=True, exist_ok=False)
    for cell in cells:
        receipt = args.execution / cell['id'] / 'receipt.json'
        assert receipt.is_file()
        cell['subject_execution'] = json.loads(receipt.read_text())
    brief = (ROOT / 'judge-instructions.md').read_text()
    brief += '\nFrozen registration: ' + str(args.registration) + '\n'
    fields = ('id', 'situation', 'boundary', 'repetition', 'workspace', 'run', 'source_sha', 'earliest_invalid_action', 'rule', 'private_reference_proof', 'subject_execution')
    brief += 'Completed cells to judge (file inventories remain at the registration locator):\n' + json.dumps([{k: row[k] for k in fields} for row in cells], indent=2) + '\n'
    (target / 'input.md').write_text(brief)
    before = evidence_hashes(cells)
    save(target / 'evidence-pre.json', before)
    argv = ['codex', 'exec', '--profile', 'shiploop-judge', '--model', 'gpt-6-astra',
            '-c', 'model_reasoning_effort="high"', '--sandbox', 'read-only',
            '-C', reg['source']['path'], '--json', '-o', str(target / 'judgment.json'), '-']
    save(target / 'launch.json', {'argv': argv, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 'cells': args.cells, 'input_sha256': hashlib.sha256(brief.encode()).hexdigest()})
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    with (target / 'events.jsonl').open('w') as out, (target / 'stderr.log').open('w') as err:
        result = subprocess.run(argv, input=brief, text=True, stdout=out, stderr=err, env=env, check=False)
    after = evidence_hashes(cells)
    save(target / 'evidence-post.json', after)
    save(target / 'exit.json', {'exit_code': result.returncode,
         'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'evidence_files_unchanged': before == after})
    assert result.returncode == 0 and before == after
    verdict = json.loads((target / 'judgment.json').read_text())
    assert sorted(row['id'] for row in verdict['cells']) == sorted(args.cells)
    print(json.dumps({'group': args.group, 'cells': [{k: r[k] for k in
        ('id', 'diagnosis', 'disposition', 'protocol', 'contamination', 'verdict')} for r in verdict['cells']]}))
