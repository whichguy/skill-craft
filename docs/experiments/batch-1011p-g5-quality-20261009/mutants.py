#!/usr/bin/env python3
"""The mutants the G5 quality tests are checked against: break the implementation one way at a time and see the tests go red.

usage: python3 mutants.py <worktree> <result.json> [id-prefix ...]

Each entry is (id, file relative to the worktree, text to find (exactly once), replacement, the test selectors to run). The
runner restores every file afterwards. A mutant that survives is either equivalent (the note says why) or a gap in the tests.
It stands in for a fail-first run of quality.py, whose code was drafted before its tests.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

Q = "test/shiploop_e2e/quality.py"
R = "test/shiploop_e2e/run.py"
C = "test/shiploop_e2e/checks/checkers_accept.py"
G = "test/shiploop_e2e/refuse_ports.cjs"

EQUIVALENT = {}  # id -> why a surviving mutant is equivalent

MUTANTS = []


def mutant(ident, path, old, new, selectors, equivalent=None):
    MUTANTS.append((ident, path, old, new, selectors))
    if equivalent:
        EQUIVALENT[ident] = equivalent


# ---- processes
mutant("P01 end_group signals a reaped pid", Q, "    if proc.returncode is not None:  # reaped: the pid may belong to someone else now\n        return False\n", "",
       "ProcessSafetyTest")
mutant("P02 end_group does not check the leader leads its group", Q, "            if os.getpgid(proc.pid) != proc.pid:\n                return False\n", "            pass\n", "ProcessSafetyTest")
mutant("P03 finish does not end the group", Q, "    end_group(proc)\n    proc.wait()\n    groups.discard(proc.pid)", "    proc.wait()\n    groups.discard(proc.pid)", "ProcessSafetyTest")
mutant("P04 start does not register", Q, "    groups.add(proc.pid)\n    return proc", "    return proc", "ProcessSafetyTest")
mutant("P05 finish does not forget", Q, "    proc.wait()\n    groups.discard(proc.pid)", "    proc.wait()", "ProcessSafetyTest")
mutant("P06 a leader that exited is waited for forever", Q, "    while not exited(proc):\n        if time.monotonic() >= end:\n            return False\n", "    while not exited(proc):\n        if False:\n            return False\n", "ProcessSafetyTest.test_a_hanging_mutant_is_counted_killed_and_its_whole_group_ends MutationRunTest.test_a_baseline_that_does_not_finish_is_not_observed")

# ---- fixed ports
mutant("G01 runs get no guard environment", Q, "        env = {**(extra or {}), **(catalog.guard_env(ports, log) if ports else {})}", "        env = {**(extra or {})}", "PortGuardTest")
mutant("G02 a baseline that touches a port is run", Q, "    if base_refusals:\n        return {\"observed\": False, \"baseline\": baseline, \"refuse_ports\"", "    if False:\n        return {\"observed\": False, \"baseline\": baseline, \"refuse_ports\"", "PortGuardTest")
mutant("G03 a mutant's refusals are not counted", Q, "        port_refusals += refusals\n        row[\"port_refusals\"] += refusals", "        pass", "PortGuardTest")
mutant("G04 one refusal log for every run", Q, "        log = refusal_logs / f\"{label}.log\"", "        log = refusal_logs / \"all.log\"", "PortGuardTest")
mutant("G05 the kill record drops the marker", Q, "            if refusals:\n                port_refused += 1", "            if False:\n                port_refused += 1", "PortGuardTest")
mutant("G06 NODE_OPTIONS replaced, not extended", Q, "    options = \" \".join(part for part in (os.environ.get(\"NODE_OPTIONS\", \"\").strip(), f\"--require {quoted}\") if part)", "    options = f\"--require {quoted}\"", "PortGuardTest")
mutant("G07 a path with a space is not quoted", Q, "    quoted = f'\"{preload}\"' if \" \" in str(preload) else str(preload)", "    quoted = str(preload)", "PortGuardTest")
mutant("G08 acceptance server not guarded", Q, "child_env({\"PORT\": str(port), **guard})", "child_env({\"PORT\": str(port)})", "PortGuardTest")
mutant("G09 preload ignores numeric strings", G, "  if (typeof value === 'string' && /^\\d+$/.test(value)) value = Number(value);\n", "", "PortGuardNodeTest")
mutant("G10 preload does not refuse connect", G, "    if (port !== undefined && ports.has(port)) {\n      note('connect', port);", "    if (false) {\n      note('connect', port);", "PortGuardNodeTest")
mutant("G11 preload does not note the refusal", G, "  try { fs.appendFileSync(log, `${process.pid} ${kind} ${port}\\n`); } catch (_) { /* a log that cannot be written must not change a run */ }", "  void log;", "PortGuardNodeTest")
mutant("G12 preload does not read an options object", G, "  if (value && typeof value === 'object' && !Array.isArray(value)) value = value.port;\n", "", "PortGuardNodeTest")
mutant("G13 preload does not refuse listen", G, "    if (port !== undefined && ports.has(port)) {\n      note('listen', port);", "    if (false) {\n      note('listen', port);", "PortGuardNodeTest")
mutant("G14 declared ports not inherited from the followed case", R, "    ports = own.get(\"refuse_ports\") or earlier.get(\"refuse_ports\")", "    ports = own.get(\"refuse_ports\")", "PortGuardTest")

# ---- confirmation, evidence, signs of a load, page script
mutant("C01 a failure is not confirmed", Q, "        elif again is not None and not failed(again):", "        elif False:", "MutationRunTest")
mutant("C02 a hang is run again", Q, "            if failed(result) and not result[\"timeout\"]:\n                ended = stopped(", "            if failed(result):\n                ended = stopped(", "MutationRunTest")
mutant("C03 the stop is not asked before the second run", Q, "                ended = stopped(position, f\"during mutant {position + 1} of {total}\")  # a run the stop killed must not confirm anything\n                if ended:\n                    return ended\n", "", "MutationRunTest")
mutant("C04 a kill records no evidence", Q, "catalog.failing_line(result[\"output\"])})", "\"\"})", "MutationRunTest")
mutant("C05 a hang is a sign of a load", Q, "    signs = {kill[\"file\"] for kill in kills if not kill[\"timeout\"]}", "    signs = {kill[\"file\"] for kill in kills}", "MutationRunTest")
mutant("C06 unconfirmed counts against the ratio", Q, "            \"ratio\": ratio(killed, survived), \"ceiling_hit\": ceiling_hit,", "            \"ratio\": ratio(killed, survived + unconfirmed), \"ceiling_hit\": ceiling_hit,", "MutationRunTest")
mutant("C07 a syntax check that hangs is invalid", Q, "                if syntax[\"timeout\"] or syntax[\"returncode\"] == 127:", "                if syntax[\"returncode\"] == 127:", "MutationRunTest")
mutant("C08 a syntax check that cannot start is invalid", Q, "                if syntax[\"timeout\"] or syntax[\"returncode\"] == 127:", "                if syntax[\"timeout\"]:", "MutationRunTest")
mutant("C09 page script counted in docs", Q, "        if any(part in JS_NOT_SOURCE_FOLDERS for part in path.relative_to(copy).parts[:-1]):\n            continue\n        if any(relative == prefix", "        if any(relative == prefix", "MutationRunTest")
mutant("C10 a script with src counted", Q, "                    if \"src=\" not in attrs.lower())", "                    if True)", "MutationRunTest")
mutant("C11 the line says never loaded", Q, "f\", no sign of a load in: {', '.join(idle)}\"", "f\", never loaded by the tests: {', '.join(idle)}\"", "PrintedLineTest")
mutant("C12 a file's lines are not recorded", Q, "\"lines\": len(originals[name].splitlines()), ", "\"lines\": 0, ", "MutationRunTest")
mutant("C13 unconfirmed not in the line", Q, "f\"{mut['unconfirmed']} unconfirmed\" if mut.get(\"unconfirmed\") else \"\"", "\"\"", "PrintedLineTest")
mutant("C14 no stop check after the last mutant", Q, "    ended = stopped(len(ordered), \"during its last mutant\")", "    ended = None", "MutationRunTest")
mutant("C15 the ceiling's reason is not recorded", Q, "            not_run_reasons[\"the phase ceiling was reached\"] = len(ordered) - position\n", "", "MutationRunTest")
mutant("C16 TAP numbering stays in the evidence", Q, "        name = re.sub(r\"^(?:\\d+\\s+)?-?\\s*\", \"\", JS_TIMING.sub(\"\", found.group(1)))", "        name = JS_TIMING.sub(\"\", found.group(1))", "MutationRunTest")

# ---- order, hosts, regrade, options (run.py and the block)
mutant("R01 the phase runs before the export", R, "    exported = review_export(out)\n    style = json.loads(CASES.read_text())", "    result['quality'] = quality_record(out, work, name, None, stop_file)\n    exported = review_export(out)\n    style = json.loads(CASES.read_text())", "QualityThroughMainTest")
mutant("R02 the row carries the block", R, "            \"output\": result.get(\"output\")}", "            \"output\": result.get(\"output\"), \"quality\": result.get(\"quality\")}", "QualityThroughMainTest")
mutant("R03 a regrade replaces a measurement with a gap", R, "    if isinstance(kept, dict) and kept.get(\"observed\") and not block.get(\"observed\"):", "    if False:", "QualityThroughMainTest")
mutant("R04 the failed block lacks declared", Q, "    return {\"observed\": False, \"declared\": declared_keys(spec), \"hosts_used\": used, \"mixed_host\": mixed,\n            \"reason\": f\"the quality phase failed", "    return {\"observed\": False, \"hosts_used\": used, \"mixed_host\": mixed,\n            \"reason\": f\"the quality phase failed", "QualityThroughMainTest MeasureBlockTest")
mutant("R05 stage appends the sentence", R, "    if planning_review == \"none\" and not resumed:\n        # The run option rides", "    if planning_review and not resumed:\n        # The run option rides", "PlanningReviewOptionTest")
mutant("R06 the card is looked for after the host CLI", R, "        if not resumed:\n            require_improve_card(planning_review, plugin_dir)  # before the host CLI installs the plugin into its profile\n", "", "PlanningReviewOptionTest")
mutant("R07 mixed_host recomputed wrongly", Q, "    return runrecord.hosts_used(out), runrecord.mixed_host(out), None", "    return runrecord.hosts_used(out), False, None", "MeasureBlockTest")
mutant("R08 no launch record reads as an empty host list", Q, "    if not runrecord.launches(out):\n        return None, None, NO_LAUNCH_RECORD", "    if False:\n        return None, None, NO_LAUNCH_RECORD", "MeasureBlockTest")
mutant("R09 the mixed-host note is dropped", Q, "    if used and \"claude\" in used and len(used) > 1:", "    if False:", "MeasureBlockTest")
mutant("R10 the held-out note is dropped", Q, "    if facts[\"held_out_seen\"] is not None:\n        notes.append(", "    if False:\n        notes.append(", "MeasureBlockTest")
mutant("R11 a custom run is measured by battleship", R, "case_quality(name) if name != \"custom\" else {}", "case_quality(name if name != \"custom\" else \"battleship\")", "QualityThroughMainTest")
mutant("R12 quality_stop ignores the signal", R, "return stop_cause(stop_file) if TERMINATION.is_set() or stop_file.exists() else None", "return stop_cause(stop_file) if stop_file.exists() else None", "QualityGateTest")
mutant("R13 quality_stop ignores the stop file", R, "return stop_cause(stop_file) if TERMINATION.is_set() or stop_file.exists() else None", "return stop_cause(stop_file) if TERMINATION.is_set() else None", "QualityGateTest")
mutant("R14 a follow-on does not inherit the declaration", R, "    found = {key: own.get(key) or earlier.get(key) for key in (\"mutation\", \"acceptance\", \"refuse_ports\")}", "    found = {key: own.get(key) for key in (\"mutation\", \"acceptance\", \"refuse_ports\")}", "CaseQualityTest PortGuardTest")
mutant("R15 the child inherits the harness's PORT", Q, "    env = {key: value for key, value in os.environ.items() if key != \"PORT\"}", "    env = dict(os.environ)", "ProcessSafetyTest")
mutant("R16 coverage matches a sibling folder", Q, "                if place.startswith(real + os.sep):", "                if place.startswith(real):", "MutationRunTest")
mutant("R17 the gate ignores the lock", R, "    if not lock_held:\n        return (\"this harness", "    if False:\n        return (\"this harness", "QualityGateTest QualityThroughMainTest")
mutant("R18 the seed-at refusal is removed", R, "    if args.planning_review and args.seed_at:\n        raise SystemExit", "    if False:\n        raise SystemExit", "PlanningReviewOptionTest")
mutant("R19 a resume may change the mode", R, "    if requested is not None and requested != recorded:", "    if False:", "PlanningReviewOptionTest")
mutant("R20 the phase's error fails closed", R, "    except Exception as exc:\n        return quality.failed_block(out, spec, exc)", "    except ZeroDivisionError as exc:\n        return quality.failed_block(out, spec, exc)", "QualityThroughMainTest")

# ---- the 48 mutants of review lens A (its ids kept after "A:"), ported to the code as it is after the fix round; where the code
# the mutant broke no longer exists the entry breaks its successor and says so
mutant("A:M01 end_group: no reaped-pid guard", Q, "    if proc.returncode is not None:  # reaped: the pid may belong to someone else now\n        return False\n", "", "ProcessSafetyTest")
mutant("A:M02 end_group: no leader check", Q, "            if os.getpgid(proc.pid) != proc.pid:\n                return False\n", "            pass\n", "ProcessSafetyTest")
mutant("A:M03 start: not registered", Q, "    groups.add(proc.pid)\n    return proc", "    return proc", "ProcessSafetyTest")
mutant("A:M04 finish: never forgotten", Q, "    proc.wait()\n    groups.discard(proc.pid)", "    proc.wait()", "ProcessSafetyTest")
mutant("A:M05 run_once: timeout not group-killed", Q, "    try:\n        timed_out = not wait_exit(proc, ceiling)\n    finally:\n        finish(proc, groups)\n", "    try:\n        timed_out = not wait_exit(proc, ceiling)\n    finally:\n        proc.kill()\n        proc.wait()\n        groups.discard(proc.pid)\n", "ProcessSafetyTest")
mutant("A:M06 no stop check before a mutant", Q, "        ended = stopped(position, f\"after {position} of {total} mutants\")\n        if ended:\n            return ended\n", "", "MutationRunTest")
mutant("A:M07 no stop check after the last", Q, "    ended = stopped(len(ordered), \"during its last mutant\")", "    ended = None", "MutationRunTest")
mutant("A:M08 ceiling >= to >", Q, "        if clock() - began >= PHASE_CEILING_SECONDS:", "        if clock() - began > PHASE_CEILING_SECONDS:", "MutationRunTest")
mutant("A:M09 file order instead of round robin", Q, "    ordered = round_robin(found)", "    ordered = [(n, s) for n in sorted(found) for s in found[n]]", "MutationRunTest")
mutant("A:M10 a confirmed kill is no sign of a load", Q, "        if name in signs and row[\"loaded_by_tests\"] is not True:", "        if False:", "MutationRunTest")
mutant("A:M11 no restore of the mutated file", Q, "        finally:\n            path.write_bytes(text.encode(\"utf-8\", \"surrogateescape\"))", "        finally:\n            pass", "MutationRunTest")
mutant("A:M12 unreadable events count 0", Q, "    facts: dict = {\"memory_writes\": None, \"held_out_seen\": None}", "    facts: dict = {\"memory_writes\": [], \"held_out_seen\": 0}", "EventFactsTest")
mutant("A:M13 MultiEdit not a write", Q, "MEMORY_TOOLS = (\"Write\", \"Edit\", \"MultiEdit\")", "MEMORY_TOOLS = (\"Write\", \"Edit\")", "EventFactsTest")
mutant("A:M14 memory regex no boundary", Q, "memory(?:/|$)\")", "memory)\")", "EventFactsTest")
mutant("A:M15 reap the whole output folder", Q, "block[\"left_behind\"] = listeners.reap(folder)", "block[\"left_behind\"] = listeners.reap(out)", "QualityReapTest MeasureBlockTest")
mutant("A:M16 an earlier copy reused", Q, "        shutil.rmtree(folder, ignore_errors=True)  # ours: a regrade's earlier copy", "        pass", "MeasureBlockTest")
mutant("A:M17 acceptance server not ended", Q, "    finally:\n        finish(proc, groups)\n    return {\"observed\": True, \"source\"", "    finally:\n        pass\n    return {\"observed\": True, \"source\"", "AcceptanceRunTest AcceptanceCalibrationTest")
mutant("A:M18 PORT not stripped", Q, "    env = {key: value for key, value in os.environ.items() if key != \"PORT\"}", "    env = dict(os.environ)", "ProcessSafetyTest")
mutant("A:M19 a zero-test baseline accepted", Q, "    if not tests:\n", "    if tests is None:\n", "MutationRunTest")
mutant("A:M20 a red baseline accepted", Q, "    if base[\"returncode\"] != 0:\n        return {\"observed\": False, \"baseline\": baseline, \"reason\": f\"the unmutated copy's test run exited", "    if base[\"returncode\"] not in (0, 1):\n        return {\"observed\": False, \"baseline\": baseline, \"reason\": f\"the unmutated copy's test run exited", "MutationRunTest")
mutant("A:M21 timeouts not counted", Q, "            if result[\"timeout\"]:\n                timeouts += 1\n                row[\"timeout\"] += 1", "            if False:\n                timeouts += 1\n                row[\"timeout\"] += 1", "ProcessSafetyTest MutationRunTest")
mutant("A:M22 test-file pattern loses -test", Q, "(?:\\.(?:test|spec)|[-_]test)", "(?:\\.(?:test|spec))", "MutationRunTest")
mutant("A:M23 E2E_CHECKS marker dropped", Q, "    names = {\"E2E_CHECKS\", ", "    names = {", "EventFactsTest")
mutant("A:M24 coverage path check loosened", Q, "                if place.startswith(real + os.sep):", "                if place.startswith(real):", "MutationRunTest")
mutant("A:M25 mixed_host always false", Q, "    return runrecord.hosts_used(out), runrecord.mixed_host(out), None", "    return runrecord.hosts_used(out), False, None", "MeasureBlockTest")
mutant("A:R01 gate: engine active ignored", R, "    if engine.get(\"status\") == \"active\":\n        return f\"ShipLoop is still active", "    if False:\n        return f\"ShipLoop is still active", "QualityGateTest")
mutant("A:R02 gate: stop file ignored", R, "process.get(\"status\") == \"stopped\" or stop_file.exists():", "process.get(\"status\") == \"stopped\":", "QualityGateTest")
mutant("A:R03 gate: lock ignored", R, "    if not lock_held:\n        return (\"this harness", "    if False:\n        return (\"this harness", "QualityGateTest")
mutant("A:R04 no first result write", R, "    (out / \"result.json\").write_text(json.dumps(result, indent=2) + \"\\n\")\n    exported = review_export(out)", "    exported = review_export(out)", "QualityThroughMainTest")
mutant("A:R05 phase groups not live", R, "groups=LIVE_HOST_GROUPS, stop=lambda: quality_stop(stop_file))", "groups=set(), stop=lambda: quality_stop(stop_file))", "QualityThroughMainTest")
mutant("A:R06 quality_stop ignores TERMINATION", R, "return stop_cause(stop_file) if TERMINATION.is_set() or stop_file.exists() else None", "return stop_cause(stop_file) if stop_file.exists() else None", "QualityGateTest")
mutant("A:R07 resume any mode", R, "    if requested is not None and requested != recorded:", "    if False:", "PlanningReviewOptionTest")
mutant("A:R08 none without the card allowed", R, "    if planning_review == \"none\" and not improve_card(plugin_dir).is_file():", "    if False:", "PlanningReviewOptionTest")
mutant("A:R09 hosts from the flag", Q, "    return runrecord.hosts_used(out), runrecord.mixed_host(out), None", "    return [\"claude\"], False, None", "MeasureBlockTest QualityThroughMainTest")
mutant("A:R10 the none sentence omits the card (the stage sentence no longer exists)", R, "    return f\"Start ShipLoop with the run option --planning-review none and --improve-skill {improve_skill}.\"", "    return \"Start ShipLoop with the run option --planning-review none.\"", "PlanningReviewOptionTest")
mutant("A:R11 a custom run measured by battleship", R, "case_quality(name) if name != \"custom\" else {}", "case_quality(name if name != \"custom\" else \"battleship\")", "QualityThroughMainTest")
mutant("A:R12 gate: committed ignored", R, "    if not committed.get(\"pass\"):\n        return \"the returned", "    if False:\n        return \"the returned", "QualityGateTest")
mutant("A:R13 the followed case outranks the case's own declaration (acceptance lists no longer concatenate)", R, "    found = {key: own.get(key) or earlier.get(key) for key in", "    found = {key: earlier.get(key) or own.get(key) for key in", "CaseQualityTest")
mutant("A:M14b memory regex needs no slash", Q, "memory(?:/|$)\")", "memory\")", "EventFactsTest")
mutant("A:M26 memory read for every host", Q, "    elif \"claude\" in hosts_used:\n", "    elif True:\n", "EventFactsTest")
mutant("A:M28 acceptance ignores the stop", Q, "            why = stop()\n            if why:\n                return {\"observed\": False, \"reason\": f\"{why}: the held-out checks", "            why = None\n            if why:\n                return {\"observed\": False, \"reason\": f\"{why}: the held-out checks", "AcceptanceRunTest")
mutant("A:M30 acceptance server not given PORT", Q, "child_env({\"PORT\": str(port), **guard})", "child_env(guard)", "AcceptanceRunTest AcceptanceCalibrationTest")
mutant("A:M31 baseline coverage env dropped", Q, "run_tests(\"baseline\", catalog.coverage_env(coverage))", "run_tests(\"baseline\")", "MutationNodeTest")
mutant("A:M32 an unparseable mutant is run as if valid", Q, "                if syntax[\"returncode\"] != 0:\n                    invalid += 1\n                    row[\"invalid\"] += 1\n                    continue\n", "                if syntax[\"returncode\"] != 0:\n                    pass\n", "MutationRunTest")
mutant("A:R14 the seed-at refusal removed", R, "    if args.planning_review and args.seed_at:\n        raise SystemExit", "    if False:\n        raise SystemExit", "PlanningReviewOptionTest")
mutant("A:R15 the phase's error fails closed", R, "    except Exception as exc:\n        return quality.failed_block(out, spec, exc)", "    except ZeroDivisionError as exc:\n        return quality.failed_block(out, spec, exc)", "QualityThroughMainTest")
mutant("A:R16 no second result write", R, "    (out / \"result.json\").write_text(json.dumps(result, indent=2) + \"\\n\")\n    print(f\"  quality   ", "    print(f\"  quality   ", "QualityThroughMainTest")
mutant("A:R17 the stage option appends the sentence", R, "    if planning_review == \"none\" and not resumed:\n        # The run option rides", "    if planning_review and not resumed:\n        # The run option rides", "PlanningReviewOptionTest")


def main():
    tree, out, only = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    results = []
    for ident, rel, old, new, selectors in MUTANTS:
        if only and not any(ident.startswith(o) for o in only):
            continue
        path = tree / rel
        text = path.read_text()
        if text.count(old) != 1:
            results.append({"id": ident, "error": f"the text to replace matches {text.count(old)} times"})
            print(ident, "NO MATCH", flush=True)
            continue
        path.write_text(text.replace(old, new, 1))
        began = time.time()
        try:
            done = subprocess.run([sys.executable, "-B", "test/shiploop-e2e-quality.test.py", *selectors.split()], cwd=tree, capture_output=True,
                                  text=True, timeout=600, env={**os.environ, "SHIPLOOP_PROGRESS": "off", "PYTHONDONTWRITEBYTECODE": "1"})
            failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\S+)", done.stderr, re.M)))
            verdict = "caught" if done.returncode else ("equivalent" if ident in EQUIVALENT else "SURVIVED")
            row = {"id": ident, "verdict": verdict, "failing_tests": failed[:6], "seconds": round(time.time() - began)}
        except subprocess.TimeoutExpired:
            row = {"id": ident, "verdict": "caught", "failing_tests": ["(the run hung and was ended by the runner's 600 s limit)"], "seconds": 600}
        finally:
            path.write_text(text)
        results.append(row)
        print(row["id"], row["verdict"], row["failing_tests"][:2], flush=True)
    out.write_text(json.dumps(results, indent=1) + "\n")
    print("caught", sum(r.get("verdict") == "caught" for r in results), "equivalent", sum(r.get("verdict") == "equivalent" for r in results),
          "SURVIVED", [r["id"] for r in results if r.get("verdict") == "SURVIVED" or "error" in r])


if __name__ == "__main__":
    main()
