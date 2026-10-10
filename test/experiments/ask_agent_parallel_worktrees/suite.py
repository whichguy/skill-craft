#!/usr/bin/env python3
"""Repeatable explicit-opt-in live suites for the Ask Agent worktree experiment."""
import argparse
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic, report_check_diagnostics

import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent

# The functional hold is deliberately separate from throughput comparisons.
SUITES = {
    'smoke': [('parallel3',3,'parallel','baseline',0)],
    'functional': [('overlap3',3,'parallel','baseline',20), ('parallel5',5,'parallel','baseline',0)],
    'timing': [('parallel3-a',3,'parallel','baseline',0), ('sequential3-a',3,'sequential','baseline',0),
               ('parallel5-a',5,'parallel','baseline',0), ('parallel5-b',5,'parallel','baseline',0),
               ('sequential3-b',3,'sequential','baseline',0), ('parallel3-b',3,'parallel','baseline',0)],
    'optimization': [('baseline3-a',3,'parallel','baseline',0), ('batched3-a',3,'parallel','batched',0),
                     ('batched5-a',5,'parallel','batched',0), ('baseline5-a',5,'parallel','baseline',0),
                     ('baseline5-b',5,'parallel','baseline',0), ('batched5-b',5,'parallel','batched',0),
                     ('batched3-b',3,'parallel','batched',0), ('baseline3-b',3,'parallel','baseline',0)],
    'scripted': [('baseline3-a',3,'parallel','baseline',0), ('scripted3-a',3,'parallel','scripted',0),
                 ('baseline5-a',5,'parallel','baseline',0), ('scripted5-a',5,'parallel','scripted',0),
                 ('sequential3-a',3,'sequential','scripted',0), ('sequential3-b',3,'sequential','scripted',0),
                 ('scripted5-b',5,'parallel','scripted',0), ('baseline5-b',5,'parallel','baseline',0), ('scripted3-b',3,'parallel','scripted',0),
                 ('baseline3-b',3,'parallel','baseline',0)],
    'packet': [('packet3-a',3,'parallel','packet',0), ('packet5-a',5,'parallel','packet',0),
               ('sequential3',3,'sequential','packet',0), ('packet3-b',3,'parallel','packet',0)],
    'compact': [('compact3-a',3,'parallel','compact',0), ('compact5-a',5,'parallel','compact',0),
                ('compact3-b',3,'parallel','compact',0), ('compact5-b',5,'parallel','compact',0),
                ('compact-sequential3',3,'sequential','compact',0)],
    'compact-comparison': [('compact3-a',3,'parallel','compact',0),
                           ('baseline3-a',3,'parallel','baseline',0),
                           ('baseline3-b',3,'parallel','baseline',0),
                           ('compact3-b',3,'parallel','compact',0),
                           ('compact5-a',5,'parallel','compact',0)],
}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=['harness', *SUITES], default='harness')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--live', action='store_true', help='Explicitly permit paid model calls and local fixture writes')
    parser.add_argument('--case', help='Run one named case from the chosen suite')
    parser.add_argument('--skill-root', type=Path)
    parser.add_argument('--seed-feedback-backlog', action='store_true', help='Explicit fixture variant for the observed async-suite SessionEnd hook')
    parser.add_argument('--grok-binary')
    parser.add_argument('--model', default='grok-4.7')
    parser.add_argument('--effort', default='medium')
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps({'harness':'offline deterministic fixture and evidence tests', **SUITES}, indent=2));return 0
    if args.suite == 'harness':
        return subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT),'-p','test_*.py','-v']).returncode
    if not args.live:
        parser.error('Live suites require --live; listing and harness checks never launch a model')
    if not args.output:
        parser.error('--output must name a new retained experiment directory')
    cases = SUITES[args.suite]
    if args.case:
        cases = [c for c in cases if c[0] == args.case]
        if not cases:
            parser.error('Unknown case for this suite')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    campaign = {'suite': args.suite, 'model': args.model, 'effort': args.effort,
                'seed_feedback_backlog':args.seed_feedback_backlog,
                'seed_compact_ignore_controls':args.suite in ('compact','compact-comparison'),
                'started_epoch':time.time(), 'status':'RUNNING',
                'cases':[{'name':c[0],'status':'NOT_RUN'} for c in cases]}
    campaign_path = output/'suite-result.json'
    def save():
        campaign_path.write_text(json.dumps(campaign,indent=2)+'\n')
    save()
    for case_index,(name,n,mode,treatment,hold) in enumerate(cases):
        run = output/name
        commands = [
            [sys.executable,'-B',str(ROOT/'fixture.py'),'prepare','--run',str(run),'--workers',str(n),'--mode',mode,'--hold-seconds',str(hold)],
            [sys.executable,'-B',str(ROOT/'prompts.py'),'--run',str(run),'--workers',str(n),'--mode',mode,'--treatment',treatment],
            [sys.executable,'-B',str(ROOT/'controller.py'),'launch','--run',str(run),'--model',args.model,'--effort',args.effort],
            [sys.executable,'-B',str(ROOT/'controller.py'),'verify','--run',str(run)],
            [sys.executable,'-B',str(run/'operator/native_trace.py'),'--run',str(run)],
        ]
        if args.skill_root:
            commands[0] += ['--skill-root',str(args.skill_root.resolve())]
        if args.seed_feedback_backlog:
            commands[0] += ['--seed-feedback-backlog']
        seed_compact_ignore_controls = treatment == 'compact' or args.suite == 'compact-comparison'
        if seed_compact_ignore_controls:
            commands[0] += ['--seed-compact-ignore-controls']
        if args.grok_binary:
            commands[2] += ['--grok-binary',args.grok_binary]
        record = {'name':name,'workers':n,'mode':mode,'treatment':treatment,
                  'hold_seconds':hold,'seed_compact_ignore_controls':seed_compact_ignore_controls,
                  'seed_feedback_backlog':args.seed_feedback_backlog,
                  'run':str(run),'commands':[],'status':'RUNNING'}
        campaign['cases'][case_index]=record;save()
        failed=False
        log_dir=output/'logs'/name
        log_dir.mkdir(parents=True)
        for step,command in enumerate(commands):
            log_path=log_dir/f'{step+1:02d}.log'
            print(json.dumps({'case':name,'phase':step+1,'log':str(log_path)}),flush=True)
            began=time.monotonic()
            try:
                with log_path.open('x') as log:
                    result = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
                command_result={'argv':command,'exit_code':result.returncode,'elapsed_s':time.monotonic()-began,'evidence':str(log_path)}
            except (OSError,ValueError) as exc:
                command_result={'argv':command,'exit_code':None,'error':f'{type(exc).__name__}: {exc}','evidence':str(log_path)}
            record['commands'].append(command_result);save()
            if command_result['exit_code']!=0:
                failed=True
                # If launch failed after creating process evidence, still collect both diagnostics.
                if step<2 or (step==2 and not (run/'operator/process-result.json').exists()):
                    break
        try:
            verdict=json.loads((run/'operator/native-verification.json').read_text())
            strict_pass=isinstance(verdict,dict) and verdict.get('status')=='PASS' and verdict.get('passed') is True
            record['status']='PASS' if strict_pass and not failed else ('INCOMPLETE' if verdict.get('status') in ('INCOMPLETE','UNKNOWN') else 'FAIL')
        except (OSError,ValueError,AttributeError) as exc:
            record['status']='INCOMPLETE'
            record['error']=f'Missing or invalid native verdict: {type(exc).__name__}: {exc}'
        save()
        if record['status']!='PASS':
            campaign['status']=record['status'];campaign['finished_epoch']=time.time();save()
            emit_diagnostics([make_diagnostic(code='SUITE_CASE_NOT_ACCEPTED',severity='error',phase='suite',expected='Every selected case has exact PASS and passed=true evidence with zero phase exits',observed=record,rationale='Incomplete or contradictory records must not be promoted to a successful campaign.',rationale_ref='CONTRACT.md#pass-gates',evidence=[evidence_reference(campaign_path,json_pointer=f'/cases/{case_index}')],recovery='Inspect phase logs and retained native/filesystem reports.',retry_safety='Later cases remain NOT_RUN; use a new output directory after reconciliation.')],jsonl_path=output/'diagnostics.jsonl')
            print('Stopped after unsuccessful case. Evidence retained; later cases remain NOT_RUN.',flush=True)
            return 1
    campaign['status']='PASS';campaign['finished_epoch']=time.time();save()
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError) as exc:
        emit_diagnostics([make_diagnostic(code='SUITE_OPERATION_FAILED',severity='error',phase='suite',expected='A new writable output directory and valid suite inputs',observed={'exception':type(exc).__name__,'detail':str(exc)},rationale='Reusing or failing to persist a campaign would lose attempt identity.',rationale_ref='CONTRACT.md#retry-safety',evidence=[],recovery='Choose a new retained directory and inspect the exception.',retry_safety='Do not overwrite previous campaigns.')])
        sys.exit(2)
