"""Drive the actual navigator with synthetic declarations, never project work."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import shiploop_navigator as navigator

# Independently declared expected paths: do not derive these from routing code.
BEFORE = 'intake discovery research research-improve spec spec-improve test-strategy plan plan-improve'.split()
WORK = 'step-plan step-plan-improve implement test-refine test-author document verify product-improve integrate carry-forward'.split()
AFTER = 'system-test outer-improve release-plan release release-verify handoff'.split()
SCOPE = 'SIMULATION ONLY: actual navigator routes and packets; no project work, checks, commits, or delivery performed.'
CORE = SimpleNamespace(PACKAGE_ROOT=Path(__file__).resolve().parents[1],
                       REF_DIR=Path(__file__).resolve().parents[1] / 'references')
RUN = Path('/simulation-only/.shiploop')


def activity(*, two=False, skill=False):
    work = list(WORK)
    if skill:
        work.insert(work.index('verify'), 'skill-validate')
    path = BEFORE + work * (2 if two else 1) + AFTER
    rows = []
    for stage, target in zip(path, path[1:] + ['done']):
        result = {'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}
        if stage == 'plan' and two:
            result['work_items'] = [{'id': 'W1', 'title': 'First fixture'}, {'id': 'W2', 'title': 'Second fixture'}]
        if stage == 'document' and skill:
            result['choices'] = {'skill_required': True}
        rows.append({'at': stage, 'result': result, 'expect': target,
                     'status': 'done' if target == 'done' else 'active'})
    return rows


def scenarios():
    result = {name: {'steps': activity(**flags)} for name, flags in (
        ('delivery', {}), ('two-work-items', {'two': True}), ('skill', {'skill': True}))}
    repeat = activity()
    index = next(i for i, row in enumerate(repeat) if row['at'] == 'product-improve')
    repeat.insert(index, {'at': 'product-improve', 'result': {'outcome': 'repeat', 'summary': 'More investigation needed.'}, 'expect': 'product-improve'})
    result['repeat-improve'] = {'steps': repeat}
    for name, command, status in (('blocked-resume', 'blocked', 'blocked'), ('pause-resume', 'pause', 'paused')):
        rows = activity()
        index = next(i for i, row in enumerate(rows) if row['at'] == 'test-author')
        stop = {'at': 'test-author', 'expect': 'test-author', 'status': status}
        if command == 'blocked':
            stop['result'] = {'outcome': 'blocked', 'summary': 'Synthetic missing prerequisite.'}
        else:
            stop['command'] = command
        rows[index:index] = [stop, {'at': 'test-author', 'command': 'resume', 'expect': 'test-author'}]
        result[name] = {'steps': rows}
    result['halted'] = {'steps': [{'at': 'intake', 'command': 'halt', 'expect': 'intake', 'status': 'halted'}]}
    future = activity(two=True)
    first = next(row for row in future if row['at'] == 'carry-forward')
    first['result']['work_items'] = [{'id': 'W3', 'title': 'Newly discovered corrective work'}]
    result['corrective-work'] = {'steps': future}
    return result


def run_scenario(name, scenario):
    report = {'name': name, 'simulation_only': True, 'ok': False, 'events': []}
    try:
        if not isinstance(scenario, dict):
            raise ValueError('scenario must be an object')
        rows = scenario.get('steps')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            raise ValueError('scenario needs 1..1000 explicit steps')
        state = navigator.new_state('/simulation-only/repo', 'Inspect the SDLC graph with synthetic declarations.')
        for index, step in enumerate(rows, 1):
            if not isinstance(step, dict) or not {'at', 'expect'} <= set(step):
                raise ValueError('each step needs at and expect')
            if state['stage'] != step['at']:
                raise ValueError(f"event {index}: expected current {step['at']}, got {state['stage']}")
            row = {'sequence': index, 'from': state['stage'], 'expected': step['expect'],
                   'prompt': navigator.render(CORE, RUN, state)}
            report['events'].append(row)
            command = step.get('command', 'done')
            if command == 'done':
                state = navigator.apply(state, state['action']['id'], step.get('result', {
                    'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}))
            elif command in ('pause', 'resume', 'halt'):
                state = navigator.control(state, command, 'Synthetic control event.')
            else:
                raise ValueError(f'unknown synthetic command: {command}')
            row.update(command=command, to=state['stage'], status=state['status'])
            if state['stage'] != step['expect'] or state['status'] != step.get('status', 'active'):
                raise ValueError(f"event {index}: expected {step['expect']}/{step.get('status', 'active')}, got {state['stage']}/{state['status']}")
        report.update(ok=True, simulated_status=state['status'])
    except (ValueError, KeyError, TypeError) as exc:
        report['error'] = str(exc)
    return report


def add_arguments(parser):
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument('--scenario', choices=('all', *scenarios()), default='all')
    selected.add_argument('--script', help='JSON activity with explicit expected stages and synthetic result declarations')
    parser.add_argument('--format', choices=('summary', 'json', 'markdown'), default='summary')
    parser.add_argument('--list', action='store_true')


def run(args):
    if args.list:
        print('\n'.join(scenarios()))
        return 0
    try:
        if args.script:
            selected = {'custom': json.loads(Path(args.script).read_text(encoding='utf-8'))}
        else:
            choices = scenarios()
            selected = choices if args.scenario == 'all' else {args.scenario: choices[args.scenario]}
        reports = [run_scenario(name, value) for name, value in selected.items()]
    except (OSError, ValueError) as exc:
        print(f'Graph dry-run input error: {exc}')
        return 2
    if args.format == 'json':
        print(json.dumps({'simulation_only': True, 'scope': SCOPE, 'scenarios': reports}, indent=2))
    else:
        print(SCOPE)
        for report in reports:
            print(f"\n{'PASS' if report['ok'] else 'FAIL'} {report['name']}: {len(report['events'])} events; simulated status: {report.get('simulated_status', 'mismatch')}")
            if args.format == 'markdown':
                for row in report['events']:
                    print(f"\n## {row['sequence']}. {row['from']} -> {row.get('to', 'ERROR')}\n\n{row['prompt']}")
            if report.get('error'):
                print(report['error'])
    return 0 if all(report['ok'] for report in reports) else 1
