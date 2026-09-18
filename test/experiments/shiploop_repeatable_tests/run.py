#!/usr/bin/env python3
"""Opt-in fresh Codex test-authoring trials; no model calls on import."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()
            and not {'.git', '__pycache__', '.until-loop'}.intersection(p.relative_to(root).parts)}


def launch(repo: Path, output: Path, prompt: str, timeout: int = 1200,
           model: str | None = None, effort: str | None = None,
           runtime: Path | None = None) -> dict:
    """Retain each attempt, including failures. Never resume or retry silently."""
    repo = repo.resolve(strict=True)
    output = output.resolve()
    if repo == output or repo in output.parents:
        raise ValueError('observer output must be outside the worker repository')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'prompt.txt').write_text(prompt)
    before = hashes(repo)
    argv = ['codex', 'exec', '--ignore-user-config', '--ephemeral',
            '--skip-git-repo-check', '--json', '-s', 'workspace-write',
            '-C', str(repo), '-o', str(output / 'final.md'),
            '-c', 'web_search="disabled"', '-c', 'features.memories=false',
            '-c', 'project_doc_max_bytes=0', '-']
    if model:
        argv[-1:-1] = ['--model', model]
    if effort:
        argv[-1:-1] = ['-c', 'model_reasoning_effort=' + json.dumps(effort)]
    env = dict(os.environ, DEVELOPER_DIR='/Library/Developer/CommandLineTools',
               PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0', NO_COLOR='1')
    start = time.time()
    runtime_before = hashes(runtime) if runtime else None
    version = subprocess.run(['codex', '--version'], capture_output=True, text=True, check=True)
    record = {'schema': 'repeatable-test-trial/1', 'argv': argv, 'started_epoch': start,
              'timeout_seconds': timeout, 'requested_model': model or 'CLI default; unpinned',
              'requested_effort': effort, 'cli_version': version.stdout.strip(),
              'runtime_before': runtime_before,
              'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
              'before': before, 'status': 'running'}
    (output / 'invocation.json').write_text(json.dumps(record, indent=2) + '\n')
    with (output / 'events.jsonl').open('wb') as out, (output / 'stderr.txt').open('wb') as err:
        proc = subprocess.Popen(argv, cwd=repo, stdin=subprocess.PIPE, stdout=out,
                                stderr=err, env=env, start_new_session=True)
        try:
            proc.communicate(prompt.encode(), timeout=timeout)
            status = 'exited' if proc.returncode == 0 else 'process-failed'
        except subprocess.TimeoutExpired:
            status = 'timeout'
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
    terminal_usage = []
    errors = []
    observed_models = set()
    for line in (output / 'events.jsonl').read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') == 'turn.completed':
            terminal_usage.append(event.get('usage'))
        if event.get('type') in {'error', 'turn.failed'}:
            errors.append(event)
        for key in ('model', 'model_name'):
            if isinstance(event.get(key), str):
                observed_models.add(event[key])
    if errors and status == 'exited':
        status = 'event-error'
    improve = {'status': 'unobserved'}
    state_path = repo / '.until-loop/state.json'
    if (state_path.parent.is_dir() and not state_path.parent.is_symlink()
            and state_path.is_file() and not state_path.is_symlink()):
        try:
            state = json.loads(state_path.read_text())
            improve = {'status': state.get('status', state.get('phase', 'unknown')),
                       'cycle': state.get('cycle'), 'state_sha256': hashlib.sha256(state_path.read_bytes()).hexdigest(),
                       'evidence_boundary': 'adapter state observed; transcript and review records require independent audit'}
        except (ValueError, OSError) as exc:
            improve = {'status': 'invalid-state', 'error_type': type(exc).__name__}
    runtime_after = hashes(runtime) if runtime else None
    record.update(status=status, returncode=proc.returncode, elapsed_seconds=time.time()-start,
                  after=hashes(repo), terminal_usage=terminal_usage, errors=errors,
                  observed_models=sorted(observed_models), improve=improve,
                  runtime_after=runtime_after, runtime_unchanged=runtime_before == runtime_after if runtime else None)
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1200)
    parser.add_argument('--model', help='Pin the verified configured model; record actual identity separately')
    parser.add_argument('--effort')
    parser.add_argument('--runtime', type=Path, help='Frozen actual Improve runtime snapshot')
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    result = launch(args.repo, args.output, args.prompt.read_text(), args.timeout,
                    args.model, args.effort, args.runtime)
    print(json.dumps({key: result[key] for key in ['status', 'returncode', 'elapsed_seconds', 'terminal_usage']}))
    return 0 if result['status'] == 'exited' else 1


if __name__ == '__main__':
    raise SystemExit(main())
