"""Drive the actual navigator with synthetic declarations, never project work."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import shiploop_navigator as navigator

# Independently declared expected paths: do not derive these from routing code.
BEFORE3 = 'intake discovery research spec test-strategy plan prepare'.split()
WORK3 = ('select-work step-plan test-spec baseline test-author test-red implement test-green '
         'test-refine regression document skill-assess skill-validate static-checks verify '
         'integrate integration-verify carry-forward').split()
AFTER3 = ('system-test-author system-test product-acceptance release-plan release-check '
          'release release-verify operations handoff').split()
# Stages whose result starts an Improve child, besides the last carry-forward.
# Declared independently of the navigator's tables.
REVIEWED3 = {'spec', 'test-strategy', 'plan', 'step-plan', 'test-spec',
             'system-test-author', 'release-plan'}
SCOPE = 'SIMULATION ONLY: actual navigator routes and packets; no project work, checks, commits, or delivery performed.'
CORE = SimpleNamespace(PACKAGE_ROOT=Path(__file__).resolve().parents[1],
                       REF_DIR=Path(__file__).resolve().parents[1] / 'references')
RUN = Path('/simulation-only/.shiploop')


def _improve_receipt(stage):
    """Synthetic child result for graph traversal only.

    It never starts Improve, Until Loop, checks, or a project process.  The
    pure navigator API consumes this declaration to exercise its handoff edge.
    """
    return {
        'summary': f'Synthetic Improve completion for {stage}.',
        'review_refs': [f'synthetic://review/{stage}'],
        'check_refs': [f'synthetic://check/{stage}'],
        'lessons': f'Synthetic retained lesson for {stage}.',
    }


def activity(*, two=False):
    """Explicit producer/Improve declarations for the navigator graph.

    Improve follows only the planning stages and the last item's carry-forward.
    """
    path = BEFORE3 + WORK3 * (2 if two else 1) + AFTER3
    last_carry = len(path) - 1 - path[::-1].index('carry-forward')
    rows = []
    for index, (stage, target) in enumerate(zip(path, path[1:] + ['done'])):
        if stage not in REVIEWED3 and index != last_carry:
            rows.append({'at': stage, 'command': 'produce', 'expect': target,
                         'result': {'outcome': 'done',
                                    'summary': 'Synthetic declaration; no work executed.'},
                         'status': 'done' if target == 'done' else 'active'})
            continue
        producer = {'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}
        if stage == 'step-plan':
            producer['test_commands'] = [
                {'command': 'python3 -m unittest discover -s tests', 'suite': 'focused'},
            ]
        if stage == 'plan' and two:
            producer['work_items'] = [
                {'id': 'W1', 'title': 'First fixture'},
                {'id': 'W2', 'title': 'Second fixture'},
            ]
        rows.append({'at': stage, 'command': 'produce', 'expect': stage,
                     'result': producer, 'status': 'active'})
        rows.append({'at': stage, 'command': 'finish-improve', 'expect': target,
                     'receipt': _improve_receipt(stage),
                     'status': 'done' if target == 'done' else 'active'})
    return rows


def _insert_before(rows, stage, command, extra):
    """Insert declarations before the first matching row."""
    index = next(i for i, row in enumerate(rows) if row['at'] == stage and row['command'] == command)
    rows[index:index] = extra
    return rows


def scenarios():
    """Declarations for protocol 4: most producers advance without an Improve child."""
    repeat = _insert_before(activity(), 'plan', 'finish-improve', [
        {'at': 'plan', 'command': 'finish-improve', 'receipt': _improve_receipt('plan'),
         'final_result': {'outcome': 'repeat', 'summary': 'More investigation needed.'},
         'expect': 'plan'},
        {'at': 'plan', 'command': 'produce', 'expect': 'plan',
         'result': {'outcome': 'done', 'summary': 'Synthetic second attempt.'}},
    ])
    paused = _insert_before(activity(), 'test-author', 'produce', [
        {'at': 'test-author', 'command': 'pause', 'expect': 'test-author', 'status': 'paused'},
        {'at': 'test-author', 'command': 'resume', 'expect': 'test-author'},
    ])
    return {
        'delivery': {'steps': activity()},
        'two-work-items': {'steps': activity(two=True)},
        'blocked-resume': {
            'steps': [
                {'at': 'intake', 'result': {
                    'outcome': 'blocked', 'summary': 'Synthetic prerequisite missing.'},
                 'command': 'produce', 'expect': 'intake', 'status': 'blocked'},
                {'at': 'intake', 'command': 'resume', 'expect': 'intake'},
                *activity(),
            ],
        },
        'repeat-improve': {'steps': repeat},
        'pause-resume': {'steps': paused},
        'halted': {'steps': [{'at': 'intake', 'command': 'halt', 'expect': 'intake', 'status': 'halted'}]},
    }


def _owner(state):
    """Name the serialized cursor owner without creating another cursor schema."""
    if state.get('stage') == 'inner-loop':
        return state['work_items'][state['work_index']]['id']
    return 'root'


def _completed_instances(state):
    """Expose only durable completed-instance evidence in synthetic reports."""
    loops = state.get('inner_loops', {})
    return [
        item['id']
        for item in state['work_items']
        if loops.get(item['id']) == {'stage': 'done', 'action': None}
    ]


def run_scenario(name, scenario, *, delegation=navigator.DEFAULT_DELEGATION):
    report = {'name': name, 'simulation_only': True, 'ok': False, 'events': []}
    try:
        if not isinstance(scenario, dict):
            raise ValueError('scenario must be an object')
        extra = sorted(set(scenario) - {'steps'})
        if extra:
            raise ValueError('scenario has unsupported fields: ' + ', '.join(extra))
        rows = scenario.get('steps')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            raise ValueError('scenario needs 1..1000 explicit steps')
        state = navigator.new_state(
            '/simulation-only/repo',
            'Inspect the SDLC graph with synthetic declarations.',
            improve_skill='', delegation=delegation,
        )
        for index, step in enumerate(rows, 1):
            if not isinstance(step, dict) or not {'at', 'expect'} <= set(step):
                raise ValueError('each step needs at and expect')
            current_stage = navigator.current_stage(state)
            current_action = navigator.current_action(state)
            if current_stage != step['at']:
                raise ValueError(f"event {index}: expected current {step['at']}, got {current_stage}")
            row = {
                'sequence': index,
                'simulation_only': True,
                'from': current_stage,
                'owner': _owner(state),
                'expected': step['expect'],
                'prompt': navigator.render(CORE, RUN, state),
            }
            report['events'].append(row)
            command = step.get('command', 'done')
            if command == 'produce':
                state = navigator.apply(state, current_action['id'], step.get('result', {
                    'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}))
            elif command == 'finish-improve':
                state = navigator.finish_improve(
                    state, current_action['id'], step.get('receipt'),
                    step.get('final_result'))
            elif command == 'done':
                state = navigator.apply(state, current_action['id'], step.get('result', {
                    'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}))
            elif command in ('pause', 'resume', 'halt'):
                state = navigator.control(state, command, 'Synthetic control event.')
            else:
                raise ValueError(f'unknown synthetic command: {command}')
            next_stage = navigator.current_stage(state)
            row.update(
                command=command,
                to=next_stage,
                next_owner=_owner(state),
                completed_instances=_completed_instances(state),
                status=state['status'],
            )
            if next_stage != step['expect'] or state['status'] != step.get('status', 'active'):
                raise ValueError(f"event {index}: expected {step['expect']}/{step.get('status', 'active')}, got {next_stage}/{state['status']}")
        report.update(
            ok=True,
            simulated_status=state['status'],
            completed_instances=_completed_instances(state),
        )
    except (ValueError, KeyError, TypeError) as exc:
        report['error'] = str(exc)
    return report


def add_arguments(parser):
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument('--scenario', choices=('all', *scenarios()), default='all')
    selected.add_argument('--script', help='JSON activity with explicit expected stages and synthetic result declarations')
    parser.add_argument('--format', choices=('summary', 'json', 'markdown'), default='summary')
    parser.add_argument('--delegation', choices=navigator.DELEGATIONS, default=None,
                        help='execution delegation to simulate; default follows new runs (inline)')
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
        delegation = args.delegation or navigator.DEFAULT_DELEGATION
        reports = [run_scenario(name, value, delegation=delegation)
                   for name, value in selected.items()]
    except (OSError, ValueError) as exc:
        print(f'Graph dry-run input error: {exc}')
        return 2
    if args.format == 'json':
        print(json.dumps({'simulation_only': True, 'protocol_version': navigator.PROTOCOL_VERSION,
                          'scope': SCOPE, 'scenarios': reports}, indent=2))
    else:
        print(SCOPE)
        for report in reports:
            print(f"\n{'PASS' if report['ok'] else 'FAIL'} {report['name']}: {len(report['events'])} events; simulated status: {report.get('simulated_status', 'mismatch')}")
            if args.format == 'markdown':
                for row in report['events']:
                    print(f"\n## {row['sequence']}. {row['owner']}: {row['from']} -> {row.get('to', 'ERROR')}\n\n{row['prompt']}")
            if report.get('error'):
                print(report['error'])
    return 0 if all(report['ok'] for report in reports) else 1
