"""The repository's ShipLoop knowledge home, kept and committed at the end of planning.

Owner decision 2026-09-26: planning produces a spec and environment knowledge that
outlive the run.  The model writes them under ``docs/shiploop/`` during planning;
at four closes ShipLoop checks the expected files (prepare, test-spec, release-plan,
release-verify), screens them for credentials,
refuses a living spec that drops an earlier requirement ID, and commits exactly
``docs/shiploop/`` with its own message.  A later run starts from these files.

    docs/shiploop/README.md          index: what each file answers, the feature list
    docs/shiploop/spec.md            living product spec; stable requirement IDs, a Retired section
    docs/shiploop/environment.md     targets, aliases, working commands, platform facts
    docs/shiploop/test-strategy.md   harnesses, suites, commands, the ID convention
    docs/shiploop/features/<slug>/   this run: spec.md (delta), plan.md, test-spec.md,
                                     system-tests.md, release-plan.md, outcome.md
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import shiploop_privacy as privacy

HOME = "docs/shiploop"
LIVING = ("README.md", "spec.md", "environment.md", "test-strategy.md")
# The close that commits, and the files it requires (``{feature}`` is this run's feature directory).
CLOSES: Dict[str, Tuple[str, ...]] = {
    "prepare": ("README.md", "spec.md", "environment.md", "test-strategy.md",
                "{feature}/spec.md", "{feature}/plan.md"),
    "test-spec": ("{feature}/plan.md", "{feature}/test-spec.md"),
    "release-plan": ("{feature}/system-tests.md", "{feature}/release-plan.md", "environment.md"),
    # Before the workspace return: a commit at handoff would miss the return and stale its receipt.
    "release-verify": ("{feature}/outcome.md", "environment.md", "README.md"),
}
# What each stage writes or updates, printed in its packet.
STAGE_FILES: Dict[str, Tuple[str, ...]] = {
    "intake": ("README.md",),
    "discovery": ("environment.md",),
    "spec": ("spec.md", "{feature}/spec.md"),
    "test-strategy": ("test-strategy.md",),
    "plan": ("{feature}/plan.md", "README.md"),
    "prepare": CLOSES["prepare"],
    "step-plan": ("{feature}/plan.md",),
    "test-spec": ("{feature}/test-spec.md",),
    "system-test-author": ("{feature}/system-tests.md",),
    "release-plan": ("{feature}/release-plan.md", "environment.md"),
    "release-verify": CLOSES["release-verify"],
}
_REQUIREMENT_ID = re.compile(r"\b(R-\d+)\b")


def feature_dir(state: Mapping[str, Any]) -> str:
    """This run's feature directory under the home: a slug of the request plus the run's suffix."""
    words = re.findall(r"[a-z0-9]+", str(state.get("prompt", "")).lower())[:6]
    slug = "-".join(words) or "feature"
    return HOME + "/features/" + slug[:48].rstrip("-") + "-" + str(state["run_id"])[-6:]


def _expand(names: Sequence[str], state: Mapping[str, Any]) -> List[str]:
    feature = feature_dir(state)
    return [name.replace("{feature}", feature) if "{feature}" in name else HOME + "/" + name for name in names]


def stage_lines(state: Mapping[str, Any], stage: str) -> List[str]:
    """Packet lines: where the knowledge home is and what this stage keeps up to date there."""
    repo = Path(str(state["repo"]))
    lines = ["", "Repository knowledge home (committed, inherited by later runs): " + str(repo / HOME)
             + "/README.md. Earlier runs' spec, environment and features are there; open a file when this "
             "stage needs it."]
    files = STAGE_FILES.get(stage)
    if files:
        lines.append("This stage keeps these up to date (create them if missing): "
                     + ", ".join(str(repo / path) for path in _expand(files, state)) + ".")
    if stage == "spec":
        lines.append("spec.md is the living spec: start from the committed one, keep every requirement ID "
                     "(R-<n>), change it in place, and move a dropped requirement under a 'Retired' heading "
                     "with its reason. ShipLoop refuses a spec that loses an earlier ID. The feature's spec.md "
                     "lists the IDs this run adds, modifies and retires.")
    if stage in CLOSES:
        lines.append("On done ShipLoop checks these files, screens them for credentials and commits "
                     + HOME + "/ in the execution checkout.")
    return lines


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", *args],
                          capture_output=True, text=True, check=False)


def _committed_spec(repo: Path) -> str:
    shown = _git(repo, "show", "HEAD:" + HOME + "/spec.md")
    return shown.stdout if shown.returncode == 0 else ""


def check(state: Mapping[str, Any], stage: str) -> str:
    """Refusal text for a close whose knowledge files are missing, leak a credential or drop an ID."""
    if stage not in CLOSES:
        return ""
    repo = Path(str(state["repo"]))
    if _git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return ""
    required = _expand(CLOSES[stage], state)
    missing = [path for path in required if not (repo / path).is_file() or not (repo / path).read_text(
        encoding="utf-8", errors="replace").strip()]
    if missing:
        return ("ShipLoop keeps this run's planning knowledge in the repository so later runs inherit it. "
                "Before " + stage + " is done, write:\n" + "".join("- " + str(repo / p) + "\n" for p in missing)
                + "See the packet's knowledge-home lines for what each file holds.")
    leaks = []
    for path in sorted((repo / HOME).rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if privacy.sensitive_text(line):
                leaks.append(str(path.relative_to(repo)) + ":" + str(number))
    if leaks:
        return ("These knowledge lines look like credentials; record alias names, never tokens, passwords or "
                "session URLs: " + ", ".join(leaks[:10]))
    before = set(_REQUIREMENT_ID.findall(_committed_spec(repo)))
    now = set(_REQUIREMENT_ID.findall((repo / HOME / "spec.md").read_text(encoding="utf-8", errors="replace"))
              if (repo / HOME / "spec.md").is_file() else ())
    dropped = sorted(before - now, key=lambda value: int(value.split("-")[1]))
    if dropped:
        return ("The living spec " + str(repo / HOME / "spec.md") + " no longer mentions " + ", ".join(dropped)
                + ". Keep every earlier requirement ID: modify it in place, or move it under a 'Retired' "
                "heading with the reason.")
    return ""


def commit(state: Mapping[str, Any], stage: str) -> str:
    """Stage and commit exactly the knowledge home; return the commit ID, '' when nothing changed."""
    repo = Path(str(state["repo"]))
    if stage not in CLOSES or not (repo / HOME).is_dir():
        return ""
    added = _git(repo, "add", "--", HOME)
    if added.returncode:
        raise RuntimeError("cannot stage " + HOME + ": " + added.stderr.strip())
    if _git(repo, "diff", "--cached", "--quiet", "--", HOME).returncode == 0:
        return ""
    message = "docs(shiploop): record " + feature_dir(state).rsplit("/", 1)[-1] + " knowledge at " + stage
    done = _git(repo, "commit", "-q", "-m", message, "--", HOME)
    if done.returncode:
        raise RuntimeError("cannot commit " + HOME + ": " + (done.stderr or done.stdout).strip())
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def in_home(path: str) -> bool:
    return path == HOME or path.startswith(HOME + "/")


__all__ = ("CLOSES", "HOME", "check", "commit", "feature_dir", "in_home", "stage_lines")
