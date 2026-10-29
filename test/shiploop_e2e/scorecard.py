#!/usr/bin/env python3
"""One scorecard per E2E run, from the run's own records: the objective of the self-improving loop (P1 of
docs/shiploop-e2e-self-improving-loop-design-2026-10-25.md).

    python3 test/shiploop_e2e/scorecard.py RUN [RUN ...] [--json] [--out FILE]

A RUN is an output folder holding result.json and metrics.json; a folder above run folders is walked to them. Nothing is
written into a run folder and no model is called. Every card carries ``scorecard: SCORECARD_ID``. Two cards are compared
only when their ids are equal, so a change to what a part reads or how a floor is decided takes a new id.

The parts, each read from records the harness already writes:

* ``validity``: three dimensions (SPEC "The promotion contract", build step 2), each ``{valid, why}`` with ``valid`` true,
  false or null; null means not observed and is never valid.
  - **correctness**: false when the delivered ``work/`` changed after delivery (a check that deleted a product file, as on
    2026-10-24). From build step 4 it reads the run's delivery snapshot (result.json ``delivery``): false when the
    fingerprint after the checks differs from the one before, or when a ``work/`` that still exists now differs from what
    the checks left (a later commit or edit). So a torn-down run is graded from its records. A run recorded before the snapshot
    keeps the live reading. Null when nothing can be read, or when this run and a run that overlapped it wrote the same
    ``/tmp`` name, because shared state can't be ruled out. Null too, for a case with held-out acceptance, when the run's events
    name a held-out file, the checks folder or the case catalog (``quality.held_out_seen`` above 0, build step 3), or when
    that was not recorded: its result is not independent evidence.
  - **attribution**: false when hosts or host builds were mixed, or a Claude run on Ollama was served by a model other than
    its own (``metrics.models_served``); null for such a run when no result event names its model.
  - **timing**: false when the run overlapped others under its runs root (``environment.overlap``), was resumed, was not
    attributable to one build, or left listeners alive. Null when any of those was not observed.

  The observations are kept beside the dimensions. It is a record, never a run's verdict.
* ``accuracy`` (a floor): the verdicts, the checks (a follow-on's include the followed case's and the retention checks),
  the hidden acceptance checks and the mutation ratio. **Requiredness belongs to the case** (``cases.json``): a case that
  declares hidden acceptance requires it, so an unobserved acceptance leaves the floor ``unobserved``, never a pass.
* ``enterprise`` (a floor): ``not_applicable`` until the scripted rubric exists.
* ``fidelity`` (a floor): the engine ended done, with no open unverified entry and no skipped evidence. An entry whose due
  stage was accepted later without restating the list is unknown, and the floor is ``unobserved`` (``scorecard/5``). Edits of script-owned
  files, refusals and retired glossary terms in ShipLoop's replies (``nomenclature``, S-16) are reported beside it; the
  edit list is a heuristic to confirm (SPEC), so it decides nothing. ``improve_reviews`` is left out: on the 2.9.0 runs it
  reads 0 children beside 10 Improve children, a reader that has not followed the Improve route's change.
* ``efficiency`` (the target): minutes, cost, turns, ``tokens`` (processed: input, cache reads, cache writes and output)
  and ``output_tokens`` (``scorecard/6``, build step 8). Cost, turns and tokens are added over every reported session,
  stops and resumes included, and ``totals_lower_bound`` says when a launched session never reported, so they cover part
  of the run (``metrics.lower_bound``; ``sessions.jsonl`` makes that count exact on every host). Diagnostics beside them,
  never a target (R4): refusals, Improve children, planning minutes, re-orientation minutes, the fresh starts and their
  ``calls_before_grounding``. The re-orientation window runs to the next accepted action and includes stage work; the
  calls are what finding the place again cost.
* ``boundary`` (identity, build step 3): what graded the run (``evaluator``, ``oracle``, ``case``: result.json's
  ``boundary``, recorded from 2026-10-25) and what was graded (``candidate``: ``versions.plugin_sha256``). The promotion
  contract compares a case only across equal grading digests.

A value nothing measured is null with its reason in ``unmeasured``, never 0. A floor is ``pass``, ``fail``, ``unobserved``
(required and not measured) or ``not_applicable``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery  # noqa: E402  (delivery.fingerprint and delivery.changed: the delivery snapshot)
import environment  # noqa: E402  (environment.overlap: the one overlap reader)
import metrics  # noqa: E402  (metrics.lower_bound: the one lower-bound rule for cost and turns)
import runrecord  # runrecord.launches: the source roots recorded before any review runs

SCORECARD_ID = "scorecard/6"
VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
NOT_YET = "no scripted enterprise rubric yet (design P2)"
PASS, FAIL, UNOBSERVED, NOT_APPLICABLE = "pass", "fail", "unobserved", "not_applicable"
CASES = Path(__file__).resolve().parent / "cases.json"
_CURRENT_CASE = object()
RUN_RECEIPT_FILES = ("prompt.txt", "result.json", "metrics.json", "timeline.jsonl", "invocation.json",
                     "transcript.md", "events.jsonl", "stderr.txt")


def combined(*parts: str) -> str:
    """One floor from its parts: any fail fails, then any unobserved is unobserved, all not applicable is not applicable."""
    real = [part for part in parts if part != NOT_APPLICABLE]
    if not real:
        return NOT_APPLICABLE
    return FAIL if FAIL in real else UNOBSERVED if UNOBSERVED in real else PASS


def requires_acceptance(case, required_case=_CURRENT_CASE) -> bool | None:
    """Whether the case declares hidden acceptance checks (``cases.json`` ``quality.acceptance``): requiredness is the case's."""
    if required_case is not _CURRENT_CASE:
        if not isinstance(required_case, dict):
            return None
        quality = required_case.get("quality")
        if quality is None:
            return False
        if not isinstance(quality, dict):
            return None
        acceptance = quality.get("acceptance")
        return isinstance(acceptance, dict) if acceptance is not None else False
    try:
        declared = json.loads(CASES.read_text()).get(case) or {}
    except (OSError, ValueError):
        return False
    return bool((declared.get("quality") or {}).get("acceptance"))


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _passed(items) -> dict:
    items = [item for item in items or [] if isinstance(item, dict)]
    return {"passed": sum(1 for item in items if item.get("pass") is True), "total": len(items)}


def work_tree_after(run: Path) -> tuple[list[str] | None, str | None]:
    """The delivered work tree's `git status --porcelain` lines now (empty: clean), or None with the reason."""
    work = run / "work"
    if not (work / ".git").exists():
        return None, "no work/ repository (torn down, or nothing was delivered)"
    done = subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        return None, "git status failed: " + (done.stderr.strip().splitlines() or ["no message"])[0][:160]
    return [line for line in done.stdout.splitlines() if line.strip()], None


def delivery_reading(run: Path, result: dict) -> dict | None:
    """What the delivery snapshot says (build step 4), or None for a run recorded without one: ``during_checks``, how the
    fingerprint after the checks differs from the one before; ``after_run``, how a ``work/`` that still exists differs now
    from what the checks left, a later commit or edit (None when ``work/`` is gone)."""
    recorded = result.get("delivery") if isinstance(result.get("delivery"), dict) else {}
    before, after = recorded.get("before") or {}, recorded.get("after") or {}
    if not (before.get("observed") and after.get("observed")):
        return None
    live = delivery.fingerprint(run / "work")
    return {"head": before.get("head"), "bundle": before.get("bundle"), "during_checks": delivery.changed(before, after),
            "after_run": delivery.changed(after, live) if live.get("observed") else None}


def host_builds(result: dict, run_metrics: dict) -> list[str] | None:
    """The distinct host builds the run's launches ran on: Grok and Codex from each launch record's probe, Claude from its
    init events (``claude_code_version``, which names every build its sessions used). None where none was recorded."""
    builds = [entry.get("host_build") for entry in (result.get("environment") or {}).get("environments") or []
              if isinstance(entry, dict) and entry.get("host_build")]
    claude = run_metrics.get("claude_code_version")
    if isinstance(claude, str) and claude:
        builds += [part.strip() for part in claude.split(",") if part.strip()]
    return sorted(set(builds)) or None


def shared_tmp_names(run: Path, seen: dict, run_metrics: dict) -> tuple[list[str] | None, str | None]:
    """The /tmp names this run wrote that a run overlapping it also wrote (each run's own ``metrics.tmp_writes``), or None
    with the reason where it can't be known. A run that wrote none shares none."""
    mine = run_metrics.get("tmp_writes")
    if not isinstance(mine, list):
        return None, "this run's /tmp writes were not recorded"
    if not mine:
        return [], None
    if not seen.get("observed"):
        return None, "the overlap was not observed"
    root, shared, unknown = environment.runs_root(run), set(), []
    for neighbour in seen["runs"]:
        theirs = (_read(root / neighbour["folder"] / "metrics.json") or {}).get("tmp_writes")
        if not isinstance(theirs, list):
            unknown.append(neighbour["folder"])
            continue
        shared |= set(mine) & set(theirs)
    if shared:
        return sorted(shared), None
    return (None, "the /tmp writes of " + ", ".join(unknown) + " are not known") if unknown else ([], None)


def dimension(false_reasons: list[str], null_reasons: list[str]) -> dict:
    """One validity dimension: false with its reasons, else null when something was not observed, else true."""
    if false_reasons:
        return {"valid": False, "why": false_reasons}
    if null_reasons:
        return {"valid": None, "why": null_reasons}
    return {"valid": True, "why": []}


def qualification_overlap(run: Path, result: dict) -> dict:
    """Add current observations without erasing neighbours recorded when this run ended."""
    live = environment.overlap(run)
    recorded = (result.get("environment") or {}).get("overlap")
    if not isinstance(recorded, dict) or recorded.get("observed") is not True:
        return {**live, "observed": False, "reason": "the run recorded no observed overlap baseline"}
    historical = recorded.get("runs")
    if not isinstance(historical, list):
        return {"observed": False, "reason": "recorded overlap has no readable neighbour inventory", "runs": []}
    neighbours = {row["folder"]: row for row in historical if isinstance(row, dict) and isinstance(row.get("folder"), str)}
    neighbours.update({row["folder"]: row for row in live.get("runs", [])
                       if isinstance(row, dict) and isinstance(row.get("folder"), str)})
    if recorded.get("root") != live.get("root"):
        return {**live, "observed": False, "runs": list(neighbours.values()),
                "reason": "the current overlap root differs from the recorded run root"}
    return {**live, "runs": list(neighbours.values())}


def validity(run: Path, result: dict, run_metrics: dict, unmeasured: dict, required_case=_CURRENT_CASE) -> dict:
    environment_block = result.get("environment") or {}
    seen = (environment.overlap(run) if required_case is _CURRENT_CASE else qualification_overlap(run, result))
    if not seen.get("observed"):
        unmeasured["validity.overlap"] = seen.get("reason")
    left = result.get("left_behind") or {}
    if left.get("observed") is not True:
        unmeasured["validity.left_behind"] = left.get("reason") or "not recorded"
    status, why = work_tree_after(run)
    snapshot = delivery_reading(run, result)
    if why and snapshot is None:
        unmeasured["validity.work_tree_after"] = why
    resumed = bool(result.get("resumed_run"))
    mixed = environment_block.get("mixed_host")
    overlapped = len(seen["runs"]) if seen.get("observed") else None
    survived = len(left.get("survived") or []) if left.get("observed") is True else None
    builds = host_builds(result, run_metrics)
    if builds is None:
        unmeasured["validity.host_builds"] = "no launch record or init event names the host build"
    shared, shared_why = shared_tmp_names(run, seen, run_metrics)
    # Only a case with held-out acceptance holds anything out (quality.event_facts measures nothing for the others).
    holds_out = requires_acceptance(result.get("case"), required_case)
    held_out = (result.get("quality") or {}).get("held_out_seen") if holds_out else None
    block = {"resumed": resumed, "mixed_host": mixed if isinstance(mixed, bool) else None,
             "host_builds": builds, "overlapped_runs": overlapped, "overlap_root": seen.get("root"),
             "left_behind_survived": survived, "work_tree_after": status, "shared_tmp_names": shared,
             "held_out_seen": held_out, "delivery_snapshot": snapshot}
    if snapshot is not None:  # the records decide, whether or not work/ is still there
        tree_false = (([f"the checks changed the delivered tree: {'; '.join(snapshot['during_checks'])}"] if snapshot["during_checks"] else [])
                      + ([f"the delivered tree changed after the run: {'; '.join(snapshot['after_run'])}"] if snapshot["after_run"] else []))
        tree_null = []
    else:
        tree_false = [f"the delivered work tree changed after delivery: {', '.join(status[:3])}"] if status else []
        tree_null = [f"the delivered tree can't be read: {why}"] * (status is None)
    block["correctness"] = dimension(
        tree_false,
        tree_null
        + ([f"/tmp names shared with an overlapping run: {', '.join(shared)}"] if shared else [])
        + ([f"shared /tmp state is not known: {shared_why}"] if shared is None else [])
        + (["case requiredness is not available from the frozen qualification snapshot"] if holds_out is None else [])
        + ([f"the run's events name a held-out file, the checks folder or the case catalog {held_out} time(s)"]
           if isinstance(held_out, int) and held_out > 0 else [])
        + (["whether the run's events name a held-out file is not recorded"] if holds_out and held_out is None else []))
    # A host build that changed mid-run changes behaviour (inner-loop, 2026-10-25: Grok 1.0.62 to 1.0.70 alone blocked
    # chess run 5's deploy), so its figures are not one build's.
    # A run on Ollama routes every model class to its model, so a result event naming another served it (SPEC "The Claude
    # host can run on Ollama"); an Anthropic run's events also name the small model Claude Code uses on its own.
    ollama = result.get("backend") == "ollama"
    served = run_metrics.get("models_served")
    others = [m for m in served or [] if m != result.get("model")] if ollama else []
    block["models_served"] = served
    block["attribution"] = dimension(
        [text for text, bad in (("mixed hosts", mixed is True),
                                (f"host build changed: {', '.join(builds or [])}", len(builds or []) > 1),
                                (f"served by another model than {result.get('model')}: {', '.join(others)}", bool(others))) if bad],
        [text for text, unknown in (("whether hosts were mixed is not recorded", not isinstance(mixed, bool) and mixed is not True),
                                    ("no host build was recorded", builds is None),
                                    ("no result event names the model that served the run", ollama and not served)) if unknown])
    block["timing"] = dimension(
        [text for text, bad in (("resumed", resumed), (f"overlapped {overlapped} run(s)", bool(overlapped)),
                                (f"{survived} listener(s) survived", bool(survived)),
                                ("not attributable to one build", block["attribution"]["valid"] is False)) if bad],
        [text for text, unknown in (("the overlap was not observed", overlapped is None),
                                    ("leftover listeners were not observed", survived is None),
                                    ("attribution is not observed", block["attribution"]["valid"] is None)) if unknown])
    return block


def accuracy(result: dict, unmeasured: dict, required_case=_CURRENT_CASE) -> dict:
    quality = result.get("quality") or {}
    required = requires_acceptance(result.get("case"), required_case)
    acceptance = quality.get("acceptance")
    mutation = quality.get("mutation")
    block = {"pass": result.get("pass") is True,
             "verdicts": {name: (result.get(name) or {}).get("pass") for name in VERDICTS},
             "checks": _passed(result.get("checks")), "acceptance": None, "mutation": None}
    if isinstance(acceptance, dict) and acceptance.get("observed") is True:
        block["acceptance"] = _passed(acceptance.get("checks"))
    else:
        unmeasured["accuracy.acceptance"] = ((acceptance or {}).get("reason") if isinstance(acceptance, dict)
                                             else "the case declares no hidden acceptance checks")
    if isinstance(mutation, dict) and mutation.get("observed") is True:
        block["mutation"] = {"ratio": mutation.get("ratio"), "operator_id": mutation.get("operator_id")}
    else:
        unmeasured["accuracy.mutation"] = ((mutation or {}).get("reason") if isinstance(mutation, dict)
                                           else "the case declares no mutation measure")
    hidden = block["acceptance"]
    block["acceptance_required"] = required
    hidden_status = (UNOBSERVED if required is None else NOT_APPLICABLE if not required else UNOBSERVED if hidden is None
                     else PASS if hidden["passed"] == hidden["total"] else FAIL)
    if required is None:
        unmeasured["accuracy.requiredness"] = "the frozen case requiredness snapshot is missing or malformed"
    block["floor"] = combined(PASS if block["pass"] else FAIL, hidden_status)
    return block


def fidelity(run_metrics: dict, unmeasured: dict) -> dict:
    record = run_metrics.get("fidelity") or {}
    if not record:
        unmeasured["fidelity"] = "metrics.json has no fidelity block"
        return {"floor": UNOBSERVED}
    end = record.get("end_state") or {}
    unverified = (end.get("unverified") or {}).get("entries")
    not_restated = (end.get("unverified") or {}).get("not_restated") or 0  # a reading from before 2026-10-26 has no count
    skipped = ((record.get("evidence") or {}).get("counts") or {}).get("skipped")
    edits = (record.get("edits") or {}).get("script_owned")
    refusals = record.get("refusals") or {}
    # The edit list is a heuristic the SPEC calls a list to confirm, not a count to trust, so it is reported and never
    # decides the floor: an Improve stage's own investigation file can land in it.
    block = {"end_status": end.get("status"), "unverified": unverified, "unverified_not_restated": not_restated,
             "skipped_evidence": skipped,
             "script_owned_edits_to_confirm": len(edits) if isinstance(edits, list) else edits,
             "refusals": refusals.get("count"), "repeated_refusals": refusals.get("repeated"),
             "retired_terms": None}
    nomenclature = run_metrics.get("nomenclature")
    if isinstance(nomenclature, dict) and isinstance(nomenclature.get("retired"), dict):
        # Each retired term carries the number of ShipLoop texts (replies, refusal first lines) it appeared in.
        block["retired_terms"] = sum(int(hit.get("texts") or 0) for hit in nomenclature["retired"].values() if isinstance(hit, dict))
    else:
        unmeasured["fidelity.retired_terms"] = "metrics.json has no nomenclature record (it predates 2026-10-24)"
    missing = [name for name in ("unverified", "skipped_evidence") if block[name] is None]
    for name in missing:
        unmeasured[f"fidelity.{name}"] = "the fidelity block does not carry it"
    block["floor"] = (UNOBSERVED if missing or end.get("status") is None else
                      (FAIL if end.get("status") != "done" or unverified != 0 or skipped != 0
                       else UNOBSERVED if not_restated else PASS))
    return block


def efficiency(run_metrics: dict, unmeasured: dict) -> dict:
    span = run_metrics.get("span") or {}
    minutes = (round((span["ended"] - span["started"]) / 60, 1)
               if isinstance(span.get("started"), (int, float)) and isinstance(span.get("ended"), (int, float)) else None)
    window = (run_metrics.get("planning") or {}).get("window") or {}
    planning = round(window["seconds"] / 60, 1) if window.get("closed") and isinstance(window.get("seconds"), (int, float)) else None
    starts = run_metrics.get("fresh_starts")
    measured = ([s["reorientation"] for s in starts if isinstance(s, dict) and isinstance(s.get("reorientation"), dict)
                 and s["reorientation"].get("measured") is True and isinstance(s["reorientation"].get("seconds"), (int, float))]
                if isinstance(starts, list) else None)
    reorientation = round(sum(r["seconds"] for r in measured) / 60, 1) if measured is not None else None
    # What re-orientation itself cost: the tool calls each fresh context made before it grounded on a packet or `next`. The
    # minutes above run to the next accepted action, so they include the stage work in flight (2026-10-26: Battleship on
    # Grok, 84.8 window minutes over 14 fresh starts, 15 calls before grounding).
    grounded = [r["calls_before_grounding"] for r in measured or [] if isinstance(r.get("calls_before_grounding"), int)]
    grounding_calls = sum(grounded) if measured is not None and len(grounded) == len(measured) else None
    if isinstance(starts, list) and len(measured) < len(starts):
        unmeasured["efficiency.reorientation_minutes"] = (f"{len(starts) - len(measured)} of {len(starts)} fresh starts "
                                                          "have no measured re-orientation: a lower bound")
    tokens = run_metrics.get("tokens") if isinstance(run_metrics.get("tokens"), dict) else {}
    block = {"minutes": minutes, "cost_usd": run_metrics.get("cost_usd"),
             "totals_lower_bound": metrics.lower_bound(run_metrics), "turns": run_metrics.get("turns"),
             "tokens": tokens.get("processed"), "output_tokens": tokens.get("output"),
             "refusals": len(run_metrics["shiploop_failures"]) if isinstance(run_metrics.get("shiploop_failures"), list) else None,
             "improve_children": run_metrics.get("improve_children"), "planning_minutes": planning,
             "reorientation_minutes": reorientation, "fresh_starts": len(starts) if isinstance(starts, list) else None,
             "calls_before_grounding": grounding_calls}
    unmeasured_run = run_metrics.get("unmeasured") or {}
    reasons = {"minutes": "the run's stream has no readable span",
               "cost_usd": (run_metrics.get("unmeasured") or {}).get("cost_usd") or "the host reports no cost",
               "turns": "the host reports no turns",
               "tokens": unmeasured_run.get("tokens_processed") or "the metrics predate run tokens (build step 8): regrade",
               "output_tokens": unmeasured_run.get("tokens_output") or "the metrics predate run tokens (build step 8): regrade",
               "planning_minutes": "the planning window did not close",
               "reorientation_minutes": (run_metrics.get("fresh_starts_unmeasured") or "no fresh-start record"),
               "fresh_starts": (run_metrics.get("fresh_starts_unmeasured") or "no fresh-start record"),
               "calls_before_grounding": "a measured fresh start records no calls before grounding"}
    for name, reason in reasons.items():
        if block[name] is None:
            unmeasured.setdefault(f"efficiency.{name}", reason)
    return block


def delivery_product(result: dict) -> dict:
    """The product tree delivered to checks, valid only when before/after snapshots identify the same tree."""
    record = result.get("delivery") if isinstance(result.get("delivery"), dict) else {}
    before = record.get("before") if isinstance(record.get("before"), dict) else {}
    after = record.get("after") if isinstance(record.get("after"), dict) else {}
    required = ("head", "tree")
    if (before.get("observed") is not True or after.get("observed") is not True
            or any(not isinstance(before.get(name), str) or not before.get(name) for name in required)
            or any(not isinstance(after.get(name), str) or not after.get(name) for name in required)
            or not isinstance(before.get("status"), list) or not isinstance(after.get("status"), list)):
        return {"observed": False, "reason": "delivery before/after snapshots do not identify a product tree"}
    same = all(before.get(name) == after.get(name) for name in ("head", "tree", "status"))
    return {"observed": True, "head": before["head"], "tree": before["tree"],
            "after_head": after["head"], "after_tree": after["tree"], "unchanged_during_checks": same,
            **({} if same else {"reason": "delivery identity changed while checks ran"})}


def run_receipt(run) -> dict:
    """Seal run inputs, delivered product bytes, and reviewer source bytes; retain a stable partial receipt on gaps.

    Reviewer output files are deliberately excluded: a reviewer may add them after the run evidence is sealed. Reviewer
    source roots come only from launch records, which predate review. The ``product`` member records the live work tree's
    delivery fingerprint, while ``files`` also catches untracked content and symlink-target changes.
    """
    run = Path(run).resolve()
    files: dict[str, str] = {}
    symlinks: dict[str, str] = {}
    unsafe_symlinks: list[str] = []
    missing: list[str] = []

    def record_path(path: Path, key: str, scope_root: Path) -> None:
        try:
            if path.is_symlink():
                target = os.readlink(path)
                symlinks[key] = target
                try:
                    resolved = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    unsafe_symlinks.append(f"{key} -> {target} (broken or unreadable)")
                else:
                    if not resolved.is_relative_to(scope_root.resolve()):
                        unsafe_symlinks.append(f"{key} -> {target} (outside {scope_root})")
                    elif resolved.is_dir():
                        unsafe_symlinks.append(f"{key} -> {target} (directory target is not fully captured)")
                    elif not resolved.is_file():
                        unsafe_symlinks.append(f"{key} -> {target} (target is not a regular file)")
                    else:
                        try:
                            target_bytes = resolved.read_bytes()
                        except OSError:
                            unsafe_symlinks.append(f"{key} -> {target} (target is unreadable)")
                        else:
                            files[key] = hashlib.sha256(os.fsencode(target) + b"\0" + target_bytes).hexdigest()
            elif path.is_file():
                files[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                missing.append(key)
        except OSError as error:
            missing.append(f"{key}: {error.strerror}")

    for name in RUN_RECEIPT_FILES:
        record_path(run / name, name, run)
    for path in sorted(run.glob("invocation-resume-*.json")):
        record_path(path, path.name, run)

    # Hash a bundle when present and require it when the result records one.
    bundle = run / "delivery" / "work.bundle"
    result = _read(run / "result.json") or {}
    before = ((result.get("delivery") or {}).get("before") or {}) if isinstance(result, dict) else {}
    bundle_name = before.get("bundle") if isinstance(before, dict) else None
    if bundle.exists() or bundle.is_symlink():
        record_path(bundle, "delivery/work.bundle", run)
    elif isinstance(bundle_name, str) and bundle_name:
        missing.append("delivery/work.bundle")

    def tree(root: Path, prefix: str) -> None:
        if not root.is_dir():
            missing.append(f"{prefix}/ (tree is not present)")
            return

        def unreadable(error: OSError) -> None:
            missing.append(f"{prefix}/: {error.strerror}")

        for here, folders, names in os.walk(root, topdown=True, onerror=unreadable, followlinks=False):
            here_path = Path(here)
            keep = []
            for name in sorted(folders):
                path = here_path / name
                if name in (".git", "__pycache__"):
                    continue
                if path.is_symlink():
                    record_path(path, (Path(prefix) / path.relative_to(root)).as_posix(), root)
                    continue
                keep.append(name)
            folders[:] = keep
            for name in sorted(names):
                path = here_path / name
                if name.endswith((".pyc", ".pyo")) or name == ".git":
                    continue
                record_path(path, (Path(prefix) / path.relative_to(root)).as_posix(), root)

    work = run / "work"
    tree(work, "work")
    product = delivery.fingerprint(work)
    if product.get("observed") is not True:
        missing.append("work fingerprint: " + str(product.get("reason") or "not observed"))

    # Record the exact ShipLoop source roots available to a later reviewer, using the launch records saved with this run.
    roots = []
    unreadable_launches = runrecord.unreadable(run)
    if unreadable_launches:
        missing.append("review source launch records: " + ", ".join(unreadable_launches))
    for _name, launch in runrecord.launches(run):
        plugin_dir = launch.get("plugin_dir")
        if not isinstance(plugin_dir, str) or not plugin_dir:
            continue
        source = (Path(plugin_dir).expanduser() / "skills" / "shiploop").resolve()
        if source not in roots:
            roots.append(source)
    for source in roots:
        if not source.is_dir():
            missing.append(f"review source is unavailable: {source}")
            continue
        prefix = "review_source/" + hashlib.sha256(os.fsencode(str(source))).hexdigest()[:12]
        tree(source, prefix)

    # Ambient evidence affects correctness and timing. Bind the root and the exact overlapping neighbour inputs so
    # cleanup, a changed runs-root override, or a changed neighbour cannot silently erase an observed interference.
    overlap_root = environment.runs_root(run).resolve()
    overlap = qualification_overlap(run, result)
    if overlap.get("observed") is not True:
        missing.append("run-time overlap baseline: " + str(overlap.get("reason") or "not observed"))
    neighbours = {}
    for neighbour in overlap.get("runs", []):
        folder = neighbour.get("folder")
        if not isinstance(folder, str):
            continue
        neighbour_root = (overlap_root / folder).resolve()
        if not neighbour_root.is_relative_to(overlap_root):
            missing.append("overlapping run escapes its runs root")
            continue
        neighbours[folder] = {name: hashlib.sha256((neighbour_root / name).read_bytes()).hexdigest()
                              if (neighbour_root / name).is_file() else None
                              for name in ("timeline.jsonl", "metrics.json", "invocation.json")}
    ambient = {"root": str(overlap_root), "observed": overlap.get("observed"), "neighbours": neighbours,
               "unreadable": overlap.get("siblings_unreadable", [])}
    body = {"observed": not missing and not unsafe_symlinks, "files": files, "symlinks": symlinks,
            "unsafe_symlinks": sorted(unsafe_symlinks), "missing": sorted(missing), "product": product}
    body["ambient"] = ambient
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    return {**body, "sha256": hashlib.sha256(encoded).hexdigest()}


def score(run, *, required_case=_CURRENT_CASE) -> dict:
    """The scorecard of one run folder; a folder without readable records gives a card that says so."""
    run = Path(run)
    result, run_metrics = _read(run / "result.json"), _read(run / "metrics.json")
    if result is None:
        return {"scorecard": SCORECARD_ID, "run": str(run), "observed": False, "reason": "no readable result.json"}
    run_metrics = run_metrics or result.get("metrics") or {}
    unmeasured: dict[str, str] = {}
    versions = result.get("versions") or {}
    card = {"scorecard": SCORECARD_ID, "run": str(run), "observed": True, "case": result.get("case"),
            "driver": {k: result.get(k) for k in ("host", "backend", "model", "effort")},
            "versions": {"source": str(versions["source"]).split(" (")[0] if versions.get("source") else None,
                         "plugin_version": versions.get("plugin_version"), "shiploop_version": versions.get("shiploop_version")},
            "outcome_class": result.get("outcome_class"),
            "validity": validity(run, result, run_metrics, unmeasured, required_case),
            "accuracy": accuracy(result, unmeasured, required_case),
            "enterprise": {"observed": False, "reason": NOT_YET, "floor": NOT_APPLICABLE},
            "fidelity": fidelity(run_metrics, unmeasured), "efficiency": efficiency(run_metrics, unmeasured)}
    card["floors"] = {name: card[name]["floor"] for name in ("accuracy", "enterprise", "fidelity")}
    graded = result.get("boundary") if isinstance(result.get("boundary"), dict) else {}
    card["boundary"] = {**{name: graded.get(name) for name in ("evaluator", "oracle", "case")},
                        "candidate": versions.get("plugin_sha256")}
    if not graded:
        unmeasured["boundary"] = "result.json records no boundary (graded before build step 3, 2026-10-25)"
    for name, why in (graded.get("unmeasured") or {}).items():
        unmeasured[f"boundary.{name}"] = why
    if versions.get("plugin_sha256") is None:
        unmeasured["boundary.candidate"] = versions.get("plugin_sha256_unmeasured") or "no plugin digest recorded"
    if required_case is not _CURRENT_CASE:
        card["attempt_id"] = result.get("attempt_id")
        card["started"] = metrics.span(run / "timeline.jsonl")["started"]
        card["delivery_product"] = delivery_product(result)
        card["run_receipt"] = run_receipt(run)
    card["unmeasured"] = unmeasured
    return card


def run_folders(paths) -> list[Path]:
    """The run folders named, or found under a folder named (a folder holding result.json; the walk stops there)."""
    found = []
    for path in map(Path, paths):
        if (path / "result.json").is_file():
            found.append(path)
            continue
        found += [folder for folder in environment.run_folders(path) if (folder / "result.json").is_file()]
    return sorted(dict.fromkeys(found))


def _cell(value, unit: str = "") -> str:
    return "-" if value is None else f"{value}{unit}"


def render(cards: list[dict]) -> str:
    """One line per run: floors, the three validity dimensions, then the target's main figures and what voids a dimension."""
    lines = [f"{SCORECARD_ID}: {len(cards)} run(s); floors accuracy/enterprise/fidelity (P pass, F fail, ? unobserved, - n/a);"
             " validity correctness/attribution/timing (Y valid, n not, ? not observed)"]
    floor_mark = {PASS: "P", FAIL: "F", UNOBSERVED: "?", NOT_APPLICABLE: "-"}
    valid_mark = {True: "Y", False: "n", None: "?"}
    for card in cards:
        name = Path(card["run"]).name if Path(card["run"]).name not in ("", ".") else card["run"]
        if not card.get("observed"):
            lines.append(f"  {name:<34} {card['reason']}")
            continue
        floors = "/".join(floor_mark[card["floors"][k]] for k in ("accuracy", "enterprise", "fidelity"))
        e, v = card["efficiency"], card["validity"]
        dims = "/".join(valid_mark[v[k]["valid"]] for k in ("correctness", "attribution", "timing"))
        driver = (card["driver"].get("host") or "?") + ("@ollama" if card["driver"].get("backend") == "ollama" else "")
        part = "+" if e["totals_lower_bound"] else ""  # a total that may miss a session that never reported
        cost = _cell(e["cost_usd"]) + (part if e["cost_usd"] is not None else "")
        tokens = "-" if e["tokens"] is None else f"{e['tokens'] / 1e6:.1f}M{part}"
        why = "; ".join(f"{k}: {v[k]['why'][0]}" for k in ("correctness", "attribution", "timing") if v[k]["why"])
        lines.append(f"  {(card['case'] or '?') + ' ' + driver:<26} {floors}  {dims}  {_cell(e['minutes'], 'm'):>7} ${cost:<8} "
                     f"{_cell(e['turns']):>4}t {tokens:>7}tok {_cell(e['refusals']):>3}r" + (f"  {why}" if why else ""))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("runs", nargs="+", help="run folders, or folders above them")
    parser.add_argument("--json", action="store_true", help="print the cards as JSON")
    parser.add_argument("--out", type=Path, help="also write the cards as JSON to this file (never inside a run folder)")
    args = parser.parse_args(argv)
    folders = run_folders(args.runs)
    if args.out and any(args.out.resolve().is_relative_to(folder.resolve()) for folder in folders):
        raise SystemExit("--out names a file inside a run folder; a scorecard never writes there")
    cards = [score(folder) for folder in folders]
    if args.out:
        args.out.write_text(json.dumps({"scorecard": SCORECARD_ID, "cards": cards}, indent=1) + "\n")
    print(json.dumps({"scorecard": SCORECARD_ID, "cards": cards}, indent=1) if args.json else render(cards), end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
