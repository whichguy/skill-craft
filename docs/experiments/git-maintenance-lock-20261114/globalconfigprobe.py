"""Probe for docs/local-validation-journal.md, Round 5 (F22): does the CI step `git config --global maintenance.auto false` stop
git's detached auto-maintenance for a fixture commit, including for a suite started through the runner?

Each arm makes fixture-shaped commits (the Grok-chat suite's own command, no `-c maintenance.auto=false`) in fresh repositories
and counts the `git maintenance run --auto --quiet --detach` child launches Trace2 records. HOME is a fresh directory, as on a
CI machine, with the system config left out (GIT_CONFIG_NOSYSTEM) so this machine's own settings cannot colour the result.
  fresh:  no global setting.
  step:   after running the workflow's step, `git config --global maintenance.auto false`, under that HOME.
  runner: the same commits made by a child that test/run_suites.py `run_process` starts, so the runner's own environment
          handling (it strips GIT_CONFIG_* and keeps HOME) is in the path.
Usage: python3 -I globalconfigprobe.py <checkout> <scratch dir> [commits]. Internal: --child <repo dir> <commits>.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

COMMIT = ["commit", "--allow-empty", "-qm", "fixture"]
IDENTITY = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]


def launches(repo: str, n: int) -> int:
    count = 0
    for i in range(n):
        trace = os.path.join(repo, f"trace{i}.json")
        env = {**os.environ, "GIT_TRACE2_EVENT": trace}
        subprocess.run(["git", "-C", repo, *IDENTITY, *COMMIT], check=True, env=env)
        for line in open(trace):
            event = json.loads(line)
            if event.get("event") == "child_start" and "maintenance" in (event.get("argv") or []):
                count += 1
    return count


def machine(base: str, with_step: bool) -> dict:
    home = tempfile.mkdtemp(dir=base, prefix="home-")
    env = {**os.environ, "HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config"), "GIT_CONFIG_NOSYSTEM": "1"}
    for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"):
        env.pop(key, None)
    if with_step:
        subprocess.run(["git", "config", "--global", "maintenance.auto", "false"], check=True, env=env)
    return env


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        print(launches(sys.argv[2], int(sys.argv[3])))
        sys.exit(0)
    root, base, n = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40
    print(subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip())
    for label, with_step in (("fresh machine, no global setting", False), ("after the CI step (global setting)", True)):
        env = machine(base, with_step)
        repo = tempfile.mkdtemp(dir=base, prefix="repo-")
        subprocess.run(["git", "init", "-q", repo], check=True, env=env)
        os.environ.update({k: env[k] for k in ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM")})
        direct = subprocess.run([sys.executable, "-I", __file__, "--child", repo, str(n)], capture_output=True, text=True, env=env, check=True)
        sys.path.insert(0, str(root / "test"))
        import run_suites
        repo2 = tempfile.mkdtemp(dir=base, prefix="repo-")
        subprocess.run(["git", "init", "-q", repo2], check=True, env=env)
        through = run_suites.run_process([sys.executable, "-I", __file__, "--child", repo2, str(n)], cwd=root, timeout_seconds=300)
        print(f"{label:38s} detached maintenance launches over {n} commits: direct {direct.stdout.strip()}, through run_process {through.stdout.strip()} ({through.status})")
