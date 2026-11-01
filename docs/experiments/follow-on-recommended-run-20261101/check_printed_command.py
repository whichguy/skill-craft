"""Run the start command a finished ShipLoop run printed, on a copy of its checkout (round 6 of the follow-on journal, R3).

Usage: python3 check_printed_command.py OUTPUT_DIR --cli PATH_TO_SHIPLOOP_CLI [--scratch DIR] [--self-test]

Finds the line `python3 <cli> workspace start --repo <repo> --prompt="$(cat <file>)"` in the run's done packets and in its
report, runs it through a shell as printed, except that `--repo` names a copy of the run's checkout (the finished run is not
changed) and the CLI is the one named by --cli (the tree under test), and checks what the design asks of it (section 4.6):
exit 0, a workspace record, the stored request equal to the request file's text without its last newline (what command
substitution does), and nothing the model wrote executed by the shell.  No model is called.  Calibrated by hand on an
adversarial request (backticks, $(...), quotes, a semicolon, a newline, é) before the live runs: exit 0, the marker file of
the injected `$(touch ...)` absent, the stored prompt equal to the file text but for one trailing newline.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LINE = re.compile(r"""^python3 (?P<cli>'[^']*'|\S+) workspace start --repo (?P<repo>'[^']*'|\S+) (?P<rest>--prompt="\$\(cat (?P<file>'[^']*'|\S+)\)")$""")


def read_state(path: Path) -> dict:
    match = re.search(r"```[a-z-]*\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)
    return json.loads(match.group(1)) if match else {}


def printed_lines(run: Path) -> dict[str, list[str]]:
    """Where the command was printed: the done packets of the run and its report (every match, unescaped)."""
    found: dict[str, list[str]] = {"packets": [], "report": []}
    for packet in sorted((run / "packets").glob("*.md")):
        for line in packet.read_text(encoding="utf-8", errors="replace").splitlines():
            if LINE.match(line.strip()):
                found["packets"].append(line.strip())
    for report in run.glob("report.html"):
        text = report.read_text(encoding="utf-8", errors="replace")
        for block in re.findall(r"<pre>(.*?)</pre>", text, re.DOTALL):
            line = html.unescape(block).strip()
            if "workspace start" in line:
                found["report"].append(line)
    return found


def check(output: Path, cli: str, scratch: Path) -> dict:
    runs = sorted(path.parent for path in output.glob(".shiploop-runs/*/run/state.md"))
    if not runs:
        return {"output": str(output), "verdict": "no run folder"}
    run = runs[0]
    request = run / "follow-on-request.md"
    where = printed_lines(run)
    result = {"output": str(output), "request_file": request.is_file(), "printed_in": {k: len(v) for k, v in where.items()}}
    if not where["packets"]:
        result["verdict"] = "no start command was printed in a packet" + ("" if request.is_file() else " (and no request file: the run recommended nothing)")
        return result
    printed = where["packets"][-1]
    match = LINE.match(printed)
    result["printed"] = printed
    copy = scratch / output.name / "work"
    if copy.parent.exists():
        shutil.rmtree(copy.parent)
    shutil.copytree(output / "work", copy, symlinks=True)
    command = f"python3 -I {shlex.quote(cli)} workspace start --repo {shlex.quote(str(copy))} {match.group('rest')}"
    proc = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(scratch))
    result["exit"] = proc.returncode
    result["traceback"] = "Traceback" in proc.stderr
    started = sorted(glob.glob(str(copy.parent / ".shiploop-runs" / "*" / "run" / "state.md")))
    result["workspace_records"] = len(glob.glob(str(copy.parent / ".shiploop-runs" / "*" / "workspace.md")))
    if started:
        stored = read_state(Path(started[0])).get("prompt")
        text = request.read_text(encoding="utf-8")
        result["stored_equals_file_but_last_newline"] = stored == (text[:-1] if text.endswith("\n") else text)
        result["stored_equals_file_exactly"] = stored == text
    ok = (proc.returncode == 0 and not result["traceback"] and result["workspace_records"] == 1
          and result.get("stored_equals_file_but_last_newline") is True)
    result["verdict"] = "works as printed" if ok else "DEFECT: read the fields above and stderr"
    if not ok:
        result["stderr_head"] = proc.stderr[:600]
    return result


def self_test() -> None:
    line = ("python3 /a b/shiploop workspace start --repo /r --prompt=\"$(cat /x/follow-on-request.md)\"")
    assert LINE.match("python3 '/a b/shiploop' workspace start --repo '/r s' --prompt=\"$(cat '/x y/follow-on-request.md')\"")
    assert LINE.match("python3 /p/shiploop workspace start --repo /r --prompt=\"$(cat /x/follow-on-request.md)\"")
    assert not LINE.match(line)
    print("self-test ok")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--cli", help="the ShipLoop CLI of the tree under test")
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.output is None or not args.cli:
        parser.error("OUTPUT_DIR and --cli are required")
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="printed-command-"))
    scratch.mkdir(parents=True, exist_ok=True)
    print(json.dumps(check(args.output.expanduser().resolve(), args.cli, scratch), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
