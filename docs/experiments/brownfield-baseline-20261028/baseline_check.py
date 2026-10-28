#!/usr/bin/env python3
"""The script checks a brownfield baseline needs (experiment X4, 2026-10-28): a prototype of what ShipLoop would run.

    python3 baseline_check.py sources REPO [--json]                         # C1 at the baseline close
    python3 baseline_check.py basis REPO --since REF --request FILE [--json] # C2 at any later stage that edits KNOWLEDGE
    python3 baseline_check.py stale REPO [--json]                           # C3 at a later run's start (a notice)

C1 sources (locator validation only; whether a source supports its claim is a review's question): both files exist,
every R-<n> of docs/shiploop/spec.md has a `Status:` and a `Source:` line whose classes are known, every AD-<n> of
architecture.md a status in parentheses and an `Evidence:`, no ID starts twice, and every locator resolves: its path
exists in REPO, its quoted symbol, test name or heading occurs in that file, and a `path:line` names a line it has.
C2 basis (traceability only: a script cannot tell whether S<k> really asks for the change): every entry that REF holds
and that the working tree changes, retires or supersedes carries a basis.  An obligation (an R-<n> that is `accepted`
or `documented`, an AD-<n> that is `accepted` or links a decision record) needs `Basis: S<k>`, k in 1..N of the
request.  A default (observed behaviour, an inferred decision, an earlier run's design choice) takes `Basis: S<k>` or
`Basis: assumption <id>` naming a recorded assumption.  An evidence correction that leaves behaviour as it was takes
`Corrected: <locator>`.  Refreshing `As of` alone is no change.
C3 stale (a notice; only `fresh` may let a later run skip): each entry is `fresh`, `stale` (a cited file changed,
was deleted or has uncommitted edits since its evidence commit) or `unknown` (no usable evidence commit, or Git
failed).  The evidence commit is the entry's own `As of`, else the commit before the one that wrote the entry.

Round 2 (2026-10-28) follows Astra's max review, whose probes reproduced: an accepted entry changed freely, `S0` and a
bare `assumption` passed, an `As of` refresh was refused, deleted sources and invalid revisions looked fresh, and a
global coverage date made untouched decisions look fresh.

Reuses ShipLoop's parsers: shiploop_knowledge_home._entries (entry spans and the retired flag) and shiploop_request
(sentences S1..Sn, the rendered index and the S<n> citation syntax).  Generic: no stack, language or tool is named.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_request as request_index  # noqa: E402

HOME = knowledge.HOME
FILES = {"R": "spec.md", "AD": knowledge.ARCHITECTURE}
# A quoted span: `code`, "straight" or “curly” quotes.  A bare path:line also counts (docs are cited that way).
SPAN = re.compile(r"`([^`\n]+)`|\"([^\"\n]+)\"|“([^”\n]+)”|(?<![\w/.`-])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]{1,8}:\d+)")
LINE_REF = re.compile(r"^(.+?):(\d+)(?:-(\d+))?$")
AS_OF = re.compile(r"As of:?\s*`?([0-9a-f]{7,40})`?")
BASIS = re.compile(r"Basis:\s*([^\n]*)")
ASSUMPTION = re.compile(r"\bassumption\s+([A-Za-z]+-?\d+)\b", re.I)
CLASSES = ("documented", "tested", "observed", "inferred", "conflict", "runtime")
ENTRY_START = knowledge._ENTRY_START


class Locator(NamedTuple):
    path: str
    detail: Optional[str]     # the quoted symbol, test name or heading, or "line N"
    ok: bool
    why: str = ""


class Finding(NamedTuple):
    ident: str
    problem: str


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def _is_path_like(token: str) -> bool:
    """A token that names a repository path: no spaces, a separator or a file extension, no placeholder."""
    if any(ch in token for ch in " <>*?=|{}$") or token.startswith(("/", "http", "-")):
        return False
    return "/" in token or bool(re.fullmatch(r"[\w.-]+\.[A-Za-z0-9]{1,8}", token))


def _occurs(detail: str, text: str) -> bool:
    """Whether a quoted symbol, test name or heading occurs in a file's text: the whole of it, or for a dotted
    `Class.method` / `Class#method` / `Class::method` symbol, each part."""
    if detail in text or " ".join(detail.split()) in " ".join(text.split()):
        return True
    parts = [part for part in re.split(r"[.#:]+|\(\)", detail) if part]
    return len(parts) > 1 and all(re.search(r"\b" + re.escape(part) + r"\b", text) for part in parts)


def locators(repo: Path, text: str) -> List[Locator]:
    """Every locator in an entry's text, resolved against REPO's working tree.

    A path-like span opens a locator; a quoted span right after it (only spaces or a comma between) is that path's
    symbol, test name or heading.  Other code spans (a value, a route, an option) are not locators.
    """
    found: List[Locator] = []
    current: Optional[str] = None
    last_end = -1
    for match in SPAN.finditer(text):
        token = next(group for group in match.groups() if group is not None).strip()
        gap = text[last_end:match.start()] if last_end >= 0 else ""
        adjacent = current is not None and re.fullmatch(r"[\s,]*", gap) is not None
        line_ref = LINE_REF.match(token)
        bare = line_ref.group(1) if line_ref and _is_path_like(line_ref.group(1)) else token
        if _is_path_like(bare) and (repo / bare).exists():
            current, last_end = bare, match.end()
            if line_ref and bare != token:
                lines = (repo / bare).read_text(errors="replace").count("\n") + 1 if (repo / bare).is_file() else 0
                first = int(line_ref.group(2))
                found.append(Locator(bare, "line " + line_ref.group(2), 0 < first <= lines,
                                     "" if 0 < first <= lines else f"{bare} has {lines} lines"))
            else:
                found.append(Locator(bare, None, True))
            continue
        # A missing path is reported only when it can only be a path: it has a separator and names a file.  A dotted
        # name without one (`Channel.notify`) is a symbol, and `tests/` in prose names a kind of folder, not a locator
        # (round 2: both were false findings on the healthchecks baseline).
        if _is_path_like(bare) and "/" in bare and not bare.endswith("/") and not adjacent:
            found.append(Locator(bare, None, False, "no such path"))
            current, last_end = None, match.end()
            continue
        if adjacent and current is not None and (repo / current).is_file():
            body = (repo / current).read_text(errors="replace")
            ok = _occurs(token, body)
            found[-1] = Locator(current, token, ok, "" if ok else f"{token!r} not in {current}")
            last_end = match.end()
            current = None
            continue
        current, last_end = None, match.end()
    return found


def _text(repo: Path, name: str, ref: Optional[str] = None) -> str:
    if ref is None:
        path = repo / HOME / name
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    shown = git(repo, "show", f"{ref}:{HOME}/{name}")
    return shown.stdout if shown.returncode == 0 else ""


def obligation(prefix: str, entry: knowledge.Entry) -> bool:
    """An entry whose change needs the request itself: an accepted or documented requirement, an accepted decision or
    one that links a decision record.  Everything else (observed behaviour, an inferred decision) is a default."""
    first = entry.text.splitlines()[0] if entry.text else ""
    if prefix == "R":
        source = re.search(r"Source:(.*?)(?:·|$)", entry.text, re.M)
        return bool(re.search(r"Status:\s*accepted\b", entry.text) or (source and "documented" in source.group(1)))
    return bool(re.search(r"\(accepted|\brecord(ed)?\b", first, re.I))


def request_sentences(text: str) -> int:
    """N for S1..SN: the rendered RUN/request.md's own index when given that file, else the request split as ShipLoop
    splits it (passing the rendered file to ``sentences`` would count its index lines as sentences)."""
    indexed = request_index.index(text)
    return len(indexed) if indexed else len(request_index.sentences(text))


def _starts(text: str, prefix: str) -> Dict[str, int]:
    """How many lines outside fenced code start an entry of each ID (two starts shadow one entry)."""
    lines = text.splitlines()
    fenced = knowledge._fenced(lines)
    counts: Dict[str, int] = {}
    for line, inside in zip(lines, fenced):
        match = ENTRY_START.match(line)
        if match and not inside and match.group(1).startswith(prefix + "-"):
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return counts


def sources(repo: Path) -> dict:
    """C1: the provenance and locator check of every entry."""
    findings: List[Finding] = []
    stats = {"entries": 0, "locators": 0, "resolved": 0, "with_locator": 0}
    for prefix, name in FILES.items():
        text = _text(repo, name)
        if not text.strip():
            findings.append(Finding(name, "missing or empty"))
            continue
        findings += [Finding(ident, f"starts {count} times: only the first is read as the entry")
                     for ident, count in _starts(text, prefix).items() if count > 1]
        for ident, entry in knowledge._entries(text, prefix).items():
            stats["entries"] += 1
            first = entry.text.splitlines()[0]
            if prefix == "R":
                if "Status:" not in entry.text:
                    findings.append(Finding(ident, "no Status line"))
                source = re.search(r"Source:(.*?)(?:·|$)", entry.text, re.M)
                if not source:
                    findings.append(Finding(ident, "no Source line"))
                else:
                    named = [part.strip().split(" ")[0] for part in source.group(1).split(";") if part.strip()]
                    findings += [Finding(ident, f"unknown source class {word!r}") for word in named if word not in CLASSES]
            else:
                if not re.search(r"\((inherited|accepted)[^)]*\)", first):
                    findings.append(Finding(ident, "no (inherited) or (accepted) status"))
                if "Evidence:" not in entry.text and "stated:" not in entry.text:
                    findings.append(Finding(ident, "no Evidence"))
            found = locators(repo, entry.text)
            stats["locators"] += len(found)
            stats["resolved"] += sum(loc.ok for loc in found)
            stats["with_locator"] += any(loc.ok for loc in found)
            if not any(loc.ok for loc in found):
                findings.append(Finding(ident, "no locator that resolves"))
            findings += [Finding(ident, "locator: " + loc.why) for loc in found if not loc.ok]
    return {"check": "sources", "stats": stats, "findings": [f._asdict() for f in findings]}


def _normal(text: str) -> str:
    """An entry's text for comparison: whitespace folded, its evidence commit (As of) left out."""
    return " ".join(AS_OF.sub("As of", text).split())


def basis(repo: Path, since: str, request_text: str, assumptions: Optional[set] = None) -> dict:
    """C2: every entry ``since`` holds that the working tree changes, retires or supersedes carries a basis."""
    count = request_sentences(request_text)
    recorded = set(assumptions or ())
    findings: List[Finding] = []
    changed_ok: List[str] = []
    for prefix, name in FILES.items():
        before = knowledge._entries(_text(repo, name, since), prefix)
        after = knowledge._entries(_text(repo, name), prefix)
        for ident, old in before.items():
            if old.retired:
                continue
            new = after.get(ident)
            if new is None:
                findings.append(Finding(ident, "dropped: keep it, or move it under Retired/Superseded with its Basis"))
                continue
            if _normal(old.text) == _normal(new.text) and old.retired == new.retired:
                continue
            stated = BASIS.search(new.text)
            cited = request_index.cited(stated.group(1)) if stated else set()
            by_request = bool(cited) and min(cited) >= 1 and max(cited) <= count
            assumed = ASSUMPTION.search(stated.group(1)) if stated else None
            by_assumption = bool(assumed) and assumed.group(1) in recorded
            corrected = "Corrected:" in new.text and not new.retired
            binding = obligation(prefix, old)
            if by_request or corrected or (by_assumption and not binding):
                changed_ok.append(ident)
                continue
            what = "superseded" if prefix == "AD" and new.retired else "retired" if new.retired else "changed"
            kind = "an obligation" if binding else "a default"
            allowed = (f"'Basis: S<k>' naming the request sentence (S1..S{count}) that asks for it" if binding else
                       f"'Basis: S<k>' (S1..S{count}) or 'Basis: assumption <id>' naming a recorded assumption")
            findings.append(Finding(ident, f"{kind} {what} without a basis: keep it as found, add {allowed}, or, when "
                                           "behaviour is unchanged, 'Corrected: <locator>'"))
    return {"check": "basis", "since": since, "request_sentences": count, "changed_with_basis": changed_ok,
            "findings": [f._asdict() for f in findings]}


def _evidence_commit(repo: Path, name: str, entry: knowledge.Entry) -> Optional[str]:
    """The entry's own As of; else the commit before the one that wrote its first line; HEAD while it is uncommitted."""
    own = AS_OF.search(entry.text)
    if own:
        return own.group(1)
    first = entry.text.splitlines()[0]
    wrote = git(repo, "log", "-1", "--format=%H", "-S", first, "--", f"{HOME}/{name}")
    if wrote.returncode:
        return None
    if not wrote.stdout.strip():
        return "HEAD"
    parent = git(repo, "rev-parse", "--verify", "-q", wrote.stdout.strip() + "^")
    return parent.stdout.strip() if parent.returncode == 0 else None


def stale(repo: Path) -> dict:
    """C3: each entry fresh, stale or unknown against its evidence commit (a notice; only fresh may skip work)."""
    rows = []
    for prefix, name in FILES.items():
        for ident, entry in knowledge._entries(_text(repo, name), prefix).items():
            paths = sorted({loc.path for loc in locators(repo, entry.text)})
            commit = _evidence_commit(repo, name, entry)
            row = {"id": ident, "as_of": commit, "paths": paths, "state": "fresh", "reasons": []}
            if not paths:
                row.update(state="unknown", reasons=["no locator"])
            elif commit is None or git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode:
                row.update(state="unknown", reasons=[f"no usable evidence commit ({commit})"])
            else:
                logged = git(repo, "log", "--format=%h", f"{commit}..HEAD", "--", *paths)
                dirty = git(repo, "status", "--porcelain", "--", *paths)
                if logged.returncode or dirty.returncode:
                    row.update(state="unknown", reasons=["git failed"])
                else:
                    missing = [path for path in paths if not (repo / path).exists()]
                    reasons = ([f"changed in {', '.join(logged.stdout.split())}"] if logged.stdout.split() else []) \
                        + (["uncommitted edits"] if dirty.stdout.strip() else []) \
                        + ([f"missing: {', '.join(missing)}"] if missing else [])
                    if reasons:
                        row.update(state="stale", reasons=reasons)
            rows.append(row)
    return {"check": "stale", "entries": rows, "stale": [row for row in rows if row["state"] == "stale"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("check", choices=("sources", "basis", "stale"))
    parser.add_argument("repo", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--assumption", action="append", default=[], help="a recorded assumption ID (repeatable)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.check == "sources":
        report = sources(repo)
    elif args.check == "basis":
        if not (args.since and args.request):
            parser.error("basis needs --since and --request")
        report = basis(repo, args.since, args.request.read_text(), set(args.assumption))
    else:
        report = stale(repo)
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        for key, value in report.items():
            if key != "findings":
                print(f"{key}: {value}")
        for finding in report.get("findings", []):
            print(f"- {finding['ident']}: {finding['problem']}")
    return 1 if report.get("findings") else 0


if __name__ == "__main__":
    sys.exit(main())
