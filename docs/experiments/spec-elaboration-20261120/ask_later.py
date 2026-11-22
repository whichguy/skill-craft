#!/usr/bin/env python3
"""Asking later (journal sections 59 and 60): given what a finished ShipLoop delivery had at a point of its work, does a
fresh session list the decision that mattered among the decisions the work took for the requester?

  snap ROOT DELIVERY [DELIVERY ...]  no model: three snapshot folders a delivery (S after the specification; P the plan and the
                                     item's test cases written, nothing built; T after the item's tests ran), under codes
  ask ROOT [--repeats 3]             lister sessions (GPT Sol at medium): one list for each snapshot and repeat
  pack ROOT                          no model: the lists under shuffled codes with the target's description, for the judges
  judge ROOT JUDGE                   one judge session (opus | astra): the first item of each list that is about the target
  score ROOT                         no model: for each point, the lists that hold the target, its place, and the reading
  leaks ROOT                         no model: lister sessions whose own stream names the real folder of a delivery
  selftest SCRATCH DELIVERY [...]    no model: the whole path on real delivery folders with made-up listers and judges

A delivery folder is only read. Everything is written under ROOT, which must be outside every delivery.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
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
import grade

LISTER = {"host": "codex", "model": "gpt-6.2-sol", "effort": "medium"}
POINTS = {
    "S": "after the specification was accepted",
    "P": "the plan and the item's test cases written, nothing built",
    "T": "after the item's tests ran",
}
ELSEWHERE = "/elsewhere"  # what every path under the owner's home is replaced with in a snapshot
LIST_PROMPT = """You are preparing a question for the person who asked for a change. You report; you change nothing but the one file named at the end.

In your working directory: `request.md`, what they asked for, in their own words; `repo/`, the program's repository as it
stands now, with the work's own notes under `repo/docs/shiploop/` where there are any; and `record/`, what the work has
recorded at each step so far, in order. The work is unattended: wherever the request did not say something, it took an
answer and went on. Paths in these files that begin with `/elsewhere` name places you do not have.

List every decision the work has taken on the requester's behalf: a point the request does not settle, where the requester
could reasonably have meant something else, and where their answer would change what they, their users or their operators
get or have to do. Leave out choices they would not care about (names, file layout, internal structure) unless such a
choice changes what someone outside the code sees or must do. For each decision give: the decision as taken, in one
sentence; what else they might have meant, in one sentence; and where it is written (the file and the place in it).

Order the list by what a wrong guess would cost the requester if nobody noticed it until the change was in use, the
costliest first.

Write `verdict.json` in your working directory, and nothing else:
{"decisions": [{"decision": "<as taken>", "alternative": "<what else they might have meant>", "where": "<file and place>"}, ...]}
"""
TARGET = """The request says that the tickets already in the production data file get due times too, and that due times are
switched on in production only once the data file holds them. It does not say how they get there.

The target decision is: who or what fills in the due times of the tickets already in the data file, and when. Either the
service does it itself when it starts or when it is switched on, or a separate command has to be run by an operator
first. With it goes what the service does at start-up when the file has not been filled: start anyway, fill the file, or
refuse to start.

An item is about the target when it names this point, whichever answer it records and however it words it (a backfill, a
migration, a preparation step, an upgrade command, start-up refusing an unprepared file). An item that only touches a
neighbouring point is not: for example how a due time is computed, what the on/off setting is called, or whether an
older release can read the file afterwards.
"""
JUDGE_PROMPT = """You are matching lists against one description. You judge; you change nothing but the one file named at the end.

In your working directory: `target.md`, which describes one decision, and files named `L01.json`, `L02.json` and so on.
Each holds a list of decisions that somebody wrote down, in their order. You are not told who wrote them or when.

For each list, find the first item that is about the target decision as `target.md` defines it. Read every item of
every list.

Write `verdict.json` in your working directory, and nothing else:
{"lists": [{"list": "L01", "rank": <the 1-based position of that item in its list, or 0 when no item is about the target>, "quote": "<that item's `decision` text, copied exactly, or an empty string>"}, ...]}
One entry for every list file.
"""


def sh(argv: list[str], data: bytes | None = None) -> bytes:
    return subprocess.run(argv, input=data, capture_output=True, check=True).stdout


def squeeze(text: str) -> str:
    return " ".join(str(text).split())


def run_of(delivery: Path) -> Path:
    runs = sorted(delivery.glob(".shiploop-runs/*/run"))
    if len(runs) != 1:
        raise SystemExit(f"{delivery}: {len(runs)} ShipLoop run folders, not one")
    return runs[0]


def accepted(run: Path) -> list[tuple[str, str | None, str]]:
    """Every stage ShipLoop accepted as done, in order: stage, work item, action."""
    found = []
    for line in (run / "trace.jsonl").read_text().splitlines():
        row = json.loads(line) if line.strip() else {}
        for entry in (
            (row.get("accepted") or []) if row.get("kind") == "command" else []
        ):
            if entry.get("outcome") == "done":
                found.append((entry["stage"], entry.get("item"), entry["action"]))
    return found


def points_of(delivery: Path) -> dict[str, dict]:
    """The three points of a delivery: the commit that holds the repository then, and the stages accepted by then."""
    work, order = delivery / "work", accepted(run_of(delivery))
    log = [
        line.split("\t", 1)
        for line in sh(
            ["git", "-C", str(work), "log", "--reverse", "--format=%H%x09%s"]
        )
        .decode()
        .splitlines()
    ]
    item = next((item for _, item, _ in order if item), None)
    stages = [stage for stage, _, _ in order]
    feats = [n for n, (_, subject) in enumerate(log) if subject.startswith("feat(")]
    built = [commit for commit, subject in log if subject.startswith(f"feat({item}/")]
    spec = [
        commit for commit, subject in log if subject.endswith("knowledge after spec")
    ]
    tests = [
        n for n, (stage, its, _) in enumerate(order) if stage == "test" and its == item
    ]
    builds = [
        n
        for n, (stage, its, _) in enumerate(order)
        if stage == "implement" and its == item
    ]
    if not (
        item
        and feats
        and feats[0] > 0
        and built
        and len(spec) == 1
        and tests
        and builds
        and "spec" in stages
    ):
        raise SystemExit(
            f"{delivery}: its commits or its trace do not mark the three points"
        )
    found = {
        "S": {"commit": spec[0], "stages": order[: stages.index("spec") + 1]},
        "P": {"commit": log[feats[0] - 1][0], "stages": order[: builds[0]]},
        "T": {"commit": built[-1], "stages": order[: tests[-1] + 1]},
    }
    for earlier, later in (("S", "P"), ("P", "T")):
        if subprocess.run(
            [
                "git",
                "-C",
                str(work),
                "merge-base",
                "--is-ancestor",
                found[earlier]["commit"],
                found[later]["commit"],
            ],
            check=False,
        ).returncode:
            raise SystemExit(
                f"{delivery}: point {earlier}'s commit does not come before point {later}'s"
            )
    return found


def home_paths(text: str) -> str:
    """A snapshot must not lead its reader back to the delivery it was cut from, where later work lies."""
    return text.replace(str(Path.home()), ELSEWHERE)


def cmd_snap(root: Path, deliveries: list[Path]) -> int:
    if (root / "key.json").exists():
        raise SystemExit("key.json exists: the snapshots are made once")
    if any(root == d or root in d.parents or d in root.parents for d in deliveries):
        raise SystemExit("ROOT must be outside every delivery")
    codes = [f"N{n:02d}" for n in range(1, len(POINTS) * len(deliveries) + 1)]
    random.SystemRandom().shuffle(codes)
    key = {}
    for delivery in deliveries:
        run, result = (
            run_of(delivery),
            json.loads((delivery / "result.json").read_text()),
        )
        failed = [
            c["command"].split()[-1]
            for c in result.get("checks") or []
            if "due_times_probe" in c["command"] and not c["pass"]
        ]
        for point, at in points_of(delivery).items():
            code = codes.pop()
            dest = root / "snapshots" / code
            (dest / "repo").mkdir(parents=True)
            (dest / "record").mkdir()
            sh(
                ["tar", "-x", "-C", str(dest / "repo")],
                sh(["git", "-C", str(delivery / "work"), "archive", at["commit"]]),
            )
            (dest / "request.md").write_text((run / "request.md").read_text())
            names = []
            for n, (stage, item, action) in enumerate(at["stages"], 1):
                names.append(f"{n:02d}-{stage}" + (f"-{item}" if item else "") + ".md")
                (dest / "record" / names[-1]).write_text(
                    (run / "results" / f"{action}.md").read_text()
                )
            for file in (p for p in dest.rglob("*") if p.is_file()):
                try:
                    text = file.read_text()
                except UnicodeDecodeError:
                    continue
                if str(Path.home()) in text:
                    file.write_text(home_paths(text))
            key[code] = {
                "delivery": str(delivery),
                "point": point,
                "commit": at["commit"],
                "record": names,
                "model": result.get("model"),
                "effort": result.get("effort"),
                "probes_failed": failed,
            }
            print(
                f"{code}: {delivery.name} at {point} ({POINTS[point]}): commit {at['commit'][:10]}, {len(names)} record files"
            )
    (root / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    return 0


def one_list(root: Path, code: str, repeat: int, timeout: int) -> str:
    out = root / "lists" / f"{code}-r{repeat}.json"
    if out.is_file():
        return f"kept {out.name}"
    forbidden = {str(Path.home())} | {
        Path(info["delivery"]).name
        for info in json.loads((root / "key.json").read_text()).values()
    }
    for attempt in (
        1,
        2,
    ):  # a session that leaves no usable list is launched once more, and no more
        cwd = root / "sessions" / f"{code}-r{repeat}-{uuid.uuid4().hex[:6]}"
        shutil.copytree(root / "snapshots" / code, cwd)
        rc, cost = grade.run_session(LIST_PROMPT, cwd, LISTER, timeout)
        decisions, problem = grade.read_verdict(cwd, "decisions")
        usable = (
            rc == 0
            and isinstance(decisions, list)
            and bool(decisions)
            and all(
                isinstance(d, dict) and squeeze(d.get("decision") or "")
                for d in decisions
            )
        )
        if usable:
            stream = (cwd / ".stream.jsonl").read_text(errors="replace")
            out.write_text(
                json.dumps(
                    {
                        "code": code,
                        "repeat": repeat,
                        "attempt": attempt,
                        "lister": LISTER,
                        "prompt_sha256": hashlib.sha256(
                            LIST_PROMPT.encode()
                        ).hexdigest(),
                        "cost_usd": cost,
                        "names_outside_its_folder": sorted(
                            name for name in forbidden if name in stream
                        ),
                        "decisions": decisions,
                    },
                    indent=1,
                )
                + "\n"
            )
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


def wanted_lists(root: Path) -> list[str]:
    """The list names the test consists of: every snapshot at every repeat any list was made at."""
    key = json.loads((root / "key.json").read_text())
    repeats = sorted(
        {int(path.stem.rsplit("-r", 1)[1]) for path in (root / "lists").glob("*.json")}
    )
    return [f"{code}-r{repeat}" for code in sorted(key) for repeat in repeats]


def cmd_pack(root: Path) -> int:
    dest = root / "judging"
    if dest.exists():
        raise SystemExit("the judges' folder exists: it is made once")
    names = wanted_lists(root)
    have = [name for name in names if (root / "lists" / f"{name}.json").is_file()]
    codes = [f"L{n:02d}" for n in range(1, len(have) + 1)]
    random.SystemRandom().shuffle(codes)
    dest.mkdir()
    for name, code in zip(have, codes, strict=True):
        rows = json.loads((root / "lists" / f"{name}.json").read_text())["decisions"]
        shown = [
            {
                "decision": squeeze(row.get("decision") or ""),
                "alternative": squeeze(row.get("alternative") or ""),
            }
            for row in rows
        ]
        (dest / f"{code}.json").write_text(
            json.dumps({"decisions": shown}, indent=1) + "\n"
        )  # `where` would tell the point
    (dest / "target.md").write_text(TARGET)
    (root / "judge-key.json").write_text(
        json.dumps(
            {
                "lists": dict(zip(codes, have, strict=True)),
                "no_list": sorted(set(names) - set(have)),
            },
            indent=1,
        )
        + "\n"
    )
    print(
        f"{len(have)} lists under shuffled codes in {dest}; without a list: {sorted(set(names) - set(have)) or 'none'}"
    )
    return 0


def cmd_judge(root: Path, judge_name: str, timeout: int) -> int:
    out = root / f"judged-{judge_name}.json"
    if out.is_file():
        raise SystemExit(f"{out.name} exists: a judge reads the lists once")
    codes = json.loads((root / "judge-key.json").read_text())["lists"]
    cwd = root / "judge-sessions" / f"{judge_name}-{uuid.uuid4().hex[:6]}"
    shutil.copytree(root / "judging", cwd)
    rc, cost = grade.run_session(JUDGE_PROMPT, cwd, grade.JUDGES[judge_name], timeout)
    rows, problem = grade.read_verdict(cwd, "lists")
    if rc != 0 or not isinstance(rows, list):
        raise SystemExit(
            f"FAIL judge {judge_name}: rc={rc} {problem or ''} (session folder {cwd})"
        )
    ranks, bad = {}, []
    for row in rows:
        code = row.get("list") if isinstance(row, dict) else None
        if code not in codes or code in ranks:
            bad.append(f"{code}: not a list of the folder, or named twice")
            continue
        items = json.loads((root / "judging" / f"{code}.json").read_text())["decisions"]
        rank = row.get("rank")
        if not isinstance(rank, int) or not 0 <= rank <= len(items):
            bad.append(
                f"{code}: rank {rank!r} is not a place in a list of {len(items)}"
            )
        elif rank and squeeze(row.get("quote") or "") != items[rank - 1]["decision"]:
            bad.append(f"{code}: the quote is not the item at place {rank}")
        ranks[code] = rank
    bad += [f"{code}: no entry" for code in codes if code not in ranks]
    if bad:
        raise SystemExit(f"FAIL judge {judge_name}: {bad}  (session folder {cwd})")
    judge = grade.JUDGES[judge_name]
    out.write_text(
        json.dumps(
            {
                "judge": judge["model"],
                "judge_effort": judge["effort"],
                "cost_usd": cost,
                "prompt_sha256": hashlib.sha256(JUDGE_PROMPT.encode()).hexdigest(),
                "target_sha256": hashlib.sha256(TARGET.encode()).hexdigest(),
                "ranks": ranks,
            },
            indent=1,
        )
        + "\n"
    )
    print(
        f"DONE judge {judge_name}: the target is in {sum(1 for rank in ranks.values() if rank)} of {len(ranks)} lists"
    )
    return 0


def cmd_leaks(root: Path) -> int:
    """Did a lister reach back to the delivery its snapshot was cut from? A snapshot names that folder only under the
    replaced prefix, so the real path can stand in a session's stream only if the session built it itself. (The field
    `names_outside_its_folder` kept with each list cannot tell: a session's own folder lies under the same home, and a
    delivery's name survives inside the replaced paths. Added after the first lists came back, section 60.)"""
    key = json.loads((root / "key.json").read_text())
    real = sorted(
        {info["delivery"] for info in key.values()}
        | {str(Path(info["delivery"]).parent) for info in key.values()}
    )
    sessions = sorted(
        path
        for path in (root / "sessions").iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    named = {}
    for session in sessions:
        stream = session / ".stream.jsonl"
        hits = [
            path
            for path in real
            if stream.is_file() and path in stream.read_text(errors="replace")
        ]
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


def reading(found: dict[str, int], lists: int) -> str:
    """Section 59's reading, from how many of each point's lists hold the target."""
    if found["S"] >= lists - 1:
        return "found at the specification already: timing cannot show"
    if found["T"] - found["S"] >= 3 and found["P"] >= found["S"]:
        return "shown: asking later finds it more often"
    if found["S"] - found["T"] >= 3:
        return "the opposite: asking later finds it less often"
    return "not shown"


def cmd_score(root: Path) -> int:
    key, codes = (
        json.loads((root / "key.json").read_text()),
        json.loads((root / "judge-key.json").read_text()),
    )
    judged = {
        name: json.loads((root / f"judged-{name}.json").read_text())["ranks"]
        for name in ("opus", "astra")
    }
    place = {}
    for code, name in codes["lists"].items():
        both = [judged[judge][code] for judge in judged]
        place[name] = (
            max(both) if all(both) else 0
        )  # on the list only when both judges find it; its place is the later one
    table, found = {}, {}
    for point, when in POINTS.items():
        names = [
            name
            for name in wanted_lists(root)
            if key[name.rsplit("-r", 1)[0]]["point"] == point
        ]
        places = [place.get(name, 0) for name in names]
        lengths = [
            len(json.loads((root / "lists" / f"{name}.json").read_text())["decisions"])
            for name in names
            if (root / "lists" / f"{name}.json").is_file()
        ]
        found[point] = sum(1 for p in places if p)
        table[point] = {
            "lists": len(names),
            "on_the_list": found[point],
            "first": sum(1 for p in places if p == 1),
            "first_three": sum(1 for p in places if 1 <= p <= 3),
            "places": sorted(p for p in places if p),
            "median_length": statistics.median(lengths) if lengths else None,
            "lengths": sorted(lengths),
        }
        print(
            f"{point} ({when}): on the list in {found[point]} of {len(names)}; first in {table[point]['first']}; in the first three in {table[point]['first_three']}; places {table[point]['places']}; list lengths {table[point]['lengths']}"
        )
        for delivery in sorted({info["delivery"] for info in key.values()}):
            own = [
                place.get(name, 0)
                for name in names
                if key[name.rsplit("-r", 1)[0]]["delivery"] == delivery
            ]
            print(f"    {Path(delivery).name}: places {own} (0 is not on the list)")
    lists = table["S"]["lists"]
    said = reading(found, lists)
    print(f"READING: {said}")
    disagreed = sorted(
        name
        for code, name in codes["lists"].items()
        if bool(judged["opus"][code]) != bool(judged["astra"][code])
    )
    print(
        f"lists where one judge finds the target and the other does not: {disagreed or 'none'}"
    )
    (root / "score.json").write_text(
        json.dumps(
            {
                "points": table,
                "reading": said,
                "judges_disagree": disagreed,
                "no_list": codes["no_list"],
            },
            indent=1,
        )
        + "\n"
    )
    return 0


def cmd_selftest(scratch: Path, deliveries: list[Path]) -> int:
    """The whole path with made-up listers and judges: what is rehearsed is the handling, not any judgement."""
    if scratch.exists():
        raise SystemExit("SCRATCH must not exist")
    failed = []

    def expect(what: str, held: bool, shown: object = "") -> None:
        print(
            ("ok    " if held else "FAIL  ")
            + what
            + (f"  [{shown}]" if not held else "")
        )
        if not held:
            failed.append(what)

    root = scratch / "root"
    root.mkdir(parents=True)
    expect(
        "snapshots are cut for every delivery and point",
        cmd_snap(root, deliveries) == 0,
    )
    key = json.loads((root / "key.json").read_text())
    expect(
        "three snapshots a delivery, each point once",
        sorted(info["point"] for info in key.values())
        == sorted(list(POINTS) * len(deliveries)),
    )
    home = str(Path.home())
    texts = [p for p in (root / "snapshots").rglob("*") if p.is_file()]
    leaks = []
    for p in texts:
        try:
            if home in p.read_text():
                leaks.append(str(p))
        except UnicodeDecodeError:
            pass
    expect(
        "no file of a snapshot names a path under the owner's home",
        not leaks,
        leaks[:3],
    )
    by = {(info["delivery"], info["point"]): (code, info) for code, info in key.items()}
    grows = all(
        by[d, "S"][1]["record"]
        == by[d, "P"][1]["record"][: len(by[d, "S"][1]["record"])]
        and by[d, "P"][1]["record"]
        == by[d, "T"][1]["record"][: len(by[d, "P"][1]["record"])]
        and len(by[d, "S"][1]["record"])
        < len(by[d, "P"][1]["record"])
        < len(by[d, "T"][1]["record"])
        for d in {info["delivery"] for info in key.values()}
    )
    expect("each later point's record holds the earlier point's and more", grows)
    built = all(
        not any((root / "snapshots" / by[d, p][0] / "repo" / "test").glob("*due*"))
        for d in {i["delivery"] for i in key.values()}
        for p in ("S", "P")
    )
    expect(
        "nothing of the build is in a snapshot cut before it (no due-times test file at S or P)",
        built,
    )
    refused = False
    try:
        cmd_snap(root, deliveries)
    except SystemExit:
        refused = True
    expect("refused: cutting the snapshots twice", refused)

    def fake(prompt, cwd, judge, timeout):
        (cwd / ".stream.jsonl").write_text("")
        if prompt == LIST_PROMPT:
            point = (
                "T"
                if any((cwd / "record").glob("*-test-W*.md"))
                else "P"
                if any((cwd / "record").glob("*-plan.md"))
                else "S"
            )
            rows = [
                {
                    "decision": f"made-up decision {n}",
                    "alternative": "another",
                    "where": "nowhere",
                }
                for n in range(1, 4)
            ]
            if point == "P":
                rows[2]["decision"] = "TARGET a made-up backfill decision"
            if point == "T":
                rows[0]["decision"] = "TARGET a made-up backfill decision"
            (cwd / "verdict.json").write_text(json.dumps({"decisions": rows}))
        else:
            out = []
            for file in sorted(cwd.glob("L*.json")):
                items = json.loads(file.read_text())["decisions"]
                rank = next(
                    (
                        n
                        for n, item in enumerate(items, 1)
                        if item["decision"].startswith("TARGET")
                    ),
                    0,
                )
                out.append(
                    {
                        "list": file.stem,
                        "rank": rank,
                        "quote": items[rank - 1]["decision"] if rank else "",
                    }
                )
            (cwd / "verdict.json").write_text(json.dumps({"lists": out}))
        return 0, None

    real = grade.run_session
    grade.run_session = fake
    try:
        expect(
            "two repeats of every snapshot leave a list each",
            cmd_ask(root, 2, 60) == 0
            and len(list((root / "lists").glob("*.json"))) == 2 * len(key),
        )
        expect(
            "asking again keeps the lists it has",
            cmd_ask(root, 2, 60) == 0
            and len(list((root / "sessions").iterdir())) == 2 * len(key),
        )
        expect(
            "the lists are packed under new codes without the `where` of an item",
            cmd_pack(root) == 0
            and all(
                "where" not in row
                for file in (root / "judging").glob("L*.json")
                for row in json.loads(file.read_text())["decisions"]
            ),
        )
        expect(
            "both judges read the lists",
            cmd_judge(root, "opus", 60) == 0 and cmd_judge(root, "astra", 60) == 0,
        )
        expect("the score is written", cmd_score(root) == 0)
    finally:
        grade.run_session = real
    score = json.loads((root / "score.json").read_text())
    n = 2 * len(deliveries)
    expect(
        "the made-up lists score as made: never at S, third at P, first at T",
        [
            score["points"][p][k]
            for p in POINTS
            for k in ("on_the_list", "first", "first_three")
        ]
        == [0, 0, 0, n, 0, n, n, n, n],
        score["points"],
    )
    expect(
        "the reading: later by three lists or more with P no lower than S is shown; S at the ceiling cannot show; the reverse is the opposite",
        [
            reading(f, 9)
            for f in (
                {"S": 2, "P": 5, "T": 6},
                {"S": 2, "P": 1, "T": 6},
                {"S": 8, "P": 9, "T": 9},
                {"S": 6, "P": 5, "T": 3},
                {"S": 4, "P": 5, "T": 6},
            )
        ]
        == [
            "shown: asking later finds it more often",
            "not shown",
            "found at the specification already: timing cannot show",
            "the opposite: asking later finds it less often",
            "not shown",
        ],
    )
    print(f"\n{len(failed)} failed" if failed else "\nall held")
    return 1 if failed else 0


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
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    root = Path(args.rest[0]).resolve()
    if args.command == "snap":
        root.mkdir(parents=True, exist_ok=True)
        return cmd_snap(root, [Path(p).resolve() for p in args.rest[1:]])
    if args.command == "ask":
        return cmd_ask(root, args.repeats, args.timeout)
    if args.command == "pack":
        return cmd_pack(root)
    if args.command == "judge":
        return cmd_judge(root, args.rest[1], args.timeout)
    if args.command == "score":
        return cmd_score(root)
    if args.command == "leaks":
        return cmd_leaks(root)
    return cmd_selftest(root, [Path(p).resolve() for p in args.rest[1:]])


if __name__ == "__main__":
    sys.exit(main())
