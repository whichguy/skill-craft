"""What a work item declares it will change, and what it actually changed.

ShipLoop leaves an item's ``test`` stage out only on proof: the accepted step plan
declares ``paths``, records no test command (``test_commands_na``), and every
declared path is in a non-behavioural class of the package-owned catalog
(``references/path-classes.json``).  A path no rule matches counts as code.
After ``implement``, the item's real diff against its base tree must stay inside
those declared, non-behavioural paths, or ``done`` is refused (``scope_refusal``).

ShipLoop leaves an item's ``document`` stage out when the item's real diff since its
base tree touches no behavioural path (``behavioural``: code or test), owner decision 7
of 2026-10-10.  When the diff cannot be read, document is issued.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shlex
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import shiploop_lint as lint
import shiploop_test_loop as test_loop

CATALOG = Path(__file__).resolve().parent.parent / "references" / "path-classes.json"
# The stage an item without test commands leaves out (decided after implement, whose done is refused
# when the real diff leaves the declared non-behavioural paths).
TEST_STAGES = ("test",)
# The stage an item whose real diff touches no code or test path leaves out (owner decision 7, 2026-10-10).
DOCUMENT_STAGE = "document"
# Every stage ShipLoop can record as not applicable, in graph order.
LEFT_OUT_STAGES = TEST_STAGES + (DOCUMENT_STAGE,)
# The prefix a script-recorded stage's summary starts with; the E2E metrics and Run Review key on it.
NOT_APPLICABLE = "Not applicable to this item"


class ItemScopeError(ValueError):
    """A declared path list is malformed."""


def _catalog() -> Dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _matches(path: str, pattern: str) -> bool:
    if pattern.startswith("**/"):
        rest = pattern[3:]
        return fnmatch.fnmatchcase(path, rest) or fnmatch.fnmatchcase(path, "*/" + rest)
    return fnmatch.fnmatchcase(path, pattern)


def classify(path: str, catalog: Optional[Mapping[str, Any]] = None) -> str:
    """The first matching class for a repository-relative path; ``code`` when none matches."""
    catalog = catalog or _catalog()
    for name in catalog["order"]:
        if any(_matches(path, pattern) for pattern in catalog["classes"][name]):
            return name
    return "code"


_PATHLIKE = re.compile(r"^[\w.@-][\w./@+-]*$")
_EXTENSION = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")
_SHELL_WORDS = frozenset(("&&", "||", "|", ";", ">", ">>", "<", "2>&1", "&"))


def command_paths(command: str) -> List[str]:
    """The repository-relative file paths a shell command line names, best effort, in order and without repeats.

    Options, words without a slash or a file extension, absolute paths, paths that leave the repository (``../``), URLs,
    assignments and code passed inline (the one word ``node -e "..."`` quotes) are skipped; a ``file::test`` selector
    keeps its file.  The SG1 replay tool's reading (docs/experiments/sdlc-gates-20261030/sg1_proof_order.py
    ``proof_paths``) plus the ``../`` rule, which the shipped rule's replay needed: a Proof running
    ``../run/scratch/proofs/W1-S1.test.js`` (a script in the run's scratch folder) is not a repository test.
    """
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    paths = []
    for word in words:
        if word in _SHELL_WORDS or word.startswith("-") or "://" in word or word.startswith("/") or "=" in word:
            continue
        word = word.split("::", 1)[0]
        word = word[2:] if word.startswith("./") else word
        if word.startswith("../") or "/../" in word:
            continue
        if _PATHLIKE.match(word) and ("/" in word or _EXTENSION.search(word)) and not word.endswith("/"):
            paths.append(word)
    return list(dict.fromkeys(paths))


_CONFIRM_BY = re.compile(r"confirm by:\s*(.+?)(?:;\s*pass when|;|$)", re.I | re.S)
_INLINE_CODE = frozenset(("-e", "-c", "--eval", "-p"))
# A relative path inside inline code: not preceded by a path character, so the tail of an absolute path is not one.
_INLINE_PATH = re.compile(r"(?<![\w./@+-])[\w.@+-]+(?:/[\w.@+-]+)+")
# A quoted literal that is an absolute or home path or a URL, removed before _INLINE_PATH reads the code: a space or the
# colon of a port inside it would otherwise start a "relative" path in its tail.
_QUOTED_ELSEWHERE = re.compile(r"([\"'`])(?:/|~|[A-Za-z][\w+.-]*://)[^\"'`]*\1")


def inline_code_paths(command: str) -> List[str]:
    """The repository-relative file paths inside a command's inline code (the word after ``-e``, ``-c``, ``--eval`` or
    ``-p``), in order and without repeats.

    ``command_paths`` skips that word whole, so a Proof whose code runs ``node --test`` on a test file named inside it
    (a live run's S1: ``node -e '...execFileSync(process.execPath,["--test","test/service.test.js"])...'``) hid the
    path from rule A.  A path needs a slash and a file extension; an absolute path (a run's scratch script), a URL and
    one that leaves the repository (``../``) are skipped, as ``command_paths`` skips them.  A quoted absolute path or
    URL is removed whole first (``_QUOTED_ELSEWHERE``), so a space or a port inside it cannot leave a tail behind.
    """
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    paths = []
    for flag, code in zip(words, words[1:]):  # not itertools.pairwise: the floor is Python 3.9
        if flag not in _INLINE_CODE:
            continue
        for match in _INLINE_PATH.findall(_QUOTED_ELSEWHERE.sub(" ", code)):
            path = match.removeprefix("./")
            if not path.startswith("../") and "/../" not in path and _EXTENSION.search(path):
                paths.append(path)
    return list(dict.fromkeys(paths))


def confirm_by_command(text: Any) -> str:
    """The command a criterion's text names after ``Confirm by:``, up to ``; pass when`` or the first ``;``, or ""."""
    match = _CONFIRM_BY.search(str(text or ""))
    return match.group(1).strip() if match else ""


def generic_command(command: str) -> bool:
    """True for a suite command that runs nothing specific to a step (``npm test``, ``pytest``, ``python3 -m unittest
    -v``): no script or test path in any form (absolute, ``../`` or repository-relative) and no inline code.

    An empty ``command_paths`` is not enough: it skips absolute, ``../`` and inline-code words, and those are direct
    proofs (a scratch script, ``node -e`` assertions).  Treating them as generic would have refused 5 plans whose Proof
    tests the step (docs/experiments/proof-coverage-replay-20261101, Q1).
    """
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    if not words or _INLINE_CODE.intersection(words):
        return False
    return not any(("/" in word or _EXTENSION.search(word)) and "://" not in word
                   for word in words if not word.startswith("-"))


def _unwritten_test_refusal(name: str, path: str) -> str:
    """Rule A's refusal of step ``name``, whose Proof runs the test ``path`` that no earlier step's test stage writes."""
    return ("step " + name + "'s Proof runs " + path + ", which the item base does not have and no earlier step "
            "declares: implement writes no tests, and " + name + "'s test stage writes its tests only after its "
            "implement, so this Proof cannot pass when " + name + "'s implement reports done. Prove " + name + " with a "
            "command that runs its behaviour directly (a short script with assertions, an existing test or a recorded "
            "command), keep " + path + " in the focused command for the test stage, then run the same callback again.")


def proof_order_refusal(plan: Mapping[str, Any], exists: Callable[[str], bool]) -> str:
    """Why a step plan has a step whose Proof cannot pass when that step's implement reports done, or "" (SDLC gates D6,
    docs/shiploop-sdlc-gates-proposal-2026-10-30.md §5 SG1; replay evidence docs/experiments/question-record-20261031).

    A step's Proof runs at its implement's done, before that step's test stage writes its tests, and implement writes no
    tests.  ``exists(path)`` answers for the item base.  Rule A: a Proof that names a test-class path the base lacks
    cannot pass unless an earlier step declares that path in its ``paths`` (that step's test stage has written it by
    then), or the whole item is tests.  Rule B: a Proof that names a path the base lacks which only a later step declares
    needs that later step.  Paths are read from the Proof by ``command_paths``.  In the saved runs of 2026-10-03 to 10-31,
    9 of the 12 implement send-backs were this fault (8 on Codex Terra xhigh, 1 on DeepSeek flash).

    Rule A also reads the test-class paths inside a Proof's inline code (``inline_code_paths``; step-plan round 2,
    docs/experiments/step-plan-round2-20261101): replayed on 363 saved plans (352 at the commit each was accepted on,
    11 at their item's last lint tree), it flagged 2 steps, both a Proof that needed an unwritten test (one sent back, one in a run sent back for that Proof),
    and no Proof that passed implement.  Rule B is not extended to inline code: no replay supports it.

    Rule C: a Proof that is a generic suite command (``generic_command``, such as ``npm test``) cannot confirm an
    executed criterion of its step whose Confirm by (``confirm_by_command``) names a test-class path the base lacks and no
    earlier step declares.  Rule A's exemptions hold.  The step-plan duty says the Proof proves the step's criteria at its
    done.  A suite of the tests the base already has proves nothing about such a criterion: implement sends the plan back,
    or passes without proving it.  Replay evidence is in docs/experiments/proof-coverage-replay-20261101: rule C refused
    3 of 365 judged plans (2 later sent back, 1 passed unproven) and no plan whose Proof tests the step directly.
    """
    item_paths = [str(path) for path in plan.get("paths") or ()]
    if item_paths and all(classify(path) == "test" for path in item_paths):
        return ""
    steps = [step for step in plan.get("steps") or () if isinstance(step, Mapping)]
    ids = [str(step.get("id")) for step in steps]
    declared: Dict[str, List[str]] = {}
    for step in steps:
        for path in step.get("paths") or ():
            declared.setdefault(str(path), []).append(str(step.get("id")))
    criteria = {str(row.get("id")): row for row in plan.get("criteria") or () if isinstance(row, Mapping)}
    for index, step in enumerate(steps):
        proof = step.get("proof")
        if not isinstance(proof, str):
            continue
        name, earlier, later = ids[index], set(ids[:index]), set(ids[index + 1:])
        for path in command_paths(proof):
            if exists(path):
                continue
            owners = declared.get(path, [])
            if classify(path) == "test" and not earlier.intersection(owners):
                return _unwritten_test_refusal(name, path)
            if later.intersection(owners) and name not in owners and not earlier.intersection(owners):
                return ("step " + name + "'s Proof reads " + path + ", which the item base does not have and only a "
                        "later step (" + ", ".join(owner for owner in owners if owner in later) + ") declares: the "
                        "Proof needs that later step's work. Move that work into " + name + " or an earlier step, or "
                        "prove " + name + " without it, then run the same callback again.")
        for path in inline_code_paths(proof):
            if not exists(path) and classify(path) == "test" and not earlier.intersection(declared.get(path, [])):
                return _unwritten_test_refusal(name, path)
        if not generic_command(proof):
            continue
        for ident in step.get("criteria") or ():
            row = criteria.get(str(ident)) or {}
            if row.get("confirm") != "executed":
                continue
            for path in command_paths(confirm_by_command(row.get("text"))):
                if exists(path) or classify(path) != "test" or earlier.intersection(declared.get(path, [])):
                    continue
                return ("step " + name + "'s Proof `" + proof + "` runs only the tests the item base has, but "
                        + str(ident) + " is confirmed by " + path + ", which the item base does not have and no earlier "
                        "step declares: implement writes no tests, so this Proof cannot confirm " + str(ident) + " when "
                        + name + "'s implement reports done. Prove " + name + " with a command that runs its behaviour "
                        "directly (a short script with assertions, an existing test or a recorded command), keep " + path
                        + " in the focused command for the test stage, then run the same callback again.")
    return ""


def behavioural_paths(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> List[str]:
    """The entries of ``paths`` that count as code or test (any class outside ``non_behavioural``)."""
    catalog = catalog or _catalog()
    allowed = set(catalog["non_behavioural"])
    return [path for path in paths if classify(path, catalog) not in allowed]


def behavioural(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> bool:
    """True when any of ``paths`` is code or test, so the change needs the document stage.

    ``paths`` are repository-relative (an item's changed paths); a path no catalog rule matches counts as code.
    """
    if isinstance(paths, (str, bytes)) or not all(isinstance(path, str) for path in paths):
        raise ItemScopeError("behavioural takes a list of repository-relative paths")
    return bool(behavioural_paths(paths, catalog))


def normalise_paths(value: Any) -> List[str]:
    """Validate a step plan's ``paths``: repository-relative files or globs the item will change."""
    if not isinstance(value, list) or not value:
        raise ItemScopeError("paths must list the repository-relative files or globs this item will change")
    rows: List[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip() or "\n" in entry:
            raise ItemScopeError("each path must be one nonblank repository-relative path or glob")
        path = entry.strip()
        path = path[2:] if path.startswith("./") else path
        if path.startswith("/") or ".." in Path(path).parts:
            raise ItemScopeError("paths must stay inside the repository: " + entry)
        rows.append(path)
    if len(set(rows)) != len(rows):
        repeated = sorted({row for row in rows if rows.count(row) > 1})
        raise ItemScopeError("paths must not repeat: " + ", ".join(repeated))
    return rows


def no_test_item(state: Mapping[str, Any], work_item: str) -> Optional[str]:
    """The reason this item's test stage can be left out, or ``None`` when it must run.

    Proof needs the final accepted step plan to record no test command with a
    reason, and to declare paths that are all non-behavioural.
    """
    _action, result = test_loop._step_plan(state, work_item)
    if result.get("test_commands") != [] or not result.get("test_commands_na") or not result.get("paths"):
        return None
    if behavioural_paths(result["paths"]):
        return None
    return ("the step plan records no test command (" + str(result["test_commands_na"]).rstrip(".")
            + ") and declares only non-code paths: " + ", ".join(result["paths"]))


def no_document_item(run_dir: Path, work_item: str) -> Optional[str]:
    """The reason this item's document stage can be left out, or ``None`` when it must run.

    Proof is the item's real diff since its base tree: it must be readable, and touch no code or test path.
    An item that changed no file gets no document stage either: there is no behaviour to document.
    """
    changed = changed_paths(run_dir, work_item)
    if changed is None or behavioural(changed):
        return None
    if not changed:
        return "the item changed no file since its base"
    return "the item's changes since its base touch no code or test path: " + ", ".join(changed)


def left_out(state: Mapping[str, Any], work_item: str, stage: str,
             run_dir: Optional[Path] = None) -> Optional[str]:
    """The reason ShipLoop records ``stage`` as not applicable to this item, or ``None`` when it is issued.

    ``test`` is left out when the step plan records no test command and declares only non-code paths;
    ``document`` when the item's real diff (read from ``run_dir``) touches no code or test path.  Without
    ``run_dir`` document is always issued.
    """
    if stage in TEST_STAGES:
        return no_test_item(state, work_item)
    if stage == DOCUMENT_STAGE and run_dir is not None:
        return no_document_item(Path(run_dir), work_item)
    return None


def declared(state: Mapping[str, Any], work_item: str) -> List[str]:
    """Paths the work item's step plan declared, or an empty list."""
    _action, result = test_loop._step_plan(state, work_item)
    return list(result.get("paths") or ())


def changed_paths(run_dir: Path, work_item: str, *, timeout: float = 60.0) -> Optional[List[str]]:
    """Repository-relative paths the item changed since its base tree; ``None`` when unknown."""
    return changed_since(run_dir, lint.read_base(Path(run_dir), work_item), timeout=timeout)


# Why an item's changed paths are unknown: what a packet prints after "not computed: " and what commit_item raises with.
NO_BASE = "no base snapshot was captured when it started"
UNREADABLE = "its diff against the base snapshot could not be read"


def changed_paths_or_reason(run_dir: Path, work_item: str, *,
                            timeout: float = 60.0) -> Tuple[Optional[List[str]], str]:
    """(``changed_paths``, '') when the item's changes can be read, else (None, why not: ``NO_BASE`` or ``UNREADABLE``)."""
    base = lint.read_base(Path(run_dir), work_item)
    if not base or not base.get("toplevel") or not base.get("tree"):
        return None, NO_BASE
    changed = changed_since(run_dir, base, timeout=timeout)
    return (changed, "") if changed is not None else (None, UNREADABLE)


def changed_since(run_dir: Path, base: Optional[Mapping[str, Any]], *,
                  timeout: float = 60.0) -> Optional[List[str]]:
    """Repository-relative paths whose working content differs from ``base``; ``None`` when unknown.

    ``base`` is a snapshot record with ``toplevel``, ``prefix`` and ``tree`` (``lint.read_base``, or the
    checkout snapshot an expectation entry records).  Untracked files count; ignored files and ShipLoop runtime
    metadata do not.
    """
    if not base or not base.get("toplevel") or not base.get("tree"):
        return None
    top = Path(base["toplevel"])
    prefix = str(base.get("prefix") or ".")
    index = Path(run_dir) / "lint" / "tmp" / ("scope-" + uuid.uuid4().hex + ".index")
    try:
        current = lint.snapshot_tree(top, Path(run_dir), index, prefix=prefix, timeout=timeout)
    except lint.LintError:
        return None
    finally:
        if index.exists():
            index.unlink()
    result = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--name-only", base["tree"], current,
                       timeout=timeout)
    if result.returncode:
        return None
    paths = [raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw]
    lead = "" if prefix in (".", "") else prefix.rstrip("/") + "/"
    return sorted(path[len(lead):] for path in paths
                  if path.startswith(lead) and not lint._runtime_path(path))


def outside(paths: Sequence[str], allowed: Sequence[str]) -> List[str]:
    """Changed paths that match none of the declared paths or globs (ShipLoop's knowledge home aside)."""
    return [path for path in paths if not path.startswith("docs/shiploop/") and not any(path == rule or _matches(path, rule)
                                              or fnmatch.fnmatchcase(path, rule) for rule in allowed)]


def withheld(run_dir: Path, state: Mapping[str, Any]) -> Optional[Callable[[str], bool]]:
    """The paths a worktree run never commits (``workspace.never_committed`` over workspace.md's exclusions).

    ``None`` for an in-place run, which has no workspace manifest.  Raises ItemScopeError when the manifest of a
    worktree run cannot be read.
    """
    if state.get("execution_mode") != "navigator-worktree":
        return None
    import shiploop_workspace as workspace
    try:
        excluded = workspace.excluded_paths(Path(run_dir).parent)
    except workspace.WorkspaceError as exc:
        raise ItemScopeError("cannot read the workspace manifest: " + str(exc)) from exc
    return lambda path: workspace.never_committed(path, excluded)


def commit_scope(changed: Sequence[str], allowed: Sequence[str],
                 never: Optional[Callable[[str], bool]] = None) -> Tuple[List[str], List[str]]:
    """Split an item's changed paths into (those ShipLoop commits, those it leaves).

    ShipLoop commits the paths the step plan declared (``allowed``), ShipLoop's own knowledge home and any other
    changed file in the ``docs`` path class: the document stage edits documentation, and a README or AGENTS.md it adds
    outside the declared paths was otherwise committed by the model by hand (3 of 16 recorded runs).  A path ``never``
    holds (``withheld``: a worktree run's protected and caller-excluded paths, which ``workspace.commit_leftovers``
    skips too) is never committed.  Every other undeclared file is left: plan-return commits it in a worktree run.
    """
    undeclared = set(outside(changed, allowed))
    left = [path for path in changed
            if (never is not None and never(path)) or (path in undeclared and classify(path) != "docs")]
    return [path for path in changed if path not in left], left


def commit_item(run_dir: Path, state: Mapping[str, Any], work_item: str,
                message: str) -> Tuple[str, List[str]]:
    """Commit the item's changed files per ``commit_scope``: declared paths, documentation and the knowledge home.

    Returns (new commit ID or '', changed paths left alone (undeclared and not documentation, or withheld by the
    workspace)).  The model never writes this commit: committing is mechanical (SPEC S-5), and headless hosts
    refuse model-written ``git commit`` shell.  Raises ItemScopeError when the item's changes cannot be read: an unknown
    change is never reported as nothing to commit.
    """
    import shiploop_git
    changed, why = changed_paths_or_reason(run_dir, work_item)
    if changed is None:
        raise ItemScopeError("the item's changes cannot be read (" + why + ")")
    if not changed:
        return "", []
    chosen, undeclared = commit_scope(changed, declared(state, work_item), withheld(run_dir, state))
    try:
        committed = shiploop_git.commit_paths(Path(str(state["repo"])), chosen, message)
    except shiploop_git.CommitError as exc:
        raise ItemScopeError(str(exc)) from exc
    return committed.commit, undeclared


def scope_refusal(run_dir: Path, state: Mapping[str, Any], work_item: str) -> str:
    """Why implement's done is refused for an item whose test stage is left out ('' when it is fine)."""
    reason = no_test_item(state, work_item)
    if reason is None:
        return ""
    changed = changed_paths(run_dir, work_item)
    if changed is None:
        return ("ShipLoop leaves this item's test stage out because its step plan declares only non-code "
                "paths, but it cannot read the item's changes to confirm that. Report send-back so the step plan "
                "records test commands.")
    code = behavioural_paths(changed)
    stray = outside(changed, declared(state, work_item))
    if not code and not stray:
        return ""
    lines = ["ShipLoop leaves this item's test stage out because its step plan declared only non-code paths ("
             + ", ".join(declared(state, work_item)) + "), but the change goes further:"]
    lines += ["- " + path + " (" + classify(path) + ")" for path in code]
    lines += ["- " + path + " (not declared)" for path in stray if path not in code]
    lines.append("Keep the change within the declared paths, or report send-back naming these paths so the step "
                 "plan declares the paths and test commands this change needs; its test stage then runs.")
    return "\n".join(lines)


__all__ = ("DOCUMENT_STAGE", "LEFT_OUT_STAGES", "NOT_APPLICABLE", "TEST_STAGES", "ItemScopeError",
           "NO_BASE", "UNREADABLE",
           "behavioural", "behavioural_paths", "changed_paths", "changed_paths_or_reason", "changed_since", "classify",
           "command_paths", "commit_item", "confirm_by_command", "generic_command", "proof_order_refusal",
           "commit_scope", "declared", "left_out", "no_document_item", "no_test_item", "normalise_paths", "outside",
           "scope_refusal", "withheld")
