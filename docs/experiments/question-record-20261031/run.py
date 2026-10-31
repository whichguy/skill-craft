#!/usr/bin/env python3
"""Run the subject and judge calls of the question-record experiments (README.md), resumably.

A jobs file holds one job per line: SUBJECT<TAB>PROMPT_PATH<TAB>OUT_PATH (paths relative to this folder).
SUBJECT is ``codex:<model>:<effort>`` (``codex exec`` in a throwaway CODEX_HOME per call that links only auth.json, as
``hosts.CodexHost.env`` isolates it; read-only sandbox, ephemeral, stdin closed; the answer is the final agent message),
``sonnet`` or ``opus`` (the ``ask`` runner: the subscription Claude Code CLI, one fresh headless session per call; X1's
route) or ``ollama:<model>`` (the local Ollama server's /api/chat: one user message, no tools, ``num_ctx`` 32768).
Every call runs from an empty directory OUTSIDE any repository, ``$QR_WORK/cwd-empty`` (QR_WORK defaults to the system
temporary directory), so no repository instruction file loads; the Codex homes live in ``$QR_WORK/codex-homes``.

Each call writes OUT (an envelope with ``text``, the answer, and the runner's facts) and OUT minus .json plus .meta.json
(``rc``, ``seconds``, ``subject``).  A job whose OUT exists with exit 0 and a non-empty text is skipped, so a rerun resumes.
A failed call is retried once.  Progress lines go to stdout: ``DONE``, ``SKIP``, ``FAIL`` (for a monitor).

Usage: run.py JOBS_FILE [JOBS_FILE ...] [--limit=codex=6,opus=4]
"""
import json
import os
import subprocess
import tempfile
import uuid
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASK = "/Users/dadleet/src/grok-build-additions/skills/ask/scripts/ask.sh"
OLLAMA = "http://127.0.0.1:11434/api/chat"
TIMEOUT = 3600
PRINT = threading.Lock()
WORK = Path(os.environ.get("QR_WORK") or tempfile.gettempdir()) / "question-record-20261031"
EMPTY = WORK / "cwd-empty"


def say(*parts) -> None:
    with PRINT:
        print(*parts, flush=True)


def done(out: Path) -> bool:
    try:
        envelope = json.loads(out.read_text())
    except (OSError, ValueError):
        return False
    return envelope.get("exit", 0) == 0 and bool((envelope.get("text") or "").strip())


def call_ask(subject: str, prompt: str, out: Path) -> int:
    with open(out, "w") as stdout, open(out.with_suffix(".err"), "w") as stderr:
        try:
            return subprocess.run([ASK, subject, "--json", prompt], cwd=EMPTY, stdout=stdout,
                                  stderr=stderr, timeout=TIMEOUT).returncode
        except subprocess.TimeoutExpired:
            return 124


def call_codex(model: str, effort: str, prompt: str, out: Path) -> int:
    home = WORK / "codex-homes" / uuid.uuid4().hex[:12] / ".codex"
    home.mkdir(parents=True)
    (home / "auth.json").symlink_to(Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json")
    last = home / "last-message.txt"
    events = out.with_suffix(".events.jsonl")
    argv = ["codex", "exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check", "-s", "read-only",
            "-c", 'approval_policy="never"', "-c", f"model_reasoning_effort={effort}", "-m", model, "-C", str(EMPTY),
            "-o", str(last), prompt]
    env = {**os.environ, "CODEX_HOME": str(home)}
    with open(events, "w") as stdout, open(out.with_suffix(".err"), "w") as stderr:
        try:
            rc = subprocess.run(argv, cwd=EMPTY, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=env,
                                timeout=TIMEOUT).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    usage = {}
    for line in events.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or {}
    text = last.read_text() if last.is_file() else ""
    out.write_text(json.dumps({"model_used": model, "effort": effort, "exit": rc, "text": text, "usage": usage},
                              indent=1) + "\n")
    return rc


def call_ollama(model: str, prompt: str, out: Path) -> int:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
            "options": {"num_ctx": 32768}}
    if model.startswith("gpt-oss"):
        body["think"] = "medium"
    request = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001 - any transport or server failure is recorded and retried once
        out.write_text(json.dumps({"exit": 1, "error": str(exc)[:500], "text": ""}) + "\n")
        return 1
    message = data.get("message") or {}
    out.write_text(json.dumps({
        "model_used": model, "served_model": data.get("model"), "exit": 0, "text": message.get("content") or "",
        "thinking_chars": len(message.get("thinking") or ""), "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"), "think": body.get("think", "default"),
    }, indent=1) + "\n")
    return 0


def run_job(subject: str, prompt_path: Path, out: Path) -> None:
    if done(out):
        say("SKIP", subject, out.relative_to(HERE))
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    prompt = prompt_path.read_text()
    for attempt in (1, 2):
        start = time.time()
        if subject.startswith("codex:"):
            _, model, effort = subject.split(":")
            rc = call_codex(model, effort, prompt, out)
        elif subject.startswith("ollama:"):
            rc = call_ollama(subject.split(":", 1)[1], prompt, out)
        else:
            rc = call_ask(subject, prompt, out)
        seconds = round(time.time() - start, 1)
        ok = rc == 0 and done(out)
        meta = {"subject": subject, "prompt": str(prompt_path.relative_to(HERE)), "rc": rc, "seconds": seconds,
                "attempt": attempt, "ok": ok}
        out.with_name(out.stem + ".meta.json").write_text(json.dumps(meta) + "\n")
        if ok:
            say("DONE", subject, out.relative_to(HERE), f"{seconds}s")
            return
    say("FAIL", subject, out.relative_to(HERE), f"rc={rc}")


def pool_key(subject: str) -> str:
    return subject if not subject.startswith("ollama:") else subject


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--limit")]
    limits = {"sonnet": 6, "opus": 4, "ollama": 1, "codex": 6}
    for flag in (a for a in sys.argv[1:] if a.startswith("--limit")):
        for pair in flag.split("=", 1)[1].split(","):
            key, value = pair.split("=")
            limits[key] = int(value)
    jobs: dict[str, list] = {}
    for jobs_file in args:
        for line in Path(jobs_file).read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            subject, prompt, out = line.split("\t")
            jobs.setdefault(pool_key(subject), []).append((subject, HERE / prompt, HERE / out))
    EMPTY.mkdir(parents=True, exist_ok=True)
    pools = []
    for key, rows in jobs.items():
        width = limits.get(key, limits["ollama"] if key.startswith("ollama:")
                           else limits["codex"] if key.startswith("codex:") else 2)
        pool = ThreadPoolExecutor(max_workers=width)
        pools.append((pool, [pool.submit(run_job, *row) for row in rows]))
    for pool, futures in pools:
        for future in futures:
            future.result()
        pool.shutdown()
    say("ALL-DONE", sum(len(rows) for rows in jobs.values()), "jobs")


if __name__ == "__main__":
    main()
