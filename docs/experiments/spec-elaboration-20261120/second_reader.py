#!/usr/bin/env python3
"""A second reader: shown the decisions a finished ShipLoop delivery recorded at its specification and told the requester
(its `defaults` rows), does a second, separate reader add decisions worth telling, without repeating the rows or
flooding the requester?

  snap ROOT MANIFEST                      no model: one snapshot folder a delivery, cut right after its specification was
                                          accepted, with the rows the requester was told, under shuffled codes M01, M02, ...
  ask ROOT [--repeats 3] [--timeout 900]  lister sessions (GPT Sol at medium): one list for each snapshot and repeat
  pack ROOT                               no model: the first five items of each list under shuffled codes L01, ..., for the
                                          judges, with the rules, each case's request and its starting product
  judge ROOT JUDGE [--timeout 2400]       one judge session (opus | astra) over the whole judging folder
  score ROOT                              no model: the readings fixed in advance, for the `final` set and for all lists
  leaks ROOT                              no model: lister sessions whose own stream names a delivery's real folder
  selftest SCRATCH MANIFEST [--rows-ref REF]
                                          no model: the whole path on the real deliveries with made-up lists and verdicts

A manifest is a list of {"name", "path", "case", "wording"[, "run"]}: `case` is `due` or `hello`, `wording` is `first`,
`final` or `latest`, and `run` names the ShipLoop run folder when the delivery holds more than one. A delivery folder is
only read. Everything is written under ROOT, which must be outside every delivery. Sibling of ask_later.py, whose helpers
it uses.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import ask_later as al
import grade

TOKEN = "$skill-craft:shiploop "  # Codex-host runs record the request behind this invocation token; Claude-host runs do not
CLASSES = ("unfounded", "told", "settled", "unseen", "new")
QUESTIONS = ("told_way_back", "spec_refuses", "told_refusal")
PLACES = ("way_back", "refusal")
FINAL = ("final", "latest")  # the wordings of the set the rule reads
SHOWN = 5  # the judges see the first five items of a list
TEXTS = Path(
    "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/e8ec9342-8948-4b96-8256-d168e70e5f09/scratchpad/second-reader/texts.md"
)  # where the main session wrote the five texts below; the selftest compares them when it is there
SECOND_PROMPT = """You are preparing a question for the person who asked for a change. You report; you change nothing but the one file named at the end.

In your working directory: `request.md`, what they asked for, in their own words; `repo/`, the program's repository as it
stands now, with the work's own notes under `repo/docs/shiploop/` where there are any; `record/`, what the work has
recorded at each step so far, in order; and `told.md`, what the requester has already been told the work decided for
them. The work is unattended: wherever the request did not say something, it took an answer and went on. Paths in these
files that begin with `/elsewhere` name places you do not have.

List every other decision the work has taken on the requester's behalf, that is, every one `told.md` does not already
tell: a point the request does not settle, where the requester could reasonably have meant something else, and where
their answer would change what they, their users or their operators get or have to do. Leave out choices they would not
care about (names, file layout, internal structure) unless such a choice changes what someone outside the code sees or
must do. Do not repeat a decision `told.md` tells, even in other words. For each decision give: the decision as taken, in
one sentence; what else they might have meant, in one sentence; and where it is written (the file and the place in it).

Order the list by what a wrong guess would cost the requester if nobody noticed it until the change was in use, the
costliest first. If the work took no other such decision, the list is empty.

Write `verdict.json` in your working directory, and nothing else:
{"decisions": [{"decision": "<as taken>", "alternative": "<what else they might have meant>", "where": "<file and place>"}, ...]}
"""
TOLD_HEAD = """# What the requester has been told

The work recorded these decisions as taken on the requester's behalf and showed them to the requester.
"""
TOLD_NONE = """# What the requester has been told

The work recorded no decision taken on the requester's behalf and told the requester so.
"""
JUDGE_PROMPT = """You are sorting items of lists against written rules. You judge; you change nothing but the one file named at the end.

In your working directory: `rule.md`, the rules; `cases/`, one folder for each request, holding `request.md` (what was
asked for, in the requester's own words) and `product/` (the program as it was before the work began; it may be empty);
and files named `L01.json`, `L02.json` and so on. Each `L` file holds: `case`, the folder of its request; `told`, what
the requester had already been told the work decided for them; `specification`, the specification the work wrote; and
`items`, up to five decisions that a second reader says the work also took for the requester, in that reader's order.
You are not told who wrote any of it.

For each `L` file, following `rule.md`: answer its three questions about the file, give each item its one class, and
give the place of the first item about each of the two described decisions. Read every item of every file, and read
`product/` where a class depends on what the program already did.

Write `verdict.json` in your working directory, and nothing else:
{"lists": [{"list": "L01", "told_way_back": <true|false>, "spec_refuses": <true|false>, "told_refusal": <true|false>, "classes": ["<class of item 1>", ...], "way_back": <1-based place among the items, or 0>, "refusal": <1-based place among the items, or 0>}, ...]}
One entry for every `L` file; `classes` has one entry for each item of the file, in order, and is empty when the file has no item.
"""
RULE = """# Rules

## The class of an item

Give each item exactly one class. Take the first that applies, in this order.

1. `unfounded`: the specification does not say this, and neither `told` nor the request does. The item reports as
   decided something the work did not record.
2. `told`: `told` already tells this decision: the same point, whichever words it uses. An item that adds a different
   consequence of a point `told` names is not `told`.
3. `settled`: not a choice of this work. The request states it, or the program already behaved so before the work and
   the request does not ask for that to change.
4. `unseen`: a choice that a person who uses or runs the program would not notice: internal structure, names, file
   layout, how it is tested, how the work is organised.
5. `new`: none of the above. A choice the work made that the request does not settle, that a person who uses or runs
   the program would notice (what they see, a step they must take, something refused), and that `told` does not tell.

## Three questions about each file

They are about `told` and `specification`, not about the items.

- `told_way_back`: does `told` tell the requester what going back to the earlier release loses or requires (for
  example that the earlier release drops the due times when it next saves, or that an operator must keep a copy)?
- `spec_refuses`: does the specification say that the service refuses to start, or stops before serving, when it is
  started with due times switched on while some ticket in the data file has no due time?
- `told_refusal`: does `told` tell the requester that refusal?

For a request that has nothing to do with due times, all three are false.

## Two described decisions

Give the place of the first item about each, or 0 when no item is about it.

- `way_back`: what going back to the earlier release, 1.4.0, loses or requires. The earlier release can read the data
  file, but its next save drops the due times, so they are lost unless an operator kept a copy or restores one. An
  item is about it when it names this loss, the copy or the restoring, however worded. An item that says only that the
  earlier release can still start on the file and show every ticket is not.
- `refusal`: what the service does when it is started with due times switched on while some ticket in the data file
  has no due time: it refuses to start, or stops before serving. An item is about it when it names that refusal,
  however worded. An item that says only who fills in the due times, or that a command must be run first, is not.
"""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git(work: Path, *args: str) -> str:
    return al.sh(["git", "-C", str(work), *args]).decode()


def run_folder(entry: dict) -> Path:
    """The one place that decides a delivery's ShipLoop run folder: the entry's `run` when it names one, else the
    delivery's only one."""
    return Path(entry["run"]) if entry.get("run") else al.run_of(Path(entry["path"]))


def through_spec(entry: dict) -> list[tuple[str, str | None, str]]:
    """The stages accepted as done up to and including the last `spec` before the first `test-strategy`."""
    order = al.accepted(run_folder(entry))
    stages = [stage for stage, _, _ in order]
    end = stages.index("test-strategy") if "test-strategy" in stages else len(order)
    specs = [n for n in range(end) if stages[n] == "spec"]
    if not specs:
        raise SystemExit(
            f"{entry['path']}: no spec stage accepted before the test strategy"
        )
    return order[: specs[-1] + 1]


def spec_ts(run: Path, action: str) -> float:
    """When ShipLoop accepted the action: the `ts` of the first command row whose accepted entries hold it as done."""
    for line in (run / "trace.jsonl").read_text().splitlines():
        row = json.loads(line) if line.strip() else {}
        if row.get("kind") == "command" and any(
            entry.get("action") == action and entry.get("outcome") == "done"
            for entry in row.get("accepted") or []
        ):
            return float(row["ts"])
    raise SystemExit(f"{run}: no command row accepted {action}")


def work_log(work: Path) -> list[tuple[str, int, str]]:
    """The work repository's commits, oldest first: commit, committer time in epoch seconds, subject."""
    rows = [
        line.split("\t", 2)
        for line in git(
            work, "log", "--reverse", "--format=%H%x09%ct%x09%s"
        ).splitlines()
    ]
    return [(commit, int(when), subject) for commit, when, subject in rows]


def spec_commit(entry: dict) -> tuple[str, str, str | None]:
    """The commit that holds the repository right after the specification was accepted, how it was found (`subject` or
    `time`), and the commit the time rule gives (None when no commit but the first one is that old)."""
    delivery = Path(entry["path"])
    ts = spec_ts(run_folder(entry), through_spec(entry)[-1][2])
    log = work_log(delivery / "work")
    old = [n for n, (_, when, _) in enumerate(log) if when <= ts]
    time_commit = log[old[-1]][0] if old and old[-1] > 0 else None
    subject = [
        commit for commit, _, text in log if text.endswith("knowledge after spec")
    ]
    if len(subject) == 1:
        return subject[0], "subject", time_commit
    if time_commit is None:
        raise SystemExit(
            f"{delivery}: no commit subject marks the specification and no commit after the first is older than its acceptance ({ts})"
        )
    return time_commit, "time", time_commit


def defaults_of(run: Path, action: str, delivery: Path) -> list[dict]:
    """The rows the spec stage's result recorded under `defaults`: what the requester was shown."""
    lines = (run / "results" / f"{action}.md").read_text().splitlines()
    try:
        start = lines.index("```shiploop-state")
        end = next(
            n for n in range(start + 1, len(lines)) if lines[n].startswith("```")
        )
        rows = json.loads("\n".join(lines[start + 1 : end]))["result"]["defaults"]
    except (ValueError, StopIteration, KeyError, TypeError):
        rows = None
    if not isinstance(rows, list) or not all(
        isinstance(row, dict)
        and all(
            isinstance(row.get(k), str)
            for k in ("requirement", "question", "default", "alternative")
        )
        for row in rows
    ):
        raise SystemExit(f"{delivery}: no list of defaults: not material for this test")
    return rows


def ended(text: str) -> str:
    """The text as one sentence, as ShipLoop's packet shows a row (`_end` in skills/shiploop/scripts/shiploop_defaults.py):
    a closing mark the model wrote is kept, a text without one gets a period."""
    text = al.squeeze(text)
    return text if not text or text[-1] in ".!?" else text + "."


def row_line(n: int, row: dict) -> str:
    return al.squeeze(
        f"{n}. {row['requirement']} {ended(row['question'])} Decided: {ended(row['default'])} Otherwise:"
        f" {ended(row['alternative'])}"
    )


def told_text(rows: list[dict]) -> str:
    if not rows:
        return TOLD_NONE
    blocks = [
        f"{n}. ({al.squeeze(row['requirement'])}) {ended(row['question'])}\n"
        f"   Decided: {ended(row['default'])}\n"
        f"   Otherwise: {ended(row['alternative'])}"
        for n, row in enumerate(rows, 1)
    ]
    return TOLD_HEAD + "\n" + "\n\n".join(blocks) + "\n"


def scrub(folder: Path) -> None:
    """Replace the owner's home in every text file, as ask_later's snap does (links are left alone: none is written
    through)."""
    for file in (p for p in folder.rglob("*") if p.is_file() and not p.is_symlink()):
        try:
            text = file.read_text()
        except UnicodeDecodeError:
            continue
        if str(Path.home()) in text:
            file.write_text(al.home_paths(text))


def archive(work: Path, commit: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    al.sh(
        ["tar", "-x", "-C", str(dest)],
        al.sh(["git", "-C", str(work), "archive", commit]),
    )


def cmd_snap(root: Path, manifest: Path) -> int:
    if (root / "key.json").exists():
        raise SystemExit("key.json exists: the snapshots are made once")
    entries = json.loads(manifest.read_text())
    deliveries = [Path(entry["path"]).resolve() for entry in entries]
    if any(root == d or root in d.parents or d in root.parents for d in deliveries):
        raise SystemExit("ROOT must be outside every delivery")
    facts = []  # everything is read and checked before anything is written
    for entry in entries:
        delivery, run = Path(entry["path"]), run_folder(entry)
        stages = through_spec(entry)
        commit, found_by, _ = spec_commit(entry)
        rows = defaults_of(run, stages[-1][2], delivery)
        result = json.loads((delivery / "result.json").read_text())
        facts.append((entry, delivery, run, stages, commit, found_by, rows, result))
    root.mkdir(parents=True, exist_ok=True)
    codes = [f"M{n:02d}" for n in range(1, len(entries) + 1)]
    random.SystemRandom().shuffle(codes)
    key = {}
    for entry, delivery, run, stages, commit, found_by, rows, result in facts:
        code = codes.pop()
        dest = root / "snapshots" / code
        archive(delivery / "work", commit, dest / "repo")
        (dest / "record").mkdir()
        (dest / "request.md").write_text((run / "request.md").read_text())
        names = []
        for n, (stage, item, action) in enumerate(stages, 1):
            names.append(f"{n:02d}-{stage}" + (f"-{item}" if item else "") + ".md")
            (dest / "record" / names[-1]).write_text(
                (run / "results" / f"{action}.md").read_text()
            )
        (dest / "told.md").write_text(told_text(rows))
        scrub(dest)
        if not (dest / "repo" / "docs" / "shiploop" / "spec.md").is_file():
            raise SystemExit(
                f"{delivery}: commit {commit} holds no docs/shiploop/spec.md"
            )
        key[code] = {
            "name": entry["name"],
            "delivery": str(delivery),
            "run": str(run),
            "case": entry["case"],
            "wording": entry["wording"],
            "commit": commit,
            "found_by": found_by,
            "record": names,
            "model": result.get("model"),
            "effort": result.get("effort"),
            "rows": [row_line(n, row) for n, row in enumerate(rows, 1)],
            "told_sha256": sha((dest / "told.md").read_text()),
        }
        print(
            f"{code}: {entry['name']} ({entry['case']}, {entry['wording']}): commit {commit[:10]} found by {found_by}, {len(rows)} rows told"
        )
    (root / "key.json").write_text(
        json.dumps(dict(sorted(key.items())), indent=1) + "\n"
    )
    return 0


def usable(rc: int, decisions: object) -> bool:
    """A list is usable when the session ended well and every entry names a decision; it may be empty."""
    return (
        rc == 0
        and isinstance(decisions, list)
        and all(
            isinstance(d, dict) and al.squeeze(d.get("decision") or "")
            for d in decisions
        )
    )


def list_record(
    code: str, repeat: int, attempt: int, cost: object, decisions: list
) -> str:
    return (
        json.dumps(
            {
                "code": code,
                "repeat": repeat,
                "attempt": attempt,
                "lister": al.LISTER,
                "prompt_sha256": sha(SECOND_PROMPT),
                "cost_usd": cost,
                "decisions": decisions,
            },
            indent=1,
        )
        + "\n"
    )


def one_list(root: Path, code: str, repeat: int, timeout: int) -> str:
    out = root / "lists" / f"{code}-r{repeat}.json"
    if out.is_file():
        return f"kept {out.name}"
    for attempt in (
        1,
        2,
    ):  # a session that leaves no usable list is launched once more, and no more
        cwd = root / "sessions" / f"{code}-r{repeat}-{uuid.uuid4().hex[:6]}"
        shutil.copytree(root / "snapshots" / code, cwd)
        rc, cost = grade.run_session(SECOND_PROMPT, cwd, al.LISTER, timeout)
        decisions, problem = grade.read_verdict(cwd, "decisions")
        if usable(rc, decisions):
            out.write_text(list_record(code, repeat, attempt, cost, decisions))
            return f"DONE {out.name}: {len(decisions)} decisions"
    return f"FAIL {code} r{repeat}: rc={rc} {problem or ''} (session folder {cwd})"


def cmd_ask(root: Path, repeats: int, timeout: int) -> int:
    key = json.loads((root / "key.json").read_text())
    (root / "lists").mkdir(exist_ok=True)
    (root / "sessions").mkdir(exist_ok=True)
    jobs = [(code, repeat) for repeat in range(1, repeats + 1) for code in sorted(key)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        said = list(pool.map(lambda job: one_list(root, job[0], job[1], timeout), jobs))
    print("\n".join(said))
    return 1 if any(line.startswith("FAIL") for line in said) else 0


def cmd_pack(root: Path) -> int:
    dest = root / "judging"
    if dest.exists():
        raise SystemExit("the judges' folder exists: it is made once")
    key = json.loads((root / "key.json").read_text())
    cases = sorted({info["case"] for info in key.values()})
    letters = {case: chr(ord("A") + n) for n, case in enumerate(cases)}
    found = {}  # everything is read and checked before anything is written
    for case in cases:
        codes = sorted(code for code, info in key.items() if info["case"] == case)
        requests = {
            (root / "snapshots" / code / "request.md").read_text().replace(TOKEN, "")
            for code in codes
        }
        if len(requests) != 1:
            raise SystemExit(
                f"case {case}: the request differs across its snapshots {codes}, even without {TOKEN.strip()!r}"
            )
        firsts = {}
        for code in codes:
            work = Path(key[code]["delivery"]) / "work"
            first = work_log(work)[0][0]
            firsts[code] = (
                work,
                first,
                git(work, "rev-parse", f"{first}^{{tree}}").strip(),
            )
        trees = {code: tree for code, (_, _, tree) in firsts.items()}
        if len(set(trees.values())) != 1:
            raise SystemExit(
                f"case {case}: the first commits of its deliveries hold different trees: {trees}"
            )
        found[case] = (requests.pop(), *firsts[codes[0]][:2])
    names = al.wanted_lists(root)
    have = [name for name in names if (root / "lists" / f"{name}.json").is_file()]
    missing = sorted(set(names) - set(have))
    lcodes = [f"L{n:02d}" for n in range(1, len(have) + 1)]
    random.SystemRandom().shuffle(lcodes)
    dest.mkdir()
    (dest / "rule.md").write_text(RULE)
    for case, (request, work, first) in found.items():
        folder = dest / "cases" / letters[case]
        archive(work, first, folder / "product")
        (folder / "request.md").write_text(request)
    scrub(dest / "cases")
    shown, length = {}, {}
    for name, lcode in zip(have, lcodes, strict=True):
        code = name.rsplit("-r", 1)[0]
        snapshot = root / "snapshots" / code
        rows = json.loads((root / "lists" / f"{name}.json").read_text())["decisions"]
        items = [
            {
                "decision": al.squeeze(row.get("decision") or ""),
                "alternative": al.squeeze(row.get("alternative") or ""),
            }
            for row in rows[:SHOWN]
        ]  # `where` would tell the delivery
        (dest / f"{lcode}.json").write_text(
            json.dumps(
                {
                    "case": letters[key[code]["case"]],
                    "told": (snapshot / "told.md").read_text(),
                    "specification": (
                        snapshot / "repo" / "docs" / "shiploop" / "spec.md"
                    ).read_text(),
                    "items": items,
                },
                indent=1,
            )
            + "\n"
        )
        shown[lcode], length[lcode] = len(items), len(rows)
    (root / "judge-key.json").write_text(
        json.dumps(
            {
                "lists": dict(sorted(zip(lcodes, have, strict=True))),
                "no_list": missing,
                "shown": dict(sorted(shown.items())),
                "length": dict(sorted(length.items())),
            },
            indent=1,
        )
        + "\n"
    )
    print(
        f"{len(have)} lists packed under shuffled codes in {dest} (cases {letters}); wanted lists without a list: {missing or 'none'}"
    )
    return 0


def check_verdict(root: Path, rows: object) -> tuple[dict, list[str]]:
    """A judge's `lists` against the judging folder: the verdicts by L code, and every fault found."""
    items = {
        path.stem: json.loads(path.read_text())["items"]
        for path in sorted((root / "judging").glob("L*.json"))
    }
    if not isinstance(rows, list):
        return {}, [f"the verdict's lists is not a list: {rows!r:.80}"]
    verdicts, faults = {}, []
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            faults.append(f"entry {n} is not an object: {row!r:.80}")
            continue
        code = row.get("list")
        if not isinstance(code, str) or code not in items:
            faults.append(f"entry {n}: {code!r} is not a list of the folder")
            continue
        if code in verdicts:
            faults.append(f"{code}: named twice")
            continue
        shown = len(items[code])
        bad = [q for q in QUESTIONS if not isinstance(row.get(q), bool)]
        if bad:
            faults.append(
                f"{code}: {', '.join(f'{q} {row.get(q)!r}' for q in bad)} not true or false"
            )
        classes = row.get("classes")
        if not isinstance(classes, list) or len(classes) != shown:
            faults.append(f"{code}: classes {classes!r:.80} is not a list of {shown}")
        elif any(c not in CLASSES for c in classes):
            faults.append(f"{code}: classes {classes!r} hold a class outside {CLASSES}")
        for field in PLACES:
            place = row.get(field)
            if (
                isinstance(place, bool)
                or not isinstance(place, int)
                or not 0 <= place <= shown
            ):
                faults.append(
                    f"{code}: {field} {place!r} is not a place among {shown} items, or 0"
                )
        verdicts[code] = {
            field: row.get(field) for field in (*QUESTIONS, "classes", *PLACES)
        }
    faults += [f"{code}: no entry" for code in items if code not in verdicts]
    return verdicts, faults


def write_judged(root: Path, judge_name: str, verdicts: dict, cost: object) -> str:
    judge = grade.JUDGES[judge_name]
    (root / f"judged-{judge_name}.json").write_text(
        json.dumps(
            {
                "judge": judge["model"],
                "judge_effort": judge["effort"],
                "cost_usd": cost,
                "prompt_sha256": sha(JUDGE_PROMPT),
                "rule_sha256": sha(RULE),
                "verdicts": dict(sorted(verdicts.items())),
            },
            indent=1,
        )
        + "\n"
    )
    placed = {field: sum(1 for v in verdicts.values() if v[field]) for field in PLACES}
    return (
        f"DONE judge {judge_name}: {len(verdicts)} lists; way_back placed in {placed['way_back']}, refusal in"
        f" {placed['refusal']}; told_way_back true in {sum(1 for v in verdicts.values() if v['told_way_back'])}"
    )


def cmd_judge(root: Path, judge_name: str, timeout: int) -> int:
    if judge_name not in grade.JUDGES:
        raise SystemExit(f"JUDGE is one of {sorted(grade.JUDGES)}")
    if (root / f"judged-{judge_name}.json").is_file():
        raise SystemExit(
            f"judged-{judge_name}.json exists: a judge reads the lists once"
        )
    cwd = root / "judge-sessions" / f"{judge_name}-{uuid.uuid4().hex[:6]}"
    shutil.copytree(root / "judging", cwd)
    rc, cost = grade.run_session(JUDGE_PROMPT, cwd, grade.JUDGES[judge_name], timeout)
    rows, problem = grade.read_verdict(cwd, "lists")
    verdicts, faults = check_verdict(root, rows)
    faults = ([f"rc={rc}"] if rc != 0 else []) + ([problem] if problem else []) + faults
    if faults:
        raise SystemExit(f"FAIL judge {judge_name}: {faults}  (session folder {cwd})")
    print(write_judged(root, judge_name, verdicts, cost))
    return 0


def reading_a(considered: int, hit: int) -> str:
    if considered < 6:
        return "too few lists to read"
    if hit * 6 >= considered * 5:
        return "filled"
    if hit * 2 < considered:
        return "not filled"
    return "partly"


def reading_b1(lists: int, repeats: int) -> str:
    if lists == 0:
        return "no such list"
    return "not repeated" if repeats * 3 <= lists else "repeated"


def reading_b2(items: int, told: int) -> str:
    if items == 0:
        return "no item"
    return "does not repeat rows" if told * 5 <= items else "repeats rows"


def reading_c(new_counts: list[int]) -> str:
    if not new_counts:
        return "no list"
    middle = statistics.median(new_counts)
    return (
        "adds real open points"
        if middle >= 3
        else "adds noise"
        if middle <= 1
        else "in between"
    )


def reading_d(lengths: list[int], new_counts: list[int]) -> str:
    if not lengths:
        return "no list"
    if statistics.median(lengths) <= 2:
        return "quiet"
    if statistics.median(lengths) >= 5 and statistics.median(new_counts) <= 1:
        return "floods"
    return "in between"


def reading_e(lists: int, hit: int) -> str:
    if lists < 6:
        return "too few lists to read"
    if hit * 6 >= lists * 5:
        return "completes it"
    if hit * 2 < lists:
        return "does not"
    return "partly"


def overall(a: str, b1: str, b2: str, c: str) -> str:
    if (
        a == "filled"
        and b1 != "repeated"
        and b2 == "does not repeat rows"
        and c == "adds real open points"
    ):
        return "earns a trial in ShipLoop"
    if a == "not filled" or c == "adds noise":
        return "does not earn one"
    return "mixed: described, no proposal"


def median(values: list) -> object:
    return statistics.median(values) if values else None


def score_set(lcodes: list[str], info: dict, jk: dict, judged: dict) -> dict:
    """The readings for one set of lists (L codes)."""

    def both(lcode: str, field: str) -> tuple:
        return judged["opus"][lcode][field], judged["astra"][lcode][field]

    def by_both(lcode: str, cls: str) -> int:
        return sum(
            1 for a, b in zip(*both(lcode, "classes"), strict=True) if a == b == cls
        )

    due = [lc for lc in lcodes if info[lc]["case"] == "due"]
    hello = [lc for lc in lcodes if info[lc]["case"] == "hello"]
    considered = [lc for lc in due if both(lc, "told_way_back") == (False, False)]
    hit_a = [lc for lc in considered if all(1 <= p <= 3 for p in both(lc, "way_back"))]
    told_back = [lc for lc in due if both(lc, "told_way_back") == (True, True)]
    repeats = [lc for lc in told_back if any(p > 0 for p in both(lc, "way_back"))]
    disagree = [lc for lc in due if len(set(both(lc, "told_way_back"))) == 2]
    items = sum(jk["shown"][lc] for lc in due)
    told = sum(by_both(lc, "told") for lc in due)
    new_due = [by_both(lc, "new") for lc in due]
    lengths_hello = [jk["length"][lc] for lc in hello]
    new_hello = [by_both(lc, "new") for lc in hello]
    refusing = [
        lc
        for lc in due
        if both(lc, "spec_refuses") == (True, True)
        and both(lc, "told_refusal") == (False, False)
    ]
    hit_e = [lc for lc in refusing if all(1 <= p <= 3 for p in both(lc, "refusal"))]
    a, b1 = (
        reading_a(len(considered), len(hit_a)),
        reading_b1(len(told_back), len(repeats)),
    )
    b2, c = reading_b2(items, told), reading_c(new_due)
    cases = sorted({info[lc]["case"] for lc in lcodes})
    shown_all = [
        pair for lc in lcodes for pair in zip(*both(lc, "classes"), strict=True)
    ]
    return {
        "lists_by_case": {
            case: sum(1 for lc in lcodes if info[lc]["case"] == case) for case in cases
        },
        "lengths_by_case": {
            case: sorted(jk["length"][lc] for lc in lcodes if info[lc]["case"] == case)
            for case in cases
        },
        "A": {"considered": len(considered), "hit": len(hit_a), "reading": a},
        "B1": {
            "lists": len(told_back),
            "repeats": len(repeats),
            "due_lists_judges_disagree_told_way_back": len(disagree),
            "reading": b1,
        },
        "B2": {"items": items, "told": told, "reading": b2},
        "C": {"new_counts": new_due, "median": median(new_due), "reading": c},
        "D": {
            "lengths": lengths_hello,
            "median_length": median(lengths_hello),
            "new_counts": new_hello,
            "median_new": median(new_hello),
            "reading": reading_d(lengths_hello, new_hello),
        },
        "E": {
            "lists": len(refusing),
            "hit": len(hit_e),
            "reading": reading_e(len(refusing), len(hit_e)),
        },
        "overall": overall(a, b1, b2, c),
        "classes": {
            judge: {
                cls: sum(1 for pair in shown_all if pair[n] == cls) for cls in CLASSES
            }
            for n, judge in enumerate(("opus", "astra"))
        },
        "same_class": {
            "same": sum(1 for a_, b_ in shown_all if a_ == b_),
            "of": len(shown_all),
        },
    }


def set_text(name: str, block: dict) -> list[str]:
    a, b1, b2, c, d, e = (block[k] for k in ("A", "B1", "B2", "C", "D", "E"))
    return [
        f"== set {name}"
        + (
            " (the set the rule reads: wordings final and latest)"
            if name == "final"
            else " (every list)"
        )
        + " ==",
        f"  lists by case: {block['lists_by_case']}",
        f"  list lengths by case: {block['lengths_by_case']}",
        f"  A  way back, where told does not tell it: placed 1-3 by both judges in {a['hit']} of {a['considered']} due lists -> {a['reading']}",
        (
            f"  B1 way back, where told tells it: placed by either judge in {b1['repeats']} of {b1['lists']} due lists -> {b1['reading']}"
            f"  (due lists the judges disagree on told_way_back: {b1['due_lists_judges_disagree_told_way_back']}, counted in neither)"
        ),
        f"  B2 items both judges class told: {b2['told']} of {b2['items']} shown in due lists -> {b2['reading']}",
        f"  C  items new by both, per due list: {c['new_counts']} (median {c['median']}) -> {c['reading']}",
        (
            f"  D  hello lists: lengths {d['lengths']} (median {d['median_length']}), new by both {d['new_counts']}"
            f" (median {d['median_new']}) -> {d['reading']}"
        ),
        (
            f"  E  refusal, where the specification refuses and told does not tell it: placed 1-3 by both judges in {e['hit']}"
            f" of {e['lists']} due lists -> {e['reading']}"
        ),
        f"  OVERALL ({name}): {block['overall']}",
        f"  classes of the shown items: opus {block['classes']['opus']}; astra {block['classes']['astra']}",
        f"  the two judges give the same class to {block['same_class']['same']} of {block['same_class']['of']} shown items",
    ]


def cmd_score(root: Path) -> int:
    key = json.loads((root / "key.json").read_text())
    jk = json.loads((root / "judge-key.json").read_text())
    judged = {}
    for judge in ("opus", "astra"):
        path = root / f"judged-{judge}.json"
        if not path.is_file():
            raise SystemExit(f"{path.name} is missing: the score reads both judges")
        judged[judge] = json.loads(path.read_text())["verdicts"]
        if set(judged[judge]) != set(jk["lists"]):
            raise SystemExit(
                f"{path.name} does not hold a verdict for every packed list"
            )
    info = {lc: key[name.rsplit("-r", 1)[0]] for lc, name in jk["lists"].items()}
    sets = {
        "final": [lc for lc in sorted(jk["lists"]) if info[lc]["wording"] in FINAL],
        "all": sorted(jk["lists"]),
    }
    blocks = {
        name: score_set(lcodes, info, jk, judged) for name, lcodes in sets.items()
    }
    lcode_of = {name: lc for lc, name in jk["lists"].items()}
    deliveries = {}
    for code, entry in sorted(key.items(), key=lambda pair: pair[1]["name"]):
        lists = {}
        for name in (n for n in al.wanted_lists(root) if n.rsplit("-r", 1)[0] == code):
            lc = lcode_of.get(name)
            if lc is None:
                lists[name] = None
                continue
            pair = {
                f: [judged["opus"][lc][f], judged["astra"][lc][f]]
                for f in (*QUESTIONS, *PLACES)
            }
            new = sum(
                1
                for a, b in zip(
                    judged["opus"][lc]["classes"],
                    judged["astra"][lc]["classes"],
                    strict=True,
                )
                if a == b == "new"
            )
            lists[name] = {
                "list": lc,
                "length": jk["length"][lc],
                "shown": jk["shown"][lc],
                "new_by_both": new,
                **pair,
            }
        deliveries[entry["name"]] = {
            "case": entry["case"],
            "wording": entry["wording"],
            "rows": len(entry["rows"]),
            "lists": lists,
        }
    text = [
        "Second reader: score. The rule reads the `final` set; the `all` set is reported beside it.",
        "",
    ]
    for name, block in blocks.items():
        text += set_text(name, block) + [""]
    text.append("== per delivery (opus/astra) ==")
    for name, d in deliveries.items():
        text.append(f"{name} ({d['case']}, {d['wording']}, {d['rows']} rows told)")
        for list_name, li in d["lists"].items():
            if li is None:
                text.append(
                    f"   r{list_name.rsplit('-r', 1)[1]} ({list_name}): no list"
                )
                continue
            text.append(
                f"   r{list_name.rsplit('-r', 1)[1]} ({list_name}, {li['list']}): {li['length']} items ({li['shown']} shown); way_back"
                f" {li['way_back'][0]}/{li['way_back'][1]}; refusal {li['refusal'][0]}/{li['refusal'][1]}; new by both"
                f" {li['new_by_both']}; "
                + "; ".join(
                    f"{q} {'/'.join('T' if v else 'F' for v in li[q])}"
                    for q in QUESTIONS
                )
            )
    text.append(f"wanted lists without a list: {jk['no_list'] or 'none'}")
    print("\n".join(text))
    (root / "score.json").write_text(
        json.dumps(
            {
                "read_set": "final",
                "sets": blocks,
                "deliveries": deliveries,
                "no_list": jk["no_list"],
            },
            indent=1,
        )
        + "\n"
    )
    return 0


def cmd_leaks(root: Path) -> int:
    """Did a lister reach back to the delivery its snapshot was cut from? As ask_later's leaks; a root without a
    `sessions` folder has no sessions."""
    key = json.loads((root / "key.json").read_text())
    real = sorted(
        {info["delivery"] for info in key.values()}
        | {str(Path(info["delivery"]).parent) for info in key.values()}
    )
    folder = root / "sessions"
    sessions = sorted(
        path
        for path in (folder.iterdir() if folder.is_dir() else ())
        if path.is_dir() and not path.name.startswith(".")
    )
    named = {}
    for session in sessions:
        stream = session / ".stream.jsonl"
        text = stream.read_text(errors="replace") if stream.is_file() else ""
        hits = [path for path in real if path in text]
        if hits:
            named[session.name] = hits
    print(
        f"{len(sessions)} lister session folders; sessions whose stream names a delivery's real folder: {named or 'none'}"
    )
    (root / "leaks.json").write_text(
        json.dumps(
            {
                "real_folders": real,
                "sessions": len(sessions),
                "sessions_naming_one": named,
            },
            indent=1,
        )
        + "\n"
    )
    return 1 if named else 0


# ---------------------------------------------------------------- selftest: made-up lists and verdicts, no model

# What each made-up list holds, by the role its delivery plays: one entry an item, its class and the described
# decisions it is about. The made-up judges read the class and the markers back from the item's text.
MADE_UP = {
    "told_back": ["new", "new", "new", "unseen"],
    "refuses": ["new WAYBACK", "new REFUSAL", "new", "told", "unseen", "new", "new"],
    "plain": ["new", "new WAYBACK", "new", "settled"],
    "hello": ["unseen", "settled", "new", "unseen", "unseen", "new", "new"],
    "zero": ["told", "new"],  # and nothing at repeat 1
    "judges_split": ["told", "told", "new"],
    "classes_split": ["unfounded", "new"],
    "early": ["new", "unseen"],
    "early_hello": ["unseen"],
}


def made_up_roles(key: dict) -> dict[str, str]:
    """The role of each delivery in the made-up construction, by name: in the final set the first due delivery's rows
    tell the way back, the next two have a specification that refuses and rows that do not tell it, the others are
    plain; outside it, three due deliveries carry a list with no item, a split on told_way_back and a split on a class."""
    names = {info["name"]: info for info in key.values()}
    final_due = sorted(
        n for n, i in names.items() if i["case"] == "due" and i["wording"] in FINAL
    )
    early_due = sorted(
        n for n, i in names.items() if i["case"] == "due" and i["wording"] not in FINAL
    )
    roles = {
        n: "hello" if i["wording"] in FINAL else "early_hello"
        for n, i in names.items()
        if i["case"] == "hello"
    }
    roles.update({n: "plain" for n in final_due})
    roles.update(
        dict(zip(final_due, ["told_back", "refuses", "refuses"], strict=False))
    )
    roles.update({n: "early" for n in early_due})
    roles.update(
        dict(zip(early_due, ["zero", "judges_split", "classes_split"], strict=False))
    )
    return roles


def made_up_decisions(role: str, repeat: int) -> list[dict]:
    if role == "zero" and repeat == 1:
        return []
    return [
        {
            "decision": f"made-up decision {n} [{spec.split()[0]}]"
            + "".join(f" {m}" for m in spec.split()[1:]),
            "alternative": "another reading",
            "where": "nowhere",
        }
        for n, spec in enumerate(MADE_UP[role], 1)
    ]


def first_with(items: list[dict], marker: str) -> int:
    return next((n for n, item in enumerate(items, 1) if marker in item["decision"]), 0)


def made_up_rows(
    root: Path, judge: str, roles: dict, variant: str = "base"
) -> list[dict]:
    """What a made-up judge would write as `lists`: classes and places read from the items, the three answers from the
    delivery's role (un-blinded through the keys)."""
    key = json.loads((root / "key.json").read_text())
    jk = json.loads((root / "judge-key.json").read_text())
    rows = []
    for lc, name in sorted(jk["lists"].items()):
        info = key[name.rsplit("-r", 1)[0]]
        role = roles[info["name"]]
        items = json.loads((root / "judging" / f"{lc}.json").read_text())["items"]
        classes = [re.search(r"\[(\w+)\]", item["decision"]).group(1) for item in items]
        if role == "classes_split" and judge == "astra" and len(classes) > 1:
            classes[1] = "settled"
        row = {
            "list": lc,
            "told_way_back": role == "told_back"
            or (role == "judges_split" and judge == "opus"),
            "spec_refuses": role == "refuses",
            "told_refusal": False,
            "classes": classes,
            "way_back": first_with(items, "WAYBACK"),
            "refusal": first_with(items, "REFUSAL"),
        }
        if variant == "noise" and info["case"] == "due":
            row["classes"] = ["unseen"] * len(classes)
        if variant == "repeated" and role == "told_back" and judge == "opus":
            row["way_back"] = 1
        rows.append(row)
    return rows


def texts_of(path: Path) -> dict[str, str]:
    """The texts between `=== BEGIN NAME ===` and `=== END NAME ===` lines."""
    return dict(
        re.findall(
            r"^=== BEGIN (\w+) ===\n(.*?)^=== END \1 ===$",
            path.read_text(),
            re.DOTALL | re.MULTILINE,
        )
    )


def cmd_selftest(scratch: Path, manifest: Path, rows_ref: str | None) -> int:
    """The whole path on the real deliveries with made-up lists and verdicts: what is rehearsed is the handling, not
    any judgement. No model session can start: run_session is replaced by a tripwire for the whole selftest."""
    base = scratch / f"selftest-{uuid.uuid4().hex[:6]}"
    base.mkdir(parents=True)
    failed = []

    def expect(what: str, held: bool, detail: object = "") -> None:
        print(("ok   " + what) if held else f"FAILED {what}: {detail}")
        if not held:
            failed.append(what)

    def refused(call) -> tuple[bool, str]:
        try:
            call()
        except SystemExit as stop:
            return True, str(stop)
        return False, "it went on"

    def tripwire(*_args, **_kwargs):
        raise RuntimeError("the selftest tried to start a model session")

    real_session = grade.run_session
    grade.run_session = tripwire
    try:
        _selftest(base, manifest, rows_ref, expect, refused, tripwire)
    finally:
        grade.run_session = real_session
    print(f"\n{len(failed)} failed" if failed else "\nall held")
    return 1 if failed else 0


def _selftest(
    base: Path, manifest: Path, rows_ref: str | None, expect, refused, tripwire
) -> None:
    entries = json.loads(manifest.read_text())
    home = str(Path.home())
    root = base / "root"
    print(f"selftest folder {base}")

    # 1. snapshots
    expect("snap: the snapshots are cut", cmd_snap(root, manifest) == 0)
    key = json.loads((root / "key.json").read_text())
    by_name = {info["name"]: (code, info) for code, info in key.items()}
    how = {
        way: sorted(n for n, (_, i) in by_name.items() if i["found_by"] == way)
        for way in ("subject", "time")
    }
    expect(
        f"1 every delivery of the manifest has one snapshot ({len(key)} of {len(entries)}); commit found by subject:"
        f" {', '.join(how['subject']) or 'none'}; by time: {', '.join(how['time']) or 'none'}",
        sorted(by_name) == sorted(e["name"] for e in entries)
        and len(key) == len(entries),
        sorted(by_name),
    )

    # 2. the time rule against the subject rule
    agree, disagree = 0, []
    for entry in entries:
        commit, found_by, time_commit = spec_commit(entry)
        run, delivery = run_folder(entry), Path(entry["path"])
        ts = spec_ts(run, through_spec(entry)[-1][2])
        log = {c: (when, subject) for c, when, subject in work_log(delivery / "work")}
        if found_by == "subject":
            if time_commit == commit:
                agree += 1
            else:
                disagree.append(
                    f"{entry['name']}: subject {commit[:10]} at {log[commit][0]}, time rule"
                    f" {(time_commit or 'None')[:10]} at {log.get(time_commit, ('-',))[0]}, spec accepted at {ts}"
                )
        else:
            print(
                f"     {entry['name']}: by time, commit {commit[:10]} at {log[commit][0]} ({log[commit][1]!r});"
                f" spec accepted at {ts}"
            )
    expect(
        f"2 the time rule gives the subject's commit for {agree} of {agree + len(disagree)} deliveries found by subject",
        not disagree,
        disagree,
    )

    # 3. no home path
    snap_files = [p for p in (root / "snapshots").rglob("*") if p.is_file()]
    leaks = []
    for p in snap_files:
        try:
            if home in p.read_text():
                leaks.append(str(p))
        except UnicodeDecodeError:
            pass
    expect(
        f"3 no text file of a snapshot names the home path ({len(snap_files)} files)",
        not leaks,
        leaks[:3],
    )

    # 4. the files of a snapshot
    bad = []
    for code, info in key.items():
        dest = root / "snapshots" / code
        records = sorted(p.name for p in (dest / "record").iterdir())
        specs = [r for r in records if r.endswith("-spec.md")]
        told = (dest / "told.md").read_text() if (dest / "told.md").is_file() else ""
        if not all(
            (dest / f).is_file()
            for f in ("request.md", "told.md", "repo/docs/shiploop/spec.md")
        ):
            bad.append(f"{info['name']}: a file is missing")
        if len(specs) != 1 or records[-1] != specs[0] or records != info["record"]:
            bad.append(f"{info['name']}: records {records}")
        rows = len(info["rows"])
        told_ok = (
            told.startswith(TOLD_HEAD + "\n1. (")
            and told.count("\n   Decided: ") == told.count("\n   Otherwise: ") == rows
            and told.count("\n\n")
            == rows + 1  # under the title, under the head, and between rows
            and told.endswith("\n")
            and not told.endswith("\n\n")
            if rows
            else told == TOLD_NONE
        )
        if not told_ok or sha(told) != info["told_sha256"]:
            bad.append(f"{info['name']}: told.md")
    expect(
        "4 every snapshot has request.md, told.md (one block a row told) and the spec, and its one -spec.md record is its last",
        not bad,
        bad,
    )

    # 5. the rows against the other session's rows.txt
    if rows_ref:
        compared, matched, absent, differ = 0, 0, [], []
        for name, (_, info) in sorted(by_name.items()):
            where = next(
                (
                    path
                    for path in (
                        f"docs/experiments/ratchet-pilot-20261120/shiploop-defaults/evidence/{folder}/{name}/rows.txt"
                        for folder in ("wave-1", "wave-2", "sonnet-1")
                    )
                    if subprocess.run(
                        [
                            "git",
                            "-C",
                            str(REPO),
                            "cat-file",
                            "-e",
                            f"{rows_ref}:{path}",
                        ],
                        capture_output=True,
                        check=False,
                    ).returncode
                    == 0
                ),
                None,
            )
            if where is None:
                absent.append(name)
                continue
            compared += 1
            theirs = [
                al.squeeze(line)
                for line in git(REPO, "show", f"{rows_ref}:{where}").splitlines()
                if line.strip()
            ]
            if theirs == info["rows"]:
                matched += 1
            else:
                differ.append(f"{name}: {where}")
        print(
            f"     rows.txt not at {rows_ref} for: {', '.join(absent) or 'none'} (not a failure)"
        )
        expect(
            f"5 the rows equal the other session's rows.txt for {matched} of {compared} compared",
            not differ,
            differ,
        )
    else:
        print("     5 skipped: no --rows-ref")

    # 6. made once
    held, said = refused(lambda: cmd_snap(root, manifest))
    expect(
        "6 snap refuses a second run on the same root",
        held and "made once" in said,
        said,
    )

    # 7. made-up lists, pack, made-up verdicts, score
    roles = made_up_roles(key)
    names = {i["name"]: i for i in key.values()}
    final_due = sorted(
        n for n, i in names.items() if i["case"] == "due" and i["wording"] in FINAL
    )
    final_hello = sorted(
        n for n, i in names.items() if i["case"] == "hello" and i["wording"] in FINAL
    )
    if len(final_due) < 3 or not final_hello:
        expect(
            "7 the manifest has the deliveries the construction needs",
            False,
            (final_due, final_hello),
        )
        return
    (root / "lists").mkdir()
    for code, info in key.items():
        for repeat in (1, 2, 3):
            (root / "lists" / f"{code}-r{repeat}.json").write_text(
                list_record(
                    code,
                    repeat,
                    1,
                    None,
                    made_up_decisions(roles[info["name"]], repeat),
                )
            )
    expect("7 pack: the made-up lists are packed", cmd_pack(root) == 0)
    jk = json.loads((root / "judge-key.json").read_text())
    letters = sorted(p.name for p in (root / "judging" / "cases").iterdir())
    lfiles = sorted((root / "judging").glob("L*.json"))
    packed = [json.loads(p.read_text()) for p in lfiles]
    expect(
        f"7 the judges' folder: rule.md is RULE, cases {letters} (due A, hello B), {len(lfiles)} L files of at most five"
        " items with no `where`, the key's shown and length right",
        (root / "judging" / "rule.md").read_text() == RULE
        and letters == ["A", "B"]
        and len(lfiles) == 3 * len(key)
        and not jk["no_list"]
        and all(
            len(f["items"]) <= SHOWN
            and all(set(i) == {"decision", "alternative"} for i in f["items"])
            for f in packed
        )
        and all(
            jk["length"][lc]
            == len(
                made_up_decisions(
                    roles[key[n.rsplit("-r", 1)[0]]["name"]], int(n.rsplit("-r", 1)[1])
                )
            )
            and jk["shown"][lc] == min(SHOWN, jk["length"][lc])
            for lc, n in jk["lists"].items()
        ),
    )
    first_tree = {}
    for case in ("due", "hello"):
        code = min(c for c, i in key.items() if i["case"] == case)
        work = Path(key[code]["delivery"]) / "work"
        first_tree[case] = sorted(
            git(work, "ls-tree", "-r", "--name-only", work_log(work)[0][0]).split()
        )
    product = {
        case: sorted(
            str(p.relative_to(root / "judging" / "cases" / letter / "product"))
            for p in (root / "judging" / "cases" / letter / "product").rglob("*")
            if p.is_file()
        )
        for case, letter in (("due", "A"), ("hello", "B"))
    }
    letter_of = {"due": "A", "hello": "B"}
    requests = {
        case: (root / "judging" / "cases" / letter / "request.md").read_text()
        for case, letter in letter_of.items()
    }
    expect(
        f"7 each case's product/ is its deliveries' first commit ({len(product['due'])} files for due,"
        f" {len(product['hello'])} for hello)",
        product == first_tree,
        {case: (product[case][:5], first_tree[case][:5]) for case in product},
    )
    expect(
        f"A2 the judges' request.md files hold no {TOKEN.strip()!r} and equal every snapshot's request without it",
        all(TOKEN.strip() not in text and text.strip() for text in requests.values())
        and all(
            (root / "snapshots" / c / "request.md").read_text().replace(TOKEN, "")
            == requests[i["case"]]
            for c, i in key.items()
        ),
        {case: text[:120] for case, text in requests.items()},
    )
    held, said = refused(lambda: cmd_pack(root))
    expect("6 pack refuses a second run", held and "made once" in said, said)
    for judge in ("opus", "astra"):
        verdicts, faults = check_verdict(root, made_up_rows(root, judge, roles))
        expect(
            f"7 check_verdict takes the made-up verdicts of {judge}",
            not faults,
            faults[:3],
        )
        write_judged(root, judge, verdicts, None)
    held, said = refused(lambda: cmd_judge(root, "opus", 1))
    expect(
        "7 judge refuses a judge that has read the lists",
        held and "reads the lists once" in said,
        said,
    )
    expect("7 score: the made-up verdicts are scored", cmd_score(root) == 0)
    score = json.loads((root / "score.json").read_text())
    final = score["sets"]["final"]
    n_refuses, n_plain = 2, len(final_due) - 3
    expected = {
        "A": {
            "considered": 3 * (n_refuses + n_plain),
            "hit": 3 * (n_refuses + n_plain),
            "reading": "filled",
        },
        "B1": {
            "lists": 3,
            "repeats": 0,
            "due_lists_judges_disagree_told_way_back": 0,
            "reading": "not repeated",
        },
        "B2": {
            "items": 3 * (4 + 5 * n_refuses + 4 * n_plain),
            "told": 3 * n_refuses,
            "reading": "does not repeat rows",
        },
        "C": {
            "new_counts": [3] * 3 * len(final_due),
            "median": 3,
            "reading": "adds real open points",
        },
        "D": {
            "lengths": [7] * 3 * len(final_hello),
            "median_length": 7,
            "new_counts": [1] * 3 * len(final_hello),
            "median_new": 1,
            "reading": "floods",
        },
        "E": {"lists": 3 * n_refuses, "hit": 3 * n_refuses, "reading": "completes it"},
        "overall": "earns a trial in ShipLoop",
    }
    expect(
        f"7 the final set scores as built: A filled ({expected['A']['hit']} of {expected['A']['considered']}), B1 not"
        f" repeated (the rows of {final_due[0]} judged to tell the way back), B2 does not repeat rows, C adds real open"
        f" points, D floods, E completes it ({', '.join(final_due[1:3])} judged to refuse, untold), overall earns a trial",
        all(final[k] == v for k, v in expected.items()),
        {k: final[k] for k in expected if final[k] != expected[k]},
    )
    every = score["sets"]["all"]
    split = 3 if "judges_split" in roles.values() else 0
    class_split = 3 if "classes_split" in roles.values() else 0
    expect(
        f"7 the all set counts the judges' splits: {split} due lists split on told_way_back, the same class on"
        f" {every['same_class']['of'] - class_split} of {every['same_class']['of']} shown items",
        every["B1"]["due_lists_judges_disagree_told_way_back"] == split
        and every["same_class"]["same"] == every["same_class"]["of"] - class_split
        and every["lists_by_case"]
        == {
            "due": 3 * sum(1 for i in names.values() if i["case"] == "due"),
            "hello": 3 * sum(1 for i in names.values() if i["case"] == "hello"),
        },
        {k: every[k] for k in ("B1", "same_class", "lists_by_case")},
    )
    for variant, want in (
        ("noise", "does not earn one"),
        ("repeated", "mixed: described, no proposal"),
    ):
        other = (
            base / f"root-{variant}"
        )  # the same packed lists, scored again under other made-up verdicts
        for part in ("lists", "judging"):
            shutil.copytree(root / part, other / part)
        for part in ("key.json", "judge-key.json"):
            shutil.copy(root / part, other / part)
        faults = []
        for judge in ("opus", "astra"):
            verdicts, found = check_verdict(
                other, made_up_rows(other, judge, roles, variant)
            )
            faults += found
            write_judged(other, judge, verdicts, None)
        cmd_score(other)
        got = json.loads((other / "score.json").read_text())["sets"]["final"]
        expect(
            f"7 a second construction ({variant}) gives another overall reading: {want}"
            f" (C {got['C']['reading']}, B1 {got['B1']['reading']})",
            not faults and got["overall"] == want,
            (got["overall"], faults[:3]),
        )

    # 8. check_verdict refuses each fault on its own
    good = made_up_rows(root, "opus", roles)
    some = next(n for n, row in enumerate(good) if row["classes"])

    def changed(change) -> list:
        rows = copy.deepcopy(good)
        change(rows)
        return rows

    cases = {
        "a missing list": lambda r: r.pop(0),
        "a list named twice": lambda r: r.append(copy.deepcopy(r[0])),
        "a class outside the five": lambda r: r[some]["classes"].__setitem__(
            0, "novel"
        ),
        "classes longer than the items shown": lambda r: r[some]["classes"].append(
            "new"
        ),
        "a way_back past the items shown": lambda r: r[some].__setitem__(
            "way_back", len(r[some]["classes"]) + 1
        ),
        "a boolean given as a string": lambda r: r[some].__setitem__(
            "told_way_back", "false"
        ),
        "true where a place is expected": lambda r: r[some].__setitem__(
            "refusal", True
        ),
        "lists that are not a list": None,
    }
    for what, change in cases.items():
        rows = {"lists": good} if change is None else changed(change)
        _, faults = check_verdict(root, rows)
        expect(f"8 check_verdict refuses {what} (one fault)", len(faults) == 1, faults)

    # 9. the texts
    if TEXTS.is_file():
        given = texts_of(TEXTS)
        ours = {
            "SECOND_PROMPT": SECOND_PROMPT,
            "TOLD_HEAD": TOLD_HEAD,
            "TOLD_NONE": TOLD_NONE,
            "JUDGE_PROMPT": JUDGE_PROMPT,
            "RULE": RULE,
        }
        expect(
            f"9 the five texts equal {TEXTS.name} character for character, each ending in one newline",
            sorted(given) == sorted(ours)
            and all(
                given[n] == t
                and t.endswith("\n")
                and not t.endswith("\n\n")
                and not t.startswith("\n")
                for n, t in ours.items()
            ),
            [n for n in ours if given.get(n) != ours[n]],
        )
    else:
        print(f"     9 skipped: {TEXTS} is not there")

    # 10. the readings on their boundaries
    calls = [
        (reading_a(6, 5), "filled"),
        (reading_a(6, 4), "partly"),
        (reading_a(6, 2), "not filled"),
        (reading_a(5, 5), "too few lists to read"),
        (reading_b1(0, 0), "no such list"),
        (reading_b1(3, 1), "not repeated"),
        (reading_b1(3, 2), "repeated"),
        (reading_b2(10, 2), "does not repeat rows"),
        (reading_b2(10, 3), "repeats rows"),
        (reading_b2(0, 0), "no item"),
        (reading_c([3, 3, 2]), "adds real open points"),
        (reading_c([1, 1, 4]), "adds noise"),
        (reading_c([2, 2, 2]), "in between"),
        (reading_c([]), "no list"),
        (reading_d([1, 2, 2], [0, 0, 0]), "quiet"),
        (reading_d([6, 5, 9], [1, 0, 1]), "floods"),
        (reading_d([6, 5, 9], [2, 2, 2]), "in between"),
        (reading_d([], []), "no list"),
        (reading_e(6, 5), "completes it"),
        (reading_e(6, 2), "does not"),
        (reading_e(4, 4), "too few lists to read"),
        (reading_e(6, 4), "partly"),
        (
            overall(
                "filled",
                "not repeated",
                "does not repeat rows",
                "adds real open points",
            ),
            "earns a trial in ShipLoop",
        ),
        (
            overall(
                "filled",
                "no such list",
                "does not repeat rows",
                "adds real open points",
            ),
            "earns a trial in ShipLoop",
        ),
        (
            overall(
                "not filled",
                "not repeated",
                "does not repeat rows",
                "adds real open points",
            ),
            "does not earn one",
        ),
        (
            overall("filled", "not repeated", "does not repeat rows", "adds noise"),
            "does not earn one",
        ),
        (
            overall(
                "partly",
                "not repeated",
                "does not repeat rows",
                "adds real open points",
            ),
            "mixed: described, no proposal",
        ),
        (
            overall(
                "filled", "repeated", "does not repeat rows", "adds real open points"
            ),
            "mixed: described, no proposal",
        ),
    ]
    expect(
        "10 the readings on their boundaries",
        all(got == want for got, want in calls),
        [(n, got, want) for n, (got, want) in enumerate(calls) if got != want],
    )

    # 11. a list with no item
    zero = next((n for n, r in roles.items() if r == "zero"), None)
    if zero is None:
        expect(
            "11 the manifest has a delivery outside the final set for the list with no item",
            False,
            roles,
        )
    else:
        name = f"{by_name[zero][0]}-r1"
        lc = next(lc for lc, n in jk["lists"].items() if n == name)
        rows = made_up_rows(root, "astra", roles)
        row = next(r for r in rows if r["list"] == lc)
        verdicts, faults = check_verdict(root, rows)
        scored = score["deliveries"][zero]["lists"][name]
        expect(
            f"11 a list with no decision ({zero} r1, {lc}) is packed with no item, judged with empty classes and places 0,"
            " and scored with length 0",
            json.loads((root / "judging" / f"{lc}.json").read_text())["items"] == []
            and row["classes"] == []
            and row["way_back"] == row["refusal"] == 0
            and not faults
            and verdicts[lc]["classes"] == []
            and scored["length"] == 0
            and scored["new_by_both"] == 0,
            scored,
        )

    # 12. leaks with no sessions
    expect(
        "12 leaks: no session folder is none",
        cmd_leaks(root) == 0
        and json.loads((root / "leaks.json").read_text())["sessions"] == 0,
    )

    # 13. ask and judge with made-up sessions in place of a model
    sroot = base / "sessions-root"  # the same snapshots, with no list yet
    shutil.copytree(root / "snapshots", sroot / "snapshots")
    shutil.copy(root / "key.json", sroot / "key.json")
    codes = sorted(key)
    retry, fail, empty = codes[0], codes[1], codes[2]
    seen = []

    def lister(prompt, cwd, judge, timeout):
        code = cwd.name.split("-r")[0]
        attempt = len(list(cwd.parent.glob(f"{code}-r1-*")))
        seen.append(
            (prompt == SECOND_PROMPT, judge == al.LISTER, (cwd / "told.md").is_file())
        )
        (cwd / ".stream.jsonl").write_text("")
        if code == fail:
            return 1, None
        decisions = [
            {"decision": "made-up", "alternative": "other", "where": "nowhere"}
        ] * 2
        if code == retry and attempt == 1:
            decisions = [{"decision": "  ", "alternative": "other"}]
        if code == empty:
            decisions = []
        (cwd / "verdict.json").write_text(json.dumps({"decisions": decisions}))
        return 0, 0.01

    grade.run_session = lister
    try:
        rc = cmd_ask(sroot, 1, 60)
        lists = {
            p.stem: json.loads(p.read_text()) for p in (sroot / "lists").glob("*.json")
        }
        sessions = len(list((sroot / "sessions").iterdir()))
        expect(
            "13 ask: an empty list is kept, an unusable one is asked once more, a failing one twice and then reported",
            rc == 1
            and sorted(lists) == sorted(f"{c}-r1" for c in codes if c != fail)
            and lists[f"{retry}-r1"]["attempt"] == 2
            and lists[f"{empty}-r1"]["decisions"] == []
            and all(
                li["prompt_sha256"] == sha(SECOND_PROMPT) and li["lister"] == al.LISTER
                for li in lists.values()
            )
            and "names_outside_its_folder" not in lists[f"{empty}-r1"]
            and sessions == len(codes) + 2
            and all(all(s) for s in seen),
            (rc, sorted(lists), sessions),
        )
        rc = cmd_ask(sroot, 1, 60)
        expect(
            "13 ask again: kept lists stay, only the missing one is launched (twice)",
            rc == 1 and len(list((sroot / "sessions").iterdir())) == sessions + 2,
        )
        cmd_pack(sroot)

        def judge_session(faulty):
            def session(prompt, cwd, judge, timeout):
                seen.append(
                    (
                        prompt == JUDGE_PROMPT,
                        judge in grade.JUDGES.values(),
                        (cwd / "rule.md").is_file(),
                    )
                )
                rows = [
                    {
                        "list": p.stem,
                        "told_way_back": False,
                        "spec_refuses": False,
                        "told_refusal": False,
                        "classes": ["new"] * len(json.loads(p.read_text())["items"]),
                        "way_back": 0,
                        "refusal": 0,
                    }
                    for p in sorted(cwd.glob("L*.json"))
                ]
                (cwd / "verdict.json").write_text(
                    json.dumps({"lists": rows[1:] if faulty else rows})
                )
                return 0, 0.5

            return session

        grade.run_session = judge_session(False)
        rc = cmd_judge(sroot, "opus", 60)
        judged = json.loads((sroot / "judged-opus.json").read_text())
        grade.run_session = judge_session(True)
        held, said = refused(lambda: cmd_judge(sroot, "astra", 60))
        expect(
            "13 judge: a whole verdict is written with the judge's model, a verdict missing a list writes nothing",
            rc == 0
            and judged["judge"] == grade.JUDGES["opus"]["model"]
            and judged["prompt_sha256"] == sha(JUDGE_PROMPT)
            and judged["rule_sha256"] == sha(RULE)
            and len(judged["verdicts"]) == len(codes) - 1
            and held
            and "no entry" in said
            and not (sroot / "judged-astra.json").exists()
            and all(all(s) for s in seen),
            said,
        )
    finally:
        grade.run_session = tripwire


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "command",
        choices=("snap", "ask", "pack", "judge", "score", "leaks", "selftest"),
    )
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="seconds a session may take (ask 900, judge 2400)",
    )
    parser.add_argument(
        "--rows-ref",
        default=None,
        help="selftest: the git ref holding the other session's rows.txt files",
    )
    args = parser.parse_args()
    root = Path(args.rest[0]).resolve()
    if args.command == "snap":
        return cmd_snap(root, Path(args.rest[1]))
    if args.command == "ask":
        return cmd_ask(root, args.repeats, args.timeout or 900)
    if args.command == "pack":
        return cmd_pack(root)
    if args.command == "judge":
        return cmd_judge(root, args.rest[1], args.timeout or 2400)
    if args.command == "score":
        return cmd_score(root)
    if args.command == "leaks":
        return cmd_leaks(root)
    return cmd_selftest(root, Path(args.rest[1]), args.rows_ref)


if __name__ == "__main__":
    sys.exit(main())
