"""Launch the frozen R05 subjects; collect original output without interpreting behavior."""
from pathlib import Path
import concurrent.futures
import datetime
import hashlib
import json
import os
import shlex
import stat
import subprocess
import time

ROOT = Path(__file__).parent
REG = json.loads((ROOT / 'registration.json').read_text())
OUT = ROOT / 'baseline'
SOURCE = Path(REG['source']['path'])


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_identity():
    names = subprocess.check_output(['git', '-C', str(SOURCE), 'ls-files', '-z']).split(b'\0')
    files = {}
    for raw in names:
        if not raw:
            continue
        p = SOURCE / os.fsdecode(raw)
        data = os.fsencode(os.readlink(p)) if p.is_symlink() else p.read_bytes()
        files[os.fsdecode(raw)] = {'sha256': hashlib.sha256(data).hexdigest(),
                                 'mode': stat.S_IMODE(p.lstat().st_mode)}
    return {'head': subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD']).decode().strip(),
            'status': subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain=v1']).decode(),
            'files': files}


def environment(path):
    env = os.environ.copy()
    for line in path.read_text().splitlines():
        if line.startswith('export '):
            key, value = line[7:].split('=', 1)
            env[key] = shlex.split(value)[0]
        elif line.startswith('unset '):
            for key in line[6:].split():
                env.pop(key, None)
    return env


def run(cell):
    key = cell['id']
    folder = OUT / key
    folder.mkdir(parents=True, exist_ok=False)
    final = folder / 'native-final.md'
    events, errors = folder / 'events.jsonl', folder / 'stderr.log'
    neutral = ('Use only this package, its current run, and the ShipLoop/Improve resources the assignment names. '
               'Do not inspect other runs or operator analysis. Perform this assignment inline; start no advisors '
               'or child agents. Do not contact a real person or external service. An awaiting-person callback '
               'records the request; leave actual person observations unperformed.\n\n')
    prompt = neutral + Path(cell['assignment']).read_text()
    (folder / 'input.md').write_text(prompt)
    env = environment(Path(cell['environment_script']))
    argv = ['codex', 'exec', '--profile', 'shiploop', '--model', 'gpt-6.1-sol',
            '-c', 'model_reasoning_effort="medium"', '--sandbox', 'workspace-write',
            '--add-dir', str(Path(cell['run']).parent), '-C', cell['workspace'],
            '--json', '-o', str(final), '-']
    receipt = {'id': key, 'boundary': cell['boundary'], 'situation': cell['situation'],
               'repetition': cell['repetition'], 'source_sha': cell['source_sha'],
               'argv': argv, 'cwd': cell['workspace'], 'started_utc': stamp(),
               'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'environment': {k: env[k] for k in ('XDG_STATE_HOME', 'SHIPLOOP_KEEPALIVE_HOME',
                   'SHIPLOOP_PROGRESS', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE',
                   'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL')},
               'events': str(events), 'stderr': str(errors), 'final': str(final)}
    save(folder / 'launch.json', receipt)
    started = time.monotonic()
    with events.open('w') as out, errors.open('w') as err:
        p = subprocess.run(argv, cwd=cell['workspace'], env=env, input=prompt,
                           text=True, stdout=out, stderr=err, check=False)
    receipt.update(exit_code=p.returncode, ended_utc=stamp(),
                   wall_seconds=round(time.monotonic() - started, 3),
                   final_present=final.is_file() and bool(final.stat().st_size),
                   execution_status='COMPLETED' if p.returncode == 0 and final.is_file() and final.stat().st_size else 'INCOMPLETE',
                   semantic_status='NOT_JUDGED')
    save(folder / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('id', 'boundary', 'exit_code', 'wall_seconds', 'execution_status')}), flush=True)
    return receipt


if __name__ == '__main__':
    assert REG['status'] == 'REGISTERED' and REG['subjects'] == len(REG['cells']) == 16
    assert not OUT.exists(), 'Preserve original campaign output'
    OUT.mkdir()
    before = source_identity()
    assert before['head'] == REG['source']['sha'] and not before['status']
    save(OUT / 'source-pre.json', before)
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        receipts = list(pool.map(run, REG['cells']))
    after = source_identity()
    save(OUT / 'source-post.json', after)
    save(OUT / 'execution-summary.json', {'status': 'COLLECTED_NOT_JUDGED',
         'expected': 16, 'completed': len(receipts), 'receipts': receipts,
         'source_unchanged': before == after, 'wall_seconds': round(time.monotonic() - started, 3),
         'subject_retries': 0, 'semantic_outcome': 'NOT_JUDGED'})
    print(json.dumps({'collected': len(receipts), 'source_unchanged': before == after}), flush=True)
