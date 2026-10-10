"""The `packets` and `commits` blocks of metrics.json (SPEC, "How the harness checks the clauses", 2026-10-10).

Two records, built the way fidelity.py's block is (once, in run.py's main, so a regrade adds them too), changing no verdict, exit code
or baseline row. Absent means unknown: a part this module cannot read is null with its reason in a sibling ``*_unmeasured`` map, never
0 and never a pass; an empty list or a zero is a measured none.

``packets``    one entry per file in the run's ``packets/`` folder, ``{action, stage, file_bytes, head_bytes}``.
               ``action`` is the file's name without ``.md`` (the second packet a bound Improve child gets for one action is its
               own file, ``<action>-improve``, so the key is unique), ``stage`` the stage of the file's ``ShipLoop navigator |``
               line (first in some files, below a delegation preamble in others), ``file_bytes`` the size on disk (a recovery
               ``next`` rewrites the file, so it is the last write), and ``head_bytes`` the bytes of the head ShipLoop first printed
               for the packet, as the host recorded the reply. One reader for every host (``metrics.ToolLog.replies``): Claude's
               ``tool_result`` block, Grok's final ``output_for_prompt`` (after its ``exit: N`` line) and Codex's after the harness
               translator. The head is whole when it runs from its ``ShipLoop navigator |`` line to its own closing line (the
               status block's, or the narrative block's when one follows), its ``Full packet:`` line names the file, and its
               callback and keepalive lines are not shortened; whatever the reply holds before it (a command's own output, Grok's
               exit line) or after it (the host's ``Shell cwd was reset`` note, output the model chained) is not the head. The head's own last
               newline is counted when the reply shows it; a host that trims it leaves the count one byte short. A reply
               the model cut (``| head``, ``sed -n``, a script of its own), a head printed as a pointer and a prefix (a long packet in
               a state that prints whole), a call that names a packet file (the model reading it) and a packet no reply shows
               leave ``head_bytes`` null. Saved Claude runs are cut in most replies, so most of their heads are null. ``head_or_why`` is the one
               reader of a head and says, for a reply that is not whole, which of the NOT_WHOLE_* reasons it is.
``commits``    the commits made during the run in the product repository (the run folder's ``work/``; every ref; after the head a
               follow-on or seeded run started from, all of a fresh run's), counted by who made them. ``history`` classifies them (one
               row per commit: id, kind, author, subject, message) and ``commits`` counts the rows, so the baseline's regrade and
               tallies read the same classification:

               improve   named by ShipLoop's own ``improve-commit`` reply in the host's tool results ("Committed this review's changes
                         as <sha>"). The Improve card fixes no message shape: 63 of the 132 distinct commits those replies name, in
                         the 38 saved runs, carry none of its six ``Label:`` lines, and a model commit can carry all six.
               script    ShipLoop's other commits: the work item's commit, named by ShipLoop's reply ("ShipLoop committed W1's
                         changes (its declared paths and documentation) as <sha>") or by its subject ``feat: <work item id> <title>`` with an id of the run's
                         state.md, and the ones whose subject is ShipLoop's own and nothing else writes (the knowledge home's
                         ``docs(shiploop): record <feature> knowledge at|after <stage>``, the empty baseline, the leftovers
                         commit, a chain's prepared merge). An Improve commit has no mark of its own (the card fixes no
                         message shape): were the reply of ``improve-commit`` not recorded (cut by the model's pipe, or run by a
                         child whose tool results the host's stream does not carry: no saved Claude stream holds a sub-agent, so
                         that is not known), the commit would be counted under ``other``, so ``improve`` is a lower bound and a
                         comparison across slice B of the plan reads ``other`` beside it. None of the 35 ``other`` commits of the
                         38 saved runs is ShipLoop's: 32 carry the user's Git identity where every ShipLoop commit of those runs
                         carries its own, and 3 have git's own `[branch sha] subject` confirmation in the events
                         (docs/experiments/commit-baseline-20261010/tallies.json).
               other     the rest (the model's own ``git commit``). A commit that fits no class is counted here, not dropped, so the
                         classes sum to ``counted``.

               ``with_lessons`` counts commits whose message has a lessons section as ``shiploop_lessons.lessons`` reads it: the one
               reader of the commit-message grammar, the one ShipLoop's ``improve-commit`` gate reads with (SPEC S-12), so the harness
               and the gate cannot disagree about what counts. Presence only, the text is never judged: ``Key learnings: none`` is a
               section, as it is for the gate. ``improve`` also counts ``cited`` (a ``Learned-from`` line, as
               ``shiploop_lessons.citations`` reads it, whose token is a commit ID, 7 to 64 hexadecimal digits as the gate requires,
               that resolves to a commit in the repository: the harness asks Git and does not need the gate's reachable-from-HEAD
               rule) and ``cited_earlier_run`` (a cited commit reachable from the head the run started from: a lesson carried from an
               earlier run). A fresh run has nothing before it, so that zero is measured. The block is null, with the reason, when the
               repository, the starting head or the event stream cannot be read. Git is read through plumbing only (rev-list,
               cat-file, rev-parse, merge-base).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import metrics
import runrecord
import shiploop_lessons as commit_lessons

# ShipLoop's own words, pinned to its source by test/shiploop-e2e-commit-counters.test.py (a reworded line fails there, and does not
# silently turn every head into null).
HEAD_START = re.compile(r"^ShipLoop navigator \| (?P<stage>[\w-]+) \|", re.M)
HEADER = re.compile(r"^ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<revision>\d+)", re.M)
FULL_PACKET = re.compile(r"^Full packet: (?P<path>\S[^\n]*\.md)$", re.M)
STATUS_END = "=== end ShipLoop status ==="
NARRATIVE_BEGIN = "=== ShipLoop narrative ==="
NARRATIVE_END = "=== end ShipLoop narrative ==="
# A line the head prints whole, which a cut by column shortens: its end is how the cut is told.
CALLBACK_LINE = re.compile(r"^Callback for this stage[^\n]*$", re.M)
KEEPALIVE_LINE = re.compile(r"^Keepalive marker:[^\n]*$", re.M)

HEAD_BYTES_WHY = ("a reply is a whole print only from its head's first line to the head's own closing line, with the packet's "
                  "`Full packet:` line and unshortened callback and keepalive lines; no recorded reply is one for these packets "
                  "({cut} recorded head replies were cut by the model's own pipe or script or by the host, and the rest of the "
                  "packets are shown by no reply)")


# Why a reply that starts a head is not a whole print of it (the one reader of that: head_or_why; the baseline's tallies count them).
NOT_WHOLE_BEFORE_CLOSING = "the reply ends before the head's closing line"
NOT_WHOLE_IN_NARRATIVE = "the reply opens the narrative block and ends inside it"
NOT_WHOLE_SHORTENED = "every line is there and a callback or keepalive line is shortened (a cut by column)"


def head_or_why(reply: str) -> tuple[str | None, str | None]:
    """(the head, None) at the start of ``reply`` (which starts at its ``ShipLoop navigator |`` line), up to its closing line (the
    status block's end, then the narrative block when one follows it); or (None, why) with one of the NOT_WHOLE_* reasons."""
    end = reply.find(STATUS_END)
    if end < 0:
        return None, NOT_WHOLE_BEFORE_CLOSING
    cut = end + len(STATUS_END)
    if re.match(r"\n*" + re.escape(NARRATIVE_BEGIN), reply[cut:]):
        close = reply.find(NARRATIVE_END, cut)
        if close < 0:
            return None, NOT_WHOLE_IN_NARRATIVE
        cut = close + len(NARRATIVE_END)
    if reply[cut:cut + 1] == "\n":
        cut += 1
    head = reply[:cut]
    # A cut by column keeps every line and shortens the long ones: the callback line must still end with its result path and the
    # keepalive line with the run directory, as ShipLoop prints them.
    if any(not line.rstrip().endswith(".md") for line in CALLBACK_LINE.findall(head)):
        return None, NOT_WHOLE_SHORTENED
    if any(not re.search(r"\bdir=\S+$", line.rstrip()) for line in KEEPALIVE_LINE.findall(head)):
        return None, NOT_WHOLE_SHORTENED
    return head, None


def heads(reply: str):
    """Each head in a reply as (text from its first line to the next head's first line or the end of the reply)."""
    starts = [match.start() for match in HEAD_START.finditer(reply)]
    for index, start in enumerate(starts):
        yield reply[start:starts[index + 1] if index + 1 < len(starts) else len(reply)]


def _packet_file(path: Path) -> tuple[str | None, int]:
    """(stage, revision) of the first navigator line of a packet file, or (None, a large number) when it has none."""
    try:
        found = HEADER.search(path.read_text(errors="replace"))
    except OSError:
        found = None
    return (found.group("stage"), int(found.group("revision"))) if found else (None, 10 ** 9)


def packets(out: Path, run_dir: Path | None, tools) -> tuple[list[dict] | None, dict]:
    """(the ``packets`` block, the ``packets_unmeasured`` map): see the module docstring. ``tools`` is the ToolLog the run's events
    filled."""
    if run_dir is None:
        return None, {"packets": "the output folder holds no ShipLoop run directory, so there is no packets folder to read"}
    folder = Path(run_dir) / "packets"
    if not folder.is_dir():
        return None, {"packets": "the run directory has no packets folder"}
    files = {path.stem: path for path in folder.glob("*.md") if path.is_file()}
    printed: dict[str, int] = {}
    cut = 0
    for reply in tools.replies:
        if reply["packet"]:
            continue
        for text in heads(reply["text"]):
            head, _why = head_or_why(text)
            found = FULL_PACKET.search(head) if head else None
            stem = Path(found.group("path")).stem if found else None
            if head is None:
                cut += 1
            elif stem in files:
                printed.setdefault(stem, len(head.encode("utf-8")))
    rows = []
    for stem, path in files.items():
        stage, revision = _packet_file(path)
        rows.append((revision, stem, {"action": stem, "stage": stage, "file_bytes": path.stat().st_size,
                                      "head_bytes": printed.get(stem)}))
    block = [row for _revision, _stem, row in sorted(rows, key=lambda item: item[:2])]
    missing = sum(row["head_bytes"] is None for row in block)
    if not missing:
        return block, {}
    hosts = ", ".join(runrecord.hosts_used(out)) or "host not recorded"
    return block, {"head_bytes": f"{hosts}: {missing} of {len(block)} packets have no whole print in the recorded replies: "
                                 + HEAD_BYTES_WHY.format(cut=cut)}


# --- commits -------------------------------------------------------------------------------------------------------------

# The shape of an ID a Learned-from line may name. The gate refuses anything else (shiploop_git.resolve_commit); Git alone would also
# resolve a branch, HEAD or a revision expression, so the shape is checked before Git is asked. A test pins it to the gate's.
COMMIT_ID = re.compile(r"[0-9a-fA-F]{7,64}")
IMPROVE_COMMITTED = re.compile(r"Committed this review's changes as (?P<sha>[0-9a-f]{7,40})")
# ShipLoop's announcement of a work item's commit, in the two wordings saved runs hold: "declared changes" (through 1.26) and
# "changes (its declared paths and documentation)" (from release 1.27, when an item's documentation rode in its commit).
ITEM_COMMITTED = re.compile(
    r"ShipLoop committed \S+'s (?:declared changes|changes \(its declared paths and documentation\)) as (?P<sha>[0-9a-f]{7,40})")
KNOWLEDGE_SUBJECT = re.compile(r"^docs\(shiploop\): record \S+ knowledge (?:at|after) \S+$")
BASELINE_SUBJECT = "Empty baseline for the first ShipLoop run"
LEFTOVERS_SUBJECT = "chore(shiploop): commit files written after the last work item, before the return"
CHAIN_PREFIX = "ShipLoop chain prepared"
# The environment variables that point Git at another repository; a read of the run's repository drops them.
GIT_REDIRECTION = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                   "GIT_ALTERNATE_OBJECT_DIRECTORIES")


def _git(work: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if key not in GIT_REDIRECTION}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    return subprocess.run(["git", "-C", str(work), *args], input=stdin, capture_output=True, env=env, timeout=60, check=False)


def _commit_id(work: Path, name: str) -> str | None:
    """The full id of the commit ``name`` resolves to in the repository, or None."""
    done = _git(work, "rev-parse", "--verify", "--quiet", name + "^{commit}")
    return done.stdout.decode().strip() or None if done.returncode == 0 else None


def _cited_commit(work: Path, token: str) -> str | None:
    """The full id of the commit a ``Learned-from`` token names, or None: the token must be shaped like an ID and name a commit."""
    return _commit_id(work, token) if COMMIT_ID.fullmatch(token) else None


def _starting_point(out: Path, work: Path) -> tuple[str | None, str | None]:
    """(the head the run started from or None for a fresh run, why it cannot be known or None). A fresh run has no follow-on or seeded
    record, and its whole history is the run's; a follow-on or seeded run is counted after the head it recorded."""
    try:
        record = json.loads((Path(out) / "invocation.json").read_text())
    except (OSError, ValueError):
        record = None
    if not isinstance(record, dict):
        return None, "invocation.json cannot be read, so whether the run started from an earlier head is unknown"
    follow, seeded = record.get("follow_on"), record.get("seeded")
    if not follow and not seeded:
        return None, None
    head = (follow or {}).get("start_head") or (seeded or {}).get("start_head")
    if not isinstance(head, str) or not head:
        return None, "the follow-on or seeded record names no starting head, so which commits are the run's is unknown"
    found = _commit_id(work, head)
    if found is None:
        return None, f"the starting head {head[:12]} is not a commit in the work repository"
    return found, None


def _objects(work: Path, ids: list[str]) -> dict[str, dict]:
    """The author's name and the message of each commit, from the commit objects themselves (cat-file, so no log setting reaches the
    text)."""
    if not ids:
        return {}
    done = _git(work, "cat-file", "--batch", stdin=("\n".join(ids) + "\n").encode())
    data, found, position = done.stdout, {}, 0
    while position < len(data):
        end = data.index(b"\n", position)
        header = data[position:end].split()
        if len(header) != 3 or header[1] != b"commit":
            position = end + 1
            continue
        size = int(header[2])
        head, _blank, body = data[end + 1:end + 1 + size].partition(b"\n\n")
        author = next((line[len(b"author "):].rsplit(b" <", 1)[0] for line in head.split(b"\n") if line.startswith(b"author ")), b"")
        found[header[0].decode()] = {"author": author.decode("utf-8", "replace"), "message": body.decode("utf-8", "replace")}
        position = end + 1 + size + 1
    return found


def _item_prefixes(run_dir: Path | None) -> tuple[str, ...]:
    """The subject starts of the commits ShipLoop makes for the run's work items (``feat: <id> <title>``), from state.md's
    ``work_items``; empty when the run has no ledger. The integrate stage's reply names the commit too, but the model's pipe can
    cut that reply; the id is the run's own, so a model commit that starts ``feat:`` and names no work item is not matched."""
    items = metrics.engine_state(Path(run_dir) if run_dir else None).get("work_items")
    return tuple(f"feat: {item['id']} " for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)
                 and item["id"]) if isinstance(items, list) else ()


def history(out: Path, run_dir: Path | None, tools) -> tuple[dict | None, dict]:
    """(the run's commits, ``{}``) or (None, ``{"commits": why}``): ``{"work": the repository, "start": the head the run started from
    or None, "commits": [{id, kind, author, subject, message, knowledge}]}``. The one classification: ``commits`` counts these rows and
    nothing else reads the repository for the block. ``kind`` is improve, script or other; ``knowledge`` is true for the knowledge
    home's own commits (always ``script``)."""
    out = Path(out)
    work = out / "work"
    if not work.is_dir():
        return None, {"commits": "the run folder has no work directory"}
    if not (work / ".git").exists():
        return None, {"commits": "the work directory is not a Git repository"}
    start, why = _starting_point(out, work)
    if why:
        return None, {"commits": why}
    events = out / "events.jsonl"
    if not events.is_file() or not events.stat().st_size:
        return None, {"commits": "events.jsonl is missing or empty, and ShipLoop's own reply in it is what names an Improve commit"}
    listed = _git(work, "rev-list", "--all", *(["--not", start] if start else []))
    if listed.returncode:
        return None, {"commits": "git rev-list failed in the work repository: " + (listed.stderr.decode(errors="replace").strip()[:200] or "no message")}
    ids = listed.stdout.decode().split()
    objects = _objects(work, ids)
    named = {"improve": set(), "item": set()}
    for reply in tools.replies:
        named["improve"].update(found.group("sha") for found in IMPROVE_COMMITTED.finditer(reply["text"]))
        named["item"].update(found.group("sha") for found in ITEM_COMMITTED.finditer(reply["text"]))
    items = _item_prefixes(run_dir)
    rows = []
    for commit_id in ids:
        found = objects.get(commit_id, {"author": "", "message": ""})
        message = found["message"]
        subject = message.split("\n", 1)[0].strip()
        knowledge = bool(KNOWLEDGE_SUBJECT.match(subject))
        if any(commit_id.startswith(sha) for sha in named["improve"]):
            kind = "improve"
        elif (any(commit_id.startswith(sha) for sha in named["item"]) or knowledge
              or subject in (BASELINE_SUBJECT, LEFTOVERS_SUBJECT) or subject.startswith((CHAIN_PREFIX, *items))):
            kind = "script"
        else:
            kind = "other"
        rows.append({"id": commit_id, "kind": kind, "author": found["author"], "subject": subject, "message": message,
                     "knowledge": knowledge and kind == "script"})
    return {"work": work, "start": start, "commits": rows}, {}


def commits(out: Path, run_dir: Path | None, tools) -> tuple[dict | None, dict]:
    """(the ``commits`` block, the ``commits_unmeasured`` map): see the module docstring."""
    ran, why = history(out, run_dir, tools)
    if ran is None:
        return None, why
    work, start = ran["work"], ran["start"]
    block: dict = {"improve": {"n": 0, "with_lessons": 0, "cited": 0, "cited_earlier_run": 0},
                   "script": {"n": 0, "with_lessons": 0}, "other": {"n": 0, "with_lessons": 0},
                   "counted": len(ran["commits"]), "start_head": start}
    for commit in ran["commits"]:
        row = block[commit["kind"]]
        row["n"] += 1
        row["with_lessons"] += bool(commit_lessons.lessons(commit["message"]))
        if commit["kind"] == "improve":
            cited = [found for found in (_cited_commit(work, cite.token) for cite in commit_lessons.citations(commit["message"])) if found]
            row["cited"] += bool(cited)
            row["cited_earlier_run"] += bool(start and any(_git(work, "merge-base", "--is-ancestor", found, start).returncode == 0
                                                          for found in cited))
    return block, {}


def build(out: Path, run_dir: Path | None, tools) -> dict:
    """The four keys run.py adds to metrics.json: ``packets``, ``packets_unmeasured``, ``commits`` and ``commits_unmeasured``."""
    block, why = packets(out, run_dir, tools)
    cblock, cwhy = commits(out, run_dir, tools)
    return {"packets": block, "packets_unmeasured": why, "commits": cblock, "commits_unmeasured": cwhy}


def safe_build(out: Path, run_dir: Path | None, tools) -> dict:
    """``build``, failing open like fidelity.safe_build: a part that raises is null with the error as its reason, never a verdict."""
    try:
        return build(out, run_dir, tools)
    except Exception as exc:  # noqa: BLE001 - a record never takes the run's metrics down
        reason = "failed: " + type(exc).__name__ + ": " + " ".join(str(exc).split())[:200]
        return {"packets": None, "packets_unmeasured": {"packets": reason}, "commits": None, "commits_unmeasured": {"commits": reason}}
