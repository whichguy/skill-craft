#!/usr/bin/env python3
"""The guides test (journal sections 39 to 41): real ShipLoop runs from one sentence, read at the accepted specification.

Three arms of one build: A, ShipLoop as it is; C, the same with one cue sentence at the end of the spec stage's first
duty; X, the cue and, after the stage's last duty, the unchanged text of two guide sections. A sample is a real run of
test/shiploop_e2e/run.py on a small existing user service, started from the sentence REQUEST and ended through the
harness's own stop file once ShipLoop's trace shows the specification accepted. The specification is read from the
commit that held it at acceptance, with a witness that the commit's text is the accepted text.

  overlays                          no model: write the two overlays from the guide text in this checkout
  prepare ROOT [--allow-dirty]      no model: lay the base down, build the three arms, enforce how they differ
  sort JUDGE                        one sorter session (opus | astra): which checklist items apply to this base
  run ROOT SET DRIVER               launch one set (A, C, X together); refuses without a committed item list of 8 or more
  collect ROOT SETID                no model: endings, launch facts, what each author was shown; blind copies; a manifest
  judge ROOT SETID                  both judges on the manifest's blind copies
  audit-pack ROOT SETID DEST        no model: a folder for the reader who looks for added capability, arms hidden
  audit-check ROOT SETID FILE       no model: verify the reader's quotes against the blind copies
  score ROOT SETID                  no model: item-by-item differences between the arms, and the registered outcome
  replay DEST OUT [OUT ...]         no model: read existing run folders as collect would, writing only under DEST

SETID is SET-DRIVER, for example s1-sol.
"""

from __future__ import annotations

import argparse
import calendar
import concurrent.futures
import difflib
import functools
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import brownfield  # the harness's own pin of a base's bytes
import grade
import qualcheck
import run_choice

REQUEST = "Let admins upload a CSV to bulk-create users."
CASE = "csv-user-import"  # the bench case whose checklist grades the specification
BASE_CASE = "user-listing"  # its base, fixtures/node-base, is laid down by the harness's own brownfield.start
FIXTURE = REPO / "test" / "shiploop_e2e" / "fixtures" / "node-base"
HARNESS = "test/shiploop_e2e/run.py"
BUILD_ARM = "docs/experiments/sdlc-structure-20261119/build_arm.py"
OVERLAYS = HERE / "overlays"
LABELS = HERE / "labels"
RESULTS = HERE / "results"
SPEC = "docs/shiploop/spec.md"
ARMS = ("A", "C", "X")
ARM_OVERLAY = {"A": None, "C": "guides-cue.json", "X": "guides-excerpt.json"}
# Only the Sol set is registered (section 41). A Claude set needs its own registration, with its cap and its build check.
DRIVERS = {
    "sol": {
        "host": "codex",
        "model": "gpt-6.2-sol",
        "effort": "medium",
        "extra": [],
        "cell": "sol-medium",
    }
}
JUDGE_TAGS = (("opus", None), ("astra", "gpt"))
GUIDES = REPO / "skills" / "shiploop" / "references"
SECTIONS = (
    ("behavioral-requirements.md", "## Behavior model"),
    ("requirements-definition.md", "## State and data change assessment"),
)
DUTY_ONE_END = "never relax a requirement to fit the code\n   or tests."
CUE = (
    "\n   Before you write the requirements, work out the behaviour model and the state and data changes of what this\n"
    "   request asks for, and which decisions it leaves open."
)
DUTY_LAST = (
    "12. A complete spec establishes acceptance lines, not implementation or test success. `evidence_refs`: KNOWLEDGE/spec.md, each\n"
    "    requirement section and source used."
)
EXCERPT_MARK = (
    "GUIDE TEXT for the behaviour model and the state and data changes of duty 1"
)
MIN_ITEMS = 8
SHOWN = 3  # a result returning this many of a section's lines returned the passage, not a search hit
RANK = {"absent": 0, "partial": 1, "covered": 2}
HERE_LABELS = ("applies", "capability", "mixed", "unclear")
WINDOWS = (
    "before the spec packet",
    "while writing the spec",
    "during its review",
    "after the acceptance",
)
KNOWLEDGE_AFTER_SPEC = re.compile(
    r"^docs\(shiploop\): record \S+ knowledge (?:at|after) spec$"
)
# The bench judge's text with the phrases that describe the bench's document form changed to a ShipLoop specification's.
LIVE_RUBRIC = (
    (
        "It has numbered use cases (U-n) and\n  numbered clauses (C-n).",
        "It has numbered requirements (R-n),\n  each with acceptance lines, and may have other sections.",
    ),
    (
        "a use case or clause in `spec.md` states this nuance",
        "a requirement, acceptance line or other sentence in `spec.md` states this nuance",
    ),
    ("Name the U-n or C-n and quote", "Name the R-n or the section and quote"),
    ('"where": "C-14"', '"where": "R-4"'),
)
RULE = """Engineering rigour (tests against the real runtime, correct deployment steps, quotas, failure routing and ownership, data
retention, security checks, marked assumptions) is the expected standard even for a small request. Product capability the
request does not need (features, stores, services, sign-in, channels the user sees or the product runs) is overbuilding."""
SORT_PROMPT = f"""You are sorting the items of a fixed checklist. You judge; you change nothing but the one file named at the end.

In your working directory: `request.txt`, one sentence asking for a change to an existing program; `base/`, that program
as it is before the change (read all of it: it is small); and `items.json`, a list of items. Each item names something a
written specification for the request might settle. You are shown no specification and need none.

Give every item one label, `here`, by this rule, which comes from the owner of the delivery tooling these
specifications are written for. {RULE}
- "applies": a correct and safe version of what the sentence asks for, built into this program as it is, has to settle
  the whole item. It is the requested behaviour's own conduct, its boundaries and errors, who may use it, what of the
  existing program must be preserved, or rigour in the rule's sense.
- "capability": the whole item is about a product capability that this program does not have and the sentence does not
  ask for (mail, sign-in, background jobs, another screen, and the like). A specification may leave it out and say so.
- "mixed": part of the item applies and part of it needs such a capability. Say in `applies_part`, in one sentence, the
  part a specification has to settle here.
- "unclear": the sentence and the program do not let you tell.

Judge against this program and this sentence only. Do not ask whether the item would be good to have: ask what the
rule says it is.

Write `verdict.json` in your working directory, and nothing else:
{{"labels": [{{"id": "<item id>", "here": "applies|capability|mixed|unclear", "applies_part": "<only for mixed>", "why": "<one line>"}}, ...]}}
One entry for every item, in the order given.
"""
AUDIT_PROMPT = f"""You are reading specifications for added scope. You report; you change nothing but the one file named at the end.

In your working directory: `request.txt`, one sentence asking for a change to an existing program; `base/`, that program
as it is before the change; and several specifications written for that sentence, each a file named by a code (for
example `K1.md`). You do not know how they were written and must not guess.

The owner's rule: {RULE}

Find every requirement, in any of the specifications, that ADDS a product capability the sentence does not ask for and
the requested change works without. Do not list: a requirement that only excludes a capability or says it is out of
scope; a safeguard the requested change needs to be correct or safe (who may use it, limits on its input, what happens
on failure, what is preserved); anything the sentence itself asks for. Quote the requirement's own words exactly.

Write `verdict.json` in your working directory, and nothing else:
{{"capabilities": [{{"capability": "<what is added, in a few words>", "found": [{{"spec": "<code>", "requirement": "<its id or section>", "quote": "<exact words from that file>"}}, ...]}}, ...]}}
One entry for each distinct capability, and under `found` every specification that adds it. An empty list when none adds any.
"""
LAY_BASE = (
    "import sys; sys.path.insert(0, 'test/shiploop_e2e'); import brownfield, run; from pathlib import Path; "
    "work = Path(sys.argv[1]); work.mkdir(parents=True); "
    "print(__import__('json').dumps(brownfield.start(work, run.catalog()[sys.argv[2]])))"
)
RENDER = "import sys; sys.path.insert(0, sys.argv[1]); import shiploop_prompts as p; sys.stdout.write(p.prompt('spec'))"


def sh(argv: list[str], cwd: Path) -> str:
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(
            f"failed ({done.returncode}): {' '.join(str(a) for a in argv[:5])} ...\n{done.stderr[-800:]}"
        )
    return done.stdout


def git(repo: Path | None, *args: str) -> bytes | None:
    """A git command's output as bytes, or None when there is no repository or git could not answer."""
    if repo is None or not Path(repo).is_dir():
        return None
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False
    )
    return done.stdout if done.returncode == 0 else None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def squeeze(text: str) -> str:
    return " ".join(text.split())


def load(path: Path) -> dict:
    try:
        found = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


# ------------------------------------------------------------------ the two overlays


def section(file: str, heading: str) -> str:
    lines = (GUIDES / file).read_text().splitlines()
    start = next(n for n, line in enumerate(lines) if line.strip() == heading)
    end = next(
        (n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).rstrip()


def excerpt() -> str:
    text = "\n\n".join(section(file, heading) for file, heading in SECTIONS)
    if '"""' in text or "\\" in text or text.endswith('"'):
        raise SystemExit(
            "the guide text cannot sit inside the duties' string literal as it is"
        )
    return text


@functools.lru_cache(maxsize=1)
def passages() -> dict[str, list[str]]:
    """For each of the two guide sections, its lines of 60 characters or more that no other file of the skill holds."""
    package, kinds, found = (
        REPO / "skills" / "shiploop",
        ("", ".md", ".py", ".json", ".txt"),
        {},
    )
    for file, heading in SECTIONS:
        others = [
            path
            for path in sorted(package.rglob("*"))
            if path.is_file() and path.suffix in kinds and path != GUIDES / file
        ]
        elsewhere = " \n ".join(
            squeeze(path.read_text(errors="replace")) for path in others
        )
        lines = dict.fromkeys(
            squeeze(line) for line in section(file, heading).splitlines()
        )
        found[file] = [
            line for line in lines if len(line) >= 60 and line not in elsewhere
        ]
    return found


def overlay_docs() -> dict[str, dict]:
    edit = {"module": "shiploop_prompts.py", "constant": "DUTIES", "key": "spec"}
    cue = {**edit, "old": DUTY_ONE_END, "new": DUTY_ONE_END + CUE}
    block = (
        f"\n\n{EXCERPT_MARK} (the sections this packet lists as\nBehavior-model guidance and State and data assessment, unchanged):\n\n"
        + excerpt()
    )
    tail = {**edit, "old": DUTY_LAST, "new": DUTY_LAST + block}
    about = "Spec-elaboration journal sections 40 and 41, arm {} of the guides test: {} For an experiment only; not a proposed change to ShipLoop."
    return {
        "guides-cue.json": {
            "about": about.format(
                "C",
                "one cue sentence at the end of the spec stage's first duty; it delivers no guide text.",
            ),
            "edits": [cue],
        },
        "guides-excerpt.json": {
            "about": about.format(
                "X",
                "arm C's cue sentence and, after the stage's last duty, the unchanged text of two guide sections.",
            ),
            "edits": [cue, tail],
        },
    }


def cmd_overlays() -> int:
    OVERLAYS.mkdir(exist_ok=True)
    for name, doc in overlay_docs().items():
        (OVERLAYS / name).write_text(json.dumps(doc, indent=1) + "\n")
        words = sum(
            len(edit["new"].split()) - len(edit["old"].split()) for edit in doc["edits"]
        )
        chars = sum(len(edit["new"]) - len(edit["old"]) for edit in doc["edits"])
        print(
            f"{name}: {len(doc['edits'])} edit(s), {words} words and {chars} characters added"
        )
    return 0


# ------------------------------------------------------------------ prepare


def cmd_prepare(root: Path, allow_dirty: bool) -> int:
    if REPO in root.parents or root == REPO:
        raise SystemExit("ROOT must be outside the checkout")
    dirty = sh(["git", "status", "--short"], REPO).splitlines()
    if dirty and not allow_dirty:
        raise SystemExit(
            f"the checkout is not clean ({len(dirty)} paths): build from a clean detached worktree"
        )
    for name, doc in overlay_docs().items():
        if json.loads((OVERLAYS / name).read_text()) != doc:
            raise SystemExit(
                f"overlays/{name} does not match the guide text in this checkout: run `overlays` and commit"
            )
    root.mkdir(parents=True, exist_ok=True)
    base = json.loads(
        sh(
            [sys.executable, "-c", LAY_BASE, str(root / "prior" / "work"), BASE_CASE],
            REPO,
        )
    )
    plugins, prompts, hashes = {}, {}, {}
    for arm in ARMS:
        argv = [sys.executable, BUILD_ARM, str(root / f"arm-{arm}")]
        argv += [str(OVERLAYS / ARM_OVERLAY[arm])] if ARM_OVERLAY[arm] else []
        plugins[arm] = sh(argv, REPO).strip().splitlines()[-1]
        scripts = Path(plugins[arm]) / "skills" / "shiploop" / "scripts"
        prompts[arm] = sh([sys.executable, "-c", RENDER, str(scripts)], REPO)
        hashes[arm] = sha256(scripts / "shiploop_prompts.py")
    problems = []
    for arm in ("C", "X"):
        expected = prompts["A"]
        for edit in overlay_docs()[ARM_OVERLAY[arm]]["edits"]:
            if expected.count(edit["old"]) != 1:
                problems.append(
                    f"arm {arm}: an edit's anchor is not in the rendered spec stage exactly once"
                )
            expected = expected.replace(edit["old"], edit["new"])
        differing = subprocess.run(
            ["diff", "-rq", "-x", "__pycache__", plugins["A"], plugins[arm]],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()
        if len(differing) != 1 or "shiploop_prompts.py" not in differing[0]:
            problems.append(
                f"arm {arm} differs from A in {len(differing)} files, not in shiploop_prompts.py alone"
            )
        if prompts[arm] != expected:
            problems.append(
                f"arm {arm}'s rendered spec stage is not A's with the overlay's edits and nothing else"
            )
    # A guide line in a tool result is read as guide text only because the arms without the block print none of them.
    for arm in ("A", "C"):
        printed = squeeze(prompts[arm])
        if any(line in printed for lines in passages().values() for line in lines):
            problems.append(
                f"arm {arm}'s spec stage already prints a line of a guide file"
            )
    if squeeze(excerpt()) not in squeeze(prompts["X"]):
        problems.append(
            "arm X's spec stage does not print the whole of the two guide sections"
        )
    deltas = {}
    for arm in ("C", "X"):
        diff = difflib.unified_diff(
            prompts["A"].splitlines(), prompts[arm].splitlines(), lineterm="", n=0
        )
        deltas[arm] = sum(
            1 for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")
        )
    record = {
        "checkout": str(REPO),
        "head": sh(["git", "rev-parse", "HEAD"], REPO).strip(),
        "checkout_status_lines": len(dirty),
        "base": base,
        "plugins": plugins,
        "prompts_file_sha256": hashes,
        "spec_prompt_sha256": {
            arm: hashlib.sha256(text.encode()).hexdigest()[:12]
            for arm, text in prompts.items()
        },
        "spec_prompt_characters": {arm: len(text) for arm, text in prompts.items()},
        "delta_lines": deltas,
        "problems": problems,
    }
    (root / "prepare.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 1 if problems else 0


# ------------------------------------------------------------------ the item list, fixed before any run


def cmd_sort(judge_name: str, timeout: int) -> int:
    out = LABELS / f"here-{judge_name}.json"
    if out.is_file():
        raise SystemExit(f"{out.name} exists: the sort is done once")
    judge, case = grade.JUDGES[judge_name], grade.cases()[CASE]
    wanted = [n["id"] for n in case["nuances"]]
    cwd = grade.WORK / "labels" / f"here-{judge_name}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    (cwd / "request.txt").write_text(REQUEST + "\n")
    shutil.copytree(FIXTURE, cwd / "base")
    (cwd / "items.json").write_text(
        json.dumps(
            [{"id": n["id"], "item": n["nuance"]} for n in case["nuances"]], indent=1
        )
        + "\n"
    )
    rc, cost = grade.run_session(SORT_PROMPT, cwd, judge, timeout)
    labels, problem = grade.read_verdict(cwd, "labels")
    if rc != 0 or labels is None:
        raise SystemExit(
            f"FAIL sort {judge_name}: rc={rc} {problem or ''}  (session folder {cwd})"
        )
    seen = {}
    for entry in labels:
        if isinstance(entry, dict) and "id" in entry:
            entry["here"] = str(entry.get("here") or "").strip().lower()
            seen[entry["id"]] = entry
    bad = [
        i
        for i in wanted
        if i not in seen
        or seen[i]["here"] not in HERE_LABELS
        or not str(seen[i].get("why") or "").strip()
    ]
    bad += [
        i
        for i in wanted
        if i in seen
        and seen[i]["here"] == "mixed"
        and not str(seen[i].get("applies_part") or "").strip()
    ]
    if bad:
        raise SystemExit(
            f"FAIL sort {judge_name}: no usable label for {sorted(set(bad))}  (session folder {cwd})"
        )
    record = {
        "judge": judge["model"],
        "judge_effort": judge["effort"],
        "cost_usd": cost,
        "prompt_sha256": hashlib.sha256(SORT_PROMPT.encode()).hexdigest(),
        "request": REQUEST,
        "fixture_digest": brownfield.digest(FIXTURE),
        "labels": [seen[i] for i in wanted],
    }
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(
        f"DONE sort {judge_name}:",
        {
            label: sum(1 for i in wanted if seen[i]["here"] == label)
            for label in HERE_LABELS
        },
    )
    return 0


def label_files() -> dict[str, Path]:
    return {name: LABELS / f"here-{name}.json" for name, _ in JUDGE_TAGS}


def labels_committed() -> bool:
    names = [str(path.relative_to(REPO)) for path in label_files().values()]
    tracked = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", *names],
        capture_output=True,
        check=False,
    )
    return (
        tracked.returncode == 0
        and not sh(["git", "status", "--short", "--", *names], REPO).strip()
    )


def frozen_items(root: Path) -> dict:
    """The item list every score uses: fixed from the two sorts at the first launch, and checked against them afterwards."""
    files = label_files()
    missing = [path.name for path in files.values() if not path.is_file()]
    if missing:
        raise SystemExit(
            f"step 0 is not done: {missing} missing; run `sort opus` and `sort astra`"
        )
    wanted = [n["id"] for n in grade.cases()[CASE]["nuances"]]
    sorts = {}
    for name, path in files.items():
        record = json.loads(path.read_text())
        labels = {row["id"]: row["here"] for row in record["labels"]}
        if sorted(labels) != sorted(wanted) or any(
            value not in HERE_LABELS for value in labels.values()
        ):
            raise SystemExit(
                f"{path.name} does not hold one usable label for each of the {len(wanted)} items"
            )
        if (
            record.get("fixture_digest") != brownfield.digest(FIXTURE)
            or record.get("request") != REQUEST
        ):
            raise SystemExit(
                f"{path.name} was sorted against another base or another sentence"
            )
        sorts[name] = labels
    agreed = {
        label: [
            i for i in wanted if all(labels[i] == label for labels in sorts.values())
        ]
        for label in ("applies", "capability")
    }
    current = {
        "applies": agreed["applies"],
        "capability": agreed["capability"],
        "other": [
            i
            for i in wanted
            if i not in agreed["applies"] and i not in agreed["capability"]
        ],  # mixed, unclear, or the sorters differ
        "label_files_sha256": {name: sha256(path) for name, path in files.items()},
        "fixture_digest": brownfield.digest(FIXTURE),
    }
    kept = root / "items.json"
    if kept.is_file():
        if json.loads(kept.read_text()) != current:
            raise SystemExit(
                "items.json no longer matches the label files: the item list is fixed once"
            )
    else:
        kept.write_text(json.dumps(current, indent=1) + "\n")
    if len(current["applies"]) < MIN_ITEMS:
        raise SystemExit(
            f"only {len(current['applies'])} items apply for both sorters; the rule is at least {MIN_ITEMS}: nothing is run"
        )
    return current


# ------------------------------------------------------------------ reading a run


def chosen_run(out: Path) -> Path | None:
    """The run the harness itself would grade for this output folder, or None while there is none or a tie."""
    try:
        choice = run_choice.choose(out)
    except Exception:  # noqa: BLE001  a folder that is still being written can be unreadable for a moment
        return None
    return Path(choice.chosen["run_dir"]) if choice.chosen else None


def trace(run: Path | None) -> list[dict]:
    try:
        return qualcheck.rows(run / "trace.jsonl") if run else []
    except (OSError, ValueError):
        return []


def acceptance(rows: list[dict]) -> tuple[dict, str] | None:
    """The command whose `accepted` list holds the spec stage as done, and the spec action's id."""
    for row in rows:
        for entry in row.get("accepted") or []:
            if (
                row.get("kind") == "command"
                and row.get("exit") == 0
                and entry.get("stage") == "spec"
                and entry.get("outcome") == "done"
            ):
                return row, entry.get("action")
    return None


def state_of(run: Path | None) -> dict:
    try:
        found = run_choice.store.read_record(run / "state.md") if run else {}
    except Exception:  # noqa: BLE001  an unreadable state is no recorded state
        return {}
    return found if isinstance(found, dict) else {}


def worktree(run: Path | None) -> Path | None:
    recorded = state_of(run).get("repo")
    return Path(recorded) if recorded and Path(recorded).is_dir() else None


def bound_for_review(
    run: Path, action: str, dest: Path, first_bind: Path | None, submitted: list[dict]
) -> dict:
    """The specification as its author submitted it: the tree ShipLoop bound for the review, by its recorded repository."""
    kept = first_bind is not None and first_bind.is_file()
    bind = first_bind if kept else run / "improve" / f"{action}-bind.md"
    if not bind.is_file():
        return {"reviewed": False, "as_bound_for_review": None}
    record = {
        "reviewed": True,
        "bind_read_from": "the copy kept when the bind first appeared"
        if kept
        else "the run folder afterwards",
    }
    if (
        not kept and submitted
    ):  # a restarted review rewrites the bind under the same name
        record["bind_written_after_first_submission_seconds"] = round(
            bind.stat().st_mtime - submitted[0]["ts"], 1
        )
    try:
        held = run_choice.store.read_record(bind)
        top, prefix, tree = (
            Path(held["toplevel"]),
            str(held["prefix"]),
            str(held["tree"]),
        )
    except Exception:  # noqa: BLE001  a bind that cannot be read is no bind
        return {
            **record,
            "as_bound_for_review": "unavailable: the bind could not be read",
        }
    path = SPEC if prefix in ("", ".") else f"{prefix.rstrip('/')}/{SPEC}"
    blob = git(top, "show", f"{tree}:{path}")
    if blob is None:
        return {
            **record,
            "as_bound_for_review": "unavailable: git could not read the bound tree",
        }
    (dest / "spec-as-bound-for-review.md").write_bytes(blob)
    return {**record, "as_bound_for_review": measures(blob.decode(errors="replace"))}


def snapshot(
    out: Path,
    dest: Path,
    first_bind: Path | None = None,
    at_acceptance: Path | None = None,
) -> dict:
    """What cannot move: the specification from the commit that held it at acceptance, tied to the accepted spec action.

    Reads the run under `out` and writes its copies under `dest`. The commit's text counts as the accepted text only with
    a witness: the commit is the accepting command's own knowledge commit, or its text equals the working file as the
    watcher copied it at acceptance (`at_acceptance`), or as it stands now with no later commit to it.
    """
    run = chosen_run(out)
    rows = trace(run)
    found = acceptance(rows)
    record = {
        "run_dir": str(run) if run else None,
        "spec_action": None,
        "snapshot": "no acceptance in the trace",
    }
    if not (run and found):
        return record
    accepted, action = found
    submitted = [
        row
        for row in rows
        if row.get("verb") == "complete"
        and row.get("action") == action
        and row.get("exit") == 0
    ]
    record.update(
        spec_action=action,
        acceptance_action=accepted.get("action"),
        accepted_at=accepted.get("at"),
        accepted_ts=accepted["ts"],
    )
    record["submitted_ts"] = submitted[0]["ts"] if submitted else None
    record["author_submissions"] = len(submitted)
    record["commands_after_acceptance"] = sum(
        1
        for row in rows
        if row.get("kind") == "command" and row.get("ts", 0) > accepted["ts"]
    )
    tree = worktree(run)
    listed = git(tree, "log", "--format=%H %ct %s", "--", SPEC)
    if not listed:
        record["snapshot"] = "git could not list the specification's commits"
        return record
    commits = [
        line.split(" ", 2)
        for line in listed.decode(errors="replace").splitlines()
        if line.strip()
    ]
    # ShipLoop writes the acceptance row when the accepting command ends, after that command committed the knowledge files.
    held = [
        (commit, int(when), subject)
        for commit, when, subject in commits
        if int(when) <= accepted["ts"] + 2
    ]
    record["spec_commits_after_acceptance"] = len(commits) - len(held)
    if not held:
        record["snapshot"] = "no commit held the specification by the acceptance"
        return record
    commit, when, subject = held[0]
    blob = git(tree, "show", f"{commit}:{SPEC}")
    record.update(spec_commit=commit, spec_commit_subject=subject)
    if blob is None:
        record["snapshot"] = "git could not read the specification at its commit"
        return record
    began = accepted["ts"] - (accepted.get("ms") or 0) / 1000
    if KNOWLEDGE_AFTER_SPEC.match(subject) and when >= int(began) - 1:
        witness = "the accepting command's own knowledge commit"
    elif at_acceptance is not None and at_acceptance.is_file():
        witness = (
            "the working file as copied at acceptance"
            if at_acceptance.read_bytes() == blob
            else None
        )
    elif not record["spec_commits_after_acceptance"] and (tree / SPEC).is_file():
        witness = (
            "the working file, with no later commit to it"
            if (tree / SPEC).read_bytes() == blob
            else None
        )
    else:
        witness = None
    if witness is None:
        record["snapshot"] = (
            "the commit's text has no witness that it is the accepted text"
        )
        return record
    (dest / "spec-accepted.md").write_bytes(blob)
    record.update(
        snapshot="pinned", witness=witness, spec_sha256=hashlib.sha256(blob).hexdigest()
    )
    record.update(bound_for_review(run, action, dest, first_bind, submitted))
    upstream = dest / "upstream"
    upstream.mkdir(exist_ok=True)
    for row in rows:
        for entry in row.get("accepted") or []:
            result = run / "results" / f"{entry.get('action')}.md"
            if (
                entry.get("stage") in ("intake", "discovery", "research")
                and result.is_file()
            ):
                shutil.copyfile(result, upstream / f"{entry['stage']}.md")
    packet = next(
        (
            row
            for row in rows
            if row.get("kind") == "packet" and row.get("action") == action
        ),
        None,
    )
    if packet and (run / str(packet.get("file"))).is_file():
        shutil.copyfile(run / packet["file"], dest / "spec-packet-as-printed.md")
        record.update(
            packet_ts=packet.get("ts"),
            shiploop_printed_the_whole_packet=packet.get("whole"),
        )
    return record


def model_outputs(out: Path) -> list[tuple[float, str]] | None:
    """Every tool output a Codex session's model was given, with its time, from the host's own session record.

    The harness's events hold what each command printed. On this host the model runs commands from a script and
    chooses what of their output to show itself, so the two differ: only the session record says what the model saw.
    None for a run with no such record (another host).
    """
    files = sorted(out.glob("home/.codex/sessions/**/rollout-*.jsonl"))
    if not files:
        return None
    shown = []
    for path in files:
        for row in qualcheck.rows(path):
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            stamp = re.fullmatch(
                r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?Z",
                str(row.get("timestamp") or ""),
            )
            if not (stamp and str(payload.get("type") or "").endswith("_output")):
                continue
            given = payload.get("output")
            parts = given if isinstance(given, list) else [{"text": given}]
            text = "".join(
                str(part.get("text") or "") for part in parts if isinstance(part, dict)
            )
            at = calendar.timegm(
                tuple(int(value) for value in stamp.groups()[:6])
            ) + float(stamp.group(7) or 0)
            shown.append((at, text))
    return sorted(shown)


def lines_of(text: str) -> list[str]:
    """A text's lines of 20 characters or more, spaces collapsed, each once: what a check for 'was this shown' looks for."""
    return list(
        dict.fromkeys(
            line for line in map(squeeze, text.splitlines()) if len(line) >= 20
        )
    )


def exposure(out: Path, dest: Path, snap: dict) -> dict | None:
    """What the specification's author was given: how much of the spec packet, and any passage of arm X's guide text.

    Read from what the model was given between the packet's print and the author's submission (the packet), and up to
    the acceptance (guide text), by the times ShipLoop's trace records. A guide passage is `SHOWN` or more lines of the
    two sections, of those the arm's own packet does not print, in one output. None when it cannot be read.
    """
    given, printed = model_outputs(out), dest / "spec-packet-as-printed.md"
    times = [snap.get(name) for name in ("packet_ts", "submitted_ts", "accepted_ts")]
    if not given or not printed.is_file() or None in times:
        return None
    packet_at, submitted_at, accepted_at = times

    def window(at: float) -> str:
        if at < packet_at - 1:
            return WINDOWS[0]
        if at <= submitted_at + 1:
            return WINDOWS[1]
        return WINDOWS[2] if at <= accepted_at + 1 else WINDOWS[3]

    packet = printed.read_text()
    writing = squeeze("\n".join(text for at, text in given if window(at) == WINDOWS[1]))
    head, _, tail = packet.partition(
        "Result template:"
    )  # the stage's instructions, then the template and the references
    parts = {
        name: [(line, line in writing) for line in lines_of(part)]
        for name, part in (("instructions", head), ("references", tail))
    }
    block = [line in writing for line in lines_of(excerpt())]
    foreign = {
        file: [line for line in lines if line not in squeeze(packet)]
        for file, lines in passages().items()
    }
    returned = {
        name: {} for name in WINDOWS
    }  # per window and file: the most section lines any one output held
    for at, text in given:
        for file, lines in foreign.items():
            count = sum(1 for line in lines if line in squeeze(text))
            if count:
                returned[window(at)][file] = max(
                    count, returned[window(at)].get(file, 0)
                )
    return {
        "read_from": "the host's own session record: what the model was given",
        "outputs_given": len(given),
        "instructions_lines_shown": [
            sum(held for _, held in parts["instructions"]),
            len(parts["instructions"]),
        ],
        "references_lines_shown": [
            sum(held for _, held in parts["references"]),
            len(parts["references"]),
        ],
        "instructions_shown_whole": all(held for _, held in parts["instructions"]),
        "cue_shown": all(line in writing for line in lines_of(CUE)),
        "guide_block_lines_shown": [sum(block), len(block)],
        "guide_block_shown_whole": all(block) and EXCERPT_MARK in writing,
        "guide_lines_returned": returned,
        "guide_passage_before_acceptance": any(
            count >= SHOWN for name in WINDOWS[:3] for count in returned[name].values()
        ),
    }


def measures(text: str) -> dict:
    return {
        "words": len(text.split()),
        "requirement_ids": len(set(re.findall(r"\bR-[0-9]+\b", text))),
    }


def host_ending(result: dict) -> str:
    if not result:
        return "no result from the harness"
    process, termination = result.get("process") or {}, result.get("termination") or {}
    if "max_budget" in str(process.get("stop")):
        return "the host's spending cap"
    if result.get("outcome_class") == "BLOCKED":
        return "ShipLoop blocked"
    if process.get("status") == "timeout":
        return "the harness's timeout"
    if str(termination.get("resume_stop") or "").startswith("stopped by"):
        return "the stop file"
    if process.get("status") == "failed":
        return "the host failed"
    return "the host ended by itself"


def read_sample(
    out: Path,
    dest: Path | None = None,
    first_bind: Path | None = None,
    at_acceptance: Path | None = None,
) -> dict:
    dest = dest or out  # this test's own samples keep their copies beside the run
    result, metrics, invocation = (
        load(out / "result.json"),
        load(out / "metrics.json"),
        load(out / "invocation.json"),
    )
    snap = snapshot(out, dest, first_bind, at_acceptance)
    run = Path(snap["run_dir"]) if snap.get("run_dir") else None
    timing = next(
        (
            row
            for row in (metrics.get("planning") or {}).get("stages") or []
            if row.get("action") == snap.get("spec_action")
        ),
        {},
    )
    seconds, review = timing.get("seconds"), timing.get("improve_seconds")
    process, termination, plugin = (
        result.get("process") or {},
        result.get("termination") or {},
        invocation.get("plugin") or {},
    )
    ends = [
        row
        for row in (
            qualcheck.rows(out / "sessions.jsonl")
            if (out / "sessions.jsonl").is_file()
            else []
        )
        if row.get("row") == "end"
    ]
    loaded = out.glob(
        "home/.codex/plugins/cache/**/skills/shiploop/scripts/shiploop_prompts.py"
    )
    accepted = dest / "spec-accepted.md"
    return {
        # how it ended: the one-word reading, and beside it the harness's own facts
        "host_ending": host_ending(result),
        "process_status": process.get("status"),
        "returncode": process.get("returncode"),
        "host_stop": process.get("stop"),
        "resume_stop": termination.get("resume_stop"),
        "outcome_class": result.get("outcome_class"),
        "host_sessions": termination.get("sessions"),
        "harness_last_accepted": (
            (ends[-1].get("engine") or {}).get("last_accepted") if ends else None
        ),
        **snap,
        # how it started
        "prompt_is_the_request": (out / "prompt.txt").read_text().strip() == REQUEST
        if (out / "prompt.txt").is_file()
        else None,
        "case_recorded": result.get("case") or invocation.get("case"),
        "start_head": (
            result.get("follow_on") or invocation.get("follow_on") or {}
        ).get("start_head"),
        "start_route": result.get("start_route"),
        "planning_review": state_of(run).get("planning_review"),
        "plugin_wanted": plugin.get("wanted") or invocation.get("plugin_dir"),
        "plugin_check_passed": plugin.get("pass"),
        "loaded_prompts_sha256": sorted({sha256(path) for path in loaded}),
        "exposure": exposure(out, dest, snap),
        "accepted": measures(accepted.read_text(errors="replace"))
        if accepted.is_file()
        else None,
        "spec_seconds": seconds,
        "spec_review_seconds": review,
        "spec_author_seconds": round(seconds - review, 1)
        if seconds is not None and review is not None
        else None,
        "turns": metrics.get("turns"),
        "tokens": metrics.get("tokens"),
        "cost_usd": metrics.get("cost_usd"),
        "refusals": sum(1 for row in trace(run) if row.get("exit") == 2)
        if run
        else None,
    }


# ------------------------------------------------------------------ launching one set


def watch(samples: Path, s: dict) -> None:
    """One look at a live sample: keep each review bind as first seen, and decide once (acceptance, an early end, the limit)."""
    out = s["out"]
    run = chosen_run(out) if out.is_dir() else None
    if run and (run / "improve").is_dir():
        for bind in (run / "improve").glob("*-bind.md"):
            kept = samples / f"{s['name']}.binds" / bind.name
            if not kept.exists():
                kept.parent.mkdir(exist_ok=True)
                shutil.copyfile(bind, kept)
    found = acceptance(trace(run))
    ended = s["process"].poll() is not None
    over = time.time() - s["started_at"] > s["limit_minutes"] * 60
    if not (found or ended or over):
        return
    s["decided_at"] = time.time()
    s["watcher"] = (
        "saw the acceptance"
        if found
        else "the run ended with no acceptance"
        if ended
        else "the time limit"
    )
    if found:
        tree = worktree(run)
        data = (tree / SPEC).read_bytes() if tree and (tree / SPEC).is_file() else None
        if data is not None:
            (samples / f"{s['name']}.spec-at-acceptance.md").write_bytes(data)
        head = git(tree, "rev-parse", "HEAD")
        s["seen"] = {
            "run_dir": str(run),
            "spec_action": found[1],
            "at": found[0].get("at"),
            "ts": found[0].get("ts"),
        }
        s["seen"].update(
            spec_sha256=hashlib.sha256(data).hexdigest() if data is not None else None,
            head=head.decode().strip() if head else None,
        )
    if ended:
        return
    if out.is_dir():
        (out / "stop").write_text(f"guides test: {s['watcher']}\n")
        s["stop_written"] = True
    else:
        s[
            "process"
        ].terminate()  # this driver's own child, which made no output folder inside the limit
        s["watcher"] += "; no output folder, so the launch was ended"


def cmd_run(root: Path, set_name: str, driver: str, limit: float) -> int:
    ready = json.loads((root / "prepare.json").read_text())
    if (
        ready["checkout"] != str(REPO)
        or ready["problems"]
        or ready["checkout_status_lines"]
    ):
        raise SystemExit(
            "prepare.json is of another checkout, records problems, or was built with uncommitted changes: prepare again"
        )
    if driver not in DRIVERS:
        raise SystemExit(
            f"no registered driver {driver!r}; there is {', '.join(DRIVERS)}"
        )
    if not labels_committed():
        raise SystemExit(
            "the two label files are not committed in this checkout: the item list is registered before a run"
        )
    if frozen_items(root)["fixture_digest"] != ready["base"]["digest"]:
        raise SystemExit(
            "the items were sorted against another version of the base than the one laid down"
        )
    chosen, set_id, samples = DRIVERS[driver], f"{set_name}-{driver}", root / "samples"
    samples.mkdir(exist_ok=True)
    if any(samples.glob(f"{set_id}-*")):
        raise SystemExit(f"set {set_id} already has samples: a set is launched once")
    turn = int(re.sub(r"\D", "", set_name) or 0) % len(ARMS)
    live = []
    for arm in (
        ARMS[turn:] + ARMS[:turn]
    ):  # the arm that launches first rotates with the set
        name = f"{set_id}-{arm}"
        argv = [
            sys.executable,
            HARNESS,
            "--prompt",
            REQUEST,
            "--continue-from",
            str(root / "prior"),
        ]
        argv += [
            "--host",
            chosen["host"],
            "--model",
            chosen["model"],
            "--effort",
            chosen["effort"],
        ]
        argv += [
            "--source",
            "checkout",
            "--plugin-dir",
            ready["plugins"][arm],
            "--output",
            str(samples / name),
        ]
        argv += [
            "--baseline",
            str(root / "baselines.jsonl"),
            "--quiet",
            *chosen["extra"],
        ]
        log = (samples / f"{name}.log").open("w")
        process = subprocess.Popen(argv, cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        sample = {
            "name": name,
            "set": set_id,
            "arm": arm,
            "driver": driver,
            "out": samples / name,
            "process": process,
            "pid": process.pid,
        }
        sample.update(
            started_at=time.time(),
            limit_minutes=limit,
            decided_at=None,
            watcher=None,
            stop_written=False,
            seen=None,
        )
        live.append(sample)
    while any(s["decided_at"] is None for s in live):
        for s in live:
            if s["decided_at"] is None:
                watch(samples, s)
        time.sleep(1)
    end_by, late = max(s["decided_at"] for s in live) + 600, 0
    for s in live:
        try:
            s["process"].wait(timeout=max(0.0, end_by - time.time()))
        except subprocess.TimeoutExpired:
            s["watcher"] += (
                "; run.py had not exited ten minutes after the last decision"
            )
            late += 1
        keys = (
            "name",
            "set",
            "arm",
            "driver",
            "pid",
            "started_at",
            "limit_minutes",
            "decided_at",
            "watcher",
            "stop_written",
            "seen",
        )
        row = {**{key: s[key] for key in keys}, "returncode": s["process"].poll()}
        (samples / f"{s['name']}.sample.json").write_text(
            json.dumps(row, indent=1) + "\n"
        )
        print(json.dumps(row))
    return 1 if late else 0


# ------------------------------------------------------------------ collecting, blind copies, judging, auditing, scoring


def checks(sample: dict, read: dict, ready: dict) -> dict:
    """Whether a sample is its arm's accepted specification, and whether its author was given what the arm intends.

    On this host the model gives itself as much of a packet as its own script prints, so the cue and the block count only
    when they are in what it was given, and an author given less than half of the stage's instructions is not compared.
    """
    arm, shown, seen = sample["arm"], read.get("exposure"), sample.get("seen") or {}
    usable = {
        "accepted inside the limit": read.get("accepted_ts") is not None
        and read["accepted_ts"] <= sample["started_at"] + sample["limit_minutes"] * 60,
        "the specification pinned to its commit": read.get("snapshot") == "pinned",
        "the acceptance the watcher saw": read.get("spec_action") is not None
        and seen.get("spec_action") == read.get("spec_action"),
        "the registered sentence": read.get("prompt_is_the_request") is True,
        "the prepared base": read.get("start_head") is not None
        and read.get("start_head") == ready["base"]["start_head"],
        "the arm's build": bool(read.get("plugin_wanted"))
        and Path(read["plugin_wanted"]).resolve()
        == Path(ready["plugins"][arm]).resolve()
        and read.get("loaded_prompts_sha256") == [ready["prompts_file_sha256"][arm]],
    }
    delivered = None
    if shown:
        given, of = shown["instructions_lines_shown"]
        delivered = {
            "at least half of the stage's instructions given to the model": 2 * given
            >= of,
            "the cue given, as the arm has it": shown["cue_shown"] == (arm != "A"),
            "the guide text given, as the arm has it": shown["guide_block_shown_whole"]
            if arm == "X"
            else not shown["guide_passage_before_acceptance"],
        }
    return {
        "usable": all(usable.values()),
        "usable_checks": usable,
        "delivered": None if delivered is None else all(delivered.values()),
        "delivery_checks": delivered,
    }


def slot_dir(manifest: dict, code: str) -> Path:
    return RESULTS / manifest["round"] / f"{CASE}__{code}__{manifest['cell']}"


def grades_file(manifest: dict, tag: str | None, code: str) -> Path:
    return (
        grade.grades_dir(manifest["round"], tag)
        / f"{slot_dir(manifest, code).name}.json"
    )


def manifest_of(root: Path, set_id: str) -> dict:
    path = root / f"set-{set_id}.json"
    if not path.is_file():
        raise SystemExit(f"{path.name} is missing: collect the set first")
    manifest = json.loads(path.read_text())
    if not manifest["complete"]:
        raise SystemExit(
            f"set {set_id} is INCOMPLETE (see collect-{set_id}.json): nothing is judged or compared"
        )
    for code, info in manifest["slots"].items():
        spec = slot_dir(manifest, code) / "spec.md"
        if not spec.is_file() or sha256(spec) != info["spec_sha256"]:
            raise SystemExit(
                f"slot {code} is missing or is not the specification the manifest recorded"
            )
    return manifest


def cmd_collect(root: Path, set_id: str) -> int:
    samples, ready = root / "samples", json.loads((root / "prepare.json").read_text())
    rows = sorted(samples.glob(f"{set_id}-*.sample.json"))
    if len(rows) != len(ARMS):
        raise SystemExit(
            f"set {set_id} has {len(rows)} sample records, not {len(ARMS)}"
        )
    if (root / f"set-{set_id}.json").is_file():
        raise SystemExit(f"set-{set_id}.json exists: a set is collected once")
    records = []
    for path in rows:
        sample = json.loads(path.read_text())
        if sample.get("returncode") is None:
            raise SystemExit(
                f"{sample['name']}: run.py has not exited; nothing is collected from a live run"
            )
        out, seen = samples / sample["name"], sample.get("seen") or {}
        first_bind = (
            samples / f"{sample['name']}.binds" / f"{seen.get('spec_action')}-bind.md"
        )
        read = (
            read_sample(
                out,
                None,
                first_bind,
                samples / f"{sample['name']}.spec-at-acceptance.md",
            )
            if out.is_dir()
            else {"snapshot": "no output folder"}
        )
        records.append({**sample, **read, **checks(sample, read, ready)})
    (root / f"collect-{set_id}.json").write_text(json.dumps(records, indent=1) + "\n")
    for record in records:
        failed = [name for name, held in record["usable_checks"].items() if not held]
        failed += [
            name for name, held in (record["delivery_checks"] or {}).items() if not held
        ]
        words = (record.get("accepted") or {}).get("words")
        print(
            f"{record['name']}: watcher {record['watcher']}; {record.get('host_ending')}; usable {record['usable']}; delivered {record['delivered']}; words {words}",
            failed or "",
        )
    complete = all(record["usable"] for record in records)
    manifest = {
        "set": set_id,
        "cell": DRIVERS[records[0]["driver"]]["cell"],
        "complete": complete,
        "round": None,
        "slots": {},
    }
    manifest.update(
        delivered={record["arm"]: record["delivered"] for record in records},
        items=frozen_items(root),
    )
    if complete:  # an incomplete set is not judged, so no copies are made of it
        manifest["round"] = f"round-g-{set_id}-{uuid.uuid4().hex[:6]}"
        codes = [f"K{n}" for n in range(1, len(records) + 1)]
        random.SystemRandom().shuffle(codes)
        for record, code in zip(records, codes, strict=True):
            slot = slot_dir(manifest, code)
            slot.mkdir(parents=True)
            shutil.copyfile(
                samples / record["name"] / "spec-accepted.md", slot / "spec.md"
            )
            (slot / "meta.json").write_text(
                json.dumps({"case": CASE, "code": code}, indent=1) + "\n"
            )
            manifest["slots"][code] = {
                "arm": record["arm"],
                "sample": record["name"],
                "spec_sha256": sha256(slot / "spec.md"),
            }
    (root / f"set-{set_id}.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(
        f"set {set_id}: {'complete' if complete else 'INCOMPLETE'}; delivered {manifest['delivered']}"
        + (f"; blind copies in results/{manifest['round']}" if complete else "")
    )
    return 0 if complete else 1


def live_rubric() -> str:
    text = grade.JUDGE_PROMPT
    for old, new in LIVE_RUBRIC:
        if text.count(old) != 1:
            raise SystemExit(
                "the bench judge's text has changed: the live rubric's edits no longer apply"
            )
        text = text.replace(old, new)
    return text


def verdicts(manifest: dict, code: str, tag: str | None) -> dict | None:
    """One judge's 21 states for a slot, or None unless every item is there with a known state."""
    kept = grades_file(manifest, tag, code)
    if not kept.is_file():
        return None
    states = {
        v.get("id"): v.get("state")
        for v in json.loads(kept.read_text()).get("verdicts") or []
    }
    wanted = [n["id"] for n in grade.cases()[CASE]["nuances"]]
    return (
        {i: RANK[states[i]] for i in wanted}
        if all(states.get(i) in RANK for i in wanted)
        else None
    )


def seal(root: Path, manifest: dict, rubric: str) -> list:
    """Record which grade files are this set's readings of its blind copies; returns the readings that are missing."""
    sealed, missing = {}, []
    for code, info in manifest["slots"].items():
        sealed[code] = {"spec_sha256": info["spec_sha256"], "grades": {}}
        for judge_name, tag in JUDGE_TAGS:
            if verdicts(manifest, code, tag) is None:
                missing.append((code, judge_name))
            else:
                sealed[code]["grades"][judge_name] = sha256(
                    grades_file(manifest, tag, code)
                )
    record = {
        "rubric_sha256": hashlib.sha256(rubric.encode()).hexdigest(),
        "slots": sealed,
    }
    (root / f"judged-{manifest['set']}.json").write_text(
        json.dumps(record, indent=1) + "\n"
    )
    return missing


def cmd_judge(root: Path, set_id: str, timeout: int) -> int:
    manifest, case = manifest_of(root, set_id), grade.cases()[CASE]
    grade.JUDGE_PROMPT = live_rubric()  # judge_one reads the module's text when it runs
    jobs = [
        (slot_dir(manifest, code), tag, judge_name)
        for judge_name, tag in JUDGE_TAGS
        for code in manifest["slots"]
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in [
            pool.submit(
                grade.judge_one, manifest["round"], slot, case, timeout, tag, name
            )
            for slot, tag, name in jobs
        ]:
            future.result()
    missing = seal(root, manifest, grade.JUDGE_PROMPT)
    print(
        f"set {set_id}: {len(jobs) - len(missing)} of {len(jobs)} readings complete",
        missing or "",
    )
    return 1 if missing else 0


def readings(root: Path, manifest: dict) -> dict:
    """Arm -> the two judges' states, only from the grade files sealed after judging."""
    sealed = load(root / f"judged-{manifest['set']}.json").get("slots") or {}
    states = {}
    for code, info in manifest["slots"].items():
        both = []
        for judge_name, tag in JUDGE_TAGS:
            kept, reading = (
                grades_file(manifest, tag, code),
                verdicts(manifest, code, tag),
            )
            if reading is None or (sealed.get(code) or {}).get("grades", {}).get(
                judge_name
            ) != sha256(kept):
                raise SystemExit(
                    f"slot {code} has no complete, sealed reading from {judge_name}: nothing is compared"
                )
            both.append(reading)
        states[info["arm"]] = both
    return states


def cmd_audit_pack(root: Path, set_id: str, dest: Path) -> int:
    manifest = manifest_of(root, set_id)
    if dest.exists():
        raise SystemExit(f"{dest} exists: the reader gets a fresh folder")
    dest.mkdir(parents=True)
    (dest / "request.txt").write_text(REQUEST + "\n")
    shutil.copytree(FIXTURE, dest / "base")
    for code in manifest["slots"]:
        shutil.copyfile(slot_dir(manifest, code) / "spec.md", dest / f"{code}.md")
    (dest / "PROMPT.md").write_text(AUDIT_PROMPT)
    print(
        f"reader's folder: {dest} ({len(manifest['slots'])} specifications, arms hidden); its instructions are PROMPT.md there"
    )
    return 0


def cmd_audit_check(root: Path, set_id: str, verdict: Path) -> int:
    manifest = manifest_of(root, set_id)
    listed = json.loads(verdict.read_text()).get("capabilities")
    if not isinstance(listed, list):
        raise SystemExit("the reader's file has no `capabilities` list")
    texts = {
        code: squeeze((slot_dir(manifest, code) / "spec.md").read_text())
        for code in manifest["slots"]
    }
    checked = []
    for entry in listed:
        found = []
        for row in entry.get("found") or []:
            if row.get("spec") not in texts:
                raise SystemExit(
                    f"the reader names a specification that is not in the set: {row.get('spec')!r}"
                )
            quote = squeeze(str(row.get("quote") or ""))
            found.append(
                {
                    **row,
                    "quote_is_in_the_file": len(quote) >= 15
                    and quote in texts[row["spec"]],
                }
            )
        checked.append({"capability": entry.get("capability"), "found": found})
    record = {
        "reader_file_sha256": sha256(verdict),
        "prompt_sha256": hashlib.sha256(AUDIT_PROMPT.encode()).hexdigest(),
        "capabilities": checked,
    }
    (root / f"audit-{set_id}.json").write_text(json.dumps(record, indent=1) + "\n")
    for entry in checked:
        print(
            f"{entry['capability']}: verified in {sorted(row['spec'] for row in entry['found'] if row['quote_is_in_the_file'])} of {sorted(row['spec'] for row in entry['found'])}"
        )
    print(f"{len(checked)} capabilities listed; arms stay hidden until `score`")
    return 0


def compare(states: dict, items: list, high: str, low: str) -> dict:
    up = [
        i for i in items if all(states[high][j][i] > states[low][j][i] for j in (0, 1))
    ]
    down = [
        i for i in items if all(states[high][j][i] < states[low][j][i] for j in (0, 1))
    ]
    return {
        "higher": up,
        "newly_raised": [i for i in up if all(states[low][j][i] == 0 for j in (0, 1))],
        "lower": down,
        "net": len(up) - len(down),
    }


def outcome(delivered: dict, x_over_c: dict, x_alone: list) -> str:
    """The registered reading of one complete set: the first of these that holds (journal section 41)."""
    if any(value is None for value in delivered.values()):
        return "delivery unknown: nothing is claimed"
    if not all(delivered.values()):
        return "delivery failed: the set says nothing about the guide text"
    if x_over_c["net"] <= -4 or x_alone:
        return "a signal of harm"
    if (
        len(x_over_c["higher"]) >= 4
        and x_over_c["net"] >= 4
        and len(x_over_c["newly_raised"]) >= 2
    ):
        return "a signal worth repeating"
    if len(x_over_c["higher"]) < 2 and len(x_over_c["lower"]) < 2:
        return "no signal"
    return "described only: no rule applies"


def cmd_score(root: Path, set_id: str) -> int:
    manifest = manifest_of(root, set_id)
    states, arm_of = (
        readings(root, manifest),
        {code: info["arm"] for code, info in manifest["slots"].items()},
    )
    audit = load(root / f"audit-{set_id}.json").get("capabilities")
    if audit is None:
        raise SystemExit(
            "the reader's audit has not been checked in: the arms are not revealed before it is"
        )
    applies, other = manifest["items"]["applies"], manifest["items"]["other"]
    print(
        f"set {set_id}: items that apply here for both sorters ({len(applies)}): {applies}"
    )
    for arm in ARMS:
        for which, (judge_name, _) in enumerate(JUDGE_TAGS):
            row = [states[arm][which][i] for i in applies]
            print(
                f"  {arm} {judge_name}: covered {row.count(2)}, partly {row.count(1)}, absent {row.count(0)}"
            )
    pairs = {
        f"{high} over {low}": compare(states, applies, high, low)
        for high, low in (("X", "C"), ("C", "A"), ("X", "A"))
    }
    for name, pair in pairs.items():
        print(
            f"  {name}: higher under both judges {pair['higher']}; of them newly raised {pair['newly_raised']}; lower {pair['lower']}; net {pair['net']}"
        )
    print(
        "  not in the rule (mixed, unclear or the sorters differ), as states under the two judges:"
    )
    for i in other:
        print(
            f"    {i}: "
            + ", ".join(
                f"{arm} {states[arm][0][i]}/{states[arm][1][i]}" for arm in ARMS
            )
        )
    added = {}
    for entry in audit:
        arms = sorted(
            {
                arm_of[row["spec"]]
                for row in entry["found"]
                if row["quote_is_in_the_file"]
            }
        )
        if arms:
            added[str(entry["capability"])] = arms
            print(f"  added capability: {entry['capability']}: in {arms}")
    x_alone = [name for name, arms in added.items() if arms == ["X"]]
    result = outcome(manifest["delivered"], pairs["X over C"], x_alone)
    print(f"  delivered as each arm intends: {manifest['delivered']}")
    print(f"  OUTCOME (X over C): {result}")
    record = {
        "set": set_id,
        "items": manifest["items"],
        "pairs": pairs,
        "added_capability": added,
        "capability_in_x_alone": x_alone,
        "outcome": result,
    }
    record["states"] = {
        arm: {
            judge_name: states[arm][which]
            for which, (judge_name, _) in enumerate(JUDGE_TAGS)
        }
        for arm in ARMS
    }
    (root / f"score-{set_id}.json").write_text(json.dumps(record, indent=1) + "\n")
    return 0


def cmd_replay(dest: Path, outs: list[Path]) -> int:
    if dest.exists() or any(
        dest == out or dest in out.parents or out in dest.parents for out in outs
    ):
        raise SystemExit("DEST must be a new folder outside every run it reads")
    if len({out.name for out in outs}) != len(outs):
        raise SystemExit("two run folders share a name: replay them one at a time")
    for out in outs:
        copy = dest / out.name
        copy.mkdir(parents=True)
        record = read_sample(
            out, copy
        )  # reads the run where it is; writes only under dest
        print(
            json.dumps(
                {key: value for key, value in record.items() if key != "tokens"},
                indent=1,
            )
        )
    return 0


def main() -> int:
    commands = (
        "overlays",
        "prepare",
        "sort",
        "run",
        "collect",
        "judge",
        "audit-pack",
        "audit-check",
        "score",
        "replay",
    )
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=commands)
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--limit", type=float, default=20.0)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    rest, command = args.rest, args.command
    if command == "overlays":
        return cmd_overlays()
    if command == "sort":
        return cmd_sort(rest[0], args.timeout)
    root = Path(rest[0]).resolve()
    if command == "prepare":
        return cmd_prepare(root, args.allow_dirty)
    if command == "run":
        return cmd_run(root, rest[1], rest[2], args.limit)
    if command == "collect":
        return cmd_collect(root, rest[1])
    if command == "judge":
        return cmd_judge(root, rest[1], args.timeout)
    if command == "audit-pack":
        return cmd_audit_pack(root, rest[1], Path(rest[2]).resolve())
    if command == "audit-check":
        return cmd_audit_check(root, rest[1], Path(rest[2]).resolve())
    if command == "score":
        return cmd_score(root, rest[1])
    return cmd_replay(root, [Path(path).resolve() for path in rest[1:]])


if __name__ == "__main__":
    sys.exit(main())
