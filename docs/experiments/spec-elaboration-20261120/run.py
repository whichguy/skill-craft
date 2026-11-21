#!/usr/bin/env python3
"""Run one round of the spec-elaboration experiment: every case x arm x driver, resumably.

A subject call is one headless session that reads nothing but its arm's prompt with the case's request
substituted in, and writes `spec.md` (and `passes.md`, where its arm asks for one) into its own empty working
directory. That directory sits outside every repository, so no repository instruction file loads, and each host is
started with its own customizations off:

  sonnet-high  claude -p --safe-mode (no CLAUDE.md, skills, plugins, hooks, MCP, commands or agents), the latest
               Sonnet at effort high.
  sol-medium   codex exec --ignore-user-config in the E2E harness's own throwaway profile (hosts.CodexHost.env: a
               throwaway HOME with its own keychain, git identity and XDG folders, whose .codex links only
               auth.json), gpt-6.2-sol at reasoning effort medium. Rounds 1 to 3 redirected CODEX_HOME alone, and
               every one of their 16 Sol sessions read a user-level skill from the real HOME
               (~/.agents/skills, ~/.codex/skills); from round 4 on the HOME itself is a throwaway, kept outside
               the session's working directory. `grade.py leaks ROUND` checks every stream for it.
               Round 4 showed that is still not enough: Codex lists the skills under the account's real home to
               the model whatever HOME says. From round 4c on every user-level skill is turned off by a
               `skills.config` override (codex_isolation.py), and a round refuses to start unless a no-model
               render of the session's prompt input shows none of them.

Both write under a workspace-write sandbox limited to that directory. Nothing in cases.json reaches a subject: the
held-out nuance checklist is read only by grade.py.

Each finished call leaves results/<round>/<case>__<arm>__<driver>/ holding spec.md, passes.md where written,
meta.json (rc, seconds, the arm file's sha256, usage where the host reports it) and the raw stream. A call whose
spec.md is already there is skipped, so a rerun resumes and a new round re-runs everything.

Usage: python3 -I run.py ROUND [--cases a,b] [--arms A-single,B-recursive] [--drivers sonnet-high,sol-medium]
                               [--parallel 4] [--timeout 2700] [--list]
Env: SPEC_ELAB_WORK  where the throwaway working directories go (default ~/e2e-runs/spec-elaboration-20261120)
"""
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE))  # python3 -I leaves the script's own folder off the path
import codex_isolation  # beside this file
import hosts  # the E2E harness host interface: its Codex profile isolation is used as it stands

CLAUDE = shutil.which("claude") or "/Users/dadleet/.local/bin/claude"
WORK = Path(os.environ.get("SPEC_ELAB_WORK") or Path.home() / "e2e-runs" / "spec-elaboration-20261120")
PRINT = threading.Lock()

DRIVERS = {
    "sonnet-high": {"host": "claude", "model": "claude-sonnet-5-5", "effort": "high"},
    "sol-medium": {"host": "codex", "model": "gpt-6.2-sol", "effort": "medium"},
}


def say(*parts):
    with PRINT:
        print(*parts, flush=True)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def call_claude(prompt, cwd, model, effort, timeout):
    """One headless Claude session with every customization off, writing in cwd."""
    argv = [CLAUDE, "-p", prompt, "--safe-mode", "--strict-mcp-config", "--model", model, "--effort", effort,
            "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose",
            "--no-session-persistence", "--add-dir", str(cwd)]
    stream = cwd / ".stream.jsonl"
    env = {**os.environ, "NO_COLOR": "1", "GIT_TERMINAL_PROMPT": "0", "TMPDIR": str(cwd / ".tmp")}
    (cwd / ".tmp").mkdir(exist_ok=True)
    with open(stream, "w") as out, open(cwd / ".stderr.txt", "w") as err:
        try:
            rc = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, env=env,
                                timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    usage = {}
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            usage = {"cost_usd": event.get("total_cost_usd"), "turns": event.get("num_turns"),
                     "usage": event.get("usage")}
    return rc, usage


def call_codex(prompt, cwd, model, effort, timeout):
    """One codex exec in the E2E harness's throwaway profile: a HOME of its own, beside the working directory."""
    home = cwd.parent / ".homes" / cwd.name
    home.mkdir(parents=True, exist_ok=True)
    profile = hosts.CodexHost().env(home)
    stream = cwd / ".stream.jsonl"
    argv = ["codex", "exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "-s", "workspace-write", "-c", 'approval_policy="never"', "-c", f"model_reasoning_effort={effort}",
            *codex_isolation.flags(), "-m", model, "-C", str(cwd), "-o", str(cwd / ".last-message.txt"), prompt]
    with open(stream, "w") as out, open(cwd / ".stderr.txt", "w") as err:
        try:
            rc = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, env=profile,
                                timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    usage = {}
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            usage = {"usage": event.get("usage")}
    return rc, usage


SKILL = HERE.parents[2] / "skills" / "shiploop"


def give_guides(cwd):
    """Put ShipLoop's own reference guides in cwd/GUIDES, with a README saying which file each guide name means."""
    shutil.copytree(SKILL / "references", cwd / "GUIDES")
    sys.path.insert(0, str(SKILL / "scripts"))
    import shiploop_prompts
    import shiploop_reference
    rows = list(shiploop_prompts.STAGE_REFERENCES["spec"]) + list(shiploop_reference.POLICIES)
    lines = ["# Guides", "", "The guides the stage text names, and the file (and section) each one is:", ""]
    lines += [f"- {name}: `{where}`" for name, where in dict(rows).items()]
    (cwd / "GUIDES" / "README.md").write_text("\n".join(lines) + "\n")


# What an arm needs in its working directory before the session starts.
ARM_SETUP = {"P-shiploop-spec": give_guides}
OWN_FOLDERS = ("GUIDES", ".codex-home", ".tmp")


def run_one(round_name, case, arm, driver, timeout):
    slot = f"{case['id']}__{arm}__{driver}"
    kept = HERE / "results" / round_name / slot
    if (kept / "spec.md").is_file() and (kept / "spec.md").read_text().strip():
        say("SKIP", slot)
        return
    arm_text = (HERE / "arms" / f"{arm}.md").read_text()
    prompt = arm_text.replace("{request}", case["request"])
    cwd = WORK / round_name / f"{slot}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    if arm in ARM_SETUP:
        ARM_SETUP[arm](cwd)
    spec = DRIVERS[driver]
    start = time.time()
    caller = call_claude if spec["host"] == "claude" else call_codex
    rc, usage = caller(prompt, cwd, spec["model"], spec["effort"], timeout)
    seconds = round(time.time() - start, 1)
    kept.mkdir(parents=True, exist_ok=True)
    written = []
    def own(path):
        return not any(part in OWN_FOLDERS for part in path.relative_to(cwd).parts)

    for name in ("spec.md", "passes.md"):
        found = next((p for p in sorted(cwd.rglob(name)) if own(p)), None)
        if found is not None:
            shutil.copy2(found, kept / name)
            written.append(str(found.relative_to(cwd)))
    # Any other document the stage wrote (ShipLoop's stage may put a decision in architecture.md) is kept beside
    # the specification and judged with it.
    for other in sorted(p for p in cwd.rglob("*.md") if own(p) and p.name not in ("spec.md", "passes.md")):
        (kept / "also").mkdir(exist_ok=True)
        shutil.copy2(other, kept / "also" / other.name)
        written.append(str(other.relative_to(cwd)))
    for name in (".stream.jsonl", ".stderr.txt"):
        if (cwd / name).is_file():
            shutil.copy2(cwd / name, kept / name.lstrip("."))
    stray = sorted(str(p.relative_to(cwd)) for p in cwd.rglob("*")
                   if p.is_file() and not p.name.startswith(".") and own(p) and p.suffix != ".md")
    ok = rc == 0 and (kept / "spec.md").is_file() and (kept / "spec.md").read_text().strip() != ""
    (kept / "meta.json").write_text(json.dumps({
        "round": round_name, "case": case["id"], "arm": arm, "arm_sha256_12": sha(arm_text), "driver": driver,
        "host": spec["host"], "model": spec["model"], "effort": spec["effort"], "rc": rc, "seconds": seconds,
        "ok": ok, "wrote": written, "stray_files": stray, "workdir": str(cwd),
        "user_skills_turned_off": len(codex_isolation.user_skill_files()) if spec["host"] == "codex" else None,
        **usage}, indent=1) + "\n")
    say("DONE" if ok else "FAIL", slot, f"{seconds}s", f"rc={rc}", f"files={written}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {}
    for flag in (a for a in sys.argv[1:] if a.startswith("--")):
        key, _, value = flag[2:].partition("=")
        flags[key] = value or "1"
    data = json.loads((HERE / "cases.json").read_text())
    cases = data["cases"]
    if flags.get("cases"):
        want = flags["cases"].split(",")
        cases = [c for c in cases if c["id"] in want]
    arms = flags.get("arms", "A-single,B-recursive").split(",")
    drivers = flags.get("drivers", "sonnet-high,sol-medium").split(",")
    jobs = [(c, a, d) for c in cases for a in arms for d in drivers]
    if "list" in flags or not args:
        for c, a, d in jobs:
            print(f"{c['id']}__{a}__{d}")
        print(f"{len(jobs)} calls", "(pass a ROUND name to run)" if not args else "")
        return
    round_name = args[0]
    if any(DRIVERS[d]["host"] == "codex" for d in drivers):
        home = WORK / round_name / ".homes" / "preflight"
        home.mkdir(parents=True, exist_ok=True)
        shown = codex_isolation.preflight(hosts.CodexHost().env(home))
        if shown:
            raise SystemExit("refusing to start: a Codex session would still be shown, from the real home:\n  "
                             + "\n  ".join(shown))
        say(f"Codex pre-flight: no user-level skill or skill root is shown to a session "
            f"({len(codex_isolation.user_skill_files())} turned off by override)")
    timeout = int(flags.get("timeout", 2700))
    width = int(flags.get("parallel", 4))
    say(f"round {round_name}: {len(jobs)} calls, {width} at a time, work under {WORK / round_name}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(run_one, round_name, c, a, d, timeout) for c, a, d in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    say("round", round_name, "finished")


if __name__ == "__main__":
    main()
