#!/usr/bin/env python3
"""Run the design review of the proposed stage change: one read-only Codex session over this repository.

The latest Sol at maximum reasoning effort, in the E2E harness's throwaway profile with the user's own skills
turned off (codex_isolation), the repository as its working directory, a read-only sandbox, the prompt from
review/<name>-prompt.md and its last message written to review/<name>-review.md.

Usage: python3 -I review/run_review.py NAME [--model=gpt-6.2-sol] [--effort=max] [--timeout=5400]
"""
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parents[2]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
sys.path.insert(0, str(EXPERIMENT))
import codex_isolation  # the skills override and its no-model check
import hosts  # the E2E harness host interface

WORK = Path(os.environ.get("SPEC_ELAB_WORK") or Path.home() / "e2e-runs" / "spec-elaboration-20261120")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    name = args[0]
    model, effort = flags.get("model", "gpt-6.2-sol"), flags.get("effort", "max")
    home = WORK / "review" / ".homes" / f"{name}-{int(time.time())}"
    home.mkdir(parents=True)
    env = hosts.CodexHost().env(home)
    shown = codex_isolation.preflight(env)
    if shown:
        raise SystemExit("refusing to start: the reviewer would be shown, from the real home:\n  " + "\n  ".join(shown))
    out = HERE / f"{name}-review.md"
    stream = WORK / "review" / f"{name}.stream.jsonl"
    argv = ["codex", "exec", "--json", "--ephemeral", "--ignore-user-config", "-s", "read-only",
            "-c", 'approval_policy="never"', "-c", f"model_reasoning_effort={effort}", *codex_isolation.flags(),
            "-m", model, "-C", str(REPO), "-o", str(out), (HERE / f"{name}-prompt.md").read_text()]
    start = time.time()
    with open(stream, "w") as sink, open(stream.with_suffix(".stderr.txt"), "w") as err:
        done = subprocess.run(argv, cwd=REPO, stdin=subprocess.DEVNULL, stdout=sink, stderr=err, env=env,
                              timeout=int(flags.get("timeout", 5400)), check=False)
    print(f"review {name}: rc={done.returncode} model={model} effort={effort} minutes={(time.time() - start) / 60:.1f} "
          f"-> {out.relative_to(REPO) if out.is_file() else 'no output'}")


if __name__ == "__main__":
    main()
