"""Drive the actual navigator with synthetic declarations, never project work."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import shiploop_loops as stage_loops
import shiploop_navigator as navigator
import shiploop_stage_spec as stage_spec

# Independently declared expected paths: do not derive these from routing code.
BEFORE3 = 'intake discovery research spec test-strategy plan prepare'.split()
WORK3 = ('step-plan test-spec validate-existing implement test document verify '
         'carry-forward').split()
AFTER3 = ('system-test-author system-test product-acceptance release-plan release-check '
          'release release-verify operations handoff').split()
# Stages whose result starts an Improve stage, besides the last carry-forward, for each
# planning_review option.  Declared independently of the navigator's tables.  implement's
# per-step Improve runs in every mode (planning_review none does not skip it).
REVIEWED3 = {
    'stage': {'spec', 'test-strategy', 'plan', 'step-plan', 'test-spec', 'implement',
              'system-test-author', 'release-plan'},
    'none': {'implement', 'system-test-author', 'release-plan'},
}
SCOPE = 'SIMULATION ONLY: actual navigator routes and packets; no project work, checks, commits, or delivery performed.'
CORE = SimpleNamespace(PACKAGE_ROOT=Path(__file__).resolve().parents[1],
                       REF_DIR=Path(__file__).resolve().parents[1] / 'references')
RUN = Path('/simulation-only/.shiploop')


def _improve_receipt(stage: str) -> dict[str, Any]:
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


def activity(planning_review: str = 'stage', *, two: bool = False) -> list[dict[str, Any]]:
    """Explicit producer/Improve declarations for the navigator graph.

    Improve follows only the planning stages the option reviews, each implement step and the last
    item's carry-forward.
    """
    path = BEFORE3 + WORK3 * (2 if two else 1) + AFTER3
    last_carry = len(path) - 1 - path[::-1].index('carry-forward')
    rows = []
    for index, (stage, target) in enumerate(zip(path, path[1:] + ['done'])):
        status = 'done' if target == 'done' else 'active'
        producer = {'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}
        if stage == 'step-plan':
            producer['test_commands'] = [
                {'command': 'python3 -m unittest discover -s tests', 'suite': 'focused'},
            ]
            # One synthetic step, so implement's packet names it as a run's does.
            producer['steps'] = [{'id': 'S1', 'task': 'Synthetic step; no work executed.', 'deps': [],
                                  'proof': 'python3 -m unittest discover -s tests'}]
        if stage == 'plan' and two:
            producer['work_items'] = [
                {'id': 'W1', 'title': 'First fixture'},
                {'id': 'W2', 'title': 'Second fixture'},
            ]
        # Rule first-item (2026-10-19): step-plan and test-spec are reviewed for the first work item only (a sent-back
        # item's redo too; no scenario here sends one back), so the second item's advance without a child.
        later_item = stage in stage_spec.with_improve('first-item') and path[:index + 1].count('step-plan') > 1
        if (stage not in REVIEWED3[planning_review] or later_item) and index != last_carry:
            rows.append({'at': stage, 'command': 'produce', 'expect': target,
                         'result': producer, 'status': status})
            continue
        # Every reviewed stage is followed by its own Improve stage in the sequence (owner, 2026-10-11).
        rows.append({'at': stage, 'command': 'produce', 'expect': navigator.IMPROVE_STAGE,
                     'result': producer, 'status': 'active'})
        rows.append({'at': navigator.IMPROVE_STAGE, 'command': 'finish-improve', 'expect': target,
                     'receipt': _improve_receipt(stage), 'status': status})
    return rows


def _insert_before(rows: list[dict[str, Any]], stage: str, command: str,
                   extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insert declarations before the first matching row."""
    index = next(position for position, row in enumerate(rows) if row['at'] == stage and row['command'] == command)
    rows[index:index] = extra
    return rows


def scenarios(planning_review: str = 'stage') -> dict[str, list[dict[str, Any]]]:
    """Declarations for protocol 4: most producers advance without an Improve stage."""
    paused = _insert_before(activity(planning_review), 'test', 'produce', [
        {'at': 'test', 'command': 'pause', 'expect': 'test', 'status': 'paused'},
        {'at': 'test', 'command': 'resume', 'expect': 'test'},
    ])
    # implement finds the step plan unachievable: the item goes back to
    # step-plan and walks its planning and test stages again.
    base = activity(planning_review)
    send_back_rows = []
    for row in base[base.index(next(candidate for candidate in base if candidate['at'] == 'step-plan')):]:
        if row['at'] == 'implement':
            break
        send_back_rows.append(dict(row))
    revised = _insert_before(base, 'implement', 'produce', [
        {'at': 'implement', 'command': 'produce', 'expect': 'step-plan',
         'result': {'outcome': 'send-back', 'summary': 'Synthetic: a completion criterion is unachievable as planned.'}},
        *send_back_rows,
    ])
    return {
        'delivery': {'steps': activity(planning_review)},
        'two-work-items': {'steps': activity(planning_review, two=True)},
        'blocked-resume': {
            'steps': [
                {'at': 'intake', 'result': {
                    'outcome': 'blocked', 'summary': 'Synthetic prerequisite missing.', 'awaiting': {'kind': 'service', 'service': 'synthetic prerequisite', 'check': 'true', 'no_default': 'Synthetic: the prerequisite is outside this run.'}},
                 'command': 'produce', 'expect': 'intake', 'status': 'blocked'},
                {'at': 'intake', 'command': 'resume', 'expect': 'intake', 'observed': 'Synthetic: the check exited 0.'},
                *activity(planning_review),
            ],
        },
        'send-back': {'steps': revised},
        'pause-resume': {'steps': paused},
        'halted': {'steps': [{'at': 'intake', 'command': 'halt', 'expect': 'intake', 'status': 'halted'}]},
    }


def _owner(state: Mapping[str, Any]) -> str:
    """Name the serialized cursor owner without creating another cursor schema."""
    if state.get('stage') == 'inner-loop':
        return state['work_items'][state['work_index']]['id']
    return 'root'


def _completed_instances(state: Mapping[str, Any]) -> list[Any]:
    """Expose only durable completed-instance evidence in synthetic reports."""
    loops = state.get('inner_loops', {})
    return [
        item['id']
        for item in state['work_items']
        if loops.get(item['id']) == {'stage': 'done', 'action': None}
    ]


def run_scenario(name: str, scenario: Any, *, delegation: str = navigator.DEFAULT_DELEGATION,
                 backchain_passes: str = navigator.DEFAULT_BACKCHAIN_PASSES,
                 planning_review: str = navigator.DEFAULT_PLANNING_REVIEW) -> dict[str, Any]:
    """Simulate one scenario (no work is executed) and return its report: events, stages reached and ``ok``."""
    report = {'name': name, 'simulation_only': True, 'ok': False, 'events': []}
    try:
        if not isinstance(scenario, dict):
            raise ValueError(f'scenario {name!r} must be an object, got {type(scenario).__name__}')
        extra = sorted(set(scenario) - {'steps'})
        if extra:
            raise ValueError('scenario has unsupported fields: ' + ', '.join(extra))
        rows = scenario.get('steps')
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            raise ValueError('scenario needs 1..1000 explicit steps')
        state = navigator.new_state(
            '/simulation-only/repo',
            'Inspect the SDLC graph with synthetic declarations.',
            # What `init` records: the improve card installed beside ShipLoop.  The real bundled card, so every inner
            # packet resolves its Until Loop runtime and shows the RUN until-loop block, as a run's packet does.
            improve_skill=str(stage_loops.BUNDLED_IMPROVE_CARD), delegation=delegation, backchain_passes=backchain_passes,
            planning_review=planning_review,
        )
        for index, step in enumerate(rows, 1):
            if not isinstance(step, dict) or not {'at', 'expect'} <= set(step):
                raise ValueError('each step needs at and expect')
            current_stage = navigator.sequence_stage(state)
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
                    state, state['active_improve']['action_id'], step.get('receipt'),
                    step.get('final_result'))
            elif command == 'done':
                state = navigator.apply(state, current_action['id'], step.get('result', {
                    'outcome': 'done', 'summary': 'Synthetic declaration; no work executed.'}))
            elif command in ('pause', 'resume', 'halt'):
                state = navigator.control(state, command, 'Synthetic control event.',
                                          **({'observed': step['observed']} if 'observed' in step else {}))
            else:
                raise ValueError(f'unknown synthetic command: {command}')
            next_stage = navigator.sequence_stage(state)
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


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the dry-run options to ``parser``."""
    selected = parser.add_mutually_exclusive_group()
    selected.add_argument('--scenario', choices=('all', *scenarios()), default='all')
    selected.add_argument('--script', help='JSON activity with explicit expected stages and synthetic result declarations')
    parser.add_argument('--format', choices=('summary', 'json', 'markdown'), default='summary')
    parser.add_argument('--delegation', choices=navigator.DELEGATIONS, default=None,
                        help='execution delegation to simulate; default follows new runs (inline)')
    parser.add_argument('--backchain-passes', choices=navigator.BACKCHAIN_PASSES_MODES, default=None,
                        help='Backchain passes option to simulate; default follows new runs (one)')
    parser.add_argument('--planning-review', choices=navigator.PLANNING_REVIEW_MODES, default=None,
                        help='planning review option to simulate; default follows new runs (stage)')
    parser.add_argument('--list', action='store_true')


def run(args: argparse.Namespace) -> int:
    """Run the selected scenarios or the ``--script`` activity and print the report; returns the exit code."""
    if args.list:
        print('\n'.join(scenarios()))
        return 0
    try:
        if args.script:
            selected = {'custom': json.loads(Path(args.script).read_text(encoding='utf-8'))}
        else:
            choices = scenarios(args.planning_review or navigator.DEFAULT_PLANNING_REVIEW)
            selected = choices if args.scenario == 'all' else {args.scenario: choices[args.scenario]}
        delegation = args.delegation or navigator.DEFAULT_DELEGATION
        backchain_passes = args.backchain_passes or navigator.DEFAULT_BACKCHAIN_PASSES
        planning_review = args.planning_review or navigator.DEFAULT_PLANNING_REVIEW
        reports = [run_scenario(name, value, delegation=delegation, backchain_passes=backchain_passes,
                                planning_review=planning_review)
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
