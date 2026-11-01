#!/usr/bin/env python3
"""Post-hoc regrade R1 (AMENDMENTS.md A2): python3 regrade_r1.py COHORT_DIR

The registered grader packets, unchanged except that `parallel_groups` is removed from the final plan and from the
inherited draft, for both arms; three fresh passes with the same rubric, grader, model and effort, written to
COHORT_DIR/grades-r1/. Then the registered decision rule over those grades (cohort.py build_report), written to
COHORT_DIR/r1-analysis.json and r1-analysis.md. The registered grades/ and analysis.json are untouched.

`parallel_groups` is derived: lib.js computes it from the steps' inputs, which stay in the packet.
"""
import concurrent.futures
import json
import sys
from pathlib import Path

PASSES = 3


def runner(cohort_dir):
    import importlib.util
    spec = importlib.util.spec_from_file_location('cohort_runner', Path(cohort_dir) / 'cohort.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip(packet):
    for key in ('final_plan', 'inherited_draft'):
        if isinstance(packet.get(key), dict):
            packet[key] = {k: v for k, v in packet[key].items() if k != 'parallel_groups'}
    return packet


def main(cohort_dir):
    c = runner(cohort_dir)
    c.GRADES = Path(cohort_dir) / 'grades-r1'
    tasks = []
    for case in c.COHORT.cases():
        for rep in c.REPETITIONS:
            for arm in c.ARMS:
                label = c.attempt_label(case['id'], arm, rep)
                out = c.COHORT.runs / label
                if not (out / 'summary.json').is_file() or c.load_optional(out / 'artifacts/plan.json') is None:
                    continue
                packet = strip(c.attempt_packet(case, out))
                tasks += [(case, label, arm, rep, number, packet) for number in range(1, PASSES + 1)
                          if not (c.GRADES / ('p%d' % number) / (label + '.json')).is_file()]
    print('REGRADE R1: %d pending pass(es)' % len(tasks), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=c.GRADER_WORKERS) as pool:
        for future in concurrent.futures.as_completed([pool.submit(c.grade_one, *task) for task in tasks]):
            verdict = future.result()
            print('GRADED', verdict['label'], 'p%d' % verdict['pass'], 'valid=%s' % verdict['valid'],
                  'lowered=%d' % len(verdict['quote_check']['unverified']), flush=True)
    report = c.build_report(c.COHORT, c.GRADES, PASSES)
    report['regrade'] = 'R1: parallel_groups removed from final_plan and inherited_draft (AMENDMENTS.md A2)'
    mentions = {arm: 0 for arm in c.ARMS}
    for path in c.GRADES.glob('p*/*.json'):
        verdict = json.loads(path.read_text())
        for item in verdict.get('criteria') or []:
            if 'parallel_groups' in json.dumps(item).lower():
                mentions[verdict['arm']] += 1
    report['grader_rows_mentioning_parallel_groups'] = mentions
    Path(cohort_dir, 'r1-analysis.json').write_text(json.dumps(report, indent=1) + '\n')
    Path(cohort_dir, 'r1-analysis.md').write_text(c.render_markdown(report))
    print('R1 decision: %s (%s); %s' % (report['decision']['winner'], report['decision']['decided_by'],
                                        '; '.join(report['decision']['reasons'])), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
