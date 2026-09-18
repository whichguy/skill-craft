#!/usr/bin/env python3
"""Study-local bounded independent judges; no variant mapping is supplied."""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import time

p = argparse.ArgumentParser()
p.add_argument('--study', type=Path, required=True)
p.add_argument('--families', default='f1,f2,f3,f4')
p.add_argument('--repetition', type=int, default=0)
a = p.parse_args()
s = a.study.resolve()
state = json.loads((s/'study.json').read_text())
spec = importlib.util.spec_from_file_location('bounded_review', s/'frozen/review_runner.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
families = a.families.split(',')
assert families and len(families) == len(set(families)) and set(families) <= {'f1','f2','f3','f4'}
prior = sum(sum(c.get('elapsed_seconds', 0) for c in json.loads(f.read_text()).get('contexts', [])) for f in s.glob('arms/*/run/metadata.json'))
prior += sum(json.loads(f.read_text()).get('elapsed_monotonic_seconds', 0) for f in s.glob('reviews/*/transport/result.json'))
assert prior + len(families)*180 <= state['aggregate_active_limit_seconds'], 'aggregate elapsed reserve exhausted'
assert time.time() < state['hard_deadline_epoch'], 'study hard deadline expired'

def run(family):
    packet = s/f'blind/{family}-r{a.repetition}/ready-to-evaluate.md'
    assert packet.is_file()
    root = s/f'reviews/{family}-r{a.repetition}'
    root.mkdir(parents=True, exist_ok=False)
    cwd = root/'empty-workspace'
    cwd.mkdir()
    final = root/'verdict.md'
    command = ['codex','exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','--json',
               '--disable','shell_tool','--disable','unified_exec','-s','read-only','-C',str(cwd),'-o',str(final),
               '-c','web_search="disabled"','-c','features.shell_tool=false','-c','features.unified_exec=false',
               '-c','tools.enabled_tools=[]','-c','tools.disabled_tools=["exec_command","write_stdin","apply_patch","shell","web_search"]','-']
    (root/'input-manifest.json').write_text(json.dumps({'path':str(packet),'sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),
        'default_model':True,'timeout_seconds':180,'hard_deadline_epoch':state['hard_deadline_epoch'],
        'prior_measured_subprocess_seconds':prior},indent=2)+'\n')
    result = m.run_bounded(command,cwd,root/'transport',180,state['hard_deadline_epoch'],packet)
    parsed = None
    error = None
    if result['success']:
        try:
            raw=final.read_text().strip()
            if raw.startswith('```'):
                raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
            parsed=json.loads(raw)
            assert parsed['winner'] in ('Left','Right','Tie','Inconclusive')
            assert type(parsed['material_improvement']) is bool
            assert set(parsed['arms']) == {'Left','Right'}
            (root/'verdict.json').write_text(json.dumps(parsed,indent=2)+'\n')
        except Exception as exc:
            error=f'{type(exc).__name__}: {exc}'
    summary={'family':family,'repetition':a.repetition,'transport_status':result['status'],
             'elapsed_seconds':result['elapsed_monotonic_seconds'],'parsed':parsed is not None and error is None,'parse_error':error,
             'winner':parsed.get('winner') if isinstance(parsed,dict) else None,
             'material_improvement':parsed.get('material_improvement') if isinstance(parsed,dict) else None}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
    return summary

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(run,families))
raise SystemExit(0 if all(x['transport_status']=='success' and x['parsed'] for x in results) else 1)
