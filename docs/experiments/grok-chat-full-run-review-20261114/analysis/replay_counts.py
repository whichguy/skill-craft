"""Replay ShipLoop's test-count reader, before and after the TAP reader, over every retained run's recorded test runs.

    python3 -I replay_counts.py --repo REPO --base BASE_COMMIT --manifest OUT_MANIFEST ROOT [ROOT ...]

The question: does the TAP reader change any verdict a retained run recorded, other than the counts it adds?  For each
ShipLoop run directory under the ROOTs (a directory holding ``state.md`` and ``tests/``; copies under a checkout
(``/worktree/``, ``/worktrees/``), a harness, fixtures or a cache are excluded and counted), every test record
(``check``, ``check-only``, ``verifyN``, ``baseN``, ``mutationN``, ``proofN``, ``proof-check``, ``proof-check-only``) is
read, and each recorded run's output (stdout, a newline, stderr, as the judge reads it) is given to

- the BASE commit's ``shiploop_test_counts`` (read with ``git show``, loaded from a temporary directory), and
- REPO's current one,

with the run's recorded exit code.  ``shiploop_test_loop`` is the same at both (the change does not touch it); its
``counts`` module is swapped, so ``count``, ``named`` and ``outcomes`` all move together, as they would in a real run.

Reported:

- the inputs: run directories, records by form, rows, unique count inputs (stdout, stderr, exit), records with no
  ``runs`` array, rows whose stored output was cut to the engine's kept tail, and the directories excluded as copies;
- (a) an output whose old count was not ``None`` and whose new count differs, with the one registered exception (a
  TAP stream at exit status 5, which pytest's guess read as zero) listed apart;
- (b) the outputs newly counted, by reader and by run directory;
- (c) every candidate or check row (``judge``) and base row (``_judge_base`` with no exempt, retired or added IDs: an
  approximation, labelled) whose verdict changes, plus the rows whose verdict holds but now carries a count;
- (e) floor histories: per run directory, work item and newly counted command, every counted row's count in record order
  (rows the old reader counted included: a floor is the most any accepted run ran), and any later count below an
  earlier one, the only way a count floor can newly bind;
- a positive control: the 2026-11-14 trial's Security row must move from ``None`` to 9, or the replay is not trusted.

Cut rows are replayed as stored, and those that hold a TAP plan line are listed: a live run's judge reads the whole
output, the record only its tail.  OUT_MANIFEST lists each run directory with its record count and the sha256 over its
records' names and contents: written on the first run, verified on every later one, so the inputs can be checked again.
The header names each reader by the sha256 of its source.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FORMS = re.compile(r"-(check|check-only|verify\d+|base\d+|mutation\d+|proof\d+|proof-check|proof-check-only)\.md$")
JUDGED = {"check", "check-only", "verifyN", "proofN", "proof-check", "proof-check-only"}
COPIES = ("/worktree/", "/worktrees/", "/harness/", "/fixtures/", "/cache/", "/.cache/")
STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
TRIAL = ("salesforce-grokbot-independent-20261114T161019Z", "nav-3a979ba338724d97a6f0246f62e0097e-check.md",
         "SLGrokChatSecurityTest")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ledgers(roots: list[str]) -> tuple[list[str], int]:
    found, excluded = [], 0
    for root in roots:
        for path, _dirs, files in os.walk(root):
            if "state.md" in files and os.path.isdir(os.path.join(path, "tests")):
                if any(part in path + "/" for part in COPIES):
                    excluded += 1
                else:
                    found.append(path)
    return sorted(found), excluded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--manifest", required=True, help="the frozen input list: verified when it exists, written when not")
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()
    scripts = Path(args.repo) / "skills/shiploop/scripts"
    old_source = subprocess.run(["git", "-C", args.repo, "show", args.base + ":skills/shiploop/scripts/shiploop_test_counts.py"],
                                check=True, capture_output=True, text=True).stdout
    temp = Path(tempfile.mkdtemp(prefix="replay-counts-"))
    (temp / "shiploop_test_counts.py").write_text(old_source)
    sys.path.insert(0, str(scripts))
    new = load("shiploop_test_counts", scripts / "shiploop_test_counts.py")
    old = load("old_shiploop_test_counts", temp / "shiploop_test_counts.py")
    sys.modules["shiploop_test_counts"] = new
    import shiploop_test_loop as loop  # noqa: E402  (after the path is set)

    def verdicts(row, code, out, form):
        found = []
        for module in (old, new):
            loop.counts = module
            if form in JUDGED:
                found.append(loop.judge(row, code, out)["status"])
            else:
                found.append(loop._judge_base(row, code, out, [], [], [])["status"])
        loop.counts = new
        return found

    directories, excluded = ledgers(args.roots)
    forms = collections.Counter()
    manifest, rows, runless, cut = [], 0, 0, 0
    count_seen, judged_seen = {}, set()
    changed, registered, gained = [], [], collections.Counter()
    gained_by_run = collections.Counter()
    moved, counted_now = collections.Counter(), collections.Counter()
    series = collections.defaultdict(list)
    newly: set = set()
    cut_tap: list = []
    control = None
    for directory in directories:
        tests = Path(directory) / "tests"
        names = sorted(name for name in os.listdir(tests) if FORMS.search(name))
        digest = hashlib.sha256()
        for name in names:
            raw = (tests / name).read_bytes()
            digest.update(name.encode() + b"\0" + hashlib.sha256(raw).digest())
            form = re.sub(r"\d+", "N", FORMS.search(name).group(1))
            forms[form] += 1
            block = STATE.search(raw.decode("utf-8", "replace"))
            try:
                record = json.loads(block.group(1)) if block else None
            except ValueError:
                record = None
            runs = record.get("runs") if isinstance(record, dict) else None
            if not isinstance(runs, list):
                runless += 1
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                rows += 1
                stdout, stderr, code = str(run.get("stdout") or ""), str(run.get("stderr") or ""), run.get("exit")
                is_cut = stdout.startswith("[... ") or stderr.startswith("[... ")
                cut += is_cut
                out = stdout + "\n" + stderr
                key = hashlib.sha256(json.dumps([stdout, stderr, code]).encode()).hexdigest()
                if key not in count_seen:
                    before, after = old.count(out, code), new.count(out, code)
                    count_seen[key] = (before, after)
                    if before is not None and before != after:
                        tap_at_five = code == 5 and before == {"ran": 0, "failed": 0, "runners": ["pytest"]} \
                            and after is not None and after["runners"] == ["tap"]
                        (registered if tap_at_five else changed).append((directory, name, str(run.get("command"))[:80],
                                                                        before, after))
                    elif before is None and after is not None:
                        gained[tuple(after["runners"])] += 1
                        gained_by_run[directory] += 1
                before, after = count_seen[key]
                series_key = (directory, str(record.get("work_item")), str(run.get("command")))
                if after is not None:  # every counted row: a floor is the most any accepted run of the command ran
                    series[series_key].append((str(record.get("created_at")), name, after["ran"]))
                if before is None and after is not None:
                    newly.add(series_key)
                if is_cut and re.search(r"^1\.\.\d+", out, re.M):
                    cut_tap.append((directory, name, str(run.get("command"))[:60], before, after))
                if TRIAL[0] in directory and name == TRIAL[1] and TRIAL[2] in str(run.get("command")):
                    control = (before, after)
                row = {key: run[key] for key in ("command", "suite", "ids", "min_tests", "regression") if key in run}
                if "suite" not in row or "command" not in row:
                    continue
                if form not in JUDGED and form != "baseN":
                    continue
                judged_key = key + json.dumps(row, sort_keys=True) + form
                if judged_key in judged_seen:
                    continue
                judged_seen.add(judged_key)
                was, now = verdicts(row, code, out, form)
                if was != now:
                    moved[(form if form in JUDGED else "baseN (approximate)", was, now)] += 1
                elif before is None and after is not None:
                    counted_now[(form if form in JUDGED else "baseN (approximate)", now)] += 1
        manifest.append(f"{directory}\t{len(names)}\t{digest.hexdigest()}")
    frozen = Path(args.manifest)
    if frozen.is_file():
        before_lines, now_lines = set(frozen.read_text().splitlines()), set(manifest)
        manifest_note = ("verified: all %d run directories match the frozen list" % len(manifest)
                         if before_lines == now_lines else
                         "DIFFERS from the frozen list: %d missing, %d new or changed" % (len(before_lines - now_lines),
                                                                                          len(now_lines - before_lines)))
    else:
        frozen.write_text("\n".join(manifest) + "\n")
        manifest_note = "written: %d run directories" % len(manifest)

    falls = []
    for (directory, item, command), seen in sorted(item for item in series.items() if item[0] in newly):
        seen.sort()
        counts = [ran for _at, _name, ran in seen]
        if any(counts[index] < max(counts[:index]) for index in range(1, len(counts))):
            falls.append((directory, item, command[:80], counts))

    new_source = (scripts / "shiploop_test_counts.py").read_bytes()
    print("base reader:", args.base + ":skills/shiploop/scripts/shiploop_test_counts.py", "sha256",
          hashlib.sha256(old_source.encode()).hexdigest()[:16])
    print("new reader: ", "skills/shiploop/scripts/shiploop_test_counts.py", "sha256", hashlib.sha256(new_source).hexdigest()[:16])
    print("manifest:", manifest_note)
    print("run directories:", len(directories), "| excluded as copies:", excluded)
    print("records:", sum(forms.values()), dict(sorted(forms.items())))
    print("rows:", rows, "| unique count inputs:", len(count_seen), "| unique judged rows:", len(judged_seen),
          "| records with no runs:", runless, "| rows with cut output:", cut)
    print("positive control (the trial's Security row):", control[0] if control else "NOT FOUND", "->",
          control[1] if control else "")
    print("(a) old count not None and changed:", len(changed), "| registered exception (TAP at exit 5):", len(registered))
    for entry in changed + registered:
        print("   ", entry)
    print("(b) newly counted inputs:", sum(gained.values()), dict(gained), "in", len(gained_by_run), "run directories")
    for directory, number in sorted(gained_by_run.items()):
        print("   ", number, directory)
    print("(c) verdict changes (form, old, new):", dict(sorted(moved.items())) or "none")
    print("    verdict held, now counted (form, verdict):", dict(sorted(counted_now.items())))
    print("    cut rows that hold a TAP plan line (stored tail only; the live judge read the whole output):", len(cut_tap))
    for entry in cut_tap:
        print("       ", entry)
    print("(e) floor histories:", len(newly), "newly counted command series, each with every counted row of its command"
          " | with a later count below an earlier one:", len(falls))
    for entry in falls:
        print("   ", entry)
    trusted = control is not None and control[0] is None and control[1] is not None and control[1]["ran"] == 9
    print("positive control flips:", trusted)
    return 0 if trusted else 1


if __name__ == "__main__":
    sys.exit(main())
