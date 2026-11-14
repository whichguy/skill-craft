#!/usr/bin/env python3
"""identity.py: one trial of the identity probe (journal entry E10): can a skill tell which harness it runs in?

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A7). The parent runs whoami.py, starts one fresh native
sub-agent that runs it too, and reports both lines and the names of the tools each of them has for starting or waiting for another
agent. The scorer compares what the repository's own ``detect_host`` said, in each context, with the host that was launched, and reads
the host's own record of its sub-agents to confirm that the child was native.

  identity.py --host claude|codex|grok --out TRIAL_DIR [--effort E] [--model M] [--timeout 300] [--binary EXE] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE))
import hosts  # noqa: E402  (the E2E harness's host adapters, used read-only)
import launch  # noqa: E402
import score  # noqa: E402

PACKET = """You are probing which harness you run in. Do these steps in order.

1. Run exactly this command and keep the one JSON line it prints (call it PARENT): python3 {whoami}
2. Start one fresh sub-agent, using your built-in facility for starting an agent with its own context. It has no memory of this
   conversation, so give it this whole instruction: "Run exactly `python3 {whoami}` and reply with one JSON object of the form
   {{"whoami": <the JSON line it printed, as an object>, "tools": [the exact names of every tool you have that can start another
   agent, wait for one, or run a command in the background]}}. Reply with only that object." Wait for its reply (call it CHILD).
3. List the exact names of every tool you have that can start another agent, wait for one, or run a command in the background (call it
   PARENT_TOOLS).
4. End with one last line, exactly in this form: FINAL {{"parent": <PARENT as an object>, "child": <CHILD's whoami object>, "parent_tools": [PARENT_TOOLS], "child_tools": [CHILD's tools]}}
"""


def make_whoami(dest: Path) -> Path:
    text = (HERE / "whoami.py").read_text().replace("@REPO@", str(REPO))
    dest.write_text(text)
    return dest


def judge(host: str, final: dict | None, native_agents: int) -> dict:
    """What the probe shows, from the parent's FINAL object and the host's own sub-agent record."""
    final = final or {}
    parent, child = final.get("parent") or {}, final.get("child") or {}
    spawn_words = ("agent", "task", "spawn", "wait", "background", "bash", "command")
    return {"reported": bool(final), "parent_detects": parent.get("detect_host"), "child_detects": child.get("detect_host"),
            "parent_right": parent.get("detect_host") == host, "child_right": child.get("detect_host") == host,
            "child_ran": bool(child), "native_agents": native_agents,
            "markers_same": (parent.get("markers") == child.get("markers")) if parent and child else None,
            "ids_differ": (parent.get("ids") != child.get("ids")) if parent and child else None,
            "parent_ids": parent.get("ids"), "child_ids": child.get("ids"),
            "parent_markers": parent.get("markers"), "child_markers": child.get("markers"),
            "parent_ancestors": parent.get("ancestors"), "child_ancestors": child.get("ancestors"),
            "parent_tools": final.get("parent_tools"), "child_tools": final.get("child_tools"),
            "child_can_spawn": any(("spawn" in str(t).lower() or str(t).lower() in ("agent", "task")) for t in (final.get("child_tools") or [])) if "child_tools" in final else None,
            "tool_words_checked": spawn_words}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, choices=sorted(hosts.HOSTS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--effort")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--binary")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    trial = Path(args.out).resolve()
    work = trial / "work"
    host = hosts.host(args.host, args.binary)
    model = args.model or host.model
    effort = args.effort if args.effort is not None else host.effort
    whoami = work / "whoami.py"
    packet = PACKET.format(whoami=whoami)
    allow = (f"Bash(python3 {whoami}:*)",)

    def build(prompt_file: Path) -> list:
        return host.argv(prompt=packet, prompt_file=prompt_file, cwd=work, model=model, effort=effort, permission_mode="auto",
                         max_turns=None, max_budget_usd=2.0 if args.host == "claude" else None, allow=allow)
    if args.dry_run:
        print(f"host={args.host} model={model} effort={effort}\nargv: {['<packet>' if p == packet else p for p in build(trial.parent / '.dry-run-prompt.txt')]}\n--- packet\n{packet}")
        return 0
    trial.mkdir(parents=True, exist_ok=False)
    work.mkdir()
    (trial / "home").mkdir()
    make_whoami(whoami)
    (trial / "packet.md").write_text(packet)
    env = host.env(trial / "home")
    version, why = hosts.probe_version(host.binary, env)
    inv = {"host": args.host, "binary": host.binary, "version": version or why, "model": model, "effort": effort, "probe": "identity",
           "allow": list(allow), "packet_sha256": score.dagkit._sha(packet), "loadavg": [round(x, 2) for x in os.getloadavg()], "status": "starting"}
    (trial / "invocation.json").write_text(json.dumps(inv, indent=1) + "\n")
    inv.update(launch.run_host(build(trial / "prompt.txt"), work, env, trial / "events.raw.jsonl", trial / "stderr.txt", args.timeout))
    (trial / "invocation.json").write_text(json.dumps(inv, indent=1) + "\n")
    view = score.host_view(trial, args.host)
    native = score.native_agents(trial, args.host)
    result = {"trial": trial.name, "host": args.host, "elapsed_s": inv.get("elapsed_s"), "status": inv.get("status"),
              **judge(args.host, score.final_claim(view), len(native["agents"]))}
    (trial / "identity.json").write_text(json.dumps(result, indent=1) + "\n")
    print(f"{trial.name}: host={args.host} status={result['status']} parent_right={result['parent_right']} child_right={result['child_right']} "
          f"native_agents={result['native_agents']} ids_differ={result['ids_differ']} markers_same={result['markers_same']} elapsed={result['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
