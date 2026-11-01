#!/usr/bin/env python3
"""Amendment A1's analyses (AMENDMENTS.md), run after `cohort.py analyze`: python3 a1_sensitivity.py COHORT_DIR

1. Packaging-normalized structure: plan_structure and plan_completion re-checked on a packaged copy of each attempt's
   artifacts/plan.json (lib.js packagePlan through the frozen check-plan.js; only parallel_groups changes), giving a
   packaging-normalized outcome and qualification.
2. The candidate-win blocks (qualification, mechanical keys, F7's pooled block) under both qualification definitions;
   a block under either blocks a candidate win.
3. The quality comparison without the dependency-logic criterion, with its own grader noise, and the decision under
   it; grader rows that mention parallel_groups, per arm.

It imports the frozen cohort.py and changes no frozen input. Writes COHORT_DIR/a1.json and a1.md.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

CRITERION = 'dependency-logic'


def runner(cohort_dir):
    spec = importlib.util.spec_from_file_location('cohort_runner', Path(cohort_dir) / 'cohort.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_outcome(c, case, row, scratch):
    """The attempt's registered outcome checks with plan_structure and plan_completion taken from a packaged copy."""
    out = c.COHORT.runs / row['label']
    summary = c.load_optional(out / 'summary.json') or {}
    checks = dict((summary.get('outcome') or {}).get('checks') or {})
    plan = c.load_optional(out / 'artifacts/plan.json')
    if not checks or plan is None:
        return None, None
    packaged = c.package(plan, c.COHORT, scratch)
    path = Path(tempfile.mkdtemp(dir=scratch)) / 'plan.json'
    c.save(path, packaged)
    structure = c.structural_check(path, c.COHORT, path.with_name('structure.json'))
    checks['plan_structure'] = 'pass' if structure['structure_ok'] else 'fail'
    checks['plan_completion'] = 'pass' if structure['completion'] == case['expected']['plan_completion'] else 'fail'
    return all(value in ('pass', 'n/a') for value in checks.values()), checks


def scores_without(c, row, passes):
    """Mean over passes of the score with CRITERION left out; None for an attempt with no plan (scored by rule)."""
    if not row['has_plan']:
        return [0.0] * passes
    values = []
    for number in range(1, passes + 1):
        verdict = c.load_optional(c.GRADES / ('p%d' % number) / (row['label'] + '.json'))
        if verdict and verdict.get('valid'):
            grades = {r['id']: r['grade'] for r in verdict['criteria'] if r['id'] != CRITERION}
            values.append(c.score(grades))
    return values


def mentions(c, rows, passes):
    found = {arm: 0 for arm in c.ARMS}
    for row in rows:
        for number in range(1, passes + 1):
            verdict = c.load_optional(c.GRADES / ('p%d' % number) / (row['label'] + '.json'))
            for item in (verdict or {}).get('criteria', []):
                text = json.dumps(item).lower()
                if 'parallel_groups' in text or 'parallel groups' in text:
                    found[row['arm']] += 1
    return found


def combine(registered, packaged):
    """A block under either qualification definition blocks a candidate win (stricter on the candidate)."""
    if registered['winner'] == 'candidate' and packaged['blocked']:
        return dict(packaged)
    return registered


def main(cohort_dir, passes=3):
    c = runner(cohort_dir)
    cases = {case['id']: case for case in c.COHORT.cases()}
    rows = [c.attempt_row(c.COHORT, c.GRADES, case, arm, rep, passes)
            for case in cases.values() for rep in c.REPETITIONS for arm in c.ARMS]
    explained = {arm: {'registered_failures': 0, 'pass_after_packaging': 0} for arm in c.ARMS}
    with tempfile.TemporaryDirectory(prefix='a1-') as scratch:
        for row in rows:
            ok, checks = normalized_outcome(c, cases[row['case']], row, Path(scratch))
            row['outcome_ok_packaged'] = bool(ok)
            row['qualified_packaged'] = bool(row['present'] and ok and row['graded_passes']
                                             and not row['critical_missed_by_majority'])
            if row['present'] and not row['outcome_ok']:
                explained[row['arm']]['registered_failures'] += 1
                explained[row['arm']]['pass_after_packaging'] += bool(ok)
    measured, noise = c.grader_noise(rows, passes)
    quality = c.paired(rows, 'score')
    tokens, seconds = c.paired(rows, 'input_plus_output_tokens'), c.paired(rows, 'wall_seconds')
    keys = c.paired(rows, 'key_rate', only=lambda r: r['heldout'])
    missing = sum(not r['present'] for r in rows)
    ungraded = sum(r['has_plan'] and r['graded_passes'] < passes for r in rows)
    cases_compared = quality['cases'] if quality else 0
    registered = c.decide(quality, tokens, seconds, noise, c.paired(rows, 'qualified'), keys, cases_compared,
                          missing, ungraded, c.family_block(rows))
    packaged_rows = [dict(r, qualified=r['qualified_packaged']) for r in rows]
    packaged = c.decide(quality, tokens, seconds, noise, c.paired(packaged_rows, 'qualified'), keys, cases_compared,
                        missing, ungraded, c.family_block(packaged_rows))
    combined = combine(registered, packaged)
    for row in rows:
        row['pass_scores_without'] = scores_without(c, row, passes)
        row['score_without'] = c.mean(row['pass_scores_without'])
    without_rows = [dict(r, score=r['score_without'], pass_scores=r['pass_scores_without']) for r in rows]
    measured_w, noise_w = c.grader_noise(without_rows, passes)
    quality_w = c.paired(without_rows, 'score')
    cases_w = quality_w['cases'] if quality_w else 0
    without = combine(
        c.decide(quality_w, tokens, seconds, noise_w, c.paired(rows, 'qualified'), keys, cases_w, missing, ungraded,
                 c.family_block(rows)),
        c.decide(quality_w, tokens, seconds, noise_w, c.paired(packaged_rows, 'qualified'), keys, cases_w, missing,
                 ungraded, c.family_block(packaged_rows)))
    report = {
        'schema': 'backchain-efficiency-a1/v1', 'amendment': 'AMENDMENTS.md A1',
        'packaging': {'qualified': {arm: {'registered': sum(r['qualified'] for r in rows if r['arm'] == arm),
                                          'packaged': sum(r['qualified_packaged'] for r in rows if r['arm'] == arm),
                                          'attempts': sum(r['arm'] == arm for r in rows)} for arm in c.ARMS},
                      'outcome_failures_explained_by_packaging': explained,
                      'paired_qualified_packaged': c.paired(packaged_rows, 'qualified'),
                      'family_block_packaged': c.family_block(packaged_rows)},
        'decisions': {'registered': registered, 'blocks_under_packaging': packaged, 'combined': combined,
                      'without_' + CRITERION: without},
        'robust_to_criterion': (without['winner'], without['decided_by']) == (combined['winner'],
                                                                                combined['decided_by']),
        'grader_noise_without_' + CRITERION: {'mean_pairwise_pass_difference': measured_w, 'bound': noise_w},
        'quality_without_' + CRITERION: quality_w,
        'grader_rows_mentioning_parallel_groups': mentions(c, rows, passes)}
    Path(cohort_dir, 'a1.json').write_text(json.dumps(report, indent=1) + '\n')
    lines = ['# Amendment A1 analyses', '',
             'Decision as registered: %s (%s).' % (registered['winner'], registered['decided_by']),
             'With the blocks also under packaging-normalized qualification: %s (%s)%s.' % (
                 combined['winner'], combined['decided_by'], ', blocked' if combined.get('blocked') else ''),
             'Without `%s`: %s (%s); robust: %s.' % (CRITERION, without['winner'], without['decided_by'],
                                                     report['robust_to_criterion']), '',
             '| Arm | Qualified (registered) | Qualified (packaged) | Registered outcome failures | of them pass once packaged |',
             '|-----|---:|---:|---:|---:|']
    for arm in c.ARMS:
        q, e = report['packaging']['qualified'][arm], explained[arm]
        lines.append('| %s | %d/%d | %d/%d | %d | %d |' % (arm, q['registered'], q['attempts'], q['packaged'],
                                                         q['attempts'], e['registered_failures'],
                                                         e['pass_after_packaging']))
    lines += ['', 'Grader rows mentioning parallel_groups: %s.' % report['grader_rows_mentioning_parallel_groups'], '',
              'Reasons (combined): ' + '; '.join(combined['reasons'])]
    Path(cohort_dir, 'a1.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:5]))


if __name__ == '__main__':
    main(sys.argv[1])
