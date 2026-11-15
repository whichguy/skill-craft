#!/usr/bin/env python3
"""Render source-bound hermetic receipts, including failed and incomplete work."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess

import suite_catalog

ROOT = Path(__file__).resolve().parents[1]


def escape(value):
    # HTML entities prevent Markdown links, tables, mentions and raw HTML in data.
    value = html.escape(str(value), quote=True).replace('\n', ' ').replace('\r', ' ')
    return re.sub(r'([\\`*_{}\[\]()#+.!|@~>-])', lambda m: '&#%d;' % ord(m[0]), value)


def selection_ids(groups, changed=()):
    return [s.id for s in suite_catalog.select(groups, changed)]


def targeted_ids(changed):
    return suite_catalog.targeted(changed)


def selection_counts(groups, changed=(), change_scope_available=True):
    groups = tuple(groups)
    changed = tuple(changed)
    selected = {s.id for s in suite_catalog.select(groups, changed)}
    smoke = {s.id for s in suite_catalog.smoke()}
    targeted = suite_catalog.targeted(changed)
    # Count selected full-only targets too: 'affected' is a reporting scope,
    # while the affected CLI remains the quick-minus-smoke execution scope.
    affected = targeted - smoke
    quick = {s.id for s in suite_catalog.quick(changed)}
    is_quick = bool(set(groups) & {'quick', 'quick-1', 'quick-2'})
    return {
        'selected': len(selected), 'executions': sum(len(selection_ids([g], changed)) for g in dict.fromkeys(groups)),
        'smoke': len(selected & smoke),
        'affected': len(selected & affected) if change_scope_available else 'UNAVAILABLE',
        'other_selected': len(selected - smoke - affected),
        'deferred_targeted': len(targeted - selected) if change_scope_available else 'UNAVAILABLE',
        'deferred_policy': len(targeted - quick) if is_quick else 0,
        'not_in_this_shard': len(quick - selected) if is_quick else 0,
    }


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid duration')
    return value


def render(receipt, expected_sha, group, job_status, expected_base=None, expected_changes=None):
    """Return (Markdown, success). A claimed pass alone is never sufficient."""
    if not isinstance(receipt, dict) or receipt.get('schema') != 'skill-craft-hermetic-receipt/1':
        raise ValueError('invalid receipt schema')
    source = receipt.get('source')
    if not isinstance(source, dict):
        raise ValueError('missing or invalid source object')
    if source['head'] != expected_sha or not expected_sha:
        raise ValueError('stale receipt: source SHA mismatch')
    if source.get('status') != []:
        raise ValueError('receipt source checkout was not clean')
    if receipt['groups'] != [group]:
        raise ValueError('receipt group mismatch')
    selected, completed = receipt.get('selected'), receipt.get('completed')
    if not isinstance(selected, list) or not isinstance(completed, list):
        raise ValueError('invalid selected/completed records')
    if not all(isinstance(r, dict) for r in selected + completed):
        raise ValueError('invalid selected/completed objects')
    ids = [r['id'] for r in selected]
    done = [r['id'] for r in completed]
    if not ids or not all(isinstance(i, str) for i in ids + done):
        raise ValueError('invalid suite ids')
    if len(set(ids)) != len(ids) or len(set(done)) != len(done) or not set(done) <= set(ids):
        raise ValueError('duplicate or unexpected completed suite')
    changed = receipt['changed']
    if not isinstance(changed, list) or not all(isinstance(p, str) for p in changed):
        raise ValueError('invalid change paths')
    if expected_base is not None and receipt.get("changed_from") != (expected_base or None):
        raise ValueError("receipt change base differs from planned base")
    if expected_changes is not None and changed != list(expected_changes):
        raise ValueError("receipt changes differ from independently derived planned range")
    actual = selection_ids([group], changed)
    if ids != actual:
        raise ValueError('receipt selection differs from source catalog')
    for record in completed:
        seconds(record['duration_seconds'])
        if record['status'] not in {'passed', 'failed', 'timed_out'}:
            raise ValueError('invalid suite status')
        if isinstance(record['returncode'], bool) or (
                not isinstance(record['returncode'], int) and record['returncode'] is not None):
            raise ValueError('invalid return code')
    failures = [r for r in completed if r['status'] != 'passed' or r['returncode'] != 0]
    missing = [i for i in ids if i not in set(done)]
    status = receipt['status']
    if status not in {'passed', 'failed', 'running'}:
        raise ValueError('invalid receipt status')
    wall = receipt.get('wall_seconds')
    if wall is not None:
        seconds(wall)
    success = status == 'passed' and not failures and not missing and wall is not None and job_status == 'success'
    label = 'PASSED' if success else 'FAILED / INCOMPLETE'
    counts = selection_counts([group], changed, change_scope_available=expected_base != "")
    lines = [f'### Hermetic {escape(group)}: {label}', '',
             f'Source SHA: {escape(expected_sha)}', '',
             f'Job: {escape(job_status)}; receipt: {escape(status)}; selected/completed: {len(ids)}/{len(done)}.', '',
             'Scopes: ' + '; '.join(f'{escape(k)}: {v}' for k, v in counts.items()) + '.', '',
             f'Wall duration: {wall if wall is not None else "unavailable (unfinished)"} seconds.', '',
             'Runtimes: ' + escape(json.dumps(receipt['runtimes'], sort_keys=True)), '',
             'Failures: ' + (', '.join(escape(r['id']) + ' (' + escape(r['status']) + ')' for r in failures) or 'none recorded'), '',
             'Incomplete: ' + (', '.join(escape(i) for i in missing) or 'none'), '', 'Slowest completed suites:', '']
    for r in sorted(completed, key=lambda r: -r['duration_seconds'])[:5]:
        lines.append(f"- {escape(r['id'])}: {r['duration_seconds']:.3f} seconds")
    lines.extend(['', 'Scope is hermetic qualification; it does not establish live acceptance.', ''])
    return '\n'.join(lines), success


def independent_changes(base):
    from run_suites import changed_paths
    return changed_paths(ROOT, base) if base else ()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--group', required=True)
    parser.add_argument('--job-status', required=True)
    parser.add_argument('--base', required=True, help='Planner base, empty for full runs')
    args = parser.parse_args(argv)
    try:
        expected_changes = independent_changes(args.base)
        report, success = render(json.loads(args.receipt.read_text()), args.expected_sha, args.group,
                                 args.job_status, expected_base=args.base, expected_changes=expected_changes)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.CalledProcessError) as exc:
        report = (f'### Hermetic {escape(args.group)}: FAILED / INCOMPLETE\n\n'
                  f'Missing or invalid receipt: {escape(exc)}\n\n'
                  f'Expected SHA: {escape(args.expected_sha)}; job: {escape(args.job_status)}.\n')
        success = False
    print(report)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
        output.write(report + '\n')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
