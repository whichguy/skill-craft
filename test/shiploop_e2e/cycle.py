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
              A/A calibration (spread.py) whose scoring digest still matches, or, with no measurement, stated by
              the owner with ``--tolerance`` and ``--attempts`` and recorded everywhere as unmeasured; efficiency
              on tokens
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
    python3 test/shiploop_e2e/iterate.py --qualify --case user-listing --tolerance 0.25 --attempts 3   # unmeasured
    python3 test/shiploop_e2e/cycle.py --record LR-... --case user-listing --generality-case battleship \\
        --calibration calibration.json --control-plugin DIR --candidate-plugin DIR --prediction P.json --output OUT
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import secrets
import subprocess
import sys
import tempfile
import time
import traceback
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


class RegistrationRefused(ValueError):
    """A registration was refused before any product attempt could run."""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def candidate_source(worktree: Path, tip: str, candidate: str) -> dict[str, str]:
    """Keep the full candidate commit message and a stat summary, never its historical patch."""
    message = _git(worktree, "show", "-s", "--format=%B", candidate)
    diff_stat = _git(worktree, "diff", "--stat", f"{tip}..{candidate}") or "(no file changes)"
    return {"message": message, "diff_stat": diff_stat}


def candidate_source_lines(source: dict[str, str], tip: str, candidate: str, decision: str) -> list[str]:
    """Make the status of the quoted candidate message clear at the point where it is shown."""
    if decision == "PROMOTE":
        label = f"**Promoted candidate source — disposition: {decision} (full commit message; no historical diff).**"
    else:
        label = f"**UNADOPTED PROPOSAL — actual disposition: {decision} (full commit message; no historical diff).**"
    return [label, "", source["message"], "", f"**Candidate diff stat (`{tip}..{candidate}`).**", "",
            source["diff_stat"], ""]


def _durable_write(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(contents)
        handle.flush()
        os.fsync(handle.fileno())


def _interruption_artifact_dir(worktree: Path, stage: Path) -> Path:
    root, requested = worktree.resolve(), stage.resolve()
    if requested == root or root in requested.parents:
        return Path(tempfile.mkdtemp(prefix="shiploop-cycle-interrupted-"))
    requested.mkdir(parents=True, exist_ok=True)
    return requested


def load_calibration(path: Path, cases: list[str]) -> dict:
    """attempts and tolerance from an A/A calibration, refused when it did not calibrate a case, cannot decide its
    metric, was scored by other scoring files than this checkout's, or is not a calibration report at all."""
    try:
        return _load_calibration(path, cases)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"{path} is a malformed calibration report: {error!r}") from None


def _load_calibration(path: Path, cases: list[str]) -> dict:
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
            "metric": recommended["metric"], "sha256": now["sha256"], "measured": True, "basis": now["sha256"]}


UNMEASURED = "stated, not measured"
STATED_METRIC = "tokens"


def stated_calibration(attempts, tolerance, metric: str = STATED_METRIC) -> dict:
    """The attempts per arm and the tolerance the owner states when no calibration was run (owner decision,
    2026-10-31). Nothing measured them: ``measured`` is False and every record, entry and event this cycle writes says
    so, because the rate at which that tolerance calls noise a win or a loss is unknown."""
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("--attempts must be a positive whole number")
    if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance)
            or not 0 < tolerance < 1):
        # A cost cannot fall by 100% or more, so a tolerance of 1 or more could never promote an efficiency change.
        raise ValueError("--tolerance must be a relative change above 0 and below 1 (0.25 is 25%)")
    return {"attempts": attempts, "tolerance": float(tolerance), "metric": metric, "sha256": None, "measured": False,
            "basis": UNMEASURED}


def resolve_calibration(args, cases: list[str]) -> dict:
    """The measured calibration (``--calibration``), or the stated one (``--tolerance`` with ``--attempts``): never
    both, never neither, and never a default, so an unmeasured basis is always a choice someone made."""
    report, tolerance, attempts = (getattr(args, name, None) for name in ("calibration", "tolerance", "attempts"))
    if report is not None:
        if tolerance is not None or attempts is not None:
            raise ValueError("--calibration is the measured basis: do not also pass --tolerance or --attempts")
        return load_calibration(report, cases)
    if tolerance is None or attempts is None:
        raise ValueError("a cycle needs --calibration (spread.py's report of an A/A epoch), or --tolerance and "
                         "--attempts together, which are recorded as unmeasured")
    return stated_calibration(attempts, tolerance)


def calibration_basis(calibration: dict) -> str:
    return calibration.get("basis") or calibration.get("sha256") or "unknown"


def calibration_phrase(basis: str) -> str:
    return f"{UNMEASURED}: the false-decision rate is unknown" if basis == UNMEASURED else f"calibration {basis}"


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
    try:
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
    except ValueError as error:
        raise RegistrationRefused(str(error)) from error
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
    if not calibration.get("measured", True):
        # A verdict under an unmeasured tolerance is real evidence about this comparison and no evidence about how often
        # the tolerance misleads: the record says both.
        after = {**after, "reason": f"{after['reason']} [tolerance and attempts {UNMEASURED}]", "calibration": UNMEASURED}
    learning_records.append("decided", record, ledger, decision=decided["decision"], reasons=decided.get("reasons"),
                            epoch=str(root), calibration=calibration_basis(calibration))
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
    return iterate.improver_prompt(worktree, [finding], base,
                                   reviewer.last_commit_messages(worktree, record_id=record["record"])) + f"""
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
             f"({calibration_phrase(setup['calibration'])}); epoch {setup['epoch']}. Cases: "
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
    source = setup.get("candidate_source")
    if source:
        lines += candidate_source_lines(source, setup["tip"], setup["candidate"], result["decision"])
    lines += [f"**What it shows.** Decision {result['decision']}: {'; '.join(result.get('reasons') or []) or 'no reasons given'}.",
              f"Prediction {judged.get('verdict', 'not judged')}; the record is now "
              f"{(result.get('outcome') or {}).get('outcome', 'unchanged')}"
              f" ({(result.get('outcome') or {}).get('reason', '')}).",
              setup.get("tip_note", ""), ""]
    if result.get("opened"):
        lines += ["Records opened by this cycle's reviews: " + ", ".join(result["opened"]) + ".", ""]
    return "\n".join(line for line in lines if line is not None) + "\n"


def terminal_entry(record: dict | None, decision: str, reason: str, tip: str, candidate: str | None,
                   calibration: dict | None, cases: list[str], note: str,
                   observed_summary: str | None = None, candidate_details: dict | None = None,
                   interrupted: bool = False) -> str:
    """Retain a terminal outcome with cycle or exploration evidence kept distinct."""
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    record_id = record.get("record") if record else None
    title = record.get("title") if record else None
    anchor = learning_records._anchor_text(record.get("anchor")) if record else None
    if record_id:
        heading = f"## Cycle outcome: {record_id} — {decision} ({day})"
        question = (f"**Question.** {title or '(untitled)'} ({anchor}). Why was the cycle interrupted?"
                    if interrupted else
                    f"**Question.** {title or '(untitled)'} ({anchor}). Why did this cycle end before a product comparison?")
    else:
        heading = f"## Invalid review from exploration: {decision} ({day})"
        question = "**Question.** Did this exploration produce a discovery-qualified review?"
    calibration_sha = (calibration or {}).get("sha256") or "not used"
    basis_text = (f"scoring digest `{calibration_sha}`" if (calibration or {}).get("measured", True)
                  else f"{UNMEASURED}: the false-decision rate is unknown")
    candidate_sha = candidate or "none; no candidate commit was available"
    calibration_details = (f"{calibration['attempts']} attempts per arm, tolerance {calibration['tolerance']} "
                           f"on {calibration['metric']} ({basis_text})"
                           if calibration else "not used; no product comparison was registered")
    if observed_summary is None:
        observed_summary = ("unknown: exploration result.json was missing or malformed" if record is None else
                            "not applicable: the cycle ended before product runs")
    lines = [
        heading, "", question, "",
        f"**Setup.** Loop tip commit `{tip}`; candidate commit `{candidate_sha}`; "
        f"calibration: {calibration_details}; cases: {', '.join(cases) or 'none'}.", "",
    ]
    if candidate_details:
        lines += candidate_source_lines(candidate_details, tip, candidate, decision)
    evidence_heading = "**Observed epoch evidence.** " if interrupted else "**Observed exploration-run measurements.** "
    comparison = (f"**Product comparison.** Interrupted with outcome unknown/incomplete: {reason}."
                  if interrupted else f"**Product comparison.** Improvement remains unmeasured: {reason}.")
    lines += [evidence_heading + observed_summary, comparison,
        f"**What it shows.** Decision {decision}: {reason}.", note, "",
    ]
    return "\n".join(lines)


def exploration_run_summary(path: Path) -> str:
    """Report only values present in a readable run receipt; missing or malformed fields stay explicitly unknown."""
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError):
        return "unknown: result.json was missing or malformed"
    if not isinstance(result, dict):
        return "unknown: result.json was not an object"
    process = result.get("process") if isinstance(result.get("process"), dict) else {}
    cli = result.get("cli") if isinstance(result.get("cli"), dict) else {}
    details = []
    turns = cli.get("num_turns")
    details.append(f"{turns} turns" if isinstance(turns, int) and not isinstance(turns, bool) and turns >= 0
                   else "turns unknown")
    elapsed = process.get("elapsed_seconds")
    details.append(f"host elapsed {elapsed:g} seconds"
                   if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool)
                   and math.isfinite(elapsed) and elapsed >= 0 else "host elapsed unknown")
    checks = result.get("checks")
    if isinstance(checks, list) and all(isinstance(check, dict) and type(check.get("pass")) is bool for check in checks):
        details.append(f"{sum(check['pass'] for check in checks)}/{len(checks)} checks passed")
    elif isinstance(checks, list):
        details.append(f"{len(checks)} checks; pass results unknown")
    else:
        details.append("checks unknown")
    cost = cli.get("cost_usd", "missing")
    if cost is None:
        details.append("cost unknown (reported cost_usd is null)")
    elif isinstance(cost, (int, float)) and not isinstance(cost, bool) and math.isfinite(cost) and cost >= 0:
        details.append(f"cost_usd {cost:g}")
    else:
        details.append("cost unknown (cost_usd missing or invalid)")
    return "; ".join(details)


def apply_decision(worktree: Path, loop: str, record: str, tip: str, candidate: str, decision: str) -> str:
    """PROMOTE keeps the candidate as the tip; anything else keeps it as a ref and resets the worktree to the tip.

    The learning records appended during the cycle are not committed yet: they are carried across the reset."""
    if decision == "PROMOTE":
        return f"The loop tip advanced to {candidate}."
    ref = f"refs/shiploop-loop/{loop}/{record}"
    for number in range(2, 100):
        held = subprocess.run(["git", "-C", str(worktree), "rev-parse", "--verify", "-q", ref], capture_output=True,
                              text=True)
        if held.returncode != 0 or held.stdout.strip() == candidate:
            break  # the ref is free, or already names this candidate
        ref = f"refs/shiploop-loop/{loop}/{record}-{number}"  # an earlier kept candidate must stay reachable
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    kept = ledger.read_bytes() if ledger.is_file() else None
    _git(worktree, "update-ref", ref, candidate)
    _git(worktree, "reset", "-q", "--hard", tip)
    if kept is not None:
        ledger.write_bytes(kept)
    return f"The candidate is kept as {ref} at {candidate}; the loop tip stays at {tip}."


def commit_entry(worktree: Path, text: str, record: str | None, decision: str, verdict: str, stage: Path,
                 terminal: bool = False) -> str:
    journal = worktree / JOURNAL
    with journal.open("a") as out:
        out.write("\n" + text)
    if record and terminal:
        subject = f"test(e2e): retain cycle outcome for {record}: {decision}, product measurement {verdict}"
    elif record:
        subject = f"test(e2e): qualified cycle for {record}: {decision}, prediction {verdict}"
    else:
        subject = f"test(e2e): retain invalid review from exploration: {decision}, measurement {verdict}"
    message = f"{subject}\n\n{text}\nCo-Authored-By: ShipLoop E2E harness <shiploop-e2e@example.invalid>\n"
    (stage / "learnings-commit.txt").write_text(message)
    _git(worktree, "add", JOURNAL.as_posix(), f"test/shiploop_e2e/{learning_records.LEDGER.name}")
    _git(worktree, "commit", "-q", "-F", str(stage / "learnings-commit.txt"))
    return _git(worktree, "rev-parse", "HEAD")


def commit_terminal_learning(worktree: Path, stage: Path, record_id: str | None, record: dict | None,
                             decision: str, reason: str, tip: str, candidate: str | None,
                             calibration: dict | None, cases: list[str], note: str,
                             observed_summary: str | None = None,
                             candidate_details: dict | None = None, measurement: str = "unmeasured",
                             interrupted: bool = False) -> str:
    text = terminal_entry(record, decision, reason, tip, candidate, calibration, cases, note,
                          observed_summary, candidate_details, interrupted)
    return commit_entry(worktree, text, record_id, decision, measurement, stage, terminal=True)


def build(worktree: Path, out: Path) -> Path:
    subprocess.run([sys.executable, "-B", str(worktree / "scripts" / "build-packages.py"), str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    return out / "plugins" / "skill-craft"


def _write_recovery_note(path: Path, text: str) -> bool:
    try:
        with path.open("ab") as handle:
            handle.write(("\n" + text + "\n").encode("utf-8", errors="replace"))
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return False
    return True


def retain_interrupted_cycle(worktree: Path, loop: str, record_id: str, stage: Path, record: dict,
                              tip: str, calibration: dict, cases: list[str], ledger_before: bytes,
                              error: BaseException) -> None:
    """Keep an interrupted cycle's ledger bytes and candidate before restoring the accepted loop tip."""
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    current_ledger = ledger.read_bytes() if ledger.is_file() else b""
    head = _git(worktree, "rev-parse", "HEAD")
    status = _git(worktree, "status", "--porcelain", "--untracked-files=all")
    epoch_root = stage / "epoch"
    if head == tip and current_ledger == ledger_before and not status and not epoch_root.exists():
        return

    artifacts = _interruption_artifact_dir(worktree, stage)
    backup = artifacts / f"interrupted-ledger-{record_id}.jsonl"
    failure_note = artifacts / f"interrupted-exception-{record_id}.txt"
    _durable_write(backup, current_ledger)
    original_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    _durable_write(failure_note,
                   (f"Cycle {record_id} interrupted before a complete outcome was retained.\n"
                    f"Exception: {type(error).__name__}: {error}\n"
                    f"Original traceback:\n{original_traceback}\n"
                    f"Ledger bytes before recovery: {backup}\n").encode("utf-8", errors="replace"))

    ledger_is_valid = True
    if not current_ledger.startswith(ledger_before):
        ledger_is_valid = False
        _write_recovery_note(failure_note,
                             "Current ledger bytes no longer extend the accepted history; raw bytes were preserved "
                             "externally and the accepted ledger will be restored before deferral.")
    try:
        if ledger_is_valid:
            learning_records.rows(backup)
    except (OSError, ValueError) as ledger_error:
        ledger_is_valid = False
        _write_recovery_note(failure_note,
                             f"Raw ledger bytes were preserved externally but not restored into the active ledger: "
                             f"{type(ledger_error).__name__}: {ledger_error}")

    candidate = head if head != tip else None
    ref = f"refs/shiploop-loop/{loop}/{record_id}"
    if candidate is None:
        try:
            candidate = _git(worktree, "rev-parse", "--verify", ref)
        except subprocess.CalledProcessError:
            pass
    failure_reason = f"{type(error).__name__}: {str(error)[:800]}"
    if candidate and candidate != tip:
        note = apply_decision(worktree, loop, record_id, tip, candidate, "INTERRUPTED")
    else:
        _git(worktree, "reset", "-q", "--hard", tip)
        note = f"No candidate commit was retained; the loop tip stays at {tip}."
    if ledger_is_valid:
        _durable_write(ledger, current_ledger)
    else:
        _durable_write(ledger, ledger_before)

    learning_records.append("deferred", record_id, ledger,
                            reason=f"Cycle interrupted before its outcome was retained: {failure_reason}")
    evidence = (f"unknown/incomplete; do not infer a product outcome from partial runs. "
                f"Inspect epoch artifacts and any retained result receipts at {epoch_root}; "
                f"the full cycle stage remains at {stage}.")
    details = (f"Cycle interrupted by {failure_reason}; no promotion or rejection outcome was retained. "
               f"The ledger snapshot is preserved at {backup}; the original exception is recorded at {failure_note}. "
               f"Product evidence is unknown/incomplete; inspect {epoch_root}. {note}")
    commit_terminal_learning(worktree, stage, record_id, record, "INTERRUPTED", failure_reason, tip,
                             candidate, calibration, cases, details, evidence,
                             measurement="unknown/incomplete", interrupted=True)


def qualify(worktree: Path, loop: str, record_id: str, stage: Path, args, calibration: dict) -> dict:
    """Run a qualified cycle only from a clean loop tip; preserve and journal interrupted mutations before re-raising."""
    ledger = worktree / "test" / "shiploop_e2e" / learning_records.LEDGER.name
    dirty = _git(worktree, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise ValueError("qualify requires a clean worktree; refusing to reset existing changes")
    if stage.exists():
        raise FileExistsError(f"cycle stage already exists; preserving prior evidence at {stage}")
    tip = _git(worktree, "rev-parse", "HEAD")
    ledger_before = ledger.read_bytes()
    record = learning_records.improver_view(record_id, ledger)
    cases = [args.case] + ([args.generality_case] if args.generality_case else [])
    try:
        result = _qualify_impl(worktree, loop, record_id, stage, args, calibration)
    except BaseException as error:
        try:
            retain_interrupted_cycle(worktree, loop, record_id, stage, record, tip, calibration, cases,
                                     ledger_before, error)
        except BaseException as recovery_error:
            # Never replace the original failure: keep both diagnostics beside the external ledger backup when possible.
            note_written = False
            try:
                artifacts = _interruption_artifact_dir(worktree, stage)
                failure_note = artifacts / f"interrupted-exception-{record_id}.txt"
                note_written = _write_recovery_note(
                    failure_note,
                    f"Original exception: {type(error).__name__}: {error}\n"
                    f"Original traceback:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n"
                    f"Recovery wrapper failed; recovery is incomplete: "
                    f"{type(recovery_error).__name__}: {recovery_error}")
            except BaseException:
                pass
            if not note_written:
                print(f"cycle: interrupted recovery incomplete ({type(recovery_error).__name__}: {recovery_error}); "
                      f"original exception remains: {type(error).__name__}: {error}", file=sys.stderr)
        raise
    # Learning is already committed when the operation returns. Export errors must not reset a completed outcome.
    # Candidate-controlled commit messages never decide whether recovery runs.
    (stage / "cycle-result.json").write_text(json.dumps({"contract": CONTRACT, **result}, indent=2, default=str) + "\n")
    return result


def _qualify_impl(worktree: Path, loop: str, record_id: str, stage: Path, args, calibration: dict) -> dict:
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
    def no_usable_candidate(change: dict, crossed: str | None, improve_dir: Path) -> dict:
        """Reset to the tip and record why the improver's work cannot be measured. Both improver calls (the first and
        the retry after an `extra` purpose review) end here when they cross the boundary, strand uncommitted work or
        leave the scope: what is measured must be exactly what was committed."""
        head = _git(worktree, "rev-parse", "HEAD")
        candidate_sha = head if head != tip else None
        _git(worktree, "reset", "-q", "--hard", tip)
        if crossed:
            why = crossed
        elif change["out_of_scope"] or change["uncommitted"]:
            why = "out of scope or uncommitted work"
        else:
            why = "the improver committed nothing"
        reason = f"No usable candidate: {why}"
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=reason)
        if candidate_sha:
            note = (f"Committed candidate {candidate_sha} was not adopted; the loop tip remains at {tip}. "
                    f"Improve artifacts remain at {improve_dir}.")
        else:
            note = (f"No candidate commit was available; the loop tip remains at {tip}. "
                    f"Improve artifacts remain at {improve_dir}.")
        result = {"decision": "NO_CANDIDATE", "reasons": [why], "stop": bool(crossed), "tip_note": note}
        result["learnings_commit"] = commit_terminal_learning(
            worktree, stage, record_id, record, result["decision"], reason, tip, candidate_sha, calibration, cases,
            note)
        return result

    crossed = iterate.boundary_crossing(change)
    if crossed or change["out_of_scope"] or change["uncommitted"] or not change["commits"]:
        return no_usable_candidate(change, crossed, stage / "improve")
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
        crossed = iterate.boundary_crossing(change)
        if crossed or change["out_of_scope"] or change["uncommitted"]:
            return no_usable_candidate(change, crossed, stage / "improve-retry")
        predicted = (change["report"] or {}).get("prediction") or predicted
    candidate_sha = _git(worktree, "rev-parse", "HEAD")
    if verdict["result"] != "passed":
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REJECTED")
        reason = "Purpose review rejected the candidate: " + "; ".join(verdict["reasons"])
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=reason[:500])
        result = {"decision": "REJECTED_AT_PURPOSE", "reasons": verdict["reasons"], "tip_note": note}
        result["learnings_commit"] = commit_terminal_learning(
            worktree, stage, record_id, record, result["decision"], reason, tip, candidate_sha,
            calibration, cases, note, candidate_details=candidate_source(worktree, tip, candidate_sha))
        return result
    prediction_file = stage / "prediction.json"
    prediction_file.write_text(json.dumps(predicted, indent=2) + "\n")
    try:
        roles = roles_for(predicted, args.case, args.generality_case)
    except (KeyError, TypeError, ValueError) as error:
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REJECTED")
        reason = f"No usable prediction: {error}"
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=reason)
        result = {"decision": "NO_PREDICTION", "reasons": [str(error)], "tip_note": note}
        result["learnings_commit"] = commit_terminal_learning(
            worktree, stage, record_id, record, result["decision"], reason, tip, candidate_sha,
            calibration, cases, note, candidate_details=candidate_source(worktree, tip, candidate_sha))
        return result
    candidate_plugin = build(worktree, stage / "candidate-build")
    driver = hosts.resolve_role("subject", {"host": args.host, "model": args.model, "effort": args.effort})
    driver = {key: driver[key] for key in ("host", "model", "effort")}
    try:
        result = qualify_built(stage / "epoch", record_id, prediction_file, control_plugin, candidate_plugin, roles,
                               driver, calibration, args, ledger, candidate_sha)
    except RegistrationRefused as error:
        note = apply_decision(worktree, loop, record_id, tip, candidate_sha, "REFUSED")
        reason = f"Registration refused: {error}"
        learning_records.append("rejected_at_purpose", record_id, ledger, reason=reason)
        result = {"decision": "REFUSED", "reasons": [str(error)], "tip_note": note}
        result["learnings_commit"] = commit_terminal_learning(
            worktree, stage, record_id, record, result["decision"], reason, tip, candidate_sha,
            calibration, cases, note, candidate_details=candidate_source(worktree, tip, candidate_sha))
        return result
    note = apply_decision(worktree, loop, record_id, tip, candidate_sha,
                          result["decision"] if result["decision"] == "PROMOTE" else "KEEP_AS_REF")
    setup = {"cases": list(roles), "roles": roles, "tip": tip, "candidate": candidate_sha,
             "control_build": result["control_build"], "candidate_build": result["candidate_build"],
             "candidate_source": candidate_source(worktree, tip, candidate_sha),
             "driver": f"{driver['host']} {driver['model']} {driver['effort']}", "attempts": calibration["attempts"],
             "tolerance": calibration["tolerance"], "metric": calibration["metric"],
             "calibration": calibration_basis(calibration), "epoch": str(stage / "epoch"), "tip_note": note}
    result["tip_note"] = note
    result["learnings_commit"] = commit_entry(worktree, entry({"record": record_id, **record}, result, setup), record_id,
                                              result["decision"], (result.get("verdict") or {}).get("verdict", "not judged"),
                                              stage)
    return result


def explore(worktree: Path, stage: Path, args) -> list[str]:
    """One exploration run of the exposing case on the tip, reviewed and judged; returns the records it opened."""
    import iterate
    import judge
    import review as reviewer
    import run as runner
    stage.mkdir(parents=True, exist_ok=True)
    tip = _git(worktree, "rev-parse", "HEAD")
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
        validity = verdict.get("validity") if isinstance(verdict.get("validity"), dict) else {}
        status = validity.get("status") or "unknown"
        detail = validity.get("reason") or "the review did not qualify a discovery"
        reason = f"Review validity {status}: {detail}; no discovery-qualified learning record was admitted"
        note = f"No learning record was admitted; exploration artifacts remain at {stage / 'run'}."
        commit_terminal_learning(worktree, stage, None, None, "INVALID_REVIEW", reason, tip, None,
                                 None, [args.case], note,
                                 exploration_run_summary(stage / "run" / "result.json"))
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
    cases = [args.case] + ([args.generality_case] if args.generality_case else [])
    try:
        calibration = resolve_calibration(args, cases)
    except ValueError as error:
        raise SystemExit(f"--qualify: {error}")
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
                              f"- basis: {calibration_phrase(calibration_basis(calibration))}; "
                              f"{calibration['attempts']} attempts per arm, "
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
    parser.add_argument("--calibration", type=Path, help="spread.py's report of an A/A epoch (the measured basis)")
    parser.add_argument("--tolerance", type=float, help="without --calibration: the relative efficiency tolerance, "
                        "stated and recorded as unmeasured")
    parser.add_argument("--attempts", type=int, help="without --calibration: attempts per arm, stated and recorded "
                        "as unmeasured")
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
        calibration = resolve_calibration(args, cases)
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
             "calibration": calibration_basis(calibration), "epoch": str(out / "epoch"),
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
