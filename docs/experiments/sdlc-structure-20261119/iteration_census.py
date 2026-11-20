#!/usr/bin/env python3
"""Where the build loop iterates: per step, what happens after `implement` is accepted.

For every finished run in the census (stage_census.py's output) this pairs three records of each build step:

- the navigator trace (run/trace.jsonl): when each action was issued and accepted, and each refused callback;
- ShipLoop's own snapshots: every lint record holds the Git tree of the working copy at that moment
  (run/lint/<action>.<n>.md, .gate<n>.md), the review snapshot (run/improve/<action>-bind.md) and the step commit
  (run/iterations/<item>.json), so the product-code lines changed during `test`, during `document` and by the step
  review can be counted from Git, whatever the host;
- the host's command stream (events.jsonl with timeline.jsonl beside the run): the test commands the model itself
  ran inside a stage, their exit codes, and the Until Loop receipts (run/loops/<action>-terminal.json).

Paths are classed with ShipLoop's own catalog (shiploop_item_scope.classify).

Usage: python3 -I iteration_census.py CENSUS.json OUT.json [--all]   (--all also reads runs that did not finish,
such as slices, which stop after carry-forward)
"""
import bisect
import collections
import json
import pathlib
import re
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as item_scope

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.DOTALL)
TEST_RUN = re.compile(
    r"\b(unittest|pytest|node --test|npm (?:run )?test|npx (?:jest|vitest|mocha)|go test|cargo test|jest\b|vitest|bats\b"
    r"|sf apex run test|mvn\b.*\btest|gradle\w*\b.*\btest)")
SHIPLOOP = re.compile(r"skills/shiploop/scripts/shiploop\S*\s+(?:--\S+\s+)*([a-z-]+)")
SURVIVED = re.compile(r"mutation check: \w+ is not done\. (\d+) of (\d+) mutants")
EDIT_TOOLS = {"search_replace", "write", "apply_patch", "edit", "str_replace", "multi_edit"}
SKIP_PREFIX = (".shiploop-improve/", ".until-loop", "docs/shiploop/")


def state(path):
    try:
        return json.loads(STATE.search(path.read_text(errors="replace")).group(1))
    except (OSError, ValueError, AttributeError):
        return None


def git(top, *args):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else None


def churn(top, old, new):
    """Lines added plus deleted between two trees, by ShipLoop path class."""
    if not old or not new:
        return None
    if old == new:
        return {}
    out = git(top, "diff", "--numstat", "--no-renames", old, new)
    if out is None:
        return None
    total = collections.Counter()
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or parts[2].startswith(SKIP_PREFIX):
            continue
        added = int(parts[0]) if parts[0].isdigit() else 0
        deleted = int(parts[1]) if parts[1].isdigit() else 0
        total[item_scope.classify(parts[2])] += added + deleted
    return dict(total)


def commands(folder):
    """The host's tool calls: start time, end time, command text, exit code, tool name."""
    events, timeline = folder / "events.jsonl", folder / "timeline.jsonl"
    if not events.exists() or not timeline.exists():
        return []
    when = {}
    for line in timeline.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
            when[row["line"]] = row["t"]
        except (ValueError, KeyError):
            continue
    calls, order = {}, []
    with events.open(errors="replace") as handle:
        for number, line in enumerate(handle):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get("type")
            if kind == "tool_call":
                raw = event.get("rawInput") or {}
                text = raw.get("command") or " ".join(
                    str(raw[key]) for key in ("target_file", "file_path", "path", "target_directory") if raw.get(key))
                call = {"t": when.get(number), "end": None, "exit": None, "tool": event.get("toolName") or "",
                        "command": text, "output": ""}
                calls[event.get("toolCallId")] = call
                order.append(call)
            elif kind == "tool_call_update" and event.get("toolCallId") in calls:
                call = calls[event["toolCallId"]]
                raw = event.get("rawOutput") or {}
                if event.get("status") in ("completed", "failed"):
                    call["end"] = when.get(number)
                    if isinstance(raw.get("exit_code"), int):
                        call["exit"] = raw["exit_code"]
                    elif event.get("status") == "failed":
                        call["exit"] = 1
                    call["output"] = str(raw.get("output_for_prompt") or "")[:400]
                if not call["command"] and raw.get("command"):
                    call["command"] = raw["command"]
    return [c for c in order if c["t"] is not None]


REASONS = (("mutation check", "tests too weak (a seeded fault survived)"), ("base run", "a new test already passes on the old code"),
           ("test run", "a recorded command failed"), ("lint", "lint finding"), ("Until Loop", "loop receipt"),
           ("receipt", "loop receipt"), ("result file", "result file shape"), ("shiploop-state", "result file shape"))


def reason(output):
    for needle, label in REASONS:
        if needle in output:
            return label
    return "result or record rule"


def read_run(run):
    rundir = pathlib.Path(run["trace"]).parent
    worktree = rundir.parent / "worktree"
    rows = []
    for line in (rundir / "trace.jsonl").read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    issued, accepted, refused, own, stage_of = {}, {}, collections.defaultdict(list), collections.Counter(), {}
    cursor_times, cursor_actions = [], []
    previous, reviewed_action = None, None
    for row in rows:
        if row.get("kind") == "packet" and row.get("action"):
            issued.setdefault(row["action"], row["ts"])
            stage_of.setdefault(row["action"], row.get("stage"))
        if row.get("kind") != "command" or not isinstance(row.get("stage"), list):
            continue
        origin = row["stage"][0]
        before = (row.get("cursor") or [None, None])[0]
        if origin != "improve":
            reviewed_action = before
        if previous is not None and origin and row["ts"] - previous <= 45 * 60:
            own[(reviewed_action, "improve" if origin == "improve" else "own")] += row["ts"] - previous
        previous = row["ts"]
        if row.get("exit") not in (0, None) and row.get("verb") in ("complete", "check") and row.get("action"):
            refused[row["action"]].append(row["ts"])
        for done in row.get("accepted") or []:
            accepted[done["action"]] = {"ts": row["ts"], "stage": done["stage"], "item": done.get("item"),
                                        "outcome": done["outcome"]}
        cursor_times.append(row["ts"])
        cursor_actions.append((row.get("cursor") or [None, None])[1])
    calls = commands(pathlib.Path(run["folder"]))
    by_action = collections.defaultdict(list)
    for call in calls:
        index = bisect.bisect_right(cursor_times, call["t"]) - 1
        if index >= 0 and cursor_actions[index]:
            by_action[cursor_actions[index]].append(call)

    lint = collections.defaultdict(list)
    for path in (rundir / "lint").glob("nav-*.md"):
        record = state(path)
        if record and record.get("tree"):
            lint[record.get("action")].append((record.get("created_at") or "", ".gate" in path.name, record["tree"]))
    binds = []
    for passes in (rundir / "improve").glob("nav-*/passes.md"):
        table = [[c.strip() for c in l.strip().strip("|").split("|")] for l in passes.read_text().splitlines()]
        table = [c for c in table if len(c) >= 8 and c[1].isdigit()]
        bind = rundir / "improve" / f"{passes.parent.name}-bind.md"
        bound = state(bind) if bind.exists() else None
        if table and bound and bound.get("tree"):
            binds.append((bind.stat().st_mtime, table[0][0], bound["tree"]))
    binds.sort()
    step_commits = []
    for path in (rundir / "iterations").glob("*.json"):
        try:
            plans = json.loads(path.read_text()).get("plans") or {}
        except ValueError:
            continue
        for steps in plans.values():
            for step in steps.values():
                if step.get("commit"):
                    stamp = git(worktree, "show", "-s", "--format=%ct %T", step["commit"])
                    if stamp:
                        step_commits.append((int(stamp.split()[0]), stamp.split()[1], step.get("base")))
    step_commits.sort()
    mutation = collections.defaultdict(list)
    for path in (rundir / "tests").glob("nav-*-mutation*.md"):
        record = state(path)
        if record and record.get("sample_size"):
            left = sorted(m.get("operator") or "?" for m in record.get("mutants") or [] if m.get("status") == "survived")
            mutation[record.get("action")].append((record.get("created_at") or "", record.get("killed") or 0,
                                                   record.get("survived") or 0, len(record.get("undisposed") or []), left))
    loops = {}
    for path in (rundir / "loops").glob("*-terminal.json"):
        try:
            receipt = json.loads(path.read_text())
        except ValueError:
            continue
        loops[path.name[:-len("-terminal.json")]] = (receipt.get("progress") or {}).get("action_number")

    def summary(action):
        """What the model did inside one action, from its own command stream."""
        info = {"calls": 0, "test_runs": 0, "test_fails": 0, "checks": 0, "check_fails": 0, "edits": 0,
                "loop_calls": 0, "loop_seconds": 0.0, "first_run": None, "last_fail": None, "green_after_fail": None,
                "refusals": [], "survivors": []}
        start = issued.get(action)
        for call in by_action.get(action, ()):
            info["calls"] += 1
            text = call["command"]
            if call["tool"] in EDIT_TOOLS or "apply_patch" in text:
                info["edits"] += 1
            if "until_loop" in text:
                info["loop_calls"] += 1
                info["loop_seconds"] += max(0.0, (call["end"] or call["t"]) - call["t"])
            verb = SHIPLOOP.search(text)
            if verb and verb.group(1) in ("check", "complete", "red-check"):
                info["checks"] += 1
                if call["exit"] not in (0, None):
                    info["check_fails"] += 1
                    info["last_fail"] = call["end"] or call["t"]
                    info["refusals"].append(reason(call["output"]))
                    counted = SURVIVED.search(call["output"])
                    if counted:
                        info["survivors"].append((int(counted.group(1)), int(counted.group(2))))
                continue
            if TEST_RUN.search(text) and "--help" not in text:
                info["test_runs"] += 1
                if info["first_run"] is None and start:
                    info["first_run"] = call["t"] - start
                if call["exit"] not in (0, None):
                    info["test_fails"] += 1
                    info["last_fail"] = call["end"] or call["t"]
                    info["green_after_fail"] = None
                elif info["last_fail"] and info["green_after_fail"] is None:
                    info["green_after_fail"] = call["end"] or call["t"]
        if info["last_fail"] and start:
            end = info["green_after_fail"] or accepted.get(action, {}).get("ts") or info["last_fail"]
            info["fix_span"] = max(0.0, end - start - (info["first_run"] or 0.0))
        else:
            info["fix_span"] = 0.0
        return info

    steps, current = [], None
    order = sorted(accepted.items(), key=lambda pair: pair[1]["ts"])
    for action, done in order:
        if done["stage"] == "implement" and done["outcome"] == "done":
            current = {"item": done["item"], "implement": action}
            steps.append(current)
        elif current and done["stage"] in ("test", "document") and done["outcome"] == "done" \
                and done["item"] == current["item"] and done["stage"] not in current:
            current[done["stage"]] = action
        elif done["stage"] in ("step-plan", "carry-forward"):
            current = None
    out = []
    for step in steps:
        implement, test, document = step["implement"], step.get("test"), step.get("document")
        record = {"item": step["item"], "implement_s": own[(implement, "own")], "loop_implement": loops.get(implement),
                  "implement_refused": len(refused[implement]), "implement": summary(implement)}
        impl_tree = max(lint[implement])[2] if lint[implement] else None
        test_tree = None
        if test and issued.get(test):
            record["test_s"] = own[(test, "own")]
            record["test"] = summary(test)
            record["test_refused"] = len(refused[test])
            record["refusal_tail_s"] = accepted[test]["ts"] - min(refused[test]) if refused[test] else 0.0
            record["mutation"] = sorted(mutation[test])[-1:]
            record["loop_test"] = loops.get(test)
            gates = sorted(entry for entry in lint[test] if entry[1]) or sorted(lint[test])
            test_tree = gates[-1][2] if gates else None
        built_at = accepted[test]["ts"] if test else accepted[implement]["ts"]
        end = accepted[document]["ts"] if document else built_at
        commit = next((c for c in step_commits if c[0] >= end - 2), None)
        review = ([b for b in binds if b[1] == "document" and built_at - 2 <= b[0] <= end + 2] or [None])[-1]
        if document:
            record["document_s"] = own[(document, "own")]
            record["review_s"] = own[(document, "improve")]
        if commit:
            base_tree = (git(worktree, "rev-parse", f"{commit[2]}^{{tree}}") or "").strip() if commit[2] else None
            record["built"] = churn(worktree, base_tree, impl_tree)
            record["in_test"] = churn(worktree, impl_tree, test_tree)
            record["in_document"] = churn(worktree, test_tree or impl_tree, review[2] if review else None)
            record["in_review"] = churn(worktree, review[2] if review else None, commit[1])
            record["after_implement"] = churn(worktree, impl_tree, commit[1])
            record["trees"] = {"base": base_tree, "implement": impl_tree, "test": test_tree,
                               "before_review": review[2] if review else None, "commit": commit[1]}
        out.append(record)
    stage_loops = [(stage_of.get(action), number) for action, number in loops.items() if number]
    closing = [b for b in binds if b[1] == "carry-forward"]
    return out, {"loops": stage_loops, "end_review_tree": closing[-1][2] if closing else None,
                 "end_review_at": closing[-1][0] if closing else None,
                 "loop_calls": sum("until_loop" in c["command"] for c in calls),
                 "loop_seconds": sum(max(0.0, (c["end"] or c["t"]) - c["t"]) for c in calls if "until_loop" in c["command"]),
                 "calls": len(calls), "worktree": str(worktree)}


def share(values):
    values = list(values)
    return f"{sum(bool(v) for v in values) / len(values):>5.0%}" if values else "    -"


def median(values, digits=0):
    values = [v for v in values if v is not None]
    return f"{statistics.median(values):.{digits}f}" if values else "-"


def code(change):
    return (change or {}).get("code", 0)


def report(rows):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["host"], row["model"], row["effort"] or "-")].append(row)
    groups[("all", "", "")] = rows
    print(f"{'host model effort':<34}{'steps':>6}{'runs':>6}")
    for key, group in sorted(groups.items(), key=lambda pair: -len(pair[1])):
        name = " ".join(key).strip()
        tested = [r for r in group if "test" in r]
        diffed = [r for r in group if r.get("after_implement") is not None and r.get("built") is not None]
        print(f"\n== {name}: {len(group)} steps in {len({r['run'] for r in group})} runs; {len(tested)} with a test "
              f"stage; {len(diffed)} with every snapshot ==")
        if not tested:
            continue
        print(f"  median seconds per step: implement {median(r['implement_s'] for r in group)}, test "
              f"{median(r['test_s'] for r in tested)}, document {median(r.get('document_s') for r in group)}, step "
              f"review {median(r.get('review_s') for r in group)}")
        streamed = [r for r in tested if r["test"]["calls"]]
        if streamed:
            runs = [r["test"]["test_runs"] for r in streamed]
            fails = [r["test"]["test_fails"] for r in streamed]
            print(f"  test stage, the model's own test runs ({len(streamed)} steps with a command stream): median "
                  f"{median(runs)} runs, mean {statistics.mean(runs):.1f}; a failing run in {share(fails).strip()} of "
                  f"steps; failing runs per step mean {statistics.mean(fails):.2f}, of steps with any "
                  f"{median([f for f in fails if f], 0)} median, max {max(fails)}")
            spans = [r["test"]["fix_span"] for r in streamed]
            total = sum(r["test_s"] for r in streamed)
            first = [r["test"]["first_run"] for r in streamed if r["test"]["first_run"] is not None]
            print(f"  test stage time: first own test run a median {median(first)} s in; from first run to the first "
                  f"green after the last failure {sum(spans) / total:.0%} of all test-stage seconds "
                  f"(median {median([s for s in spans if s])} s where there was a failure)")
            impl = [r for r in group if r["implement"]["calls"]]
            print(f"  implement stage: own test or proof runs median {median(r['implement']['test_runs'] for r in impl)}"
                  f"; a failing one in {share(r['implement']['test_fails'] for r in impl).strip()} of steps")
        print(f"  ShipLoop refused a callback: implement {share(r['implement_refused'] for r in group).strip()} of "
              f"steps, test {share(r['test_refused'] for r in tested).strip()} (mean "
              f"{statistics.mean(r['test_refused'] for r in tested):.2f} a step)")
        refusals = collections.Counter(label for r in tested for label in r["test"]["refusals"])
        if refusals:
            print("    why (from the refused command's own output): " + "; ".join(f"{label} {count}" for label, count in refusals.most_common()))
        tails = [r["refusal_tail_s"] for r in tested]
        print(f"    from the first refusal to acceptance: {sum(tails) / sum(r['test_s'] for r in tested):.0%} of all test-stage "
              f"seconds (median {median([t for t in tails if t])} s where refused)")
        counted = [pair for r in tested for pair in r["test"]["survivors"]]
        if counted:
            print(f"    seeded faults at the {len(counted)} refusals that give a count: {sum(a for a, _ in counted)} of "
                  f"{sum(b for _, b in counted)} sampled faults survived the step's tests (median "
                  f"{median([a for a, _ in counted])} of {median([b for _, b in counted])})")
        last = [r["mutation"][0] for r in tested if r.get("mutation")]
        if last:
            kept = collections.Counter(op for m in last for op in m[4])
            print(f"    in the accepted result of {len(last)} steps: {sum(m[1] for m in last)} sampled faults caught, "
                  f"{sum(m[2] for m in last)} left uncaught with a written reason, in {share(m[2] for m in last).strip()} of steps"
                  f" ({', '.join(f'{op} {n}' for op, n in kept.most_common())})")
        looped = [r for r in group if r.get("loop_implement")]
        looped_test = [r for r in tested if r.get("loop_test")]
        print(f"  Until Loop took more than one iteration: implement {share(r['loop_implement'] > 1 for r in looped).strip()}"
              f" of {len(looped)}, test {share(r['loop_test'] > 1 for r in looped_test).strip()} of {len(looped_test)}")
        if diffed:
            built = [code(r["built"]) for r in diffed]
            print(f"  product code after implement was accepted ({len(diffed)} steps; implement wrote a median "
                  f"{median(built)} lines):")
            for label, field in (("during test", "in_test"), ("during document", "in_document"),
                                 ("by the step review", "in_review"), ("any of the three", "after_implement")):
                have = [r for r in diffed if r.get(field) is not None]
                changed = [code(r[field]) for r in have]
                ratio = [code(r[field]) / code(r["built"]) for r in have if code(r[field]) and code(r["built"])]
                print(f"    {label:<20} changed in {share(changed).strip():>4} of {len(have):>3} steps; where changed a "
                      f"median {median([c for c in changed if c])} lines, {median(ratio, 2)} of what implement wrote")


def report_loops(whole):
    print("\n== the Until Loop, every stage ==")
    by_stage = collections.defaultdict(list)
    for run in whole:
        for stage, number in run["loops"]:
            by_stage[stage].append(number)
    total = sum(len(v) for v in by_stage.values())
    more = sum(n > 1 for v in by_stage.values() for n in v)
    print(f"stage loops with a receipt: {total}; ended on their first iteration: {total - more} ({(total - more) / total:.1%})")
    for stage, numbers in sorted(by_stage.items(), key=lambda pair: -len(pair[1])):
        print(f"  {stage!s:<20}{len(numbers):>5} loops; more than one iteration {sum(n > 1 for n in numbers):>3}; most {max(numbers)}")
    groups = collections.defaultdict(list)
    for run in whole:
        if run["calls"]:
            groups[(run["host"], run["model"], run["effort"] or "-")].append(run)
    for key, group in sorted(groups.items(), key=lambda pair: -len(pair[1])):
        calls = [r["loop_calls"] for r in group]
        print(f"  {' '.join(key)}: loop commands per run median {median(calls)}, {sum(calls) / sum(r['calls'] for r in group):.0%} of the "
              f"run's commands; the commands themselves take {sum(r['loop_seconds'] for r in group) / sum(r['seconds'] for r in group):.1%} "
              f"of run time (the model's reading of each printed instruction is not counted)")


def main(census, out, everything=False):
    runs = [r for r in json.loads(pathlib.Path(census).read_text()) if r["current_era"] and (r["done"] or everything)]
    rows, failed, whole = [], 0, []
    for run in runs:
        try:
            steps, facts = read_run(run)
            facts.update(run=run["trace"], host=run.get("host"), model=run.get("model"), effort=run.get("effort"),
                         case=run.get("case"), seconds=sum(run["seconds"].values()))
            whole.append(facts)
        except (OSError, ValueError, KeyError, TypeError) as error:  # a damaged run folder is reported, not fatal
            failed += 1
            print(f"skipped {run['trace']}: {error}", file=sys.stderr)
            continue
        for step in steps:
            step.update(run=run["trace"], host=run.get("host"), model=run.get("model"), effort=run.get("effort"),
                        case=run.get("case"))
            rows.append(step)
    pathlib.Path(out).write_text(json.dumps({"steps": rows, "runs": whole}, indent=1))
    print(f"finished runs read: {len(runs) - failed} of {len(runs)}; build steps: {len(rows)}\n")
    report(rows)
    report_loops(whole)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--all" in sys.argv)
