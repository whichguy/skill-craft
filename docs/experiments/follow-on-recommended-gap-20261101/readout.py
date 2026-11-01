"""Read the finished runs of round 7 (the recommended-gap check) out of their folders.

Usage: python3 readout.py OUT_ROOT [--json]

Read-only, except that it runs `python3 -B slug.py ...` in each run's work folder (commands that write nothing).  For every `link1-*`
and `link2-*` folder under OUT_ROOT it reports what the plan's rules read: the harness verdicts and turns, the handoff refusals, the
accepted `follow_on` list with each entry's request sentence, whether the request file and the report section exist, and (link 2)
whether the prompt was the prior run's request file (prompt.txt against the file, final newline ignored), the files the run changed
against the prior run's head, which knowledge files name the option, and what the tool does for the plan, the two examples and an
unknown option.  It computes no rate and calls no model.  Written, and run on a finished Round 6 folder and on an empty folder, before
any Round 7 run was read.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("extract_follow_on", HERE.parent / "follow-on-build-20261101" / "extract_follow_on.py")
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)

GATES = ("invoked", "plugin", "process", "shiploop", "committed", "checks")
FINDING = re.compile(r"max-length|max_length", re.I)
PROBES = (("plain", ["Hello, World"]), ("max 8", ["Hello, World", "--max-length", "8"]), ("max 6", ["Hello, World", "--max-length", "6"]),
          ("unknown option", ["Hello", "--bogus", "1"]))


def gate(value):
    """A verdict's pass flag: a bare flag, a mapping with a `pass` key, or (checks) a list of such mappings, all of which pass."""
    if isinstance(value, list):
        return bool(value) and all(gate(item) is True for item in value)
    if isinstance(value, dict):
        for key in ("pass", "passed", "ok"):
            if key in value:
                return value[key]
    return value


def git(work: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True).stdout


def behaviour(work: Path) -> dict:
    """What `slug.py` does in the run's work folder for the plain title, the request's two examples and an unknown option."""
    if not (work / "slug.py").is_file():
        return {"all": "no slug.py"}
    rows = {}
    for label, argv in PROBES:
        proc = subprocess.run([sys.executable, "-B", "slug.py", *argv], cwd=work, capture_output=True, text=True, timeout=30)
        rows[label] = {"exit": proc.returncode, "stdout": proc.stdout.strip()[:60], "stderr": proc.stderr.strip()[:80]}
    return rows


def mentions(work: Path) -> dict:
    """Lines naming the option in the knowledge home of the run's checkout (docs/shiploop/*.md; KNOWLEDGE/*.md in a checkout that
    uses that name), by file."""
    found = {}
    for folder in ("docs/shiploop", "KNOWLEDGE"):
        for path in sorted((work / folder).glob("*.md")) if (work / folder).is_dir() else []:
            count = sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if FINDING.search(line))
            found[f"{folder}/{path.name}"] = count
    return found


def describe(folder: Path) -> dict:
    row = {"folder": str(folder), "name": folder.name}
    result = folder / "result.json"
    data = json.loads(result.read_text(encoding="utf-8")) if result.is_file() else {}
    row["result_json"] = bool(data)
    row["pass"] = data.get("pass")
    row["gates"] = {name: gate(data.get(name)) for name in GATES}
    row["turns"] = (data.get("metrics") or {}).get("turns")
    row["span"] = data.get("span")
    row["plugin_sha256"] = (data.get("versions") or {}).get("plugin_sha256")
    row["follow_on_extract"] = extract.describe(folder)["runs"]
    work = folder / "work"
    row["work"] = str(work)
    if folder.name.startswith("link1"):
        row["files"] = git(work, "ls-files").split()
    start = (data.get("follow_on") or {}).get("start_head")
    if folder.name.startswith("link2"):
        prior = Path((data.get("follow_on") or {}).get("prior", ""))
        request = next(iter(sorted(prior.glob(".shiploop-runs/*/run/follow-on-request.md"))), None)
        sent_file = folder / "prompt.txt"
        if request is not None and sent_file.is_file():
            text = request.read_text(encoding="utf-8")
            row["prompt_is_prior_request_file"] = sent_file.read_text(encoding="utf-8").rstrip("\n") == text.rstrip("\n")
            row["prior_request_text"] = text
        row["start_head"] = start
        row["files_changed_vs_prior_head"] = git(work, "diff", "--name-only", f"{start}..HEAD").split() if start else None
    row["finding_mentions"] = mentions(work)
    row["behaviour"] = behaviour(work)
    return row


def show(row: dict) -> None:
    print("=" * 100)
    print(row["name"], "| pass", row["pass"], "| turns", row["turns"], "| plugin", str(row["plugin_sha256"])[:12], "| gates", row["gates"])
    print("  span:", row["span"])
    for run in row["follow_on_extract"]:
        entries = run["follow_on"]
        print("  handoff attempts:", run["handoff_attempts"], "| status", run["status"], "| request file", run["request_file"],
              "| report section", run["report_has_section"])
        print("  follow_on:", "NOT RECORDED" if entries is None else f"{len(entries)} entries")
        for entry in entries or []:
            print("    -", entry.get("class"), "|", entry.get("source"), "| request_sentence", entry.get("request_sentence") or "-")
            print("        statement:", " ".join(str(entry.get("statement", "")).split()))
            print("        needs:    ", " ".join(str(entry.get("needs", "")).split()))
    if "files" in row:
        print("  files in HEAD:", row["files"])
    if row["name"].startswith("link2"):
        print("  prompt is the prior request file:", row.get("prompt_is_prior_request_file"))
        print("  files changed against the prior head:", row.get("files_changed_vs_prior_head"))
    print("  knowledge lines naming the option:", row["finding_mentions"])
    for label, value in row["behaviour"].items():
        print(f"  slug.py [{label}]:", value)


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv if not arg.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        return 2
    folders = sorted(path for path in paths[0].iterdir() if path.is_dir() and path.name.startswith(("link1", "link2")))
    if not folders:
        print(f"no link1-* or link2-* folder under {paths[0]}", file=sys.stderr)
        return 1
    rows = [describe(folder) for folder in folders]
    if "--json" in argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        return 0
    for row in rows:
        show(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
