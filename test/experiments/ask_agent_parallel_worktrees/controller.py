#!/usr/bin/env python3
"""External experimental operator. Starts only the Grok parent; never its workers."""
import argparse
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic, report_check_diagnostics

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def launch(run, grok_binary=None, model='grok-4.7', effort='medium'):
    run = Path(run).resolve()
    op = run / 'operator'
    prompt = op / 'parent-prompt.txt'
    if not prompt.is_file():
        raise ValueError('Missing reviewed parent prompt')
    if (op / 'launch.json').exists():
        raise ValueError('Existing attempt; preserve it and use a new run')
    (op/'launch-attempt').mkdir()  # Atomic reservation; failed launches are retained.
    executable = grok_binary or shutil.which('grok')
    if not executable:
        raise ValueError('Grok is unavailable; install/configure it separately before a live run')
    grok = Path(executable).resolve(strict=True)
    version = subprocess.run([str(grok), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    session = str(uuid.uuid4())
    argv = [str(grok), '--cwd', str(run / 'caller'), '--prompt-file', str(prompt),
            '--verbatim', '--output-format', 'streaming-json', '--model', model,
            '--reasoning-effort', effort, '--session-id', session, '--always-approve']
    started = time.time()
    started_clock = time.monotonic()
    identity = {'session_id': session, 'argv': argv, 'cwd': str(run / 'caller'),
                'started_epoch': started, 'model': model, 'reasoning_effort': effort, 'version': version,
                'binary_sha256': hashlib.sha256(grok.read_bytes()).hexdigest(),
                'prompt_sha256': hashlib.sha256(prompt.read_bytes()).hexdigest(),
                'manifest_sha256': hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest(),
                'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    identity['apparatus_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (op/name for name in ('fixture.py','operations.py','probe-fixture.py','native_trace.py','suite.py','controller.py','diagnostics.py','CONTRACT.md','prompts.py','treatment.json','briefs.py','worker_phase.py')) if p.exists()}
    inspect_result = subprocess.run([str(grok),'--cwd',str(run/'caller'),'inspect','--json'],capture_output=True,text=True)
    if inspect_result.returncode == 0:
        try:
            config=json.loads(inspect_result.stdout)
            write_json(op/'host-profile.json',{k:config.get(k) for k in ('grokVersion','cwd','projectRoot','projectTrusted','hooks','plugins','externalCompat')})
        except ValueError:
            write_json(op/'host-profile.json',{'status':'unparseable'})
    write_json(op / 'launch.json', identity)
    print(json.dumps({'launched': session, 'run': str(run)}), flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GROK_DISABLE_AUTOUPDATER='1')
    identity['environment_overrides']={'PYTHONDONTWRITEBYTECODE':'1','GROK_DISABLE_AUTOUPDATER':'1'}
    with (op / 'stdout.jsonl').open('w') as raw, (op / 'stderr.log').open('w') as err, (op / 'observed.jsonl').open('w') as observed:
        process = subprocess.Popen(argv, cwd=run / 'caller', stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=err, text=True, env=env)
        identity['pid'] = process.pid
        write_json(op / 'launch.json', identity)
        for line in process.stdout:
            now = time.time()
            raw.write(line); raw.flush()
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = {'unparsed': line.rstrip()}
            observed.write(json.dumps({'observed_epoch': now, 'elapsed_s': time.monotonic()-started_clock, 'event': event}) + '\n')
            observed.flush()
        code = process.wait()
    finished = time.time()
    elapsed = time.monotonic()-started_clock
    write_json(op / 'process-result.json', {'exit_code': code, 'finished_epoch': finished, 'elapsed_s': elapsed})
    exports=[]
    for name, args in [('usage.txt', ['usage', session]), ('trace-export.json', ['trace', '--local', '--json', '--output', str(op / 'native-trace.tar.gz'), session])]:
        result = subprocess.run([str(grok), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True)
        (op / name).write_text(result.stdout + result.stderr)
        exports.append({'name':name,'exit_code':result.returncode})
    write_json(op/'export-results.json',exports)
    print(json.dumps({'finished': session, 'exit_code': code, 'elapsed_s': elapsed}), flush=True)
    return code

def verify_after_exit(run):
    """One immutable post-exit attempt; process, input integrity and files must pass."""
    run=Path(run).resolve();op=run/'operator'
    process_path=op/'process-result.json'
    if not process_path.is_file():
        raise ValueError(f'Parent has not exited: required evidence {process_path}')
    if any((op/name).exists() for name in ('post-exit-verification.json','integrity-result.json','post-exit-verify.log')):
        raise ValueError(f'Post-exit evidence already exists in {op}; preserve it and audit without replacing it')
    (op/'post-exit-attempt').mkdir()  # Includes failed attempts and concurrent callers.
    process=json.loads(process_path.read_text())
    if not isinstance(process,dict) or type(process.get('exit_code')) is not int:
        raise ValueError(f'Malformed process evidence: {process_path}; expected integer exit_code')
    process_ok=process['exit_code']==0
    launch=json.loads((op/'launch.json').read_text())
    integrity={}
    expected={'manifest.json':launch.get('manifest_sha256')}
    for name,digest in launch.get('apparatus_sha256',{}).items(): expected['operator/'+name]=digest
    expected['operator/parent-prompt.txt']=launch['prompt_sha256']
    for name,digest in expected.items():
        # Older exploratory trials explicitly lack this measurement; never invent it.
        if digest is not None:
            path=run/name
            integrity[name]=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest
    write_json(op/'integrity-result.json',{'passed':all(integrity.values()),'checks':integrity,
                                         'legacy_missing_manifest_hash':expected['manifest.json'] is None})
    if not all(integrity.values()):
        write_json(op/'post-exit-result.json',{'status':'FAIL','passed':False,'reason':'Frozen experiment inputs changed',
                                              'evidence':str(op/'integrity-result.json')})
        return 1
    verification=op/'verification.json'
    if verification.exists():
        shutil.copy2(verification,op/'parent-verification.json')
    frozen=op/'fixture.py'
    if not frozen.exists():frozen=op/'probe-fixture.py'
    if verification.exists():verification.unlink()  # Original retained as parent-verification.json.
    result=subprocess.run([sys.executable,'-B',str(frozen),'verify','--run',str(run)],capture_output=True,text=True)
    (op/'post-exit-verify.log').write_text(result.stdout+result.stderr)
    # A process returning zero without a new verdict cannot reuse parent evidence.
    filesystem_ok=False
    if verification.exists() and result.returncode==0:
        try:filesystem_ok=json.loads(verification.read_text()).get('passed') is True
        except (ValueError,AttributeError):pass
    if verification.exists():shutil.copy2(verification,op/'post-exit-verification.json')
    passed=process_ok and filesystem_ok and result.returncode==0
    report={'status':'PASS' if passed else 'FAIL','passed':passed,'parent_exit_code':process.get('exit_code'),
            'filesystem_passed':filesystem_ok,'verifier_exit_code':result.returncode,
            'evidence':[str(process_path),str(op/'integrity-result.json'),str(op/'post-exit-verify.log'),str(op/'post-exit-verification.json')]}
    write_json(op/'post-exit-result.json',report)
    print(json.dumps(report))
    return 0 if passed else 1

def inspect(run):
    run = Path(run)
    rows = []
    path = run / 'operator/observed.jsonl'
    if not path.exists():
        return {'status':'not launched'}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        event = row['event']
        p = event.get('params', {})
        update = p.get('update', event.get('update', event))
        kind = update.get('sessionUpdate', event.get('type', event.get('method','')))
        if kind in ('tool_call', 'tool_call_update', 'subagent_spawned', 'subagent_finished', 'end'):
            rows.append({'t':round(row['elapsed_s'],2), 'session':p.get('sessionId'), 'kind':kind,
                         'tool':update.get('title'), 'id':update.get('toolCallId'),
                         'status':update.get('status'), 'input':update.get('rawInput'),
                         'output':str(update.get('rawOutput',update.get('content','')))[:700]})
    return {'events':rows[-18:], 'count':len(rows), 'finished':(run/'operator/process-result.json').exists()}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['launch','inspect','verify'])
    parser.add_argument('--run', required=True)
    parser.add_argument('--grok-binary')
    parser.add_argument('--model', default='grok-4.7')
    parser.add_argument('--effort', choices=['low','medium','high'],default='medium')
    args = parser.parse_args(argv)
    try:
        if args.command == 'launch':code=launch(args.run,args.grok_binary,args.model,args.effort)
        elif args.command == 'verify':code=verify_after_exit(args.run)
        else:print(json.dumps(inspect(args.run),indent=2));return 0
        observed={'exit_code':code}
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        code=2;observed={'exception':type(exc).__name__,'detail':str(exc)}
    if code:
        op=Path(args.run).resolve()/'operator'
        record=make_diagnostic(code='CONTROLLER_PHASE_FAILED',severity='error',phase=args.command,
            expected='One valid launch attempt, terminal zero parent exit, unchanged frozen inputs and fresh passing post-exit evidence',
            observed=observed,rationale='Process success and final filesystem integrity are separate required gates; failures must remain visible.',
            rationale_ref='CONTRACT.md#proof-precedence',
            evidence=[evidence_reference(op/name) for name in ('launch.json','process-result.json','integrity-result.json','post-exit-result.json','post-exit-verify.log')],
            recovery='Read the cited records and exact stderr; preserve the failed attempt before starting another run.',
            retry_safety='Do not relaunch or repeat post-exit verification in the same run; read-only audit is permitted.')
        emit_diagnostics([record],jsonl_path=op/'controller-diagnostics.jsonl' if op.is_dir() else None)
    return code

if __name__ == '__main__':
    sys.exit(main())
