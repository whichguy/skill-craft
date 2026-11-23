#!/usr/bin/env python3
"""Every script measure of one finished run (journal section 4, M1 to M7a). No model is called.

    python3 measure.py ROOT LABEL [--only PART ...] [--again]
    python3 measure.py held-out KIND WORK COMMIT OUT.json    one held-out grader grade.py does not have (roundtable)

ROOT is the comparison's runs root (launch.py's), LABEL a run in it. Results go under ROOT/measure/LABEL/: one file a
part and point, and ROOT/measure/LABEL/measures.json, the run's whole record. A part already measured is read back,
not run again, unless --again. Parts: time, tokens, hidden, static, coverage, mutation, calibrated.

Points. ShipLoop: `final`, its delivered head. Ratchet: `first-build` (its build-1 commit) and `final` (its last
stage commit). Each point is cloned with its history into ROOT/measure/LABEL/POINT/tree, and the tools read the clone.
The base is the commit the run started from (ShipLoop: the harness's start_head; Ratchet: its `base` commit), and the
starting files (for the seeded faults' "changed lines") are that commit's tree, exported to ROOT/measure/LABEL/fixture.

The tools: the pilot's grade.py tree (held-out checks; for roundtable, which grade.py has no grader of, this script's
own `held-out`, run the same way), mutate.py (seeded faults; --own-command for a case whose
tests run with `node --test`; with --manifest for Ratchet, so its acceptance suite is read too), baseline.py (ticket
assignment's calibrated defects), and this folder's static.py and coverage.py. TMPDIR is a plain folder under ROOT
for all of them (the macOS temporary folder is a symbolic link that path-watching tests trip on).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "ratchet-pilot-20261120"
E2E = HERE.parents[2] / "test" / "shiploop_e2e"  # the harness grade.py reads (REPO/test/shiploop_e2e beside the pilot)
sys.path.insert(0, str(PILOT))

CASES = {
    "shared-expenses": {"kinds": ["expenses"], "own": "node --test", "entries": ["server.js"]},
    "node-chess-engine": {"kinds": ["chess"], "own": "npm test", "entries": ["src/chess.js"]},
    "ticket-assignment": {"kinds": ["ticket-assignment"], "own": "npm test", "entries": ["src/server.js", "bin/tickets.js"],
                          "calibrated": True},
    "grokbot-local": {"kinds": ["grokbot", "grokbot2"], "own": "npm test", "entries": ["server.js"]},
    "roundtable": {"kinds": ["roundtable", "roundtable-checks"], "own": "node --test", "entries": ["server.js"]},
}
PARTS = ("time", "tokens", "hidden", "static", "coverage", "mutation", "calibrated")
HELD_OUT = ("roundtable", "roundtable-checks")  # held-out graders of this script's own (`held-out`), not grade.py's
HELD_OUT_SECONDS = 1800  # the browser check's driver waits without a limit of its own: its groups are ended after this


def git(*args, check=True) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {done.stderr.strip()[-300:]}")
    return done.stdout.strip()


def run_tool(argv: list[str], env: dict, log: Path, seconds: int = 7200) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as handle:
        handle.write(f"[{time.strftime('%H:%M:%S')}] {' '.join(argv)}\n")
        handle.flush()
        try:
            done = subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env,
                                  timeout=seconds, check=False)
            return done.returncode
        except subprocess.TimeoutExpired:
            handle.write(f"timed out after {seconds} s\n")
            return -1


class Run:
    def __init__(self, root: Path, label: str):
        self.root, self.label = root, label
        self.launch = json.loads((root / f"{label}.launch.json").read_text())
        self.arm, self.case = self.launch["arm"], self.launch["case"]
        self.spec = CASES[self.case]
        self.out = Path(self.launch["output"])
        self.work = self.out / "work"
        self.folder = root / "measure" / label
        self.folder.mkdir(parents=True, exist_ok=True)
        self.tmp = root / "measure" / "tmp"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, TMPDIR=str(self.tmp))
        self.env.pop("PROVIDER_TOKEN", None)
        self.log = self.folder / "measure.log"
        if self.arm == "shiploop":
            result = json.loads((self.out / "result.json").read_text())
            self.result = result
            self.base = (result.get("committed") or {}).get("start_head") or (result.get("base") or {}).get("start_head")
            self.points = {"final": (result.get("committed") or {}).get("head")}
        else:
            record = json.loads((self.out / "run.json").read_text())
            if not record.get("finished"):
                raise SystemExit(f"{label}: the Ratchet run has not finished (run.json has no 'finished'); measure it when it ends")
            self.record = record
            shots = {shot["label"]: shot for shot in record.get("snapshots", [])}
            self.base = shots["base"]["commit"]
            last = record["snapshots"][-1]
            self.points = {"first-build": shots["build-1"]["commit"] if "build-1" in shots else None, "final": last["commit"]}
            self.first_build_at = shots["build-1"]["at"] if "build-1" in shots else None
        self.points = {name: commit for name, commit in self.points.items() if commit}

    # ------------------------------------------------------------------ shared pieces
    def tree(self, point: str) -> Path:
        target = self.folder / point / "tree"
        if not (target / ".git").exists():
            shutil.rmtree(target, ignore_errors=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            git("clone", "-q", "--no-hardlinks", str(self.work), str(target))
            git("-C", str(target), "checkout", "-q", self.points[point])
        return target

    def fixture(self) -> Path:
        target = self.folder / "fixture"
        if not target.exists():
            target.mkdir(parents=True)
            if self.base:  # a ShipLoop run of a case that starts empty (roundtable) has no start commit: no starting files
                archive = subprocess.run(["git", "-C", str(self.work), "archive", self.base], capture_output=True, check=True).stdout
                subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)
        return target

    def cached(self, path: Path, again: bool):
        if path.exists() and not again:
            try:
                return json.loads(path.read_text())
            except ValueError:
                return None
        return None

    # ------------------------------------------------------------------ parts
    def time_part(self) -> dict:
        if self.arm == "shiploop":
            process = self.result.get("process") or {}
            sessions = process.get("sessions") or []
            seconds = sum(row.get("elapsed_seconds") or 0 for row in sessions) or process.get("elapsed_seconds")
            resumes = (self.result.get("termination") or {}).get("resumes")
            return {"minutes": round(seconds / 60, 1) if seconds else None, "seconds": seconds, "resumes": resumes,
                    "outcome": self.result.get("outcome_class"), "pass": self.result.get("pass"),
                    "shiploop_version": (self.result.get("versions") or {}).get("shiploop_version")}
        record = self.record
        by_role = {}
        for session in record.get("sessions", []):
            by_role[session.get("role")] = round(by_role.get(session.get("role"), 0) + (session.get("seconds") or 0), 1)
        return {"minutes": round(record["seconds"] / 60, 1) if record.get("seconds") else None, "seconds": record.get("seconds"),
                "first_build_minutes": round(self.first_build_at / 60, 1) if self.first_build_at else None,
                "stop": record.get("stop"), "cycles": len(record.get("cycles", [])), "sessions": len(record.get("sessions", [])),
                "final_pass": record.get("final_pass"), "clauses": record.get("clauses"), "seconds_by_role": by_role,
                "finished": record.get("finished")}

    def tokens_part(self) -> dict:
        totals = dict.fromkeys(("input", "cached", "output", "reasoning", "total"), 0)
        files = sorted((self.out / "home").rglob("rollout-*.jsonl"))
        per_file = []
        for path in files:
            last = None
            for line in path.read_text(errors="replace").splitlines():
                if '"total_token_usage"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                info = ((event.get("payload") or {}).get("info") or event.get("info") or {})
                usage = info.get("total_token_usage")
                if usage:
                    last = usage
            if last:
                row = {"input": last.get("input_tokens", 0), "cached": last.get("cached_input_tokens", 0),
                       "output": last.get("output_tokens", 0), "reasoning": last.get("reasoning_output_tokens", 0),
                       "total": last.get("total_tokens", 0)}
                per_file.append({"file": str(path.relative_to(self.out)), **row})
                for key in totals:
                    totals[key] += row[key]
        result = {"rollouts": len(files), "counted": len(per_file), **totals, "uncached_input": totals["input"] - totals["cached"]}
        if self.arm == "ratchet":
            import analyze  # the pilot's reader of each session's reported usage
            first = dict.fromkeys(("input", "cached", "output", "reasoning"), 0)
            build_number = next((s["number"] for s in self.record.get("sessions", []) if s.get("label") in ("build-1",)), None)
            for folder in sorted((self.out / "sessions").iterdir()):
                number = int(folder.name.split("-", 1)[0]) if folder.name.split("-", 1)[0].isdigit() else None
                if build_number is None or number is None or number > build_number:
                    continue
                use = analyze.usage(folder)
                for key in first:
                    first[key] += use.get(key, 0)
            result["first_build"] = first
        return result

    def hidden_part(self, point: str, again: bool) -> dict:
        rows = {}
        for kind in self.spec["kinds"]:
            path = self.folder / point / f"hidden-{kind}.json"
            row = self.cached(path, again)
            if row is None:
                tool = ([sys.executable, str(Path(__file__).resolve()), "held-out"] if kind in HELD_OUT
                        else [sys.executable, str(PILOT / "grade.py"), "tree"])
                run_tool(tool + [kind, str(self.work), self.points[point], str(path)], self.env, self.log)
                row = self.cached(path, False) or {"observed": False, "reason": f"{Path(tool[1]).name} wrote no result"}
            rows[kind] = {"observed": row.get("observed"), "passed": len(row.get("passed") or []),
                          "failed": sorted(row.get("failed") or {}), "of": len(row.get("passed") or []) + len(row.get("failed") or {}),
                          **({"stated": row["stated"], "implied": row["implied"]} if row.get("stated") else {})}
        return rows

    def static_part(self, point: str, again: bool) -> dict:
        path = self.folder / point / "static.json"
        row = self.cached(path, again)
        if row is None:
            argv = [sys.executable, str(HERE / "static.py"), str(self.tree(point)), self.base or "-", str(path)]
            for entry in self.spec["entries"]:
                argv += ["--entry", entry]
            run_tool(argv, self.env, self.log)
            row = self.cached(path, False) or {}
        return row

    def coverage_part(self, point: str, again: bool) -> dict:
        rows = {}
        scopes = [("own", False)] + ([("all-suites", True)] if self.arm == "ratchet" else [])
        for name, manifest in scopes:
            path = self.folder / point / f"coverage-{name}.json"
            row = self.cached(path, again)
            if row is None:
                argv = [sys.executable, str(HERE / "coverage.py"), str(self.tree(point)), self.base or "-", str(path),
                        "--command", self.spec["own"]] + (["--manifest"] if manifest else [])
                run_tool(argv, self.env, self.log)
                row = self.cached(path, False) or {}
            rows[name] = {scope: row.get(scope) for scope in ("all", "changed")}
            rows[name]["browser_free"] = browser_free(row) if row else None
            rows[name]["commands"] = len(row.get("commands") or [])
            rows[name]["tests"] = (row.get("commands") or [{}])[0].get("tests") if row else None
            rows[name]["unloaded"] = row.get("unloaded")
        return rows

    def mutation_part(self, point: str, again: bool) -> dict:
        path = self.folder / point / "mutation.json"
        row = self.cached(path, again)
        if row is None:
            tree = self.tree(point)
            # none yet at a first build; and not for Grokbot, whose acceptance suite is about 300 browser commands: a
            # fault that survives runs all of them, so 60 faults would take many hours (R4 reads the own tests only)
            manifest = (self.arm == "ratchet" and (tree / "ratchet" / "acceptance.json").is_file()
                        and self.case != "grokbot-local")
            argv = [sys.executable, str(PILOT / "mutate.py"), f"{self.label}-{point}", str(tree), str(self.fixture()),
                    str(path), "--workers", "2", "--own-command", self.spec["own"]] + (["--manifest"] if manifest else [])
            run_tool(argv, self.env, self.log)
            row = self.cached(path, False) or {}
        return summarize_mutation(row)

    def calibrated_part(self, point: str, again: bool) -> dict | None:
        if not self.spec.get("calibrated"):
            return None
        path = self.folder / point / "calibrated.json"
        row = self.cached(path, again)
        if row is None:
            run_tool([sys.executable, str(PILOT / "baseline.py"), self.case, f"{self.label}-{point}", str(self.tree(point)), str(path)],
                     self.env, self.log)
            row = self.cached(path, False) or {}
        return summarize_calibrated(row)

    def measure(self, only: set[str], again: bool) -> dict:
        record_path = self.folder / "measures.json"
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        record.update(label=self.label, arm=self.arm, case=self.case, base=self.base, points=self.points,
                      commit=self.launch.get("commit"), model=self.launch.get("model"), effort=self.launch.get("effort"))
        if "time" in only:
            record["time"] = self.time_part()
        if "tokens" in only:
            record["tokens"] = self.tokens_part()
        measured = record.get("measured_points") or {}
        for point in self.points:
            if measured.get(point) not in (None, self.points[point]):  # a point measured at another commit: start it again
                shutil.rmtree(self.folder / point, ignore_errors=True)
                record.get("at", {}).pop(point, None)
            measured[point] = self.points[point]
            record["measured_points"] = measured
            (self.folder / point).mkdir(parents=True, exist_ok=True)
            row = record.setdefault("at", {}).setdefault(point, {})
            same = point == "first-build" and self.points.get("final") == self.points[point]
            if "hidden" in only:
                row["hidden"] = self.hidden_part(point, again)
            if "static" in only:
                row["static"] = slim_static(self.static_part(point, again))
            if "coverage" in only:
                row["coverage"] = self.coverage_part(point, again)
            if "mutation" in only and not same:
                row["mutation"] = self.mutation_part(point, again)
            if "calibrated" in only and not same:
                row["calibrated"] = self.calibrated_part(point, again)
            record_path.write_text(json.dumps(record, indent=1) + "\n")
        record_path.write_text(json.dumps(record, indent=1) + "\n")
        return record


def browser_free(row: dict) -> dict | None:
    """Coverage over the product files Node can run: files the product serves to a browser left out (journal 4)."""
    files = row.get("files") or {}
    keep = {name: values for name, values in files.items() if not served_to_browser(name)}
    totals = {}
    for scope, prefix in (("all", ""), ("changed", "changed_")):
        lines = sum(values[f"{prefix}lines"] for values in keep.values())
        ran = sum(values[f"{prefix}run"] for values in keep.values())
        functions = sum(values[f"{prefix}functions"] for values in keep.values())
        functions_run = sum(values[f"{prefix}functions_run"] for values in keep.values())
        totals[scope] = {"lines": lines, "run": ran, "line_share": round(ran / lines, 4) if lines else None,
                         "functions": functions, "functions_run": functions_run,
                         "function_share": round(functions_run / functions, 4) if functions else None}
    totals["left_out"] = sorted(set(files) - set(keep))
    return totals


BROWSER_DIRS = {"public", "static", "client", "www", "assets", "frontend", "web", "browser"}


def served_to_browser(name: str) -> bool:
    return any(part in BROWSER_DIRS for part in Path(name).parts[:-1])


def slim_static(row: dict) -> dict:
    if not row:
        return {}
    docs = row.get("docs") or {}
    return {"code": row.get("code"), "comments": row.get("comments"), "surfaces": row.get("surfaces"),
            "docs": {"user": docs.get("user"), "all": docs.get("all"), "user_words": docs.get("user_words"),
                     "process_words": docs.get("process_words"), "user_files": docs.get("user_files"),
                     "process_files": docs.get("process_files")}, "product_files": row.get("product_files")}


def summarize_mutation(row: dict) -> dict:
    """mutate.py's own summaries per suite; a suite whose command fails on the untouched copy is not measured."""
    if not row:
        return {"measured": False}
    failing = row.get("commands_failing_on_the_untouched_copy") or []
    out = {"measured": True, "sampled": row.get("sampled"), "invalid": row.get("invalid"),
           "sites_on_changed_lines": row.get("sites_on_changed_lines"), "failing_on_untouched": failing}
    for suite in ("own", "acceptance", "either"):
        if isinstance(row.get(suite), dict):
            out[suite] = dict(row[suite])
    if "own" in out and any(command in failing for command in ("npm test", "node --test")):
        out["own"]["not_measured"] = "the own test command fails on the untouched copy"
    return out


def summarize_calibrated(row: dict) -> dict:
    if not row:
        return {"measured": False}
    return {"measured": True, "caught": row.get("caught"), "pool": row.get("pool"), "missed": row.get("missed"),
            "not_judged": row.get("not_judged"), "failing_on_reference": row.get("failing_on_reference"),
            "test_files": row.get("test_files")}


def held_out(kind: str, work: str, commit: str, out: str) -> None:
    """KIND's held-out checks on COMMIT of WORK, written to OUT in the shape grade.py's `tree` writes, for a case grade.py
    has no grader of. As grade.py's grade_tree, the commit's files are exported and Ratchet's own folders removed first.

    roundtable         the harness's held-out check of the case (its cases.json quality.acceptance: roundtable_accept's
                       `conversation`, a browser driving the page), run by the harness's own quality.acceptance, as
                       grade.py runs ticket assignment's, with grade.py's Playwright and browser
    roundtable-checks  the harness case's own checks (the pass-count `node --test`; the page and the local agent
                       endpoint, serve.py with roundtable_contract.py api), each run as the harness runs a check, a shell
                       line in the copy with E2E_CHECKS set, as grade.py's battleship kind runs that case's. The Ratchet
                       arm's gate runs only the first, so the second is held out from that arm and not from ShipLoop's
                       harness, whose verdict includes it
    """
    import grade  # the pilot's: its apparatus folders and this machine's Playwright and browser
    sys.path.insert(0, str(E2E))
    import listeners
    import quality
    case = json.loads((E2E / "cases.json").read_text())["roundtable"]
    scratch = Path(tempfile.mkdtemp(prefix="held-out-"))
    copy = scratch / "copy"
    copy.mkdir()
    try:
        archive = subprocess.run(["git", "-C", work, "archive", commit], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(copy)], input=archive, check=True)
        for name in grade.APPARATUS:  # a check that runs `node --test` must see the delivery's tests only
            shutil.rmtree(copy / name, ignore_errors=True)
        if kind == "roundtable":
            os.environ.setdefault("PLAYWRIGHT_NODE_PATH", grade.PLAYWRIGHT)
            os.environ.setdefault("BROWSER_EXECUTABLE_PATH", grade.BROWSER)
            groups, ended = set(), []

            def end_groups():  # this process's own children only: the groups quality.acceptance registered
                ended.extend(pid for pid in groups.copy() if listeners.end_group(pid))

            timer = threading.Timer(HELD_OUT_SECONDS, end_groups)
            timer.start()
            try:
                spec = case["quality"]
                found = quality.acceptance(copy, spec["acceptance"], groups=groups, stop=lambda: None, logs=scratch / "logs",
                                           ports=list(spec.get("refuse_ports") or []))
            finally:
                timer.cancel()
            rows = found.get("checks") or []
            result = {"observed": bool(found.get("observed")), "reason": found.get("reason"),
                      "passed": [row["id"] for row in rows if row.get("pass")],
                      "failed": {row["id"]: row.get("note") for row in rows if not row.get("pass")}}
            if ended:
                result.update(observed=False, reason=f"ended after {HELD_OUT_SECONDS} s; {result['reason'] or ''}".strip("; "))
        elif kind == "roundtable-checks":
            names = ("own-tests", "page-and-agent")
            passed, failed = [], {}
            for index, command in enumerate(case["checks"]):
                name = names[index] if len(case["checks"]) == len(names) else f"check-{index + 1}"
                try:
                    done = subprocess.run(command, shell=True, cwd=copy, capture_output=True, stdin=subprocess.DEVNULL,
                                          text=True, timeout=300, env=dict(os.environ, E2E_CHECKS=str(E2E / "checks")),
                                          check=False)
                    ok, note = done.returncode == 0, (done.stdout + done.stderr).strip()[-240:]
                except subprocess.TimeoutExpired:
                    ok, note = False, "timed out after 300 s"
                if ok:
                    passed.append(name)
                else:
                    failed[name] = note
            result = {"observed": True, "reason": None, "passed": passed, "failed": failed}
        else:
            raise SystemExit(f"no held-out grader of this script named {kind!r}: {', '.join(HELD_OUT)}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = {"observed": False, "reason": f"{type(error).__name__}: {error}"[:300]}
    finally:
        listeners.reap(scratch)  # a server a check or a test left listening in the copy
        shutil.rmtree(scratch, ignore_errors=True)
    resolved = subprocess.run(["git", "-C", work, "rev-parse", commit], capture_output=True, text=True, check=False).stdout.strip()
    Path(out).write_text(json.dumps(dict(result, kind=kind, work=str(Path(work).resolve()), commit=resolved), indent=1) + "\n")
    print(f"{Path(work).resolve().parent.name:<34}{kind:<18}passed {len(result.get('passed') or []):>2}  "
          f"failed {sorted(result.get('failed') or {})}" + ("" if result.get("observed") else f"  (not observed: {result.get('reason')})"))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 5 and argv[0] == "held-out":  # held-out KIND WORK COMMIT OUT.json: run by hidden_part
        held_out(*argv[1:])
        return 0
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("label")
    parser.add_argument("--only", nargs="+", choices=PARTS, default=list(PARTS))
    parser.add_argument("--again", action="store_true")
    args = parser.parse_args(argv)
    run = Run(args.root.expanduser().resolve(), args.label)
    record = run.measure(set(args.only), args.again)
    print(json.dumps({key: record.get(key) for key in ("label", "arm", "case", "time", "tokens")}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
