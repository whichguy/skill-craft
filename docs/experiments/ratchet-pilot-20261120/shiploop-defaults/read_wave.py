#!/usr/bin/env python3
"""Read the deliveries of one wave: what each recorded, printed, said and delivered about its defaults.

Usage: ``read_wave.py ROOT [--json FILE]``.  ROOT holds one output folder per delivery (``launch_wave.sh``).  For each
it gathers, from the delivery's own files and nothing else:

- the harness's verdict and each held-out check;
- the accepted spec result's ``defaults`` and summary, and the living specification's size and requirement count;
- for each row, whether the clause of the requirement it names says it is a default;
- whether the packet of the stage after the spec printed the block, and the rows it printed;
- every message the host wrote to the user after that packet, up to the end of the run, that names a default
  (the ``say`` lines of the harness's transcript);
- whether the last print of the run and the report carry the rows;
- how often the ``defaults`` gate refused, the spec stage's seconds, the run's seconds and output tokens;
- the stand-in requester's record, when there is one.

It prints one block of text per delivery and can write the same facts as JSON.  With ``--export DIR`` it also writes,
for each delivery, the two texts the reader of ``reader-brief.md`` is given and nothing else: ``DIR/<name>/spec.md``
(the living specification as the spec stage's commit left it, when that commit can be found, else as delivered) and
``DIR/<name>/rows.txt`` (the rows as the packet printed them).  It changes nothing in a delivery's folder.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))

import shiploop_defaults as defaults
import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as planning_revision
import shiploop_store as store

HEAD = "Defaults the spec recorded:"
ROW = re.compile(r"^\d+\. R-\d+ .+$")
SAY = re.compile(r"^say\s+(.*)$")
DEFAULT_WORD = re.compile(r"\bdefault", re.IGNORECASE)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def check_name(command: str) -> str:
    return command.split('"$E2E_CHECKS/')[-1].replace('"', "") if "E2E_CHECKS" in command else command[:40]


def packet_block(run_dir: Path, state: dict) -> dict:
    """The block as the packet of the stage after the spec printed it: present or not, and its printed rows."""
    actions = [row["action"] for row in state.get("history") or () if row.get("stage") == defaults.SHOWN_AT]
    current = state.get("action") or {}
    if state.get("stage") == defaults.SHOWN_AT and current.get("id"):
        actions.append(current["id"])
    found = {"packets": 0, "with_block": 0, "rows": []}
    for action in dict.fromkeys(actions):
        path = run_dir / "packets" / (action + ".md")
        if not path.is_file():
            continue
        found["packets"] += 1
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        start = next((index for index, line in enumerate(lines) if line.startswith(HEAD)), None)
        if start is None:
            continue
        found["with_block"] += 1
        rows = []
        for line in lines[start + 1:]:
            if not ROW.match(line):
                break
            rows.append(line)
        found["rows"] = rows
    return found


def read(out: Path) -> dict:
    result, metrics = load(out / "result.json"), load(out / "metrics.json")
    record: dict = {"name": out.name, "pass": result.get("pass"), "class": result.get("outcome_class"),
                    "checks": {check_name(str(row.get("command", ""))): row.get("pass")
                               for row in result.get("checks") or () if isinstance(row, dict)}}
    span = result.get("span") or {}
    if span.get("started") and span.get("ended"):
        record["seconds"] = round(span["ended"] - span["started"])
    record["output_tokens"] = (metrics.get("tokens") or {}).get("output")
    record["gate_counts"] = metrics.get("gate_counts")
    record["spec_seconds"] = [row.get("seconds") for row in metrics.get("stages") or () if row.get("stage") == "spec"]
    record["requester"] = load(out.with_name(out.name + "-requester.json")) or None
    run_dir = Path(str((result.get("shiploop") or {}).get("run_dir") or load(out / "shiploop-run.json").get("run_dir") or ""))
    if not (run_dir / "state.md").is_file():
        record["run"] = "no run directory"
        return record
    state = store.read_record(run_dir / "state.md")
    record["status"] = state.get("status")
    action = planning_revision.current_actions(state).get((None, "spec"))
    spec = (state.get("accepted") or {}).get(action) or {}
    record["spec_action"] = action
    record["spec_results"] = sum(1 for row in state.get("history") or () if row.get("stage") == "spec")
    record["defaults"] = spec.get("defaults") if "defaults" in spec else "not recorded"
    record["spec_summary"] = spec.get("summary")
    repo = Path(str(state.get("repo") or ""))
    living = repo / knowledge.HOME / "spec.md"
    if living.is_file():
        text = living.read_text(encoding="utf-8", errors="replace")
        entries = knowledge.entries(repo, "spec.md")
        record["spec_md"] = {"words": len(text.split()),
                             "requirements": sum(1 for entry in entries.values() if not entry.retired),
                             "default_words": len(DEFAULT_WORD.findall(text))}
        if isinstance(record["defaults"], list):
            record["clause_says_default"] = [
                bool(DEFAULT_WORD.search(entries[row["requirement"]].text)) if row.get("requirement") in entries else None
                for row in record["defaults"] if isinstance(row, dict)]
    record["block"] = packet_block(run_dir, state)
    says = [found.group(1) for found in map(SAY.match, (out / "transcript.md").read_text(encoding="utf-8", errors="replace").splitlines())
            if found] if (out / "transcript.md").is_file() else []
    record["says"] = len(says)
    record["says_naming_a_default"] = [text[:600] for text in says if DEFAULT_WORD.search(text)]
    report = run_dir / "report.html"
    if report.is_file():
        html_text = report.read_text(encoding="utf-8", errors="replace")
        heading = "<h2>" + defaults.HEADING + "</h2>"
        record["report"] = {"section": heading in html_text,
                            "after_request": ("<h2>Original request</h2>" in html_text and heading in html_text
                                              and html_text.index("<h2>Original request</h2>") < html_text.index(heading)
                                              < html_text.index("<h2>Accepted transitions</h2>")),
                            "rows": html_text.count("<tr><td>") if heading in html_text else 0,
                            "none": "none: the specification recorded no answer" in html_text,
                            "not_recorded": "not recorded: this run's spec result has no defaults list" in html_text}
    record["notes"] = sorted(path.name for path in (run_dir / "owner-notes").glob("N*.md")) if (run_dir / "owner-notes").is_dir() else []
    record["owner_notes_state"] = state.get("owner_notes")
    return record


def spec_as_accepted(repo: Path, run_dir: Path, action: str | None) -> tuple[str, str]:
    """(the living spec's text, where it was read): from the knowledge commit ShipLoop made when the spec stage was
    accepted, found by its subject, so a later stage's edit is not what the reader sees; else the file as delivered."""
    living = repo / knowledge.HOME / "spec.md"
    log = subprocess.run(["git", "-C", str(repo), "log", "--format=%H %s", "--", str(Path(knowledge.HOME) / "spec.md")],
                         capture_output=True, text=True, check=False).stdout.splitlines()
    commits = [line.split(" ", 1) for line in log if " " in line]
    if commits:
        first = commits[-1][0]   # the oldest commit that touched the file: the spec stage wrote it
        shown = subprocess.run(["git", "-C", str(repo), "show", first + ":" + str(Path(knowledge.HOME) / "spec.md")],
                               capture_output=True, text=True, check=False)
        if shown.returncode == 0 and shown.stdout.strip():
            return shown.stdout, "commit " + first + " (" + commits[-1][1][:80] + ")"
    return (living.read_text(encoding="utf-8", errors="replace") if living.is_file() else ""), "the delivered file"


def export(out: Path, record: dict, target: Path) -> None:
    """Write the reader's two texts for one delivery."""
    result = load(out / "result.json")
    run_dir = Path(str((result.get("shiploop") or {}).get("run_dir") or ""))
    if not (run_dir / "state.md").is_file():
        return
    state = store.read_record(run_dir / "state.md")
    text, where = spec_as_accepted(Path(str(state.get("repo") or "")), run_dir, record.get("spec_action"))
    folder = target / record["name"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "spec.md").write_text(text, encoding="utf-8")
    (folder / "rows.txt").write_text("\n".join((record.get("block") or {}).get("rows") or []) + "\n", encoding="utf-8")
    record["exported_spec_from"] = where


def show(record: dict) -> None:
    print("=" * 118)
    print(f"{record['name']}: pass {record.get('pass')} ({record.get('class')}); status {record.get('status')}; "
          f"{record.get('seconds')} s; spec stage {record.get('spec_seconds')} s; output tokens {record.get('output_tokens')}")
    print("  checks:", ", ".join(f"{name} {'P' if str(ok) == 'True' else 'F'}" for name, ok in (record.get("checks") or {}).items()))
    print("  gate counts:", json.dumps(record.get("gate_counts")))
    print(f"  spec results accepted: {record.get('spec_results')}; spec.md: {record.get('spec_md')}")
    rows = record.get("defaults")
    if isinstance(rows, list):
        print(f"  defaults: {len(rows)} rows; the named clause says default: {record.get('clause_says_default')}")
        for number, row in enumerate(rows, 1):
            for name in defaults.FIELDS:
                print(f"    {number}.{name}: {row.get(name)}")
    else:
        print("  defaults:", rows)
    print("  spec summary:", record.get("spec_summary"))
    block = record.get("block") or {}
    print(f"  stage-after-spec packets: {block.get('packets')}, with the block: {block.get('with_block')}, rows printed: {len(block.get('rows') or [])}")
    print(f"  host messages to the user: {record.get('says')}; naming a default: {len(record.get('says_naming_a_default') or [])}")
    for text in record.get("says_naming_a_default") or []:
        print("    say:", text)
    print("  report:", record.get("report"))
    requester = record.get("requester")
    if requester:
        print(f"  requester: reply enabled {requester.get('reply_enabled')}; block printed {requester.get('block_printed')}; "
              f"about the point {requester.get('about')}; note {(requester.get('note') or {}).get('id')}; ended {requester.get('ended')}")
    print(f"  owner notes in the run: {record.get('notes')}; delivered: {json.dumps(record.get('owner_notes_state'))[:300]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--export", type=Path, help="write each delivery's spec.md and rows.txt for the reader here")
    args = parser.parse_args()
    outs = [out for out in sorted(args.root.iterdir()) if out.is_dir() and (out / "result.json").is_file()]
    records = [read(out) for out in outs]
    for out, record in zip(outs, records):
        if args.export:
            export(out, record, args.export)
        show(record)
    if args.json:
        args.json.write_text(json.dumps(records, indent=1, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
