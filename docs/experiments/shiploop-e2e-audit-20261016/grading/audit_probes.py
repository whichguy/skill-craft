#!/usr/bin/env python3
"""Reproduce focused ShipLoop E2E grading findings without model calls or repo edits."""
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO = Path('/Users/dadleet/src/skill-craft')
TESTS = REPO / 'test' / 'shiploop_e2e'
RETAINED = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import review  # noqa: E402
import run  # noqa: E402


def clean_owned(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def reviewer_result(name: str, process_status: str, text: str) -> dict:
    out = RETAINED / name
    clean_owned(out)
    out.mkdir()

    class FakeAgent:
        model = 'offline-probe'
        effort = 'high'

        @staticmethod
        def env(home):
            return {'HOME': str(home)}

        @staticmethod
        def argv(**kwargs):
            return ['offline-probe']

        @staticmethod
        def translator():
            return None

    def fake_run_agent(argv, cwd, env, events_path, stderr_path, timeout, translate=None):
        Path(events_path).write_text('')
        Path(stderr_path).write_text('')
        return {'status': process_status, 'returncode': 1 if process_status == 'failed' else 0,
                'elapsed_seconds': 0}

    with patch.object(review.hosts, 'host', return_value=FakeAgent()), \
         patch.object(review.hosts, 'run_agent', side_effect=fake_run_agent), \
         patch.object(review.hosts, 'final_text', return_value=text):
        return review.review(out, host='grok', skill_root=REPO / 'skills' / 'shiploop')


failed_review = reviewer_result('review-failed-no-json', 'failed', '')
invalid_exited_review = reviewer_result('review-exited-incomplete-json', 'exited',
                                        '```json\n{"learnings": []}\n```')
required_review_keys = {'outcome', 'learnings', 'missing_considerations', 'optimizations', 'harness'}
missing_keys = sorted(required_review_keys - set(invalid_exited_review))
# This is the exact clean-streak branch in iterate.py: a review with no actionable findings
# increments on result.pass, independently of process status or schema completeness.
streak = 0
for verdict in (failed_review, invalid_exited_review):
    if not verdict['actionable']:
        streak = streak + 1 if True else 0
streak_before_failed_run = streak
streak = streak + 1 if False else 0  # counter-evidence: a failed run resets the streak

state_fixture = RETAINED / 'state-binding-fixture'
run.store.write_record(state_fixture / '.shiploop-runs' / 'stale' / 'run' / 'state.md',
                       {'status': 'done', 'stage': 'done', 'revision': 12})
(state_fixture / '.shiploop-runs' / 'stale' / 'run' / 'report.html').write_text('<html>stale</html>')
run.store.write_record(state_fixture / 'work' / '.shiploop' / 'state.md',
                       {'status': 'active', 'stage': 'implement', 'revision': 3})
selected = run.grade_shiploop(state_fixture)

cases = json.loads((TESTS / 'cases.json').read_text())
checks = cases['battleship']['checks']
battle_fixture = RETAINED / 'battleship-fixture'
(battle_fixture / 'test').mkdir(parents=True, exist_ok=True)
(battle_fixture / 'server.js').write_text("""const http=require('node:http');
http.createServer((req,res)=>{
  if(req.url==='/'){res.writeHead(200,{'content-type':'text/html'});return res.end('<title>Battleship</title><h1>Battleship</h1>');}
  if(req.url==='/api/new'){res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({game:'g',gameOver:true}));}
  if(req.url==='/api/fire'){req.resume();res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({result:'miss',gameOver:true,shots:1,hits:0}));}
  res.writeHead(404);res.end();
}).listen(Number(process.env.PORT||3000),'127.0.0.1');
""")
(battle_fixture / 'test' / 'game.test.js').write_text(
    "const test=require('node:test'); const assert=require('node:assert/strict'); "
    "test('placeholder',()=>assert.equal(1,1));\n")
ports = []
for _ in range(3):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        ports.append(sock.getsockname()[1])
port_map = dict(zip((39171, 39172, 39173), ports))
battle_results = []
for original in checks:
    command = original
    for old, new in port_map.items():
        command = command.replace(str(old), str(new))
    proc = subprocess.run(['bash', '-c', command], cwd=battle_fixture, text=True,
                          capture_output=True, timeout=30)
    battle_results.append({'returncode': proc.returncode, 'stderr_tail': proc.stderr[-300:]})

base_row = {'case': 'hello', 'source': 'checkout', 'host': 'claude', 'model': 'm', 'effort': 'high',
            'planning_review': 'stage', 'prompt_sha256': 'p', 'host_build': '2.1.1',
            'verdicts': {'shiploop': True}, 'termination': {'engine_status': 'done'}}
source_head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], check=True,
                             capture_output=True, text=True).stdout.strip()
receipt = {
    'source_head': source_head,
    'scope': 'offline synthetic probes only; no model, live deployment, or repo edits',
    'review_convergence': {
        'failed_process_no_json': {'process_status': failed_review['process']['status'],
                                   'actionable': failed_review['actionable'],
                                   'missing_required_keys': sorted(required_review_keys - set(failed_review))},
        'exited_process_incomplete_schema': {'process_status': invalid_exited_review['process']['status'],
                                             'actionable': invalid_exited_review['actionable'],
                                             'missing_required_keys': missing_keys,
                                             'review_cli_exit_gate_would_be_zero':
                                                 invalid_exited_review['process']['status'] == 'exited' and
                                                 'learnings' in invalid_exited_review},
        'two_invalid_reviews_on_passing_runs_clean_streak': streak_before_failed_run,
        'failed_run_resets_clean_streak_to': streak
    },
    'state_binding': {'fixture': str(state_fixture), 'selected_run_dir': selected['run_dir'],
                      'selected_pass': selected['pass'], 'runs_seen': selected['runs'],
                      'actual_work_state': 'active', 'note': 'conditional synthetic reproduction only'},
    'battleship_checks': {'fixture': str(battle_fixture), 'ports': ports,
                          'mutant': 'no fleet; new game is gameOver=true; every fire is miss/gameOver=true',
                          'catalog_check_returncodes': [x['returncode'] for x in battle_results],
                          'details': battle_results},
    'comparison_caveat': {'different_host_build_match_reason': run.row_matches(
        dict(base_row, host_build='2.1.2'), 'hello', 'checkout', 'claude', 'm', 'high', 'stage', 'p'),
        'interpretation': 'row_matches is descriptive across host_build drift; README/SPEC expose build identity and do not claim a controlled causal comparison'}
}
receipt_path = RETAINED / 'receipt.json'
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'receipt': str(receipt_path), 'source_head': source_head,
                  'battle_check_returncodes': receipt['battleship_checks']['catalog_check_returncodes'],
                  'review_streak': streak_before_failed_run,
                  'state_selected_pass': selected['pass']}, indent=2))
