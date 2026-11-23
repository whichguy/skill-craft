#!/usr/bin/env python3
"""Prepare an isolated Codybot project. Use --run to also launch ShipLoop."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


BRIEF = "Codybot-design-prompt.md"
CHECKOUT = Path(__file__).resolve().parents[4]
PROMPT = (
    "$skill-craft:shiploop Build Codybot from the complete brief in "
    f"`{BRIEF}`. Read every section before planning, in chunks as needed. "
    "Record the requirements and release scenarios with their brief headings in ShipLoop's "
    "durable planning artifacts. Reuse those artifacts at later checkpoints and after context "
    "loss, reopening the relevant sections of the brief for details and conflicts. "
    "Start an isolated ShipLoop workspace using this Git project as the source "
    "and the absolute path to the sibling `workspace` directory as the workspace root. "
    "Keep product build and verification local until the operator explicitly assigns and authorizes "
    "live Salesforce orgs and any required runtime service accounts. "
    "Record release scenario results and evidence or missing prerequisites in `result.md` "
    "alongside `project/` and `workspace/`."
)


def prepare_project(instance: Path, env: dict[str, str]) -> Path:
    project = instance / "project"
    project.mkdir()
    shutil.copyfile(Path(__file__).resolve().with_name(BRIEF), project / BRIEF)
    # Keep ambient Git hooks and attributes out of the fixture seed.
    git = [
        "git", "-C", str(project),
        "-c", f"core.hooksPath={os.devnull}",
        "-c", f"core.attributesFile={os.devnull}",
        "-c", "core.autocrlf=false",
    ]
    env = dict(env, GIT_ATTR_NOSYSTEM="1")
    subprocess.run([*git, "init", "--quiet", "--initial-branch=main", "--template="], env=env, check=True)
    subprocess.run([*git, "add", "--", BRIEF], env=env, check=True)
    subprocess.run(
        [
            *git,
            "-c", "user.name=Codybot case",
            "-c", "user.email=codybot-case@example.invalid",
            "commit", "--quiet", "--no-gpg-sign", "-m", "Seed the original Codybot build brief",
        ],
        env=env,
        check=True,
    )
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-root", type=Path, default=Path.home() / "e2e-runs" / "codybot",
        help="parent for retained instances (default: ~/e2e-runs/codybot)",
    )
    launch_mode = parser.add_mutually_exclusive_group()
    launch_mode.add_argument("--run", action="store_true", help="also launch one Codex session for this project")
    launch_mode.add_argument("--prepare-only", action="store_true", help="prepare without launching Codex (default)")
    args = parser.parse_args()
    runs_root = args.runs_root.expanduser().resolve()
    if runs_root == CHECKOUT or CHECKOUT in runs_root.parents:
        parser.error("--runs-root must be outside this Skill Craft checkout")

    try:
        # A Git hook or checkout job may export its own repository's paths.
        git_local_vars = subprocess.check_output(["git", "rev-parse", "--local-env-vars"], text=True).split()
        # Receive hooks also export a quarantine guard outside Git's list.
        git_local_vars.append("GIT_QUARANTINE_PATH")
        env = {key: value for key, value in os.environ.items() if key not in git_local_vars}
        runs_root.mkdir(parents=True, exist_ok=True)
        instance = Path(tempfile.mkdtemp(prefix="run-", dir=runs_root))
        print(f"Instance: {instance}", flush=True)
        project = prepare_project(instance, env)
        writable_roots = json.dumps([str(instance), str(project / ".git")], ensure_ascii=False)
        events = instance / "events.jsonl"
        command = [
            "shiploop-codex", "exec", "--json", "--cd", str(project),
            "-c", f"sandbox_workspace_write.writable_roots={writable_roots}",
            "--output-last-message", str(instance / "last-message.md"),
            PROMPT,
        ]
        unset_git_vars = shlex.join(["unset", *git_local_vars])
        launch = f"({unset_git_vars} && exec {shlex.join(command)}) </dev/null >> {shlex.quote(str(events))}"
        (instance / "launch.txt").write_text(launch + "\n", encoding="utf-8")
        print(f"Project: {project}\nEvents: {events}\nLaunch: {launch}", flush=True)
        if not args.run:
            return 0
        with events.open("ab") as event_log:
            return subprocess.run(command, env=env, stdin=subprocess.DEVNULL, stdout=event_log).returncode
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"codybot: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
