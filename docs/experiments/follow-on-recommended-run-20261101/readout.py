"""Read the finished runs of round 6 (the recommended-run check) out of their folders.

Usage: python3 readout.py OUT_ROOT [--json]

Read-only, except that it runs `python3 -B slug.py Café` in each run's work folder (a command that writes nothing).  For every
`link1-*` and `link2-*` folder under OUT_ROOT it reports what the plan's rules read: the harness verdicts and turns, the handoff
refusals, the accepted `follow_on` list, whether the request file and the report section exist, and (link 2) whether the prompt
was the prior run's request file, the files the run changed against the prior run's head, which knowledge files name the
finding, and what the tool does for "Café".  It computes no rate and calls no model.  Written before any run was read.
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
FINDING = re.compile(r"non-?ascii|transliterat|accent|diacritic", re.I)


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


def cafe(work: Path) -> dict:
    """What `slug.py Café` does in the run's work folder."""
    if not (work / "slug.py").is_file():
        return {"behaviour": "no slug.py"}
    proc = subprocess.run([sys.executable, "-B", "slug.py", "Café"], cwd=work, capture_output=True, text=True, timeout=30)
    out, err = proc.stdout.strip(), proc.stderr.strip()
    if proc.returncode == 2 and "undecided: non-ASCII" in err:
        kind = "kept the reserved error"
    elif proc.returncode == 0 and out == "cafe":
        kind = "transliterated"
    elif proc.returncode == 0 and out:
        kind = "exit 0 with " + out
    else:
        kind = f"exit {proc.returncode}"
    return {"exit": proc.returncode, "stdout": out[:80], "stderr": err[:120], "behaviour": kind}


def mentions(work: Path) -> dict:
    """Lines naming the finding in the knowledge home of the run's checkout (docs/shiploop/*.md; KNOWLEDGE/*.md in a checkout that
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
    metrics = data.get("metrics") or {}
    row["turns"] = metrics.get("turns")
    row["span"] = data.get("span")
    row["follow_on_extract"] = extract.describe(folder)["runs"]
    work = folder / "work"
    row["work"] = str(work)
    if folder.name.startswith("link1"):
        row["files"] = git(work, "ls-files").split()
    start = (data.get("follow_on") or {}).get("start_head")
    if folder.name.startswith(("link2", "link3")):
        prior = Path((data.get("follow_on") or {}).get("prior", ""))
        request = next(iter(sorted(prior.glob(".shiploop-runs/*/run/follow-on-request.md"))), None)
        sent_file = folder / "prompt.txt"
        if request is not None and sent_file.is_file():
            # prompt.txt is the prompt the host was given (the harness adds a final newline; command substitution had removed
            # the request's).  The first version compared result.json's prompt_sha256, which the harness computes over a
            # different string (it names the planning-review mode), so it read False for a prompt that was the file.
            text = request.read_text(encoding="utf-8")
            sent = sent_file.read_text(encoding="utf-8")
            row["prompt_is_prior_request_file"] = sent.rstrip("\n") == text.rstrip("\n")
            if folder.name.startswith("link3"):
                answer = (HERE / "answer.txt").read_text(encoding="utf-8")
                row["prompt_is_request_plus_answer"] = sent.rstrip("\n") == (text + answer).rstrip("\n")
            row["prior_request_text"] = text
        row["start_head"] = start
        row["files_changed_vs_prior_head"] = git(work, "diff", "--name-only", f"{start}..HEAD").split() if start else None
    row["finding_mentions"] = mentions(work)
    row["cafe"] = cafe(work)
    return row


def show(row: dict) -> None:
    print("=" * 100)
    print(row["name"], "| pass", row["pass"], "| turns", row["turns"], "| gates", row["gates"])
    print("  span:", row["span"])
    for run in row["follow_on_extract"]:
        entries = run["follow_on"]
        print("  handoff attempts:", run["handoff_attempts"], "| status", run["status"], "| request file", run["request_file"],
              "| report section", run["report_has_section"])
        print("  follow_on:", "NOT RECORDED" if entries is None else f"{len(entries)} entries")
        for entry in entries or []:
            print("    -", entry.get("class"), "|", entry.get("source"), "|", entry.get("request_sentence") or "-")
            print("        statement:", " ".join(str(entry.get("statement", "")).split()))
            print("        needs:    ", " ".join(str(entry.get("needs", "")).split()))
    if "files" in row:
        print("  files in HEAD:", row["files"])
    if row["name"].startswith(("link2", "link3")):
        print("  prompt is the prior request file:", row.get("prompt_is_prior_request_file"),
              "| request plus the answer:", row.get("prompt_is_request_plus_answer", "n/a"))
        print("  files changed against the prior head:", row.get("files_changed_vs_prior_head"))
    print("  knowledge lines naming the finding:", row["finding_mentions"])
    print("  slug.py Café:", row["cafe"])


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv if not arg.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        return 2
    folders = sorted(path for path in paths[0].iterdir() if path.is_dir() and path.name.startswith(("link1", "link2")))
    rows = [describe(folder) for folder in folders]
    if "--json" in argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        return 0
    for row in rows:
        show(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
