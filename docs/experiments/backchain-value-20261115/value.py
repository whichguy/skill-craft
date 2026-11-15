#!/usr/bin/env python3
"""Backchain value study, 2026-11-15 (PROTOCOL.md): Backchain 0.7.0 against the same model planning without the skill.

  value.py freeze              snapshot the released skill and the cases; write freeze.json
  value.py run [--pilot]       the attempts, one lane per model (--pilot: one case, both arms, three models)
  value.py grade [--pilot]     blind Opus grading, two passes per attempt
  value.py analyze [--pilot]   analysis.json and analysis.md
  value.py check               the runner's own checks (no model calls)

Results go under $VALUE_RESULTS (default /Users/dadleet/src/backchain/results/backchain-value-20261115). The workspace
layout, the Backchain arm's prompt, the caller packet, the redactor, the rubric, the grade parser and the statistics are
the 2026-11 cohort's (cohort.py, imported by path); the hosts are the E2E harness's (test/shiploop_e2e/hosts.py).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_CRAFT = HERE.parents[2]
COHORT_DIR = Path('/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort')
RESULTS = Path(os.environ.get('VALUE_RESULTS', '/Users/dadleet/src/backchain/results/backchain-value-20261115'))
ASK = Path('/Users/dadleet/src/grok-build-additions/skills/ask/scripts/ask.sh')
sys.path.insert(0, str(SKILL_CRAFT / 'test' / 'shiploop_e2e'))
import hosts as H  # noqa: E402


def _cohort():
    spec = importlib.util.spec_from_file_location('cohort', COHORT_DIR / 'cohort.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = _cohort()

# Amendment A2 (pilot): Grok's `auto` refused the subject's own `cp`/`rm` in its workspace ("a headless run cannot ask
# for approval"), so Grok and Claude run with bypassPermissions, as Codex runs with danger-full-access; each workspace
# is a throwaway temporary directory and the prompt forbids network, contact and other models.
PERMISSION_MODE = 'bypassPermissions'
MODELS = {  # owner, 2026-11-15: "Grok 4.6 on extra high, GPT Sol 6.1 on medium, and Sonnet 5.5 on high"
    'grok': ('grok', 'grok-4.6', 'xhigh'),
    'sol': ('codex', 'gpt-6.1-sol', 'medium'),
    'sonnet': ('claude', 'claude-sonnet-5-5', 'high'),
}
ARMS = ('backchain', 'none')
PILOT_CASE = 'stale-build-receipt-identity'
SUBJECT_DEADLINE = 1800
GRADER_EFFORT = 'medium'
PASSES = (1, 2)
GRADE_RETRIES = 3
GRADER_WORKERS = 3
SEED = 'backchain-value-20261115'
DELTA = 5.0  # the owner's acceptable-loss margin, D-C (2026-11-01)

TERMINAL_DISPOSITION = (
    'Completion reflects planning evidence. Missing planning prerequisites remain planning gaps; future approvals may '
    'remain execution blockers. A stop is correct when it names a gap the plan cannot close; the plan and its final '
    'status do not claim unsupported completion.')
CRITERIA_OVERRIDES = {  # PROTOCOL.md "Criteria", study changes 2 and 3 (owner decision D-B, 2026-11-01)
    ('orders-cancel-rpc', 'store-split-from-docs'): (
        'Either S3 consumes a separately checkable supplier of store.Store.SetStatus and its store.Memory '
        'implementation that excludes the docs/api.md work, with no dependency path to the API-reference deliverable '
        '(S2 or a docs step); or the plan keeps the inherited S2 whole and names that bundling as an open planning gap, '
        'instead of silently ordering S3 after the docs work.'),
    ('orders-cancel-rpc', 'bundle-claim-consistent'): (
        'If a store supplier is split out, S2, whose inherited produce still names both deliverables, consumes it, so '
        'the SetStatus work is not planned twice; a plan that keeps S2 whole and names the gap satisfies this.'),
}

NONE_INPUT_LINES = {
    'fresh': 'This is a fresh planning request.',
    'draft': ('Elaborate the supplied inherited-plan.json as an existing draft. Do not regenerate it; preserve its '
              'IDs, input edges (including inputs from initial_state), goal_needs and confirmations.'),
    'source': ('caller.json is the planning packet for this request: its edit_bounds say which parts of the inherited '
               'plan may change, and its sources and requirements are the governing material.'),
}


# ---------------------------------------------------------------- files and freeze

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Campaign:
    def __init__(self, pilot: bool):
        self.root = RESULTS / ('pilot' if pilot else 'study')
        self.runs, self.grades = self.root / 'runs', self.root / 'grades'
        self.pilot = pilot

    def cases(self):
        cases = C.load(RESULTS / 'cases.json')['cases']
        return [case for case in cases if case['id'] == PILOT_CASE] if self.pilot else cases


# Amendments A1 and A3a (pilot): both arms get plan-format.md, a hand-written restatement of the released SKILL.md's
# "Plan document shape" and "Structural invariants" with no tool or procedure name. The first build copied the shape
# section verbatim: it omitted the invariants (the no-skill Sonnet plan broke only invariant 7) and it named `check`,
# `freeze` and `record`, which sent the no-skill Grok subject looking for those tools in a sibling workspace.
PLAN_FORMAT = HERE / 'plan-format.md'
TOOLKIT_TRACES = ('resources/skills/backchain', 'skills/backchain/', 'backchain.py', 'backchain_graph.py',
                  'until_loop_ephemeral', 'check_preservation.py')
WORKSPACE_ROOT_MODE = 0o300  # A3b: the owner may create and enter workspaces but cannot list the root's siblings


def freeze(rev: str) -> dict:
    """Snapshot skills/backchain and the bundled Until Loop at `rev`, the cases and plan-format.md; refuse a second."""
    if (RESULTS / 'freeze.json').exists():
        raise SystemExit(f'{RESULTS}/freeze.json exists; this study is frozen')
    commit = subprocess.run(['git', '-C', str(SKILL_CRAFT), 'rev-parse', rev + '^{commit}'], check=True,
                            capture_output=True, text=True).stdout.strip()
    snapshot = RESULTS / 'snapshot'
    data = subprocess.run(['git', '-C', str(SKILL_CRAFT), 'archive', commit, *C.SKILL_TREES], check=True,
                          capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(snapshot, filter='data')
    shutil.copyfile(PLAN_FORMAT, snapshot / 'plan-format.md')
    shutil.copyfile(COHORT_DIR / 'cases.json', RESULTS / 'cases.json')
    versions = {}
    for name, (host_name, _, _) in MODELS.items():
        host = H.host(host_name)
        versions[name] = host.cli_version(host.env(Path(tempfile.mkdtemp(prefix='value-version-'))))
    record = {
        'schema': 'backchain-value-freeze/v1', 'frozen_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'skill_craft_commit': commit, 'models': MODELS, 'arms': ARMS, 'passes': PASSES, 'delta': DELTA,
        'cli_versions': versions,
        'sha256': {
            'cases.json': digest((RESULTS / 'cases.json').read_bytes()),
            'plan-format.md': digest((snapshot / 'plan-format.md').read_bytes()),
            'value.py': digest(Path(__file__).read_bytes()),
            'PROTOCOL.md': digest((HERE / 'PROTOCOL.md').read_bytes()),
            'cohort.py': digest((COHORT_DIR / 'cohort.py').read_bytes()),
            'grader-rubric.md': digest(C.GRADER_RUBRIC.read_bytes()),
            'hosts.py': digest((SKILL_CRAFT / 'test/shiploop_e2e/hosts.py').read_bytes()),
            **{sub: C.tree_digest(snapshot / sub) for sub in C.SKILL_TREES},
        }}
    C.save(RESULTS / 'freeze.json', record)
    return record


def verify_freeze() -> dict:
    record = C.load(RESULTS / 'freeze.json')
    now = {'cases.json': digest((RESULTS / 'cases.json').read_bytes()),
           'value.py': digest(Path(__file__).read_bytes()),
           'PROTOCOL.md': digest((HERE / 'PROTOCOL.md').read_bytes())}
    changed = [name for name, value in now.items() if record['sha256'][name] != value]
    if changed:
        raise SystemExit('changed since the freeze: ' + ', '.join(changed))
    return record


# ---------------------------------------------------------------- workspaces and prompts

_ROOT = []


def workspace_root() -> Path:
    """One root for this process's workspaces that nobody can list (A3b): a subject that walks up from its workspace
    sees the root's name but not the other attempts beside it, the Backchain arm's resources among them."""
    if not _ROOT:
        root = Path(tempfile.mkdtemp(prefix='value-ws-'))
        root.chmod(WORKSPACE_ROOT_MODE)
        _ROOT.append(root)
    return _ROOT[0]


def setup(case: dict, arm: str) -> Path:
    """The cohort's workspace (cohort.py setup), with plan-format.md in both arms and resources/ only in backchain."""
    snapshot = RESULTS / 'snapshot'
    ws = Path(tempfile.mkdtemp(prefix=C.WORKSPACE_PREFIX, dir=workspace_root()))  # one prefix: the redactor treats both arms alike
    (ws / 'artifacts').mkdir()
    for name, content in case['files'].items():
        C.save(ws / 'fixture' / name, content)
    C.save(ws / 'request.md', case['request'])
    shutil.copyfile(snapshot / 'plan-format.md', ws / 'plan-format.md')
    for sub in C.SKILL_TREES:
        shutil.copytree(snapshot / sub, ws / 'resources' / sub, symlinks=True)
    if case['draft'] is not None:
        C.save(ws / 'inherited-plan.json', case['draft'])
    packet = C.caller_packet(case, ws)
    if arm == 'none':
        shutil.rmtree(ws / 'resources')
        if packet:
            packet.pop('selection', None)
    if packet:
        C.save(ws / 'caller.json', packet)
    return ws


def none_prompt(case: dict) -> str:
    mode = case['input_mode']
    inputs = [name for name in C.read_only_inputs(case) if name != 'resources/'] + ['plan-format.md']
    return '\n'.join([
        'Plan the request in request.md as a dependency-aware plan. Paths are relative to the workspace root, your '
        'working directory.',
        '',
        'Write the plan in the JSON shape plan-format.md describes. '
        + NONE_INPUT_LINES['source' if mode.startswith('source_') else mode],
        '',
        'Constraints: planning only; do not implement or run the planned product. ' + ', '.join(inputs[:-1])
        + ' and ' + inputs[-1] + ' are read-only. No network access, no contact with people or services, no '
        'subagents and no other models. All writes belong under artifacts/.',
        '',
        'Final destinations:',
        '- artifacts/plan.json: the final plan',
        '- artifacts/result.json: {"status": "complete" or "incomplete", "planning_gaps": [...], '
        '"execution_blockers": [...]}. A planning gap is a missing prerequisite, source or authority the plan cannot '
        'close; an execution blocker is a future approval or prerequisite the plan models but cannot satisfy now. '
        'The status is complete only when no planning gap remains.',
        ''])


WORKSPACE_ONLY = 'Constraints: planning only; use only the files in this workspace, and do not read, search or run files outside it;'


def prompt_for(case: dict, arm: str) -> str:
    text = C.prompt_for(case) if arm == 'backchain' else none_prompt(case)
    assert text.count('Constraints: planning only;') == 1
    return text.replace('Constraints: planning only;', WORKSPACE_ONLY)


# ---------------------------------------------------------------- hosts

def subject_env(host, home: Path) -> dict:
    env = host.env(home)
    if host.name == 'claude':  # a nested launch must not inherit this session's identity
        env = {k: v for k, v in env.items() if not k.startswith(('CLAUDECODE', 'CLAUDE_CODE_'))}
    return env


def call(model: str, ws: Path, prompt: str, out: Path) -> dict:
    host_name, model_id, effort = MODELS[model]
    host = H.host(host_name)
    home = Path(tempfile.mkdtemp(prefix='value-home-'))
    env = subject_env(host, home)
    argv = host.argv(prompt=prompt, prompt_file=out / 'prompt.md', cwd=ws, model=model_id, effort=effort,
                     permission_mode=PERMISSION_MODE, max_turns=None)
    C.save(out / 'argv.json', argv)
    meta = H.run_agent(argv, ws, env, out / 'events.jsonl', out / 'stderr.log', SUBJECT_DEADLINE, host.translator())
    return dict(meta, host=host_name, model=model_id, effort=effort)


def session_tokens(usage, host):
    """test/shiploop_e2e/metrics.py session_tokens (copied): (processed, output); Codex counts cache reads inside input."""
    def count(key):
        value = usage.get(key) if isinstance(usage, dict) else None
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    given, output = count('input_tokens'), count('output_tokens')
    if given is None or output is None:
        return None, output
    cached = 0 if host == 'codex' else (count('cache_read_input_tokens') or 0) + (count('cache_creation_input_tokens') or 0)
    return given + cached + output, output


def usage_of(events: Path, host: str) -> dict:
    """The session's usage: the last usage object the stream carries (each host's final result line holds the total)."""
    last = None
    for line in events.read_text(errors='replace').splitlines() if events.is_file() else []:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        stack = [event]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if isinstance(node.get('usage'), dict) and 'output_tokens' in node['usage']:
                    last = node['usage']
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
    processed, output = session_tokens(last, host)
    return {'processed_tokens': processed, 'output_tokens': output, 'usage': last}


# ---------------------------------------------------------------- attempts

def check(plan: Path) -> dict:
    """The released backchain.py check of the delivered plan: structure and completion."""
    info = {'present': plan.is_file(), 'json': False, 'structure_ok': False, 'completion': None}
    if not info['present']:
        return info
    try:
        json.loads(plan.read_text())
        info['json'] = True
    except ValueError:
        return info
    cli = str(RESULTS / 'snapshot/skills/backchain/scripts/backchain.py')
    packaged = Path(tempfile.mkdtemp(prefix='value-check-')) / 'packaged.json'  # A3d: derived parallel_groups recomputed
    subprocess.run([sys.executable, '-I', '-B', cli, 'package', str(plan), '--out', str(packaged)],
                   capture_output=True, text=True, timeout=120)
    done = subprocess.run([sys.executable, '-I', '-B', cli, 'check', str(packaged if packaged.is_file() else plan)],
                          capture_output=True, text=True, timeout=120)
    try:
        receipt = json.loads(done.stdout)
    except ValueError:
        info['detail'] = (done.stdout + done.stderr)[-500:]
        return info
    info['structure_ok'] = bool(receipt.get('ok'))
    info['completion'] = receipt.get('completion')
    return info


def final_record(arm: str, path: Path) -> dict:
    """Each arm's final record, as one shape: status complete or incomplete, planning gaps, execution blockers."""
    value = C.load_optional(path)
    if not isinstance(value, dict):
        return {'status': 'no final record', 'planning_gaps': 'no final record', 'execution_blockers': 'no final record'}
    if arm == 'backchain':
        record = value.get('review') if isinstance(value.get('review'), dict) else value.get('convergence')
        record = record if isinstance(record, dict) else {}
        source = record.get('convergence') if isinstance(record.get('convergence'), dict) else record
        gaps = record.get('planning_gaps', source.get('planning_gaps'))
        blockers = record.get('execution_blockers', source.get('execution_blockers'))
        status = {'converged': 'complete', 'incomplete': 'incomplete'}.get(value.get('status'))
        if status is None:  # pilot 2: a subject may copy finish's {plan, convergence} without its top-level status
            receipt = source.get('terminal_receipt') if isinstance(source.get('terminal_receipt'), dict) else {}
            status = ('no status' if not receipt else 'complete'
                      if receipt.get('status') == 'complete' and gaps == [] else 'incomplete')
    else:
        gaps, blockers = value.get('planning_gaps'), value.get('execution_blockers')
        status = value.get('status') if value.get('status') in ('complete', 'incomplete') else 'no status'
    listed = lambda items: items if isinstance(items, list) else 'not recorded'  # noqa: E731
    return {'status': status, 'planning_gaps': listed(gaps), 'execution_blockers': listed(blockers)}


def label(case_id: str, arm: str, model: str) -> str:
    return f'{case_id}--{arm}--{model}'


def trial(campaign: Campaign, case: dict, arm: str, model: str) -> dict:
    out = campaign.runs / label(case['id'], arm, model)
    if out.exists():
        return C.load(out / 'summary.json') if (out / 'summary.json').is_file() else {'label': out.name}
    out.mkdir(parents=True)
    ws = setup(case, arm)
    print('START', out.name, ws, flush=True)
    summary = {'schema': 'backchain-value-attempt/v1', 'case': case['id'], 'arm': arm, 'model': model,
               'label': out.name, 'workspace': str(ws)}
    try:
        meta = call(model, ws, prompt_for(case, arm), out)
        host = MODELS[model][0]
        stream = (out / 'events.jsonl').read_text(errors='replace') if (out / 'events.jsonl').is_file() else ''
        uses_toolkit = any(trace in stream for trace in TOOLKIT_TRACES)
        summary.update(meta=meta, plan=check(ws / 'artifacts/plan.json'),
                       result=final_record(arm, ws / 'artifacts/result.json'),
                       keys=C.mechanical_keys(case, ws / 'artifacts/plan.json', RESULTS / 'cases.json'),
                       cost=dict(usage_of(out / 'events.jsonl', host), wall_seconds=meta.get('elapsed_seconds')),
                       ran_toolkit=uses_toolkit, contaminated=arm == 'none' and uses_toolkit)
        summary['infrastructure_failure'] = meta.get('status') != 'exited' and not summary['plan']['present']
    except Exception:  # noqa: BLE001 - recorded, never fatal to the lane
        C.save(out / 'runner-error.txt', traceback.format_exc())
        summary['infrastructure_failure'] = True
    if (ws / 'artifacts').is_dir():
        shutil.copytree(ws / 'artifacts', out / 'artifacts', symlinks=True, dirs_exist_ok=True)
    shutil.rmtree(ws / 'resources', ignore_errors=True)  # A3b: no Backchain files outlive their attempt
    C.save(out / 'summary.json', summary)
    print('DONE', out.name, 'plan', (summary.get('plan') or {}).get('present'), 'tokens',
          (summary.get('cost') or {}).get('processed_tokens'), 'seconds', (summary.get('cost') or {}).get('wall_seconds'),
          flush=True)
    return summary


def schedule(cases: list, model: str) -> list:
    """Each case with its two arms in a seeded order, so neither arm always runs first."""
    rng = random.Random(SEED + model)
    jobs = []
    for case in cases:
        arms = list(ARMS)
        rng.shuffle(arms)
        jobs += [(case, arm) for arm in arms]
    return jobs


def run(campaign: Campaign) -> None:
    verify_freeze()
    cases = campaign.cases()

    def lane(model):
        done = []
        for case, arm in schedule(cases, model):
            summary = trial(campaign, case, arm, model)
            for flag, suffix in (('infrastructure_failure', '.failed-1'), ('contaminated', '.contaminated-1')):
                if summary.get(flag):  # PROTOCOL.md: retried once before grading
                    retry = campaign.runs / (label(case['id'], arm, model))
                    shutil.move(str(retry), str(retry) + suffix)
                    summary = trial(campaign, case, arm, model)
            done.append(summary)
        return done

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS)) as pool:
        list(pool.map(lane, list(MODELS)))


# ---------------------------------------------------------------- grading

def study_criteria(case: dict) -> list:
    result = []
    for item in C.criteria(case):
        item = dict(item)
        if item['id'] == 'terminal-disposition':
            item['description'] = TERMINAL_DISPOSITION
        item['description'] = CRITERIA_OVERRIDES.get((case['id'], item['id']), item['description'])
        result.append(item)
    return result


def strip_derived(plan):
    """parallel_groups is derived from the inputs (journal R9-5): a grader read its recomputation as an edit."""
    return {k: v for k, v in plan.items() if k != 'parallel_groups'} if isinstance(plan, dict) else plan


def grade_packet(case: dict, plan, record: dict) -> dict:
    redact = C.Redactor(case)
    packet = {'request': case['request'], 'fixture_files': case['files']}
    if case['draft'] is not None:
        packet['inherited_draft'] = strip_derived(case['draft'])
    for key in ('sources', 'requirements'):
        if case[key]:
            packet[key] = case[key]
    if case['edit_bounds'] is not None:
        packet['edit_bounds'] = case['edit_bounds']
    packet['criteria'] = study_criteria(case)
    packet['final_plan'] = redact(strip_derived(plan))
    packet['final_record'] = redact(record)
    return packet


def grade_prompt(packet: dict) -> str:
    """cohort.py grade_prompt, with "disposition" read as the final record."""
    return C.grade_prompt(packet).replace('PACKET\n', 'PACKET (final_record is the planner\'s own final status)\n', 1)


def ask_opus(prompt: str, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with (out.with_suffix('.stdout.json')).open('w') as stdout, (out.with_suffix('.stderr.log')).open('w') as stderr:
        done = subprocess.run([str(ASK), 'opus', 'ask', '--json', '--no-tools', '--effort', GRADER_EFFORT, prompt],
                              stdout=stdout, stderr=stderr, timeout=1200)
    text = out.with_suffix('.stdout.json').read_text()
    if done.returncode != 0:
        raise RuntimeError(f'ask opus exited {done.returncode}')
    value, _ = json.JSONDecoder().raw_decode(text[text.index('{'):])
    if value.get('error'):
        raise RuntimeError(f"ask opus error: {value['error']}")
    return value.get('text') or '', {key: value.get(key) for key in ('model_used', 'effort', 'fallback')}


def grade_one(campaign: Campaign, case: dict, summary: dict, number: int) -> dict:
    target = campaign.grades / f'p{number}' / (summary['label'] + '.json')
    if target.is_file():
        return C.load(target)
    attempt = campaign.runs / summary['label']
    plan = C.load_optional(attempt / 'artifacts/plan.json')
    packet = grade_packet(case, plan, summary.get('result') or final_record(summary['arm'], attempt / 'artifacts/x'))
    criteria = packet['criteria']
    problems = []
    for tries in range(1, GRADE_RETRIES + 1):
        text, grader = ask_opus(grade_prompt(packet), campaign.grades / f'p{number}' / 'replies' / f"{summary['label']}-{tries}")
        rows, problems = C.parse_grades(text, criteria)
        if rows is not None:
            rows, lowered = C.apply_quote_check(rows, C.evidence_haystacks(packet))  # returns (rows, lowered ids)
            record = {'label': summary['label'], 'pass': number, 'tries': tries, 'rows': rows, 'quote_lowered': lowered,
                      'grader': grader}
            C.save(target, record)
            return record
    record = {'label': summary['label'], 'pass': number, 'tries': GRADE_RETRIES, 'rows': None, 'problems': problems}
    C.save(target, record)
    return record


def grade(campaign: Campaign) -> None:
    verify_freeze()
    cases = {case['id']: case for case in campaign.cases()}
    summaries = [C.load(path) for path in sorted(campaign.runs.glob('*/summary.json'))]
    jobs = [(cases[s['case']], s, n) for s in summaries
            if not s.get('infrastructure_failure') and not s.get('contaminated') for n in PASSES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=GRADER_WORKERS) as pool:
        for record in pool.map(lambda job: grade_one(campaign, *job), jobs):
            print('GRADED', record['label'], 'p%d' % record['pass'], 'ok' if record['rows'] else 'MALFORMED', flush=True)


# ---------------------------------------------------------------- analysis

def attempt_score(campaign: Campaign, summary: dict) -> dict:
    passes = [C.load_optional(campaign.grades / f'p{n}' / (summary['label'] + '.json')) for n in PASSES]
    scores = [C.score({row['id']: row['grade'] for row in p['rows']}) for p in passes if p and p.get('rows')]
    missed = {}
    for p in passes:
        for row in (p or {}).get('rows') or []:
            if row['critical'] and row['grade'] == 'missed':
                missed[row['id']] = missed.get(row['id'], 0) + 1
    no_plan = not (summary.get('plan') or {}).get('present')
    return {'label': summary['label'], 'case': summary['case'], 'arm': summary['arm'], 'model': summary['model'],
            'score': 0.0 if no_plan else (sum(scores) / len(scores) if len(scores) == len(PASSES) else None),
            'pass_scores': scores, 'critical_missed_every_pass': sorted(k for k, v in missed.items() if v == len(PASSES)),
            'structure_ok': (summary.get('plan') or {}).get('structure_ok'),
            'completion': (summary.get('plan') or {}).get('completion'),
            'status': (summary.get('result') or {}).get('status'),
            'keys': summary.get('keys'), 'ran_toolkit': summary.get('ran_toolkit'),
            'tokens': (summary.get('cost') or {}).get('processed_tokens'),
            'output_tokens': (summary.get('cost') or {}).get('output_tokens'),
            'seconds': (summary.get('cost') or {}).get('wall_seconds')}


def reading(low, high) -> str:
    if low is None:
        return 'inconclusive (too few pairs)'
    if low > 0:
        return 'valuable'
    if high < 0:
        return 'the skill costs quality'
    if high < DELTA:
        return 'no meaningful edge'
    return 'inconclusive'


def analyze(campaign: Campaign) -> dict:
    summaries = [C.load(path) for path in sorted(campaign.runs.glob('*/summary.json'))]
    excluded = [s['label'] for s in summaries if s.get('contaminated') or s.get('infrastructure_failure')]
    rows = [attempt_score(campaign, s) for s in summaries if s['label'] not in excluded]
    report = {'schema': 'backchain-value-analysis/v1', 'delta': DELTA, 'models': {}, 'attempts': rows,
              'excluded': excluded}
    for model in MODELS:
        mine = [r for r in rows if r['model'] == model]
        by_case = {}
        for r in mine:
            by_case.setdefault(r['case'], {})[r['arm']] = r
        pairs = {case: arms for case, arms in by_case.items()
                 if all(arm in arms and arms[arm]['score'] is not None for arm in ARMS)}
        diffs = [pairs[c]['backchain']['score'] - pairs[c]['none']['score'] for c in sorted(pairs)]
        if len(diffs) >= C.MIN_CASES or (campaign.pilot and diffs):
            mean_diff, low, high = C.bootstrap(diffs)
        else:
            mean_diff, low, high = (sum(diffs) / len(diffs) if diffs else None), None, None
        tok = [pairs[c]['backchain']['tokens'] - pairs[c]['none']['tokens'] for c in sorted(pairs)
               if pairs[c]['backchain']['tokens'] is not None and pairs[c]['none']['tokens'] is not None]
        sec = [pairs[c]['backchain']['seconds'] - pairs[c]['none']['seconds'] for c in sorted(pairs)
               if pairs[c]['backchain']['seconds'] is not None and pairs[c]['none']['seconds'] is not None]
        arm_stats = {}
        for arm in ARMS:
            these = [r for r in mine if r['arm'] == arm]
            arm_stats[arm] = {
                'attempts': len(these), 'mean_score': C.mean([r['score'] for r in these]),
                'critical_missed_attempts': sum(1 for r in these if r['critical_missed_every_pass']),
                'structure_ok': sum(1 for r in these if r['structure_ok']),
                'complete_plans': sum(1 for r in these if r['completion'] == 'complete'),
                'status_complete': sum(1 for r in these if r['status'] == 'complete'),
                'keys_passed': sum((r['keys'] or {}).get('passed', 0) for r in these),
                'keys_total': sum((r['keys'] or {}).get('total', 0) for r in these),
                'median_tokens': C.median([r['tokens'] for r in these]),
                'median_seconds': C.median([r['seconds'] for r in these]),
                'ran_toolkit': sum(1 for r in these if r['ran_toolkit'])}
        noise = [abs(r['pass_scores'][0] - r['pass_scores'][1]) for r in mine if len(r['pass_scores']) == 2]
        report['models'][model] = {
            'setting': MODELS[model], 'pairs': len(diffs), 'per_case': {c: diffs[i] for i, c in enumerate(sorted(pairs))},
            'quality': {'mean': mean_diff, 'low': low, 'high': high}, 'reading': reading(low, high),
            'tokens': {'mean': sum(tok) / len(tok) if tok else None, 'lower_in': sum(1 for t in tok if t < 0), 'of': len(tok)},
            'seconds': {'mean': sum(sec) / len(sec) if sec else None, 'lower_in': sum(1 for s in sec if s < 0), 'of': len(sec)},
            'arms': arm_stats, 'grader_pass_difference_mean': C.mean(noise)}
    C.save(campaign.root / 'analysis.json', report)
    C.save(campaign.root / 'analysis.md', render(report))
    return report


def render(report: dict) -> str:
    fmt = lambda v, d=1: '—' if v is None else f'{v:+.{d}f}' if isinstance(v, float) else str(v)  # noqa: E731
    lines = ['# Backchain value study: results', '', 'Backchain minus no skill, per model (PROTOCOL.md).', '',
             '| Model | Pairs | Quality Δ [95%] | Reading | Tokens Δ (lower in) | Seconds Δ | Critical misses (bc / none) |',
             '|---|---|---|---|---|---|---|']
    for model, m in report['models'].items():
        q = m['quality']
        lines.append(f"| {model} {m['setting'][1]} {m['setting'][2]} | {m['pairs']} | {fmt(q['mean'])} "
                     f"[{fmt(q['low'])}, {fmt(q['high'])}] | {m['reading']} | {fmt(m['tokens']['mean'], 0)} "
                     f"({m['tokens']['lower_in']}/{m['tokens']['of']}) | {fmt(m['seconds']['mean'], 0)} | "
                     f"{m['arms']['backchain']['critical_missed_attempts']} / {m['arms']['none']['critical_missed_attempts']} |")
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- self-check

def self_check() -> None:
    """No model calls: the two prompts, the workspaces, the packet's blindness and the record normalizer."""
    cases = C.load(COHORT_DIR / 'cases.json')['cases']
    snapshot = RESULTS / 'snapshot'
    assert snapshot.is_dir(), 'freeze first'
    for case in cases:
        for arm in ARMS:
            ws = setup(case, arm)
            try:
                assert (ws / 'plan-format.md').is_file()
                assert (ws / 'resources').is_dir() == (arm == 'backchain'), (case['id'], arm)
                if (ws / 'caller.json').is_file():
                    assert ('selection' in C.load(ws / 'caller.json')) == (arm == 'backchain')
                text = prompt_for(case, arm)
                assert ('resources/skills/backchain/SKILL.md' in text) == (arm == 'backchain'), (case['id'], arm)
                assert 'artifacts/result.json' in text and 'artifacts/plan.json' in text
            finally:
                shutil.rmtree(ws)
        criteria = study_criteria(case)
        assert [c['id'] for c in criteria] == [c['id'] for c in C.criteria(case)]
        assert 'runtime' not in next(c for c in criteria if c['id'] == 'terminal-disposition')['description']
    bc = final_record('backchain', Path('/nonexistent'))
    assert bc['status'] == 'no final record'
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'r.json'
        C.save(p, {'status': 'converged', 'convergence': {'planning_gaps': [], 'execution_blockers': ['approval']}})
        assert final_record('backchain', p) == {'status': 'complete', 'planning_gaps': [], 'execution_blockers': ['approval']}
        C.save(p, {'status': 'incomplete', 'review': {'planning_gaps': ['src'], 'execution_blockers': [],
                                                      'convergence': {'planning_gaps': ['src']}}})
        assert final_record('backchain', p)['status'] == 'incomplete'
        C.save(p, {'status': 'complete', 'planning_gaps': [], 'execution_blockers': []})
        assert final_record('none', p) == {'status': 'complete', 'planning_gaps': [], 'execution_blockers': []}
        C.save(p, {'plan': {}, 'convergence': {'terminal_receipt': {'status': 'complete'}, 'planning_gaps': [],
                                               'execution_blockers': []}})
        assert final_record('backchain', p)['status'] == 'complete'
        C.save(p, {'plan': {}, 'convergence': {'terminal_receipt': {'status': 'stopped'}, 'planning_gaps': ['gap'],
                                               'execution_blockers': []}})
        assert final_record('backchain', p)['status'] == 'incomplete'
    case = next(c for c in cases if c['draft'] is not None)
    plan = dict(case['draft'], parallel_groups=[['S1']])
    packet = grade_packet(case, plan, {'status': 'complete', 'planning_gaps': [], 'execution_blockers': []})
    flat = json.dumps(packet)
    assert 'parallel_groups' not in flat, 'derived field leaked'
    for word in ('convergence', 'receipt', 'until_loop', 'backchain.py'):
        assert word not in json.dumps({k: v for k, v in packet.items() if k in ('final_plan', 'final_record')}), word
    fmt = PLAN_FORMAT.read_text()
    for word in ('backchain', 'freeze', 'record`', '`check`', '`package`', 'elaborator', 'generator', '.py'):
        assert word not in fmt.lower(), ('plan-format.md names', word)
    assert all(prompt_for(case, arm).count(WORKSPACE_ONLY) == 1 for case in cases for arm in ARMS)
    assert not os.access(workspace_root(), os.R_OK), 'the workspace root is listable'
    workspace_root().chmod(0o700)  # the check's own workspaces are gone; leave no unlistable root behind
    shutil.rmtree(workspace_root())
    print('self-check: ok')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('freeze', 'run', 'grade', 'analyze', 'check'))
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--rev', default='origin/main', help='freeze: the skill-craft commit whose released skill runs')
    args = parser.parse_args(argv)
    campaign = Campaign(args.pilot)
    if args.command == 'freeze':
        print(json.dumps(freeze(args.rev), indent=1))
    elif args.command == 'run':
        run(campaign)
    elif args.command == 'grade':
        grade(campaign)
    elif args.command == 'analyze':
        print(render(analyze(campaign)))
    else:
        self_check()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
