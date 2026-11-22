#!/usr/bin/env python3
"""How well does a delivery's own test suite protect the delivery's own change? Seeded faults on the lines a delivery
changed, run against that delivery's tests. No model is called.

    python3 mutate.py LABEL TREE FIXTURE OUT.json [--sample N] [--manifest] [--unchanged] [--workers N]

TREE is a delivered product (a Git work folder); FIXTURE is the folder it started from. The faults are the E2E
harness's own catalog (test/shiploop_e2e/quality.py, `sites`: flipped comparisons, moved bounds, flipped logic and
booleans, flipped arithmetic), placed only on lines of product source that TREE added or changed against FIXTURE,
taken in the harness's round-robin order across files, the first N of them (default 60).

For each fault the script copies TREE (with its history: some tests read the base commit), applies the one edit,
checks that the file still parses, and runs

  own         `npm test`: the tests the delivery itself ships under test/
  acceptance  with --manifest, every command of ratchet/acceptance.json in order, stopping at the first that fails

With --unchanged the faults go the other way round: only on lines of product source that TREE left as FIXTURE has
them, in the files TREE changed. That reads how well the suites protect the existing code a change touches.

A command counts as failing when it fails twice in a row. A fault is caught by a suite when a command of that suite
fails on it that passes on the untouched copy; a command that already fails on the untouched copy is left out and
listed with the end of its output, and a suite with no command left is "not measured", never 0 caught. A fault whose
file no longer parses is invalid and not counted; a run that does not end is counted apart.
"""
import concurrent.futures
import difflib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import quality  # the harness's fault catalog

SECONDS = 300
NOT_MEASURED = "not measured"
NOT_PRODUCT = ["acceptance", "ratchet", "docs", "scripts", "testdata", ".shiploop-improve"]


LIVE = set()  # process groups this script started and has not yet reaped
STOPPING = threading.Event()


def stop_children(signum, _frame):
    """Asked to stop: start nothing more, take every command still running with us, and leave at once. Each command
    runs in a session of its own, so it would otherwise outlive this script; a seeded fault that makes a test spin
    then spins until someone finds it. The worker threads are not waited for: they would start the next command."""
    STOPPING.set()
    for _ in range(3):
        for group in list(LIVE):
            try:
                os.killpg(group, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        time.sleep(0.2)
    os._exit(128 + signum)


def run(command, folder, temp):
    """One shell command in `folder`: its exit code, or None when it did not end."""
    env = {key: value for key, value in os.environ.items() if key != "PORT"}
    env["TMPDIR"] = str(temp)
    if STOPPING.is_set():
        return None
    proc = subprocess.Popen(command, shell=True, cwd=str(folder), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    LIVE.add(proc.pid)
    try:
        proc.wait(timeout=SECONDS)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        code = None
    try:
        os.killpg(proc.pid, signal.SIGKILL)  # this command's own group, and anything it left running there
    except (ProcessLookupError, PermissionError):
        pass
    if code is None:
        proc.wait()
    LIVE.discard(proc.pid)
    return code


def fails(command, folder, temp):
    """True when the command fails twice in a row, False when it passes, None when it did not end."""
    first = run(command, folder, temp)
    if first == 0:
        return False
    second = run(command, folder, temp)
    if second == 0:
        return False
    return None if first is None or second is None else True


def output_tail(command, folder, temp):
    """The end of one more run's output, kept as the reason a command was left out."""
    env = {key: value for key, value in os.environ.items() if key != "PORT"}
    env["TMPDIR"] = str(temp)
    try:
        done = subprocess.run(command, shell=True, cwd=str(folder), env=env, capture_output=True, text=True, errors="replace",
                              stdin=subprocess.DEVNULL, timeout=SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return f"did not end in {SECONDS} s"
    return f"exit {done.returncode}\n" + (done.stdout + done.stderr)[-3000:]


def changed_lines(tree, fixture, name):
    """1-based numbers of the lines of TREE's file that FIXTURE does not have in that place."""
    new = (Path(tree) / name).read_text(errors="replace").splitlines()
    base = Path(fixture) / name
    if not base.is_file():
        return set(range(1, len(new) + 1))
    old = base.read_text(errors="replace").splitlines()
    lines = set()
    for tag, _, _, start, end in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            lines.update(range(start + 1, end + 1))
    return lines


def copy_tree(tree, scratch, label):
    folder = Path(tempfile.mkdtemp(prefix=f"mutate-{label}-", dir=scratch))
    shutil.rmtree(folder)
    shutil.copytree(tree, folder, symlinks=True, ignore=shutil.ignore_patterns("node_modules"))
    return folder


def suites(folder, manifest):
    found = {"own": ["npm test"]}
    if manifest:
        entries = json.loads((folder / "ratchet" / "acceptance.json").read_text())
        found["acceptance"] = [entry["command"] for entry in entries.values()]
    return found


def one(tree, scratch, number, name, site, manifest, skip):
    folder = copy_tree(tree, scratch, str(number))
    temp = Path(tempfile.mkdtemp(prefix=f"tmp-{number}-", dir=scratch))
    row = {"file": name, "line": site["line"], "op": site["op"], "old": site["old"], "new": site["new"]}
    try:
        path = folder / name
        text = path.read_bytes().decode("utf-8", "surrogateescape")
        path.write_bytes((text[:site["start"]] + site["new"] + text[site["end"]:]).encode("utf-8", "surrogateescape"))
        if run(f"node --check {json.dumps(name)}", folder, temp) != 0:
            return dict(row, invalid=True)
        for suite, commands in suites(folder, manifest).items():
            usable = [command for command in commands if command not in skip]
            if not usable:
                row[suite] = NOT_MEASURED  # every command of this suite fails on the untouched copy
                continue
            verdict = False
            for command in usable:
                result = fails(command, folder, temp)
                if result is None:
                    verdict = None
                    break
                if result:
                    verdict = True
                    break
            row[suite] = verdict
        return row
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    manifest = "--manifest" in argv
    unchanged = "--unchanged" in argv
    sample = 60
    if "--sample" in argv:
        sample = int(argv[argv.index("--sample") + 1])
        del argv[argv.index("--sample"):argv.index("--sample") + 2]
    workers = 4
    if "--workers" in argv:
        workers = int(argv[argv.index("--workers") + 1])
        del argv[argv.index("--workers"):argv.index("--workers") + 2]
    argv = [arg for arg in argv if arg not in ("--manifest", "--unchanged")]
    if len(argv) != 4:
        raise SystemExit(__doc__)
    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    label, tree, fixture, out = argv[0], Path(argv[1]).resolve(), Path(argv[2]).resolve(), Path(argv[3])
    scratch = Path(tempfile.mkdtemp(prefix="ratchet-mutate-"))
    # the untouched copy: which commands fail there and so decide nothing
    clean = copy_tree(tree, scratch, "clean")
    temp = Path(tempfile.mkdtemp(prefix="tmp-clean-", dir=scratch))
    skip = sorted(command for commands in suites(clean, manifest).values() for command in commands if fails(command, clean, temp) is not False)
    reasons = {command: output_tail(command, clean, temp) for command in skip}
    targets = quality.targets(clean, NOT_PRODUCT)
    per_file = {}
    for name in sorted(targets):
        lines = changed_lines(clean, fixture, name)
        if not lines:
            continue
        text = (clean / name).read_bytes().decode("utf-8", "surrogateescape")
        if unchanged:  # the existing lines of a file the delivery touched; a file it added has none
            if not (fixture / name).is_file():
                continue
            lines = set(range(1, len(text.splitlines()) + 1)) - lines
        found = [site for site in quality.sites(text) if site["line"] in lines]
        if found:
            per_file[name] = found
    order = quality.round_robin(per_file)
    chosen = order[:sample]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda item: one(tree, scratch, item[0], item[1][0], item[1][1], manifest, set(skip)), enumerate(chosen)))
    shutil.rmtree(scratch, ignore_errors=True)
    valid = [row for row in rows if not row.get("invalid")]
    where = "unchanged lines of the files the delivery touched" if unchanged else "changed lines"
    report = {"label": label, "tree": str(tree), "where": where, "sites_on_changed_lines": len(order), "files": {name: len(found) for name, found in per_file.items()},
              "sampled": len(chosen), "invalid": len(rows) - len(valid), "commands_failing_on_the_untouched_copy": skip, "untouched_failures": reasons, "faults": rows}
    for suite in (["own", "acceptance"] if manifest else ["own"]):
        caught = sum(1 for row in valid if row.get(suite) is True)
        survived = sum(1 for row in valid if row.get(suite) is False)
        report[suite] = {"caught": caught, "survived": survived, "did_not_end": sum(1 for row in valid if row.get(suite) is None),
                         "not_measured": sum(1 for row in valid if row.get(suite) == NOT_MEASURED),
                         "share": round(caught / (caught + survived), 3) if caught + survived else None}
    if manifest:
        both = [[row.get("own"), row.get("acceptance")] for row in valid]
        caught = sum(1 for verdicts in both if True in verdicts)
        survived = sum(1 for verdicts in both if True not in verdicts and None not in verdicts and False in verdicts)
        report["either"] = {"caught": caught, "survived": survived, "share": round(caught / (caught + survived), 3) if caught + survived else None}
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"{label}: {len(order)} fault sites on {where} in {len(per_file)} files; {len(chosen)} sampled, {report['invalid']} invalid; "
          + "; ".join((f"{suite} not measured" if report[suite].get("not_measured") else
                       f"{suite} {report[suite]['caught']} caught, {report[suite]['survived']} survived"
                       + (f" ({report[suite]['share']:.0%})" if report[suite]["share"] is not None else ""))
                      for suite in ("own", "acceptance", "either") if suite in report)
          + (f"; {len(skip)} command(s) left out because they fail on the untouched copy" if skip else ""))


if __name__ == "__main__":
    main()
