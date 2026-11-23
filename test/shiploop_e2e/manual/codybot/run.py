#!/usr/bin/env python3
"""Prepare one isolated Codybot project and launch a fresh ShipLoop session."""

import argparse
import json
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
    "Start an isolated ShipLoop workspace using this Git project as the source "
    "and the absolute path to the sibling `workspace` directory as the workspace root. "
    "Keep product build and verification local until the operator explicitly assigns and authorizes "
    "live Salesforce orgs and any required runtime service accounts. "
    "Record release scenario results and evidence or missing prerequisites in `result.md` "
    "alongside `project/` and `workspace/`."
)


def prepare_project(instance: Path) -> Path:
    project = instance / "project"
    project.mkdir()
    shutil.copyfile(Path(__file__).resolve().with_name(BRIEF), project / BRIEF)
    git = ["git", "-C", str(project)]
    subprocess.run([*git, "init", "--quiet", "--initial-branch=main", "--template="], check=True)
    subprocess.run([*git, "-c", "core.autocrlf=false", "add", "--", BRIEF], check=True)
    subprocess.run(
        [
            *git,
            "-c", "user.name=Codybot case",
            "-c", "user.email=codybot-case@example.invalid",
            "-c", "core.hooksPath=/dev/null",
            "commit", "--quiet", "--no-gpg-sign", "-m", "Seed the original Codybot build brief",
        ],
        check=True,
    )
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-root", type=Path, default=Path.home() / "e2e-runs" / "codybot",
        help="parent for retained instances (default: ~/e2e-runs/codybot)",
    )
    parser.add_argument("--prepare-only", action="store_true", help="create a project without launching Codex")
    args = parser.parse_args()
    runs_root = args.runs_root.expanduser().resolve()
    if runs_root == CHECKOUT or CHECKOUT in runs_root.parents:
        parser.error("--runs-root must be outside this Skill Craft checkout")

    try:
        runs_root.mkdir(parents=True, exist_ok=True)
        instance = Path(tempfile.mkdtemp(prefix="run-", dir=runs_root))
        print(f"Instance: {instance}", flush=True)
        project = prepare_project(instance)
        writable_roots = json.dumps([str(instance), str(project / ".git")], ensure_ascii=False)
        events = instance / "events.jsonl"
        command = [
            "shiploop-codex", "exec", "--json", "--cd", str(project),
            "-c", f"sandbox_workspace_write.writable_roots={writable_roots}",
            "--output-last-message", str(instance / "last-message.md"),
            PROMPT,
        ]
        launch = shlex.join(command) + f" </dev/null >> {shlex.quote(str(events))}"
        (instance / "launch.txt").write_text(launch + "\n", encoding="utf-8")
        print(f"Project: {project}\nEvents: {events}\nLaunch: {launch}", flush=True)
        if args.prepare_only:
            return 0
        with events.open("ab") as event_log:
            return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=event_log).returncode
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"codybot: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
