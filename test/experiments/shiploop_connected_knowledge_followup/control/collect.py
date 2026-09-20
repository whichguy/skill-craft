#!/usr/bin/env python3
"""Submit the exact sampled result to its run, then inspect real local collection."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def rewrite(value, old, new):
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [rewrite(x, old, new) for x in value]
    if isinstance(value, dict):
        return {k: rewrite(v, old, new) for k, v in value.items()}
    return value


def main(sample):
    sample = sample.resolve()
    case, package = sample/'case', sample/'package'
    run, workspace = case/'run', case/'workspace'
    result_file = workspace/'RESULT.json'
    protected = {str(workspace): files(workspace), str(case/'receipts.jsonl'): sha(case/'receipts.jsonl')}
    result_digest = sha(result_file)
    result = json.loads(result_file.read_text())
    sys.path.insert(0, str(package/'scripts'))
    import shiploop_navigator as navigator
    import shiploop_store as store
    import shiploop_planning_context as collector
    assert Path(navigator.__file__).resolve().is_relative_to(package)
    state = store.read_record(run/'state.md')
    assert navigator.current_stage(state) == 'discovery'
    # render_packet creates synthetic prelude state but saves only its last record.
    # Materialize those setup records before submitting the real sampled result.
    for entry in state['history']:
        previous = state['accepted'][entry['action']]
        assert previous['summary'].startswith('Synthetic'), 'Only synthetic prelude repair is allowed'
        path = run/'results'/(entry['action']+'.md')
        if not path.exists():
            store.write_record(path, {'navigator_protocol_version': 3,
                'run_id': state['run_id'], 'action': entry['action'],
                'stage': entry['stage'], 'workitem': entry['workitem'], 'result': previous})
    action = navigator.current_action(state)['id']
    receipt = {'summary': 'Synthetic transport setup only; no Improve execution.',
               'review_refs': [], 'check_refs': [], 'lessons': 'No review or workflow-completion claim.'}
    waiting = navigator.apply(state, action, result)
    navigator.save(run, waiting)
    state = navigator.finish_improve(waiting, action, receipt)
    navigator.save(run, state)
    assert sha(result_file) == result_digest
    assert state['accepted'][action] == result, 'Do not repair or augment sampled result'
    while navigator.current_stage(state) != 'implement':
        stage, aid = navigator.current_stage(state), navigator.current_action(state)['id']
        seed = {'outcome': 'done', 'summary': 'Synthetic transport setup; no stage work claimed.', 'evidence_refs': []}
        if stage == 'plan':
            seed['work_items'] = [{'id': 'W1', 'title': 'Conditional retry UI',
                                  'context': 'Use the actual discovery evidence and preserve its unresolved implementation prerequisites.'}]
        state = navigator.finish_improve(navigator.apply(state, aid, seed), aid, receipt)
        navigator.save(run, state)
        assert sha(result_file) == result_digest
    navigator.save(run, state)
    graph = {'version': 1, 'steps': [{'id': 'A', 'deps': [], 'contract': {'task': 'Read actual discovery evidence and form a conditional plan.'}}]}
    graph_path = case/'graph.json'
    put(graph_path, graph)
    graph_source = {'path': str(graph_path), 'sha256': sha(graph_path)}
    before = files(run)
    collected = collector.collect(run, state, graph, graph_source)
    assert before == files(run), 'Collection must be read-only'
    out = sample/'transport'
    put(out/'collection.json', {k:v for k,v in collected.items() if k != 'files'})
    for rel, content in collected['files'].items():
        path = run/rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content) if isinstance(content, str) else path.write_bytes(content)
    required = [workspace/'DISCOVERY.md', workspace/'BASELINE.txt', case/'receipts.jsonl']
    rows = {row['path']: row for row in collected['manifest']['artifacts']}
    matched = {str(path): bool(str(path) in rows and 'evidence-reference' in rows[str(path)]['roles']
                              and any(r['action'] == action for r in rows[str(path)].get('references', []))
                              and rows[str(path)]['sha256'] == sha(path)) for path in required}
    negative = sample/'negative-case'
    shutil.copytree(case, negative)
    negative_state = rewrite(copy.deepcopy(state), str(case), str(negative))
    for path in (negative/'run/results').glob('*.md'):
        store.write_record(path, rewrite(store.read_record(path), str(case), str(negative)))
    navigator.save(negative/'run', negative_state)
    (negative/'receipts.jsonl').unlink()
    negative_collection = collector.collect(negative/'run', negative_state, graph,
        {'path': str(negative/'graph.json'), 'sha256': sha(negative/'graph.json')})
    put(out/'negative-missing-receipt.json', negative_collection['missing_required'])
    diagnostics = negative_collection['missing_required']
    caught = bool(diagnostics) and all(row['kind'] == 'reference' and
        row.get('text', '').split('#')[0] == str(negative/'receipts.jsonl') for row in diagnostics)
    assert protected == {str(workspace): files(workspace), str(case/'receipts.jsonl'): sha(case/'receipts.jsonl')}
    checks = {'discovery_action': action, 'result_sha256': result_digest, 'result_bytes_unchanged': sha(result_file) == result_digest,
              'accepted_result_unchanged': state['accepted'][action] == result,
              'required_artifacts': matched, 'missing_required': collected['missing_required'],
              'negative_missing_receipt_detected': caught, 'producer_inputs_unchanged': True,
              'limits': 'Real apply/save/collect; all Improve and intervening stages synthetic. No full workflow claim.'}
    put(out/'checks.json', checks)
    print(json.dumps(checks, indent=2))
    if collected['missing_required'] or not all(matched.values()) or not caught:
        raise SystemExit('PARTIAL: preserve producer result; transport prerequisites are not all proven')
    print(collected['manifest']['briefing']['path'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', type=Path, required=True)
    main(parser.parse_args().sample)
