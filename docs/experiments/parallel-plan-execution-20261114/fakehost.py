#!/usr/bin/env python3
"""fakehost.py: a stand-in for the claude, codex and grok executables, so the launcher path runs with no model call.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (calibrate.py uses it through ``launch.py --binary``).
It answers ``--version``; reads the packet the way each real host receives it (claude: the ``-p`` argument; codex: the last
argument after ``exec``; grok: ``--prompt-file``); finds the kit and run directory in the packet text; runs every step itself,
one at a time, at ``PPE_TIME_SCALE`` 0.01 (so a scorer sees a scaled trial); and prints events in the stream shape of the host
it was started as. It is a parent that executes the steps itself, which is what arm A0 asks for.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writefix  # noqa: E402


def main(argv: list) -> int:
    if "--version" in argv:
        print("fakehost 0.0")
        return 0
    flavor = "codex" if "exec" in argv else "grok" if "--prompt-file" in argv else "claude"
    if flavor == "grok":
        packet = Path(argv[argv.index("--prompt-file") + 1]).read_text()
    elif flavor == "codex":
        packet = argv[-1]
    else:
        packet = argv[argv.index("-p") + 1]
    kit = re.search(r"python3 (\S+dagkit\.py)", packet).group(1)
    run = re.search(r"--run (\S+)", packet).group(1).rstrip("`.,")
    plan = json.loads((Path(run) / "plan.json").read_text())
    env = dict(os.environ, PPE_TIME_SCALE="0.01")
    out = []

    def emit(event: dict) -> None:
        print(json.dumps(event), flush=True)

    if flavor == "claude":
        emit({"type": "system", "subtype": "init", "model": "fake", "tools": ["Bash"]})
    elif flavor == "codex":
        emit({"type": "thread.started", "thread_id": "t0"})
    n = 0

    def shell(command: list) -> str:
        nonlocal n
        n += 1
        text = " ".join(command)
        if flavor == "claude":
            emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"toolu_{n}", "name": "Bash",
                                                                "input": {"command": text}}],
                                                   "usage": {"input_tokens": 3, "cache_read_input_tokens": 100}},
                  "parent_tool_use_id": None})
        elif flavor == "codex":
            emit({"type": "item.started", "item": {"id": f"item_{n}", "type": "command_execution", "command": text}})
        else:
            emit({"type": "tool_call", "toolCallId": f"c{n}", "toolName": "run_terminal_command", "rawInput": {"command": text}})
        done = subprocess.run(command, env=env, capture_output=True, text=True)
        line = done.stdout.strip()
        if flavor == "claude":
            emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"toolu_{n}", "content": line}]},
                  "parent_tool_use_id": None})
        elif flavor == "codex":
            emit({"type": "item.completed", "item": {"id": f"item_{n}", "type": "command_execution", "command": text,
                                                     "aggregated_output": line, "exit_code": done.returncode}})
        else:
            emit({"type": "tool_call_update", "toolCallId": f"c{n}", "status": "completed"})
        return line

    task_mode = plan["steps"][0].get("kit", {}).get("mode") == "task"
    write = plan.get("fixture") == "write"
    oracle = json.loads((Path(run).parent.parent / "oracle.json").read_text()) if task_mode and not write else {}
    for step in plan["steps"]:
        if task_mode:
            shell([sys.executable, kit, "ready", "--run", run])   # the A0 loop's first command; in an isolated write run it merges the finished branches
            begun = shell([sys.executable, kit, "begin", "--run", run, "--step", step["id"]])
            if write:   # the worker: write the reference solution into the workspace the kit printed (the plan's registering tasks append their import)
                workspace = Path(re.search(r"Workspace \(work only inside it\): (\S+)", begun).group(1))
                if step["id"] == "W5":
                    (workspace / "pkg" / "__init__.py").write_text(writefix.SKELETON["pkg/__init__.py"] + "".join(writefix.IMPORTS.values()))
                    oracle[step["id"]] = sum(writefix.TEST_COUNTS.values())
                else:
                    for rel, body in writefix.REFERENCE[step["id"]].items():
                        (workspace / rel).write_text(body)
                    if "pkg/__init__.py" in step["task"]:
                        with open(workspace / "pkg" / "__init__.py", "a") as handle:
                            handle.write(writefix.IMPORTS[step["id"]])
                    oracle[step["id"]] = writefix.TEST_COUNTS[step["id"]]
            if json.loads((Path(run) / "meta.json").read_text()).get("settle"):
                shell([sys.executable, kit, "settle", "--run", run, "--step", step["id"]])
            out.append(shell([sys.executable, kit, "complete", "--run", run, "--step", step["id"], "--result",
                              json.dumps({"answer": oracle[step["id"]], "method": "fake"})]))
        else:
            out.append(shell([sys.executable, kit, "run", "--run", run, "--step", step["id"]]))
    if task_mode:
        shell([sys.executable, kit, "ready", "--run", run])   # the loop's last command: merges the final branch of an isolated run
    verify = shell([sys.executable, kit, "verify", "--run", run])
    state = json.loads(subprocess.run([sys.executable, kit, "ready", "--run", run], env=env, capture_output=True, text=True).stdout)
    answer = {"answer": oracle[plan["steps"][-1]["id"]]} if task_mode else {}
    final = "FINAL " + json.dumps({"done": state["done"], "failed": state["failed"], "not_run": state["blocked"] + state["waiting"], **answer})
    text = verify + "\n" + final
    if flavor == "claude":
        emit({"type": "result", "result": text, "usage": {"input_tokens": 12, "output_tokens": 5, "cache_read_input_tokens": 400},
              "total_cost_usd": 0.01})
    elif flavor == "codex":
        emit({"type": "item.completed", "item": {"id": "item_final", "type": "agent_message", "text": text}})
        emit({"type": "turn.completed", "usage": {"input_tokens": 500, "cached_input_tokens": 400, "output_tokens": 5}})
    else:
        emit({"type": "text", "data": text})
        emit({"type": "end", "usage": {"input_tokens": 500, "cache_read_input_tokens": 400, "output_tokens": 5}})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
