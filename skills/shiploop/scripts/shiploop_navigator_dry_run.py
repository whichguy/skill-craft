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


def _improve_receipt(stage):
    """Synthetic child result for protocol-v3 traversal only.

    It never starts Improve, Until Loop, checks, or a project process.  The
    pure navigator API consumes this declaration to exercise its handoff edge.
    """
    return {
        'summary': f'Synthetic Improve completion for {stage}.',
        'review_refs': [f'synthetic://review/{stage}'],
        'check_refs': [f'synthetic://check/{stage}'],
        'lessons': f'Synthetic retained lesson for {stage}.',
    }


def activity_v3(*, two=False):
    """Explicit producer/Improve declarations for the v3 graph.

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


def _v3_insert_before(rows, stage, command, extra):
    """Insert declarations before the first matching v3 row."""
    index = next(i for i, row in enumerate(rows) if row['at'] == stage and row['command'] == command)
    rows[index:index] = extra
    return rows


def _v3_scenarios():
    """V3/v4 declarations: most producers advance without an Improve child."""
    activity = activity_v3
    repeat = _v3_insert_before(activity(), 'plan', 'finish-improve', [
        {'at': 'plan', 'command': 'finish-improve', 'receipt': _improve_receipt('plan'),
         'final_result': {'outcome': 'repeat', 'summary': 'More investigation needed.'},
         'expect': 'plan'},
        {'at': 'plan', 'command': 'produce', 'expect': 'plan',
         'result': {'outcome': 'done', 'summary': 'Synthetic second attempt.'}},
    ])
    paused = _v3_insert_before(activity(), 'test-author', 'produce', [
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


def scenarios(protocol_version=2):
    if protocol_version in (3, 4):
        # v3/v4 always instantiate skill-validate and ignore carry-forward work
        # items, so the protocol-2 'skill' and 'corrective-work' shapes have no
        # equivalent here; run() reports them as unavailable for this protocol.
        return _v3_scenarios()
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


def _owner(state):
    """Name the serialized cursor owner without creating another cursor schema."""
    if state.get('navigator_protocol_version') in (2, 3, 4) and state.get('stage') == 'inner-loop':
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


def run_scenario(name, scenario, *, protocol_version=2, delegation=None):
    report = {'name': name, 'simulation_only': True, 'ok': False, 'events': []}
    try:
        if not isinstance(scenario, dict):
            raise ValueError('scenario must be an object')
        rows = scenario.get('steps')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            raise ValueError('scenario needs 1..1000 explicit steps')
        state = navigator.new_state(
            '/simulation-only/repo',
            'Inspect the SDLC graph with synthetic declarations.',
            protocol_version=protocol_version,
            **({'improve_skill': '', 'delegation': delegation} if protocol_version in (3, 4) else {}),
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
    # Choices span every protocol; run() rejects a name the selected protocol lacks.
    names = dict.fromkeys(name for version in (2, 3) for name in scenarios(version))
    selected.add_argument('--scenario', choices=('all', *names), default='all')
    selected.add_argument('--script', help='JSON activity with explicit expected stages and synthetic result declarations')
    parser.add_argument('--format', choices=('summary', 'json', 'markdown'), default='summary')
    parser.add_argument('--protocol-version', choices=(2, 3, 4), type=int, default=3,
                        help='navigator protocol to simulate; default follows public navigator v3')
    parser.add_argument('--delegation', choices=navigator.DELEGATIONS, default=None,
                        help='protocol 3/4 execution delegation to simulate; default follows new runs (inline)')
    parser.add_argument('--list', action='store_true')


def run(args):
    if args.protocol_version not in (3, 4) and args.delegation is not None:
        print('Graph dry-run input error: --delegation requires protocol 3 or 4')
        return 2
    if args.list:
        print('\n'.join(scenarios(args.protocol_version)))
        return 0
    try:
        if args.script:
            selected = {'custom': json.loads(Path(args.script).read_text(encoding='utf-8'))}
        else:
            choices = scenarios(args.protocol_version)
            if args.scenario != 'all' and args.scenario not in choices:
                raise ValueError(
                    f"scenario {args.scenario!r} is not available for protocol "
                    f"{args.protocol_version}; available: {', '.join(choices)}")
            selected = choices if args.scenario == 'all' else {args.scenario: choices[args.scenario]}
        delegation = (args.delegation or navigator.DEFAULT_DELEGATION
                      if args.protocol_version in (3, 4) else None)
        reports = [run_scenario(name, value, protocol_version=args.protocol_version,
                                delegation=delegation)
                   for name, value in selected.items()]
    except (OSError, ValueError) as exc:
        print(f'Graph dry-run input error: {exc}')
        return 2
    if args.format == 'json':
        print(json.dumps({'simulation_only': True, 'protocol_version': args.protocol_version,
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
