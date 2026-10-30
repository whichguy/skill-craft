#!/usr/bin/env python3
"""Qualified iteration (SPEC promotion contract, added 2026-10-30): one learning record, one candidate, one decision.
The loop tip, the last promoted commit of the loop branch, advances only on PROMOTE.

One cycle (``qualify``), in a worktree whose HEAD is the loop tip:

  1. improve  the improver applies the one record (``learning_records.improver_view``) in one commit carrying a
              ``Learning-Record:`` trailer, and returns a prediction (prediction.py)
  2. purpose  purpose_check.py: the script part, then the fresh review; ``extra`` gets one retry, anything else
              rejects the candidate before any run
  3. build    the tip's and the candidate's plugins (scripts/build-packages.py), bound by their tree digests
  4. register a promotion/5 epoch: the exposing case and a case of another style, attempts and tolerance from an
              A/A calibration (spread.py) whose scoring digest still matches, efficiency on tokens
  5. run      every attempt, at most ``--parallel`` at once, each its own ``epoch.py launch`` process; then each
              attempt's review and judgment; then ``decide``
  6. apply    PROMOTE keeps the candidate as the tip; DROP or UNDECIDED keeps it as
              ``refs/shiploop-loop/<loop>/<record>`` and resets the worktree to the tip (the loop branch is the
              session's own and unpublished; a revert would add and delete a pending change note)
  7. record   the prediction's verdict and the record's outcome (learning-records.jsonl), and a LEARNINGS entry,
              committed after any ShipLoop commit so the release preflight's ancestry rule holds

A review of the generality case's attempts is exposure of a confirmation case: its findings open records marked
``exposure: confirmation``, which ``learning_records.select`` never offers the improver.

``loop`` repeats cycles (``iterate.py --qualify``): a record from ``learning_records.select``, or an exploration run
of the exposing case on the tip when none is admitted. It stops at ``--iterations``, when no record is admitted after
exploring, after two cycles in a row without PROMOTE (owner decision D3 may change this), or when the evaluator changed.

``--candidate-plugin`` runs steps 3 to 7 for a candidate built by hand (the stage 4 pilot): no improver, no purpose
check, no git; the entry is written to the output folder for its author to commit.

    python3 test/shiploop_e2e/iterate.py --qualify --case user-listing --generality-case battleship \\
        --calibration calibration.json --iterations 3
    python3 test/shiploop_e2e/cycle.py --record LR-... --case user-listing --generality-case battleship \\
        --calibration calibration.json --control-plugin DIR --candidate-plugin DIR --prediction P.json --output OUT
"""

from __future__ import annotations

import argparse
import datetime
import json
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402
import epoch  # noqa: E402
import hosts  # noqa: E402
import learning_records  # noqa: E402
import prediction as predictions  # noqa: E402
import purpose_check  # noqa: E402
import spread  # noqa: E402

CONTRACT = "shiploop-cycle/1"
JOURNAL = Path("test", "shiploop_e2e", "LEARNINGS.md")  # relative to the worktree
NON_PROMOTE_STOP = 2  # cycles in a row without PROMOTE before the loop stops (D3 proposal)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def load_calibration(path: Path, cases: list[str]) -> dict:
    """attempts and tolerance from an A/A calibration, refused when it did not calibrate a case, cannot decide its
    metric, or was scored by other scoring files than this checkout's."""
    calibration = json.loads(path.read_text())
    if calibration.get("contract") != spread.CONTRACT:
        raise ValueError(f"{path} is not a {spread.CONTRACT} report")
    missing = [case for case in cases if case not in (calibration.get("cases") or {})]
    if missing:
        raise ValueError("the calibration did not calibrate " + ", ".join(missing))
    catalog = json.loads((HERE / "cases.json").read_text())
    calibrated = calibration["scoring"]["cases"]
    now = spread.scoring_digest({name: catalog[name] for name in calibrated})
    if now["sha256"] != calibration["scoring"]["sha256"]:
        raise ValueError("the scoring files or case entries changed since the calibration: calibrate again")
    recommended = calibration["recommended"]
    if recommended.get("tolerance") is None:
        raise ValueError(f"the calibration cannot decide {recommended.get('metric')} at {recommended.get('attempts')} "
                         f"attempts: {recommended.get('why')}")
    return {"attempts": recommended["attempts"], "tolerance": recommended["tolerance"],
            "metric": recommended["metric"], "sha256": now["sha256"]}


def registration_template(cases: dict[str, str], control: str, candidate: str, driver: dict, attempts: int,
                          tolerance: float, metric: str, budget: dict | None = None) -> dict:
    """A promotion/5 product_change registration: `cases` maps each case to its role."""
    rows = [{"id": f"{arm}-{case}-{n}", "arm": arm, "case": case}
            for case in cases for arm in ("control", "candidate") for n in range(1, attempts + 1)]
    return {"contract": "promotion/5", "purpose": "product_change",
            "cases": {case: {"role": role, "attempts": attempts} for case, role in cases.items()},
            "arms": {"control": {"shiploop_build": control, "driver": driver},
                     "candidate": {"shiploop_build": candidate, "driver": driver}},
            "attempts": rows, "efficiency": [metric], "tolerance": tolerance, "budget": budget or {}}


def roles_for(prediction: dict, exposing: str, generality: str | None) -> dict[str, str]:
    """A case is a capability case only when the prediction says one of its floors rises; otherwise its quality is an
    established requirement that must not fall."""
    rises = {effect["case"] for effect in prediction["effects"]
             if predictions.kind(effect["measure"]) == "floor" and effect["direction"] == "up"}
    cases = [exposing] + ([generality] if generality and generality != exposing else [])
    return {case: "capability" if case in rises else "regression" for case in cases}


def launch_all(root: Path, plugins: dict[str, Path], parallel: int, logs: Path) -> list[str]:
    """Launch ready attempts, at most `parallel` at once, each in its own epoch.py process.

    Attempts for one declared platform target wait for the prior run's sealed clean cleanup. Attempts that stay blocked
    after unrelated work finishes remain undispatched and have the reason written to their launch log. The return value
    remains the IDs of processes that exited unsuccessfully.
    """
    logs.mkdir(parents=True, exist_ok=True)
    pending = [row for row in epoch.state(root)["attempts"] if row["status"] == "not_launched"]
    reg = epoch.registration(root)
    targets: dict[str, tuple[str | None, str | None]] = {}
    running: list[tuple[str, str | None, subprocess.Popen]] = []
    active_targets: dict[str, str] = {}
    failed = []
    while pending or running:
        while pending and len(running) < parallel:
            ledger_rows = epoch.events(root)
            reasons = {}
            selected = None
            for index, row in enumerate(pending):
                key, problem = epoch.target_launch_state(root, row["id"], reg=reg, rows=ledger_rows, targets=targets)
                if problem:
                    reasons[row["id"]] = problem
                    continue
                if key is not None and key in active_targets:
                    reasons[row["id"]] = f"platform target {key} is active for {active_targets[key]}"
                    continue
                selected = (index, row, key)
                break
            if selected is None:
                if not running:
                    for row in pending:
                        reason = reasons.get(row["id"]) or "platform target state is unresolved"
                        with (logs / f"{row['id']}.log").open("a") as log:
                            log.write(f"launch blocked: {reason}\n")
                    pending.clear()
                break
            index, row, key = selected
            pending.pop(index)
            command = [sys.executable, "-B", str(HERE / "epoch.py"), "launch", "--output", str(root),
                       "--attempt", row["id"], "--plugin-dir", str(plugins[row["arm"]])]
            with (logs / f"{row['id']}.log").open("w") as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL)
            running.append((row["id"], key, process))
            if key is not None:
                active_targets[key] = row["id"]
            time.sleep(2)  # distinct run starts: promotion refuses two attempts with the same start
        for attempt, key, process in list(running):
            if process.poll() is not None:
                running.remove((attempt, key, process))
                if key is not None and active_targets.get(key) == attempt:
                    del active_targets[key]
                if process.returncode != 0:
                    failed.append(attempt)
        if running:
            time.sleep(5)
    return failed


def review_all(root: Path, ledger: Path, generality: str | None) -> list[str]:
    """Review and judge every sealed attempt; their material discoveries become learning records."""
    opened = []
    for row in epoch.state(root)["attempts"]:
        if row["status"] != "recorded":
            continue
        with epoch.locked(root, epoch.INTENT_WAIT):
            event = epoch.review_attempt(root, row["id"], records=learning_records.reviewer_view(ledger))
        receipt = json.loads((root / event["receipt"]).read_text())
        exposure = "confirmation" if row["case"] == generality else "development"
        opened += learning_records.ingest(receipt["review"], receipt["routes"], {
            "epoch": str(root), "attempt": row["id"], "case": row["case"], "exposure": exposure,
            "review_sha256": (receipt.get("judge") or {}).get("review_sha256")}, ledger)
    return opened


def qualify_built(root: Path, record: str, prediction_file: Path, control_plugin: Path, candidate_plugin: Path,
                  cases: dict[str, str], driver: dict, calibration: dict, args, ledger: Path,
                  candidate_ref: str | None = None) -> dict:
    """Steps 3 to 7's measured part: register, run, review, decide, and the prediction's verdict."""
    import run as runner
    control, candidate = runner.tree_digest(control_plugin), runner.tree_digest(candidate_plugin)
    if not control or not candidate:
        raise ValueError("a plugin tree cannot be digested")
    if control == candidate:
        raise ValueError("the candidate's build is the control's: there is nothing to compare")
    template = root.parent / f"{root.name}-registration.json"
    template.write_text(json.dumps(registration_template(cases, control, candidate, driver, calibration["attempts"],
                                                         calibration["tolerance"], calibration["metric"],
                                                         getattr(args, "budget", None)), indent=2) + "\n")
    epoch.initialise(root, template, prediction_file)
    predicted = epoch.state(root)["prediction"]
    learning_records.append("predicted", record, ledger, prediction=predicted, candidate=candidate_ref or candidate,
                            epoch=str(root))
    launch_logs = root.parent / f"{root.name}-launch-logs"
    failed = launch_all(root, {"control": control_plugin, "candidate": candidate_plugin}, args.parallel, launch_logs)
    unknown = [row["id"] for row in epoch.state(root)["attempts"] if row["status"] in ("unknown_launch", "not_launched")]
    if unknown:
        target_blocks = []
        blocked_ids = set()
        for attempt in unknown:
            try:
                lines = (launch_logs / f"{attempt}.log").read_text().splitlines()
            except OSError:
                continue
            for line in lines:
                if line.startswith("launch blocked: "):
                    blocked_ids.add(attempt)
                    target_blocks.append(f"{attempt}: {line.removeprefix('launch blocked: ').strip()}")
        details = []
        if target_blocks:
            details.append("target blocks: " + "; ".join(target_blocks))
        process_failures = [attempt for attempt in failed if attempt not in blocked_ids]
        details.append("launch failures: " + (", ".join(process_failures) or "none"))
        return {"decision": "UNKNOWN_LAUNCH", "reasons": [f"attempts not sealed: {', '.join(unknown)} ({'; '.join(details)}); "
                "reconcile them, never retry"], "opened": [],
                "control_build": control, "candidate_build": candidate}
    opened = [] if args.skip_reviews else review_all(root, ledger, cases_generality(cases, args))
    with epoch.locked(root, epoch.INTENT_WAIT):
        decided = epoch.decide(root)
    registration, predicted, control_cards, candidate_cards = predictions._epoch_cards(root)
    judged = predictions.verdict(predicted, registration, control_cards, candidate_cards)
    (root.parent / f"{root.name}-verdict.json").write_text(json.dumps(judged, indent=2) + "\n")
    after = predictions.outcome(decided["decision"], judged, decided.get("reasons"))
    learning_records.append("decided", record, ledger, decision=decided["decision"], reasons=decided.get("reasons"),
                            epoch=str(root))
    learning_records.append("verdict", record, ledger, verdict=judged["verdict"], **after)
    return {"decision": decided["decision"], "reasons": decided.get("reasons"), "verdict": judged, "outcome": after,
            "opened": opened, "control_build": control, "candidate_build": candidate}


def cases_generality(cases: dict[str, str], args) -> str | None:
    return getattr(args, "generality_case", None) if getattr(args, "generality_case", None) in cases else None


def one_record_prompt(worktree: Path, record: dict, base: str, cases: list[str], calibration: dict) -> str:
    import iterate
    import review as reviewer
    finding = {"title": record["title"], "proposal": record.get("proposal"), "files": record.get("files"),
               "mission_anchor": record.get("anchor"), "materiality": "material",
               "next_experiment": record.get("next_experiment"), "implementation_eligible": True}
    return iterate.improver_prompt(worktree, [finding], base, reviewer.last_commit_messages(worktree)) + f"""
This candidate applies exactly one learning record, {record['record']}, and nothing else: no refactor, rename or fix
of anything the record does not need. Make one commit. Its message's final paragraph carries the trailer
`Learning-Record: {record['record']}` on its own line beside Co-Authored-By.

Add a "prediction" key to the JSON object you end with: what this change will measurably move, registered before its
runs (SPEC mission clause, Learning records and predictions):
{{"contract": "{predictions.CONTRACT}", "record": "{record['record']}", "anchor": "the clause it serves",
 "because": "one sentence: why this change moves this measure",
 "effects": [{{"case": one of {json.dumps(cases)}, "measure": "tokens|turns|minutes|output_tokens|cost_usd|accuracy|fidelity|a dotted scorecard path such as efficiency.refusals", "direction": "up|down", "at_least": number}}],
 "guards": [{{"case": "*", "measure": "accuracy", "direction": "not_down"}}]}}
An efficiency effect's at_least is a relative change of at least {calibration['tolerance']} (smaller cannot be resolved
at {calibration['attempts']} attempts per arm). "No worse" alone is not a prediction. Predict what this change does,
not what any change would do.
"""


def entry(record: dict, result: dict, setup: dict) -> str:
    """The LEARNINGS entry for one cycle, in the journal's Question / Setup / Result / What it shows shape."""
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    judged = result.get("verdict") or {}
    lines = [f"## Qualified cycle: {record['record']} on {', '.join(setup['cases'])} — {result['decision']}, "
             f"prediction {judged.get('verdict', 'not judged')} ({day})", "",
             f"**Question.** {record.get('title')} ({learning_records._anchor_text(record.get('anchor'))}). "
             f"Does the candidate move what it predicted?", "",
             f"**Setup.** Loop tip {setup.get('tip') or setup['control_build']}, candidate "
             f"{setup.get('candidate') or setup['candidate_build']}; driver {setup['driver']}; "
             f"{setup['attempts']} attempts per arm, tolerance {setup['tolerance']} on {setup['metric']} "
             f"(calibration {setup['calibration']}); epoch {setup['epoch']}. Cases: "
             + ", ".join(f"{case} ({role})" for case, role in setup["roles"].items()) + ".", ""]
    if judged.get("effects"):
        lines += ["**Result.**", "", "| case | measure | control | candidate | change | predicted | verdict |",
                  "|---|---|---|---|---|---|---|"]
        for row in judged["effects"]:
            lines.append(f"| {row['case']} | {row['measure']} | {row.get('control')} | {row.get('candidate')} | "
                         f"{row.get('change', row.get('unknown'))} | {row['direction']} {row['at_least']} | {row['verdict']} |")
        for row in judged.get("guards") or []:
            lines.append(f"| {row['case']} | {row['measure']} (guard) | {row.get('control')} | {row.get('candidate')} | "
                         f"{row.get('change', row.get('unknown'))} | {row['direction']} | "
                         f"{'held' if row['held'] else 'broken' if row['held'] is False else 'unknown'} |")
        lines.append("")
    lines += [f"**What it shows.** Decision {result['decision']}: {'; '.join(result.get('reasons') or []) or 'no reasons given'}.",
              f"Prediction {judged.get('verdict', 'not judged')}; the record is now "
              f"{(result.get('outcome') or {}).get('outcome', 'unchanged')}"
              f" ({(result.get('outcome') or {}).get('reason', '')}).",
              setup.get("tip_note", ""), ""]
    if result.get("opened"):
        lines += ["Records opened by this cycle's reviews: " + ", ".join(result["opened"]) + ".", ""]
    return "\n".join(line for line in lines if line is not None) + "\n"


def apply_decision(worktree: Path, loop: str, record: str, tip: str, candidate: str, decision: str) -> str:
    """PROMOTE keeps the candidate as the tip; anything else keeps it as a ref and resets the worktree to the tip.

    The learning records appended during the cycle are not committed yet: they are carried across the reset."""
    if decision == "PROMOTE":
        return f"The loop tip advanced to {candidate[:8]}."
    ref = f"refs/shiploop-loop/{loop}/{record}"
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    kept = ledger.read_bytes() if ledger.is_file() else None
    _git(worktree, "update-ref", ref, candidate)
    _git(worktree, "reset", "-q", "--hard", tip)
    if kept is not None:
        ledger.write_bytes(kept)
    return f"The candidate is kept as {ref}; the loop tip stays at {tip[:8]}."


def commit_entry(worktree: Path, text: str, record: str, decision: str, verdict: str, stage: Path) -> str:
    journal = worktree / JOURNAL
    with journal.open("a") as out:
        out.write("\n" + text)
    message = (f"test(e2e): qualified cycle for {record}: {decision}, prediction {verdict}\n\n{text}\n"
               "Co-Authored-By: ShipLoop E2E harness <shiploop-e2e@example.invalid>\n")
    (stage / "learnings-commit.txt").write_text(message)
    _git(worktree, "add", JOURNAL.as_posix(), f"test/shiploop_e2e/{learning_records.LEDGER.name}")
    _git(worktree, "commit", "-q", "-F", str(stage / "learnings-commit.txt"))
    return _git(worktree, "rev-parse", "--short", "HEAD")


def build(worktree: Path, out: Path) -> Path:
    subprocess.run([sys.executable, "-B", str(worktree / "scripts" / "build-packages.py"), str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    return out / "plugins" / "skill-craft"


def qualify(worktree: Path, loop: str, record_id: str, stage: Path, args, calibration: dict) -> dict:
    """One improver cycle in the worktree (HEAD is the loop tip); see the module docstring."""
    import iterate
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    record = learning_records.improver_view(record_id, ledger)
    tip = _git(worktree, "rev-parse", "HEAD")
    stage.mkdir(parents=True)
    control_plugin = build(worktree, stage / "control-build")  # the tip, before the improver changes anything
    cases = [args.case] + ([args.generality_case] if args.generality_case else [])
    prompt = one_record_prompt(worktree, record, tip, cases, calibration)
    change = iterate.improve(worktree, [], stage / "improve", args, prompt=prompt)
    crossed = iterate.boundary_crossing(change)
    if crossed or change["out_of_scope"] or change["uncommitted"] or not change["commits"]:
        _git(worktree, "reset", "-q", "--hard", tip)
        why = crossed or ("out of scope or uncommitted work" if change["commits"] else "the improver committed nothing")
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=f"no usable candidate: {why}")
        return {"decision": "NO_CANDIDATE", "reasons": [why], "stop": bool(crossed)}
    reviewed, verdict = None, None
    predicted = (change["report"] or {}).get("prediction")
    for attempt in (1, 2):
        head = _git(worktree, "rev-parse", "HEAD")
        script = purpose_check.script_check(worktree, tip, head, record_id, record.get("files"))
        reviewed = None if not script["passed"] else purpose_check.review(
            worktree, tip, head, record, predicted, stage / f"purpose-{attempt}", codex_bin=getattr(args, "codex_bin", "codex"))
        verdict = purpose_check.decide(script, reviewed)
        (stage / f"purpose-{attempt}.json").write_text(json.dumps({"script": script, "review": reviewed,
                                                                   "decision": verdict}, indent=2) + "\n")
        if verdict["result"] != "retry" or attempt == 2:
            break
        retry = (prompt + "\n\nThe purpose review found changes that do not serve this record. Remove them in a further "
                 "commit with the same trailer, and change nothing else:\n- " + "\n- ".join(verdict["reasons"]))
        change = iterate.improve(worktree, [], stage / "improve-retry", args, prompt=retry)
        predicted = (change["report"] or {}).get("prediction") or predicted
    candidate_sha = _git(worktree, "rev-parse", "HEAD")
    if verdict["result"] != "passed":
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REJECTED")
        learning_records.append("rejected_at_purpose", record_id, ledger, reason="; ".join(verdict["reasons"])[:500])
        return {"decision": "REJECTED_AT_PURPOSE", "reasons": verdict["reasons"], "tip_note": note}
    prediction_file = stage / "prediction.json"
    prediction_file.write_text(json.dumps(predicted, indent=2) + "\n")
    try:
        roles = roles_for(predicted, args.case, args.generality_case)
    except (KeyError, TypeError, ValueError) as error:
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REJECTED")
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=f"no usable prediction: {error}")
        return {"decision": "NO_PREDICTION", "reasons": [str(error)], "tip_note": note}
    candidate_plugin = build(worktree, stage / "candidate-build")
    driver = hosts.resolve_role("subject", {"host": args.host, "model": args.model, "effort": args.effort})
    driver = {key: driver[key] for key in ("host", "model", "effort")}
    try:
        result = qualify_built(stage / "epoch", record_id, prediction_file, control_plugin, candidate_plugin, roles,
                               driver, calibration, args, ledger, candidate_sha)
    except ValueError as error:
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REFUSED")
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=f"registration refused: {error}")
        return {"decision": "REFUSED", "reasons": [str(error)], "tip_note": note}
    note = apply_decision(worktree, loop, record_id, tip, candidate_sha,
                          result["decision"] if result["decision"] == "PROMOTE" else "KEEP_AS_REF")
    setup = {"cases": list(roles), "roles": roles, "tip": tip[:8], "candidate": candidate_sha[:8],
             "control_build": result["control_build"], "candidate_build": result["candidate_build"],
             "driver": f"{driver['host']} {driver['model']} {driver['effort']}", "attempts": calibration["attempts"],
             "tolerance": calibration["tolerance"], "metric": calibration["metric"],
             "calibration": calibration["sha256"][:12], "epoch": str(stage / "epoch"), "tip_note": note}
    result["tip_note"] = note
    result["learnings_commit"] = commit_entry(worktree, entry({"record": record_id, **record}, result, setup), record_id,
                                              result["decision"], (result.get("verdict") or {}).get("verdict", "not judged"),
                                              stage)
    (stage / "cycle-result.json").write_text(json.dumps({"contract": CONTRACT, **result}, indent=2, default=str) + "\n")
    return result


def explore(worktree: Path, stage: Path, args) -> list[str]:
    """One exploration run of the exposing case on the tip, reviewed and judged; returns the records it opened."""
    import iterate
    import judge
    import review as reviewer
    import run as runner
    plugin = build(worktree, stage / "build")
    runner.main(["--case", args.case, "--host", args.host, "--output", str(stage / "run"), "--plugin-dir", str(plugin),
                 "--permission-mode", args.permission_mode,
                 *(["--model", args.model] if args.model else []), *(["--effort", args.effort] if args.effort else [])])
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    verdict = reviewer.review(stage / "run", **iterate.role_profile(args, "reviewer"),
                              skill_root=worktree / "skills" / "shiploop",
                              prior_learnings=reviewer.last_commit_messages(worktree),
                              records=learning_records.reviewer_view(ledger))
    if not (verdict.get("validity") or {}).get("discovery_qualified"):
        return []
    judged = judge.judge(stage / "run", verdict, **iterate.role_profile(args, "judge"))
    routes = judge.admitted(verdict, judged)
    opened = learning_records.ingest(verdict, routes, {"run": str(stage / "run"), "case": args.case,
                                                       "review_sha256": judged.get("review_sha256"),
                                                       "exposure": "development"}, ledger)
    result = json.loads((stage / "run" / "result.json").read_text())
    verdict["judge"], verdict["actionable"], verdict["learning_records"] = judged, routes["implementation"], opened
    sha = _git(worktree, "rev-parse", "HEAD")
    iterate.record_learnings(worktree, iterate.learnings_message(0, args, sha, result, verdict, []), stage)
    return opened


def loop(args) -> int:
    """`iterate.py --qualify`: qualified cycles in a new worktree from HEAD; see the module docstring."""
    import iterate
    if not args.calibration:
        raise SystemExit("--qualify needs --calibration (spread.py's report of an A/A epoch)")
    cases = [args.case] + ([args.generality_case] if args.generality_case else [])
    calibration = load_calibration(args.calibration, cases)
    name = f"shiploop-loop-{secrets.token_hex(3)}"
    out = (args.output or Path(tempfile.gettempdir()) / "shiploop-e2e" / name).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    worktree, branch = iterate.new_worktree(name)
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    frozen = boundary.qualification_snapshot(HERE, cases)
    journal = out / "LOOP.md"
    iterate.journal(journal, [f"# Qualified loop: {', '.join(cases)}", "", f"- worktree {worktree}, branch {branch}",
                              f"- calibration {args.calibration}: {calibration['attempts']} attempts per arm, "
                              f"tolerance {calibration['tolerance']} on {calibration['metric']}"])
    stop, misses = f"reached --iterations {args.iterations}", 0
    for index in range(1, args.iterations + 1):
        if boundary.qualification_snapshot(HERE, cases) != frozen:
            stop = "the evaluator changed: start a new loop"
            break
        record = learning_records.select(ledger)
        if record is None:
            opened = explore(worktree, out / f"explore-{index}", args)
            iterate.journal(journal, [f"## Exploration {index}", "", f"- records opened: {', '.join(opened) or 'none'}"])
            record = learning_records.select(ledger)
            if record is None:
                stop = "no admitted learning record after exploring"
                break
        result = qualify(worktree, name, record, out / f"cycle-{index}", args, calibration)
        iterate.journal(journal, [f"## Cycle {index}: {record}", "", f"- decision: {result['decision']}",
                                  f"- reasons: {'; '.join(result.get('reasons') or [])}",
                                  f"- {result.get('tip_note', '')}"])
        if result.get("stop"):
            stop = "; ".join(result.get("reasons") or ["the improver crossed the evaluator boundary"])
            break
        misses = 0 if result["decision"] == "PROMOTE" else misses + 1
        if misses >= NON_PROMOTE_STOP:
            stop = f"{misses} cycles in a row without PROMOTE"
            break
    iterate.journal(journal, ["## Result", "", f"- stopped: {stop}", f"- branch {branch}: review it, merge it, then "
                              "scripts/release.py; nothing was published"])
    print(f"cycle: {stop}\n  journal: {journal}\n  branch:  {branch}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """A hand-built candidate (the stage 4 pilot): steps 3 to 7 without an improver, a purpose check or git."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", required=True)
    parser.add_argument("--case", required=True, help="the exposing case")
    parser.add_argument("--generality-case", help="a case of another style; omitted, the claim covers one style")
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--control-plugin", type=Path, required=True)
    parser.add_argument("--candidate-plugin", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="a new folder outside the checkout")
    parser.add_argument("--host", default=hosts.RUN_DEFAULT_HOST)
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--skip-reviews", action="store_true",
                        help="no review or judgment: the decision can then only DROP or stay UNDECIDED")
    parser.add_argument("--ledger", type=Path, default=learning_records.LEDGER)
    args = parser.parse_args(argv)
    out = args.output.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error(f"output must be outside the checkout: {out}")
    try:
        cases = [args.case] + ([args.generality_case] if args.generality_case else [])
        calibration = load_calibration(args.calibration, cases)
        record = learning_records.improver_view(args.record, args.ledger)
        predicted = json.loads(args.prediction.read_text())
        roles = roles_for(predicted, args.case, args.generality_case)
        driver = hosts.resolve_role("subject", {"host": args.host, "model": args.model, "effort": args.effort})
        driver = {key: driver[key] for key in ("host", "model", "effort")}
        out.mkdir(parents=True, exist_ok=False)
        result = qualify_built(out / "epoch", args.record, args.prediction, args.control_plugin, args.candidate_plugin,
                               roles, driver, calibration, args, args.ledger)
    except (OSError, ValueError, KeyError) as error:
        print(f"cycle: {error}", file=sys.stderr)
        return 1
    setup = {"cases": list(roles), "roles": roles, "control_build": result.get("control_build"),
             "candidate_build": result.get("candidate_build"),
             "driver": f"{driver['host']} {driver['model']} {driver['effort']}", "attempts": calibration["attempts"],
             "tolerance": calibration["tolerance"], "metric": calibration["metric"],
             "calibration": calibration["sha256"][:12], "epoch": str(out / "epoch"),
             "tip_note": "A hand-built candidate: nothing on a loop branch moved."}
    (out / "entry.md").write_text(entry({"record": args.record, **record}, result, setup))
    (out / "cycle-result.json").write_text(json.dumps({"contract": CONTRACT, **result}, indent=2, default=str) + "\n")
    print(json.dumps({"decision": result["decision"], "verdict": (result.get("verdict") or {}).get("verdict"),
                      "outcome": result.get("outcome"), "entry": str(out / "entry.md")}, indent=2))
    return promotion_exit(result["decision"])


def promotion_exit(decision: str) -> int:
    import promotion
    return promotion.EXIT.get(decision, 1)


if __name__ == "__main__":
    raise SystemExit(main())
