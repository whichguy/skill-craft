"""The run reference file, `<run>/reference.md`: run-wide detail a packet names by section instead of reprinting.

Owner, 2026-10-10: a packet holds the key file references, what to do, when it is complete, and what to execute.
Detail a stage seldom needs lives here, in labelled sections. A packet names only the sections its stage uses
(`reference#<anchor>`) and says when to open each one. Grounding never moves here (SPEC S-6): a stage's goal,
operation, Done-when, Checked-by, result contract, recovery command and the rules it can hit stay in its packet.

The file is derived from state.md and the package: `navigator.save()` writes it with every transition (beside
context-index.md, in the same transaction), and `emit` writes it again when it is missing or was written by another
ShipLoop version, so a run that started before this file existed gets it on its next `next`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import shiploop_prompts as guidance

REFERENCE_FILE = "reference.md"
SCRIPTS = Path(__file__).resolve().parent
REFERENCES = SCRIPTS.parent / "references"
VERSION_LINE = "<!-- shiploop-reference: {version} -->"

# (anchor, heading). Packets cite `reference#<anchor>`; tests check every cited anchor exists.
SECTIONS = (
    ("rules", "Rules for every step"),
    ("blocked", "Blocked, and waiting for a person"),
    ("outcomes", "Result outcomes"),
    ("recovery", "Recovery"),
    ("progress", "Progress reporting"),
    ("requirements", "Requirements and references"),
    ("policies", "Policies and guides"),
    ("workspace", "Workspace and the source return"),
)
ANCHORS = frozenset(anchor for anchor, _ in SECTIONS)

# Label, file and anchor of each policy or guide a stage's prose may name ("the packet's X guide").
POLICIES = (
    ("Access-readiness policy", "research-loop.md#early-access-readiness"),
    ("Delivery-authority policy", "delivery-authority.md"),
    ("Environment lifecycle policy", "environment-lifecycle.md"),
    ("Cross-run knowledge policy", "project-knowledge.md"),
    ("Maintained requirements policy", "project-knowledge.md#maintained-product-requirements"),
    ("Requirements definition guide", "requirements-definition.md"),
    ("Stage readiness and completion guide", "testing-and-documentation.md#stage-readiness-and-completion"),
    ("Initial repository baseline guide", "execution-planning.md#initial-repository-baseline"),
    ("Reference handoff policy", "project-knowledge.md#reference-handoffs-and-destinations"),
    ("Consumer testing guide", "testing-and-documentation.md#lightweight-and-browser-checks"),
    ("Repeatable test-suite guide", "repeatable-test-suites.md"),
    ("Selected-case reconciliation guide", "testing-and-documentation.md#test-cases"),
    ("Real-boundary selection guide", "testing-and-documentation.md#surface-selection"),
    ("Interaction design guide", "behavioral-requirements.md#actors-channels-and-state-ownership"),
    ("Worktree and artifact policy", "workspace-lifecycle.md"),
    ("Navigator contract", "navigator.md"),
)

AWAITING_TEXT = """\
ShipLoop runs unattended: no one is watching and nothing arrives on standard input.
- An open decision: take the default that best fits the request and the recorded knowledge, record it as an
  assumption (the alternatives and why this one), and continue.
- A step only a person can do (a sign-in, a grant, an observation in a signed-in browser): record it as an open item
  in the result (who must do what, what they report back) and continue with everything that does not depend on it.
- Only when nothing further can proceed without the person: outcome `blocked` with `blocked_by` user (or access, for
  a sign-in) and `awaiting`, one decision per question, in words the user can answer in one reply:
  - a decision: `{"kind": "answer", "question": "...", "options": [...], "no_default": "..."}`
  - something only a person can do: `{"kind": "present", "steps": [...], "report": "...", "no_default": "..."}`
  `no_default` says why no recorded default would do; ShipLoop refuses a wait without it. The run then stops until
  the user's own reply resumes it.
- Blocked means work this stage cannot do (a missing target, account or approval, or a command with no replacement
  inside the stage). A retained command that does not run what it claims is a documentation fix made in this stage,
  then rerun, not a blocker. A problem this run can fix itself is repaired in this stage."""

OUTCOMES_TEXT = """\
The result file holds one `shiploop-state` block whose object has "outcome" and "summary" as top-level fields; do
not wrap it in action or result keys. An outcome other than done keeps headline and evidence_refs and drops the
done-only fields (work_items, assumptions, steps, test_commands, ...):
- repeat: {"outcome": "repeat", "summary": "<what is still open>"}
- blocked: {"outcome": "blocked", "blocked_by": "user | access | external", "summary": "<what stopped the work>"},
  plus "awaiting" only as described in reference#blocked
- revise: {"outcome": "revise", "summary": "<what in the step plan or test spec is wrong>"}: the item goes back to
  step-plan with this result as evidence
- replan (only where the packet allows it): {"outcome": "replan", "summary": "...", "work_items": [{"id": "...",
  "title": "...", "context": "..."}]}
A packet lists the outcomes its stage accepts; any other is refused."""

RECOVERY_TEXT = """\
After an interruption or a reset, run the packet's Recover command: it only reads the saved state and reprints the
current packet. Check the paths and the task and repository identity, then reconcile actual effects with the saved
history and relevant evidence before repeating work. If the same run cannot be located, keep recovery incomplete; do
not initialize a replacement or invent a callback. If paused or blocked, resolve the condition and follow the
printed resume route; if halted or done, stop. Keep the run directory and the Recover command in any durable handoff:
they locate state.md and store no other graph position."""

WORKSPACE_TEXT = """\
All product work happens in the execution checkout; run state, results and reports stay outside it. Each item is
assembled there, and ShipLoop commits its declared files when verify is accepted; the original branch is returned only
at release or handoff, after the assembled-candidate checks. There, `workspace plan-return` commits product files still uncommitted onto the
run branch (never run evidence or protected paths) and binds a path review;
decide every path with `workspace review-return --keep PATH... --exclude PATH...` (keep lasting work, exclude
transient output), then `workspace return`. The release packet prints the exact commands. No automatic push,
cleanup or publication is implied."""


def render(state: Mapping[str, Any], root: Path, version: str = "") -> str:
    """The reference file for this run (pure: the same state and package give the same text)."""
    root = Path(root)
    repo = Path(str(state.get("repo", "")))
    blocks = {
        "rules": guidance.common_text(state["planning_review"]).strip(),
        "blocked": AWAITING_TEXT,
        "outcomes": OUTCOMES_TEXT,
        "recovery": RECOVERY_TEXT + "\nRecover: python3 " + str(SCRIPTS / "shiploop") + " next --run-dir=" + str(root),
        "progress": guidance.PROGRESS_REPORTING.strip(),
        "requirements": guidance.REQUIREMENTS_RULES.strip(),
        "policies": "\n".join(
            ["Each label is what a packet or stage text names; open only the section a step needs."]
            + [f"- {label}: {REFERENCES / target}" for label, target in POLICIES]
            + [f"- Environment lifecycle note (host-authored, if present): {root / 'notes' / 'environment-lifecycle.md'}",
               f"- Repository knowledge index (host-authored, if present): {repo / 'SHIPLOOP.md'}",
               f"- ShipLoop skill card: {SCRIPTS.parent / 'SKILL.md'}",
               f"- State: {root / 'state.md'} · results: {root / 'results'} · inbox: {root / 'inbox'}"]),
        "workspace": WORKSPACE_TEXT,
    }
    lines = [VERSION_LINE.format(version=version), "# ShipLoop run reference", "",
             f"Run {state.get('run_id', '')}. Packets name a section as reference#<anchor>; open it only when the "
             "packet says to, or after a reset.", ""]
    for anchor, heading in SECTIONS:
        lines += [f"## {heading} {{#{anchor}}}", "", blocks[anchor], ""]
    return "\n".join(lines)


def package_version() -> str:
    """The ShipLoop version of this package, from its skill card's frontmatter ("" when it cannot be read)."""
    try:
        for line in (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").splitlines()[1:40]:
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"')
            if line.strip() == "---":
                break
    except OSError:
        pass
    return ""


def stale(root: Path, version: str) -> bool:
    """Whether the file is missing or was written by another ShipLoop version."""
    path = Path(root) / REFERENCE_FILE
    try:
        first = path.read_text(encoding="utf-8").split("\n", 1)[0]
    except OSError:
        return True
    return first != VERSION_LINE.format(version=version)
