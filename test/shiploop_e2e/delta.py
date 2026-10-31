#!/usr/bin/env python3
"""The `delta` block of metrics.json: what a run changed against the head it started from, and what it left for the next run.

A record beside the verdicts, built the way counters.py's blocks are (once, in run.py's main, so a regrade adds it too), changing
no verdict, exit code or baseline row. Absent means unknown: a part this module cannot read is null with its reason in
``delta_unmeasured``, never 0 and never a pass; an empty list or a zero is a measured none.

Why it exists (docs/shiploop-multipass-journal.md, 2026-10-31). ShipLoop keeps a product's knowledge in three living files
(``docs/shiploop/spec.md``, ``environment.md``, ``architecture.md``) and everything about one run in its run folder. A run after the
first starts from those files. Eight saved runs (four pass-1 and pass-2 pairs of the ticket pair) showed that the permanent files
are not where a second pass leaves them tidy: it appended its decision after ``## Superseded`` (the engine then marks a live
decision superseded), and it appended dated sections of its own to ``environment.md``. This block measures that, and the
other half of what a follow-on is for: that the run built on what the first run left and did not build it again.

    ids        spec.md's R-<n> and architecture.md's AD-<n> entries, by the engine's own parser (shiploop_knowledge_home._entries):
               ``added``, ``dropped``, ``changed`` (an earlier entry whose text differs, whitespace aside), ``retired_by_run`` (an
               earlier entry moved under Retired or Superseded) and ``born_retired`` (an entry this run added that sits under
               Retired or Superseded: a live entry the engine reads as retired).
    placement  per living file: the title, the level-2 headings that are no named section (``stray``; ``stray_added`` by this run),
               a named section that appears twice (``duplicate``), ``named_missing`` and ``named_empty`` (the engine's notice rule),
               headings this run put under Retired or Superseded (``added_under_retired``), the named sections whose text the
               run changed (``changed_sections``: where an in-place update landed), bytes before and after, and
               ``relative_wording``: phrases in the lines the run added that name "this run" ("current request"), which mean
               something else in the next run. A heuristic list to confirm, not a count to trust.
    footprint  the files the run changed since its start head, by class (source, tests, docs, living), with lines added and removed;
               ``prior_tests_modified`` (tests that existed at the start and were changed or deleted) and how many of the start's
               source files the run modified: the blast radius of the new feature.
    writes     how the host handled each living file, read from its shell commands and tool calls: ``reads``, ``appends`` (a ``>>``
               redirect or ``tee -a``: the way a decision lands after the last heading) and ``other_writes``. Heuristic.
    plan       the run's own records read against the IDs it added or changed (``delta``) and the IDs it kept as they were
               (``preserved``): the ``follows`` of its step plans, the ``requirement`` of its test cases and its ``primary`` set.
    handoff    what the next run finds: the release-verify lessons commit and the size of its three fields, the named sections
               each living file still lacks, and whether the files are tracked at the head.

Consumers: the owner reading a follow-on or a chain; ``delta.py OUTPUT...`` prints one line per run; and the qualification of any
change to how ShipLoop's stages write the living files (a placement rule or a consolidation duty), which is read from
``born_retired``, ``stray_added`` and ``appends`` before and after. The block is never a verdict until a style has a baseline for
it and a later dated amendment to SPEC.md says so.

Reads Git through plumbing only (show, diff, ls-tree, log, rev-parse) and the files of the run folder; it writes nothing.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))

import counters  # noqa: E402  (_starting_point and _git: the one reading of a run's starting head, and of Git)
import metrics  # noqa: E402  (ToolLog, events, RECORD_BLOCK)
import shiploop_knowledge_home as knowledge  # noqa: E402  (the engine's own entry parser and section names)

FILES = knowledge.LIVING
PREFIX = {"spec.md": "R", knowledge.ARCHITECTURE: "AD"}
# The heading a retired entry moves under, by file (``knowledge._ENTRY_FILES``): the word a heading starts with.
RETIRED_WORD = {"spec.md": "retired", knowledge.ARCHITECTURE: "superseded"}
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # Git's empty tree: a fresh run is measured against nothing

TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs"}
TEST_FILE = re.compile(r"(?:^|[._-])(?:test|tests|spec)(?:[._-]|$)", re.I)
DOC_SUFFIX = (".md", ".rst", ".adoc")
# Never part of the product: installed, compiled, a log, or ShipLoop's own run folders inside a checkout.
NOISE = re.compile(r"(?:^|/)(?:node_modules|__pycache__|\.shiploop[\w-]*)(?:/|$)|\.(?:log|pyc)$")
CLASSES = ("source", "tests", "docs", "living")
RELATIVE = re.compile(r"\b(?:current|this|new|latest|present)\s+(?:request|run|change|feature|iteration|pass|prompt)\b", re.I)
HEURISTIC = ("writes, relative_wording and the class of a path are heuristics: lists to confirm, not counts to trust; no hit is "
             "not proof and a hit can be quoted text")


def _out(work: Path, *args: str) -> str | None:
    done = counters._git(work, *args)
    return done.stdout.decode(errors="replace") if done.returncode == 0 else None


def _show(work: Path, rev: str, rel: str) -> str | None:
    """The file as ``rev`` holds it, or None when ``rev`` has no such file."""
    return _out(work, "show", f"{rev}:{rel}")


def _number(ident: str) -> tuple[str, int]:
    """The sort key of an ID: its prefix, then its number, so R-10 follows R-9 and AD-2 never ties with R-2."""
    prefix, _, digits = ident.partition("-")
    return prefix, int(digits)


def _squeeze(text: str) -> str:
    return " ".join(text.split())


# --- ids ----------------------------------------------------------------------------------------------------------------

def ids_block(prior_text: str | None, final_text: str | None, prefix: str) -> dict:
    """The ``ids`` entry of one file: the entries the run added, dropped, changed, retired and filed as retired when new."""
    prior = knowledge._entries(prior_text, prefix) if prior_text and prior_text.strip() else {}
    final = knowledge._entries(final_text, prefix) if final_text and final_text.strip() else {}
    kept = prior.keys() & final.keys()
    new = final.keys() - prior.keys()
    changed = sorted((i for i in kept if _squeeze(prior[i].text) != _squeeze(final[i].text)), key=_number)
    return {"prefix": prefix, "prior": len(prior), "final": len(final),
            "added": sorted(new, key=_number),
            "dropped": sorted(prior.keys() - final.keys(), key=_number),
            "changed": changed,
            "unchanged": len(kept) - len(changed),
            "retired_by_run": sorted((i for i in kept if final[i].retired and not prior[i].retired), key=_number),
            "born_retired": sorted((i for i in new if final[i].retired), key=_number)}


# --- placement ----------------------------------------------------------------------------------------------------------

def _outline(text: str | None) -> list[tuple[int, int, str]]:
    return knowledge._outline(text.splitlines()) if text else []


def _added_lines(prior_text: str | None, final_text: str | None) -> list[str]:
    diff = difflib.unified_diff((prior_text or "").splitlines(), (final_text or "").splitlines(), lineterm="", n=0)
    return [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]


def section_texts(text: str | None, names) -> dict[str, str]:
    """The text of each named section of a living file (the first heading that starts with the name), its heading included, up to the
    next heading of the same or a higher level: what a stage that updates the section in place changes."""
    lines = (text or "").splitlines()
    outline = knowledge._outline(lines)
    found: dict[str, str] = {}
    for position, (index, level, title) in enumerate(outline):
        for word in names:
            if word not in found and title.lower().startswith(word.lower()):
                end = next((at for at, deeper, _ in outline[position + 1:] if deeper <= level), len(lines))
                found[word] = "\n".join(lines[index:end])
    return found


def placement_block(name: str, prior_text: str | None, final_text: str | None) -> dict:
    """The ``placement`` entry of one living file; None text is a file that did not exist."""
    named = knowledge.SECTIONS.get(name, ())

    def is_named(title: str) -> bool:
        return any(title.lower().startswith(word.lower()) for word in named)

    now, before = _outline(final_text), _outline(prior_text)
    level2 = [title for _, level, title in now if level == 2]
    stray = [title for title in level2 if not is_named(title)]
    stray_before = [title for _, level, title in before if level == 2 and not is_named(title)]
    # Multiset difference, so a section the run wrote twice under one title counts twice.
    stray_added = list(stray)
    for title in stray_before:
        if title in stray_added:
            stray_added.remove(title)
    lines = (final_text or "").splitlines()
    states = {word: knowledge._section_state(lines, now, word) for word in named} if final_text else {}
    word = RETIRED_WORD.get(name)
    prior_titles = {title for _, _, title in before}
    under, chain = [], []
    for _, level, title in now:
        while chain and chain[-1][0] >= level:
            chain.pop()
        if word and any(parent.lower().startswith(word) for _, parent in chain) and title not in prior_titles:
            under.append(title)
        chain.append((level, title))
    added = _added_lines(prior_text, final_text)
    relative = [match.group(0) for line in added for match in RELATIVE.finditer(line)]
    before_text, after_text = section_texts(prior_text, named), section_texts(final_text, named)
    changed = [word for word in named if _squeeze(before_text.get(word, "")) != _squeeze(after_text.get(word, ""))]

    def title_of(text: str | None) -> str | None:
        return next((title for _, level, title in _outline(text) if level == 1), None)

    return {"title": {"prior": title_of(prior_text), "final": title_of(final_text)},
            "level2": len(level2), "stray": stray, "stray_added": stray_added,
            "duplicate": sorted(word_ for word_ in named
                                if sum(title.lower().startswith(word_.lower()) for title in level2) > 1),
            "named_missing": [w for w, state in states.items() if state == "missing"],
            "named_empty": [w for w, state in states.items() if state == "empty"],
            "added_under_retired": under,
            "changed_sections": changed,
            "bytes": {"prior": len((prior_text or "").encode()), "final": len((final_text or "").encode())},
            "relative_wording": {"n": len(relative), "examples": relative[:5]}}


# --- footprint ----------------------------------------------------------------------------------------------------------

def classify(path: str) -> str:
    """The class of a path: ``living`` (the knowledge home), ``tests``, ``docs`` or ``source`` (everything else)."""
    if path == knowledge.HOME or path.startswith(knowledge.HOME + "/"):
        return "living"
    pure = PurePosixPath(path)
    if any(part.lower() in TEST_DIRS for part in pure.parts[:-1]) or TEST_FILE.search(pure.name):
        return "tests"
    if pure.parts[0] == "docs" or pure.name.lower().endswith(DOC_SUFFIX):
        return "docs"
    return "source"


def footprint_block(work: Path, start: str | None, head: str) -> dict | None:
    """The files changed from ``start`` (the empty tree when there is none) to ``head``, by class; None when Git cannot say."""
    base = start or EMPTY_TREE
    names, numbers, tree = (_out(work, "diff", "--name-status", "--no-renames", base, head),
                            _out(work, "diff", "--numstat", "--no-renames", base, head),
                            _out(work, "ls-tree", "-r", "--name-only", base))
    if names is None or numbers is None or tree is None:
        return None
    by_class = {name: {"added": 0, "modified": 0, "deleted": 0, "insertions": 0, "deletions": 0} for name in CLASSES}
    prior_tests_modified, source_touched = [], 0
    for line in names.splitlines():
        status, _, path = line.partition("\t")
        if not path or NOISE.search(path):
            continue
        kind = classify(path)
        key = {"A": "added", "M": "modified", "D": "deleted"}.get(status[:1])
        if key is None:
            continue
        by_class[kind][key] += 1
        if kind == "tests" and key != "added":
            prior_tests_modified.append(path)
        if kind == "source" and key != "added":
            source_touched += 1
    for line in numbers.splitlines():
        added, removed, path = line.split("\t", 2) if line.count("\t") >= 2 else (None, None, None)
        if path is None or NOISE.search(path):
            continue
        by_class[classify(path)]["insertions"] += int(added) if added.isdigit() else 0  # a binary file shows "-"
        by_class[classify(path)]["deletions"] += int(removed) if removed.isdigit() else 0
    prior_source = sum(1 for path in tree.splitlines() if path and not NOISE.search(path) and classify(path) == "source")
    return {"by_class": by_class, "prior_tests_modified": sorted(prior_tests_modified),
            "prior_source_files": prior_source, "prior_source_modified": source_touched}


# --- writes -------------------------------------------------------------------------------------------------------------

def _write_patterns(rel: str) -> tuple[re.Pattern, re.Pattern]:
    """(append, other write) patterns for a shell command that names ``rel``."""
    target = r"[\"']?\S*" + re.escape(rel)
    append = re.compile(r">>\s*" + target + r"|\btee\s+-a\s+" + target)
    write = re.compile(r"(?<![>\w])>\s*" + target + r"|\btee\s+(?!-a)" + target + r"|\b(?:sed|perl)\s+-\w*i\b[^\n]*" + re.escape(rel))
    return append, write


CODE_WRITE = re.compile(r"""open\([^)]*['"][wa]\+?['"]|\.write_text\(|\.write\(|writeFile(?:Sync)?\(|appendFile(?:Sync)?\(""")


def writes_block(tools) -> dict:
    """How the host handled each living file, from the tool log's shell commands and tool calls (heuristic, see HEURISTIC)."""
    found = {name: {"reads": 0, "appends": 0, "other_writes": 0} for name in FILES}
    for call in getattr(tools, "sequence", []):
        command, paths, tool = call.get("command") or "", call.get("paths") or [], call.get("tool") or ""
        for name in FILES:
            rel = f"{knowledge.HOME}/{name}"
            row = found[name]
            if rel in command:
                append, write = _write_patterns(rel)
                if append.search(command):
                    row["appends"] += 1
                elif write.search(command) or CODE_WRITE.search(command):
                    row["other_writes"] += 1
                else:
                    row["reads"] += 1
            elif any(str(path).endswith(rel) for path in paths):
                row["other_writes" if metrics.WRITE_TOOL.search(tool) else "reads"] += 1
    return found


# --- plan ---------------------------------------------------------------------------------------------------------------

def _state(run_dir: Path | None) -> dict | None:
    if run_dir is None:
        return None
    try:
        found = metrics.RECORD_BLOCK.search((Path(run_dir) / "state.md").read_text(errors="replace"))
        state = json.loads(found.group(1)) if found else None
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) and isinstance(state.get("history"), list) else None


def plan_block(run_dir: Path | None, delta: set[str], prior: set[str]) -> tuple[dict | None, str | None]:
    """(the ``plan`` block, why not): the run's step-plan ``follows``, test-case ``requirement`` and spec ``primary`` read against the
    IDs it added or changed (``delta``) and the IDs the start head already held (``prior``): an ID in neither is ``unknown``. Only a
    result the engine accepted (outcome ``done``) is read."""
    state = _state(run_dir)
    if state is None:
        return None, "the run's state.md cannot be read, so its plan is unknown"

    def split(values) -> dict:
        row = {"delta": 0, "preserved": 0, "unknown": 0}
        for value in values:
            row["delta" if value in delta else "preserved" if value in prior else "unknown"] += 1
        return row

    accepted = state.get("accepted") if isinstance(state.get("accepted"), dict) else {}
    follows, primary, requirements = set(), set(), []
    for row in state["history"]:
        result = accepted.get(row.get("action")) if row.get("outcome") == "done" else None
        if not isinstance(result, dict):
            continue
        if row.get("stage") == "step-plan":
            follows.update(v for v in result.get("follows") or [] if isinstance(v, str))
        elif row.get("stage") == "spec":
            primary.update(v for v in result.get("primary") or [] if isinstance(v, str))
        elif row.get("stage") == "test-spec":
            requirements += [case.get("requirement") for case in result.get("test_cases") or [] if isinstance(case, dict)]
    return {"delta_ids": sorted(delta, key=_number), "primary": split(sorted(primary)),
            "step_plan_follows": split(sorted(follows)),
            "test_cases": {**split(r for r in requirements if isinstance(r, str)),
                           "no_requirement": sum(1 for r in requirements if not isinstance(r, str))}}, None


# --- handoff ------------------------------------------------------------------------------------------------------------

def handoff_block(work: Path, start: str | None, head: str, finals: dict[str, str | None]) -> dict:
    """What the next run finds: the lessons commit of this run, the sections still lacking, and whether the files are tracked."""
    shown = _out(work, "log", "--format=%H%x00%s%x00%b%x1e", f"{start}..{head}" if start else head) or ""
    lessons, sizes = None, None
    labels = {label: key for key, label in knowledge.LESSON_FIELDS}
    for record in shown.split("\x1e"):
        parts = record.lstrip("\n").split("\0", 2)
        if len(parts) == 3 and knowledge.LESSONS_SUBJECT.fullmatch(parts[1]):
            lessons, sizes = parts[0][:12], dict.fromkeys(labels.values(), 0)
            current = None
            for line in parts[2].splitlines():
                if line.strip() in labels:
                    current = labels[line.strip()]
                elif current and line.startswith("Open items left at release-verify"):
                    current = None
                elif current:
                    sizes[current] += len(line.strip())
            break
    tracked = _out(work, "ls-tree", "-r", "--name-only", head, "--", knowledge.HOME) or ""
    sections = {}
    for name, text in finals.items():
        lines = (text or "").splitlines()
        outline = knowledge._outline(lines)
        states = {word: knowledge._section_state(lines, outline, word) for word in knowledge.SECTIONS.get(name, ())}
        sections[name] = {"missing": [w for w, s in states.items() if s == "missing"],
                          "empty": [w for w, s in states.items() if s == "empty"]} if text else None
    return {"lessons_commit": lessons, "lessons_chars": sizes, "sections": sections,
            "tracked": {name: f"{knowledge.HOME}/{name}" in tracked.splitlines() for name in FILES}}


# --- the block ----------------------------------------------------------------------------------------------------------

def _kind(out: Path) -> tuple[str, str | None]:
    """(``follow-on``, ``base``, ``seed`` or ``fresh``; the followed case) from the run's invocation record."""
    try:
        record = json.loads((Path(out) / "invocation.json").read_text())
    except (OSError, ValueError):
        return "unknown", None
    follow = record.get("follow_on") if isinstance(record, dict) else None
    if follow:
        return "follow-on", follow.get("prior_case")
    return ("base" if record.get("base") else "seed" if record.get("seeded") else "fresh"), None


def build(out: Path, run_dir: Path | None, tools) -> dict:
    """The two keys run.py adds to metrics.json: ``delta`` and ``delta_unmeasured``."""
    out = Path(out)
    work = out / "work"
    if not (work / ".git").exists():
        return {"delta": None, "delta_unmeasured": {"delta": "the run folder has no work repository"}}
    start, why = counters._starting_point(out, work)
    if why:
        return {"delta": None, "delta_unmeasured": {"delta": why}}
    head = counters._commit_id(work, "HEAD")
    if head is None:
        return {"delta": None, "delta_unmeasured": {"delta": "the work repository has no commit"}}
    unmeasured: dict = {}
    priors = {name: _show(work, start, f"{knowledge.HOME}/{name}") if start else None for name in FILES}
    finals = {}
    for name in FILES:
        path = work / knowledge.HOME / name
        try:
            finals[name] = path.read_text(encoding="utf-8-sig", errors="replace") if path.is_file() else None
        except OSError:
            finals[name] = None
    ids = {name: ids_block(priors[name], finals[name], prefix) for name, prefix in PREFIX.items()}
    changed = {i for entry in ids.values() for key in ("added", "changed") for i in entry[key]}
    held = {i for name, prefix in PREFIX.items() if priors[name] for i in knowledge._entries(priors[name], prefix)}
    plan, plan_why = plan_block(run_dir, changed, held)
    if plan is None:
        unmeasured["plan"] = plan_why
    foot = footprint_block(work, start, head)
    if foot is None:
        unmeasured["footprint"] = "Git could not list the changes since the starting head"
    kind, followed = _kind(out)
    block = {"basis": {"kind": kind, "followed_case": followed, "start_head": start, "head": head},
             "ids": ids,
             "placement": {name: placement_block(name, priors[name], finals[name]) for name in FILES},
             "footprint": foot, "writes": writes_block(tools), "plan": plan,
             "handoff": handoff_block(work, start, head, finals), "heuristics": HEURISTIC}
    return {"delta": block, "delta_unmeasured": unmeasured}


def safe_build(out: Path, run_dir: Path | None, tools) -> dict:
    """``build``, failing open like counters.safe_build: a part that raises is null with the error as its reason, never a verdict."""
    try:
        return build(out, run_dir, tools)
    except Exception as exc:  # noqa: BLE001 - a record never takes the run's metrics down
        reason = "failed: " + type(exc).__name__ + ": " + " ".join(str(exc).split())[:200]
        return {"delta": None, "delta_unmeasured": {"delta": reason}}


# --- the command line: the same block for a saved run --------------------------------------------------------------------

def saved(out: Path) -> dict:
    """The block for a run folder already on disk: its tool log is read again from events.jsonl and its run folder from
    shiploop-run.json, the way a regrade finds them."""
    out = Path(out)
    tools = metrics.ToolLog()
    if (out / "events.jsonl").is_file():
        for number, event in metrics.events(out / "events.jsonl"):
            tools.feed(event, None, number)
    try:
        named = json.loads((out / "shiploop-run.json").read_text()).get("run_dir")
    except (OSError, ValueError, AttributeError):
        named = None
    run_dir = Path(named) if isinstance(named, str) and named else None  # Path("") is the current folder, so never build one from nothing
    return safe_build(out, run_dir if run_dir and run_dir.is_dir() else None, tools)


def line(name: str, block: dict) -> str:
    """One line per run: the facts a reader compares across passes."""
    d = block.get("delta")
    if d is None:
        return f"{name}: not measured ({block['delta_unmeasured'].get('delta')})"
    spec, arch = d["ids"]["spec.md"], d["ids"][knowledge.ARCHITECTURE]
    place = d["placement"]
    foot = d["footprint"] or {}
    plan = d["plan"] or {}
    written = d["writes"]

    def moves(entry: dict) -> str:
        return (f"+{len(entry['added'])} ~{len(entry['changed'])} -{len(entry['dropped'])} "
                f"retired {len(entry['retired_by_run'])} born-retired {len(entry['born_retired'])}")

    follows, tests = plan.get("step_plan_follows") or {}, plan.get("test_cases") or {}
    return (f"{name}: {d['basis']['kind']} | R {moves(spec)} | AD {moves(arch)} | "
            f"stray+ spec {len(place['spec.md']['stray_added'])} env {len(place['environment.md']['stray_added'])} "
            f"arch {len(place[knowledge.ARCHITECTURE]['stray_added'])} | "
            f"appends spec {written['spec.md']['appends']} env {written['environment.md']['appends']} "
            f"arch {written[knowledge.ARCHITECTURE]['appends']} | "
            f"prior tests modified {len(foot.get('prior_tests_modified') or [])} src "
            f"{foot.get('prior_source_modified', '?')}/{foot.get('prior_source_files', '?')} | "
            f"follows d{follows.get('delta', '?')}/p{follows.get('preserved', '?')} "
            f"tests d{tests.get('delta', '?')}/p{tests.get('preserved', '?')} | "
            f"lessons {d['handoff']['lessons_commit'] or 'none'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The delta block of metrics.json for one or more saved run folders.")
    parser.add_argument("outputs", nargs="+", type=Path, help="run output folders (the ones run.py wrote)")
    parser.add_argument("--json", action="store_true", help="print each full block as JSON instead of one line per run")
    args = parser.parse_args(argv)
    for out in args.outputs:
        block = saved(out)
        print(json.dumps({out.name: block}, indent=2) if args.json else line(out.name, block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
