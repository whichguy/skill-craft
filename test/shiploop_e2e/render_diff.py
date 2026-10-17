#!/usr/bin/env python3
"""What a change did to the packets, line by line: G-RENDER of the ShipLoop efficiency plan.  Stdlib only; no model.

    python3 test/shiploop_e2e/packets.py --offline CASE --text-dir OLD --run-dir-length 83 --cli-path-length 96   # before the edit
    python3 test/shiploop_e2e/packets.py --offline CASE --text-dir NEW --run-dir-length 83 --cli-path-length 96   # after it
    python3 test/shiploop_e2e/render_diff.py OLD NEW --unit U8 [--unit U9 ...] [--json]
    python3 test/shiploop_e2e/render_diff.py --emit-table DIR [--write]    # the head table values of one render

Both directories are packets.py --text-dir renders made with the same options (the manifest says which; a render made
with other options, or from a checkout whose packets differ in the lengths of the paths they print, is refused).  Per
stage it compares the printed text (what the host prints, a head when the packet passes the print limit) and the whole
text (the packet file).  A line that exists in one render and not the other, counted as a multiset, is an added or a
removed line, printed with its size in characters (line plus newline); a line that only moved is not a change, and
blank lines are not listed (they count in the sizes).  The exit code is 1 when any of these holds, 0 when none does:

  * an added line is not in the allowlist of a --unit (packet_changes.json: a line prefix, optionally the stages and
    routes it applies to, and one of
      "offset": prefixes of lines that this change removes from the same stage; the added lines of the entry may not
                be longer in all than the removed lines they name (a removed line pays for one entry only), or
      "approval": the decision that allows the growth, as the plan row, owner message or review that carries it);
  * a printed text is longer than the value for its stage in the head table (packet_head_table.json, by case, route,
    run-directory length and CLI path length; the values are the journaled per-stage head table: they change in the
    commit that journals the new value, U1 and U7 for the efficiency plan) or the table has no value for it
    (--no-head-table skips this check and says so).

Exit 2 is a refusal to compare (different render options, a malformed allowlist or table).  The allowlist has one key per
unit (U1 to U35, each an empty list until the unit adds entries), so units that change packet text edit different lines
of the file.  Domain-neutral: it knows lines, prefixes and sizes, no stage or platform.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHANGES = HERE / "packet_changes.json"
HEAD_TABLE = HERE / "packet_head_table.json"
MANIFEST = "manifest.json"
EXIT_OK, EXIT_FAIL, EXIT_REFUSED = 0, 1, 2
# The render settings that decide the text.  Two renders that differ in one cannot be compared line by line.
SETTINGS = ("text_format", "case", "delegation", "run_dir_length", "cli_path_length", "install_root_length", "python", "print_limit")
ENTRY_FIELDS = {"prefix", "stages", "routes", "offset", "approval", "note"}
MIN_PREFIX = 8  # a shorter prefix would allow a family of lines, not a line


class Refused(Exception):
    """The inputs cannot be compared (exit 2)."""


# --- renders -------------------------------------------------------------------------------------------------------

def stage_of(key: str) -> str:
    """`06-implement` -> `implement`: the packet's stage (and `-improve` for the Improve stage that follows it)."""
    return re.sub(r"^\d+-", "", key)


@dataclass
class Render:
    directory: Path
    manifest: dict
    packets: dict[str, dict] = field(default_factory=dict)  # stage key -> {"printed": text, "whole": text, "head": bool}

    @property
    def route(self) -> str:
        return self.manifest["delegation"]

    def table_key(self) -> str:
        m = self.manifest
        return f"{m['delegation']}/{m['run_dir_length']}/{m['cli_path_length'] if m['cli_path_length'] is not None else 'bare'}"


def load_render(directory: Path) -> Render:
    directory = Path(directory)
    try:
        manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"{directory} is not a packets.py --text-dir render ({MANIFEST}: {exc})") from exc
    render = Render(directory, manifest)
    seen: Counter = Counter()
    for row in manifest.get("packets", []):
        stage = stage_of(row["key"])
        seen[stage] += 1
        name = stage if seen[stage] == 1 else f"{stage}#{seen[stage]}"
        try:
            texts = {form: (directory / f"{row['key']}.{form}.txt").read_text(encoding="utf-8")
                     for form in ("printed", "whole")}
        except OSError as exc:
            raise Refused(f"{directory}: {exc}") from exc
        if len(texts["printed"]) != row["printed"] or len(texts["whole"]) != row["whole"]:
            raise Refused(f"{directory}/{row['key']}: the files and the manifest disagree on the sizes")
        render.packets[name] = {**texts, "head": bool(row.get("head"))}
    return render


def check_comparable(old: Render, new: Render) -> None:
    differing = [f"{name}: {old.manifest.get(name)!r} -> {new.manifest.get(name)!r}"
                 for name in SETTINGS if old.manifest.get(name) != new.manifest.get(name)]
    if differing:
        raise Refused("the renders were made with different options, so their lines cannot be compared: "
                      + "; ".join(differing) + " (render both with the same packets.py options)")


# --- lines ---------------------------------------------------------------------------------------------------------

def size(line: str) -> int:
    return len(line) + 1


def nonblank(text: str) -> list[str]:
    return [line.rstrip() for line in text.split("\n") if line.strip()]


def line_diff(old: str, new: str) -> tuple[list[str], list[str], int]:
    """(added lines, removed lines, moved lines): multiset differences in the order of the file they come from."""
    before, after = nonblank(old), nonblank(new)
    pool = Counter(before)
    added = []
    for line in after:
        if pool[line] > 0:
            pool[line] -= 1
        else:
            added.append(line)
    pool = Counter(after)
    removed = []
    for line in before:
        if pool[line] > 0:
            pool[line] -= 1
        else:
            removed.append(line)
    common = len(after) - len(added)
    in_order = sum(block.size for block in difflib.SequenceMatcher(None, before, after, autojunk=False).get_matching_blocks())
    return added, removed, max(0, common - in_order)


# --- the allowlist ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Entry:
    unit: str
    prefix: str
    stages: tuple[str, ...]
    routes: tuple[str, ...]
    offset: tuple[str, ...]
    approval: str | None

    def matches(self, line: str, stage: str, route: str) -> bool:
        return (line.lstrip().startswith(self.prefix) and any(fnmatch.fnmatchcase(stage, p) for p in self.stages)
                and any(fnmatch.fnmatchcase(route, p) for p in self.routes))

    def describe(self) -> str:
        return f"{self.unit} " + (f"approval: {self.approval}" if self.approval else "offset: " + " | ".join(self.offset))


def _strings(value, where: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(isinstance(v, str) and v for v in value):
        raise Refused(f"{where} must be a non-empty list of non-empty strings")
    return tuple(value)


def load_entries(path: Path, units: list[str]) -> list[Entry]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise Refused(f"{path} must be an object with one key per unit")
    entries: list[Entry] = []
    for unit in units:
        if unit not in data:
            raise Refused(f"{path} has no key {unit!r} (keys: {', '.join(k for k in data if not k.startswith('_'))})")
        rows = data[unit]
        if not isinstance(rows, list):
            raise Refused(f"{path}[{unit}] must be a list")
        for number, row in enumerate(rows, 1):
            where = f"{path.name}[{unit}][{number}]"
            if not isinstance(row, dict) or set(row) - ENTRY_FIELDS:
                raise Refused(f"{where} must be an object with fields from {sorted(ENTRY_FIELDS)}")
            prefix = row.get("prefix")
            if not isinstance(prefix, str) or len(prefix) < MIN_PREFIX:
                raise Refused(f"{where}: prefix must be a string of at least {MIN_PREFIX} characters (one line, not a family of lines)")
            offset, approval = row.get("offset"), row.get("approval")
            if (offset is None) == (approval is None):
                raise Refused(f"{where}: give exactly one of offset (removed-line prefixes) and approval (the decision)")
            if approval is not None and not (isinstance(approval, str) and approval.strip()):
                raise Refused(f"{where}: approval must name the decision that allows the growth")
            entries.append(Entry(unit, prefix, _strings(row.get("stages", ["*"]), where + ".stages"),
                                 _strings(row.get("routes", ["*"]), where + ".routes"),
                                 _strings(offset, where + ".offset") if offset is not None else (), approval))
    return entries


def load_table(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise Refused(f"{path} must be an object: case -> render key -> stage -> characters")
    return data


# --- judging one render pair -----------------------------------------------------------------------------------------

@dataclass
class Line:
    op: str  # "+" or "-"
    text: str
    count: int = 1
    forms: set = field(default_factory=set)  # "printed", "whole"
    verdict: str = ""  # added lines: the entry that allows it, or why not
    ok: bool = True

    @property
    def size(self) -> int:
        return size(self.text) * self.count


def judge_form(entries: list[Entry], stage: str, route: str, added: list[str], removed: list[str]) -> list[Line]:
    """Lines of one form of one stage: the removed lines as they are, the added lines with their verdicts."""
    gone = Counter(removed)
    out = [Line("-", text, count) for text, count in gone.items()]
    taken: set[str] = set()  # removed lines already named by an earlier entry: one removed line pays for one entry only
    groups: dict[int | None, Counter] = defaultdict(Counter)
    for text in added:
        groups[next((i for i, entry in enumerate(entries) if entry.matches(text, stage, route)), None)][text] += 1
    for index in sorted(groups, key=lambda i: -1 if i is None else i):
        texts = groups[index]
        if index is None:
            out += [Line("+", text, n, verdict="NOT ALLOWLISTED (no entry of the unit matches this line)", ok=False)
                    for text, n in texts.items()]
            continue
        entry = entries[index]
        problem = None
        if entry.offset:
            paid, missing = 0, []
            for prefix in entry.offset:
                hits = [text for text in gone if text not in taken and text.lstrip().startswith(prefix)]
                if not hits:
                    missing.append(prefix)
                taken.update(hits)
                paid += sum(size(text) * gone[text] for text in hits)
            used = sum(size(text) * n for text, n in texts.items())
            if missing:
                problem = "the offset names no unused removed line of this stage: " + " | ".join(missing)
            elif used > paid:
                problem = f"adds {used} characters but the removed lines it names pay {paid}"
        out += [Line("+", text, n, verdict=entry.describe() + (f": {problem}" if problem else ""), ok=problem is None)
                for text, n in texts.items()]
    return out


@dataclass
class StageResult:
    stage: str
    old: dict | None
    new: dict | None
    lines: list[Line] = field(default_factory=list)
    moved: dict = field(default_factory=dict)
    limit: int | None = None
    limit_note: str = ""
    ok: bool = True


def merge_forms(per_form: dict[str, list[Line]]) -> list[Line]:
    """One list over both forms: a line seen in both carries both tags; the form that fails keeps its verdict."""
    merged: dict[tuple[str, str], Line] = {}
    for form, lines in per_form.items():
        for line in lines:
            known = merged.get((line.op, line.text))
            if known is None:
                line.forms = {form}
                merged[(line.op, line.text)] = line
            else:
                known.forms.add(form)
                known.count = max(known.count, line.count)
                if not line.ok and known.ok:
                    known.verdict, known.ok = line.verdict, False
    return list(merged.values())


def compare(old: Render, new: Render, entries: list[Entry], table: dict | None) -> list[StageResult]:
    results: list[StageResult] = []
    stages = list(dict.fromkeys([*old.packets, *new.packets]))
    case, key = new.manifest["case"], new.table_key()
    for stage in stages:
        a, b = old.packets.get(stage), new.packets.get(stage)
        result = StageResult(stage, a, b)
        per_form: dict[str, list[Line]] = {}
        for form in ("printed", "whole"):
            added, removed, moved = line_diff(a[form] if a else "", b[form] if b else "")
            result.moved[form] = moved
            per_form[form] = judge_form(entries, stage, new.route, added, removed)
        result.lines = merge_forms(per_form)
        if any(not line.ok for line in result.lines):
            result.ok = False
        if b is not None and table is not None:
            limits = (table.get(case) or {}).get(key)
            if limits is None:
                result.limit_note, result.ok = f"no head table for {case} / {key}", False
            elif stage not in limits:
                result.limit_note, result.ok = f"no table value for {stage} ({case} / {key})", False
            else:
                result.limit = limits[stage]
                if len(b["printed"]) > result.limit:
                    result.limit_note, result.ok = f"printed {len(b['printed'])} passes the table value {result.limit}", False
        results.append(result)
    return results


# --- output ----------------------------------------------------------------------------------------------------------

def commit_of(render: Render) -> str:
    return ((render.manifest.get("source") or {}).get("commit") or "unknown")[:12]


def clip(text: str, width: int = 110) -> str:
    return text if len(text) <= width else text[:width - 1] + "…"


def render_text(old: Render, new: Render, results: list[StageResult], units: list[str], table_used: bool) -> str:
    m = new.manifest
    cut = m.get("host_cut", 20_000)
    where = f"{m['case']} / {new.table_key()}"
    lines = [f"# Render diff: {where}, unit {', '.join(units)}", "",
             f"- old {old.directory} (commit {commit_of(old)})", f"- new {new.directory} (commit {commit_of(new)})",
             f"- the head table is {'checked' if table_used else 'NOT checked (--no-head-table)'}", "",
             "| stage | printed old | printed new | Δ | table | to host cut | whole old | whole new | moved lines | result |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for r in results:
        po = len(r.old["printed"]) if r.old else None
        pn = len(r.new["printed"]) if r.new else None
        wo = len(r.old["whole"]) if r.old else None
        wn = len(r.new["whole"]) if r.new else None
        delta = "–" if po is None or pn is None else f"{pn - po:+d}"
        lines.append(f"| {r.stage} | {po if po is not None else '–'} | {pn if pn is not None else '–'} | {delta} "
                     f"| {r.limit if r.limit is not None else '–'} | {cut - pn if pn is not None else '–'} "
                     f"| {wo if wo is not None else '–'} | {wn if wn is not None else '–'} "
                     f"| {max(r.moved.values(), default=0)} | {'ok' if r.ok else 'FAIL'} |")
    lines.append("")
    for r in results:
        if r.old is None:
            lines.append(f"## {r.stage}: new packet")
        elif r.new is None:
            lines.append(f"## {r.stage}: packet no longer rendered")
        elif not r.lines and r.ok:
            continue
        else:
            lines.append(f"## {r.stage}")
        if r.limit_note:
            lines.append(f"  FAIL head table: {r.limit_note}")
        for line in sorted(r.lines, key=lambda l: (l.op != "-", l.text)):
            tags = "".join({"printed": "P", "whole": "W"}[f] for f in ("printed", "whole") if f in line.forms)
            note = f"   <- {line.verdict}" if line.op == "+" else ""
            times = f" x{line.count}" if line.count > 1 else ""
            lines.append(f"  {line.op} {line.size:>5}  [{tags}] {clip(line.text)}{times}{note}")
        lines.append("")
    failed = [r for r in results if not r.ok]
    lines.append(f"{len(failed)} of {len(results)} stages fail." if failed else f"All {len(results)} stages pass.")
    lines.append("P = printed text, W = whole text (the packet file); sizes are characters including the newline.")
    return "\n".join(lines) + "\n"


def render_json(old: Render, new: Render, results: list[StageResult], units: list[str], table_used: bool) -> str:
    return json.dumps({
        "case": new.manifest["case"], "route": new.route, "table_key": new.table_key(), "units": units,
        "old": str(old.directory), "new": str(new.directory), "head_table_checked": table_used,
        "stages": [{"stage": r.stage, "ok": r.ok, "printed_old": len(r.old["printed"]) if r.old else None,
                    "printed_new": len(r.new["printed"]) if r.new else None, "table": r.limit, "table_note": r.limit_note,
                    "moved_lines": r.moved,
                    "lines": [{"op": l.op, "size": l.size, "count": l.count, "forms": sorted(l.forms), "ok": l.ok,
                               "verdict": l.verdict, "text": l.text} for l in r.lines]} for r in results],
        "ok": all(r.ok for r in results)}, indent=2) + "\n"


# --- the head table --------------------------------------------------------------------------------------------------

def table_entry(render: Render) -> dict:
    return {render.manifest["case"]: {render.table_key(): {stage: len(p["printed"]) for stage, p in render.packets.items()}}}


def write_table(path: Path, entry: dict) -> None:
    data = load_table(path) if path.exists() else {}
    for case, keys in entry.items():
        data.setdefault(case, {}).update(keys)
    body = {k: data[k] for k in sorted(data) if k.startswith("_")} | {k: data[k] for k in sorted(data) if not k.startswith("_")}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


# --- main ------------------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?", type=Path, help="the earlier packets.py --text-dir render")
    ap.add_argument("new", nargs="?", type=Path, help="the later render")
    ap.add_argument("--unit", action="append", default=[], metavar="U", help="a unit whose allowlist entries apply (repeatable)")
    ap.add_argument("--changes", type=Path, default=CHANGES, help="the allowlist (default: packet_changes.json)")
    ap.add_argument("--head-table", type=Path, default=HEAD_TABLE, help="the per-stage head table (default: packet_head_table.json)")
    ap.add_argument("--no-head-table", action="store_true", help="do not check the printed sizes against the head table")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--emit-table", type=Path, metavar="DIR", help="print the head table values of one render (with --write: merge them into the table file)")
    ap.add_argument("--write", action="store_true", help="with --emit-table: write the values into the head table file")
    args = ap.parse_args(argv)
    try:
        if args.emit_table is not None:
            entry = table_entry(load_render(args.emit_table))
            if args.write:
                write_table(args.head_table, entry)
                print(f"wrote {sum(len(v) for keys in entry.values() for v in keys.values())} values into {args.head_table}")
            else:
                print(json.dumps(entry, indent=2))
            return EXIT_OK
        if args.old is None or args.new is None or not args.unit:
            ap.error("give OLD and NEW render directories and at least one --unit (or --emit-table DIR)")
        old, new = load_render(args.old), load_render(args.new)
        check_comparable(old, new)
        entries = load_entries(args.changes, args.unit)
        table = None if args.no_head_table else load_table(args.head_table)
        results = compare(old, new, entries, table)
    except Refused as exc:
        print(f"render_diff: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    out = (render_json if args.json else render_text)(old, new, results, args.unit, table is not None)
    print(out, end="")
    return EXIT_OK if all(r.ok for r in results) else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
