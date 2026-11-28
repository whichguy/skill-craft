#!/usr/bin/env python3
"""Read-only testing-evidence, fix-forward replan, auto-subcase, and Proof-recheck observability.

Reads only bounded regular files beneath the run root (and never follows symlinks)
via ``shiploop_store``, redacts display strings with ``shiploop_privacy``, and
screens output with ``shiploop_observation_io``.  Never mutates repository or
run files or refuses any stage gate.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

import shiploop_observation_io as obs_io
import shiploop_privacy as privacy
import shiploop_store as store
import shiploop_test_loop as test_loop

_MAX_PROOF_FILES = 128
_MAX_PROOF_BYTES = 128 * 1024
_IMPACT_TIERS = ("none", "local", "amend-remaining", "system-test")
_REPLAN_STATES = frozenset(("document", "step-plan", "reflect-and-revise", "system-test-author", "system-test"))


def _clean_text(value: Any, limit: int = 200) -> str:
    return privacy.clean_display_text(value, limit)


def _id_token(ident: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(ident) + r"(?![A-Za-z0-9_-])")


def _read_bounded_record(path: Path) -> Mapping[str, Any] | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_PROOF_BYTES:
                return None
            handle.read(min(1, info.st_size))
        loaded = store.read_record(path)
        return loaded if isinstance(loaded, Mapping) else None
    except (OSError, store.StorageError):
        return None


def _count_test_proof_rechecks(root: Path | None) -> int:
    if root is None:
        return 0
    tests_dir = Path(root) / "tests"
    if not tests_dir.is_dir() or tests_dir.is_symlink():
        return 0
    try:
        entries = sorted(tests_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return 0
    count = 0
    scanned = 0
    for entry in entries:
        if scanned >= _MAX_PROOF_FILES:
            break
        if "-step-proof" not in entry.name or not entry.name.endswith(".md"):
            continue
        scanned += 1
        rec = _read_bounded_record(entry)
        if isinstance(rec, Mapping) and rec.get("kind") == "step-proof" and rec.get("stage") == "test":
            count += 1
    return count


def testing_observability(root: Path | None, state: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return bounded, secret-screened testing-evidence and fix-forward summary from ``state`` and ``root``."""
    empty = {
        "has_evidence": False,
        "findings": [],
        "by_impact": {tier: 0 for tier in _IMPACT_TIERS},
        "findings_settled": 0,
        "replans": [],
        "added_tests_count": 0,
        "auto_subcases": [],
        "auto_subcases_count": 0,
        "not_exercisable_mutants": [],
        "not_exercisable_settled_outer": 0,
        "test_proof_rechecks": 0,
    }
    if not isinstance(state, Mapping):
        return empty
    history = state.get("history")
    accepted = state.get("accepted")
    if not isinstance(history, list) or not isinstance(accepted, Mapping):
        return empty

    by_impact = {tier: 0 for tier in _IMPACT_TIERS}
    findings: list[dict[str, Any]] = []
    seen_findings: set[tuple[str, str]] = set()
    replans: list[dict[str, Any]] = []
    seen_replans: set[str] = set()
    added_tests_count = 0
    not_exercisable: list[dict[str, Any]] = []
    seen_mutants: set[tuple[str, str]] = set()

    for index, entry in enumerate(history):
        if not isinstance(entry, Mapping) or entry.get("outcome") != "done":
            continue
        stage = str(entry.get("stage") or "")
        action = entry.get("action")
        workitem = str(entry.get("workitem") or "")
        if not isinstance(action, str):
            continue
        res = accepted.get(action)
        if not isinstance(res, Mapping):
            continue
        if stage in ("test", "document"):
            added = res.get("added_tests")
            if isinstance(added, list):
                added_tests_count += sum(1 for row in added if isinstance(row, Mapping) and row.get("id"))
        if stage == "document" and isinstance(res.get("replan_remaining"), Mapping) and action not in seen_replans:
            seen_replans.add(action)
            rp = res["replan_remaining"]
            affects = [_clean_text(a, 48) for a in (rp.get("affects") or ()) if isinstance(a, str) and a.strip()]
            replans.append({
                "item": _clean_text(workitem, 48),
                "action": _clean_text(action, 64),
                "reason": _clean_text(rp.get("reason"), 200),
                "affects": affects[:8],
            })
        if stage == "test":
            for row in res.get("test_findings") or ():
                if not isinstance(row, Mapping):
                    continue
                fid = _clean_text(row.get("id"), 48)
                impact = str(row.get("impact") or "none")
                if not fid:
                    continue
                key = (workitem, fid)
                if key in seen_findings:
                    continue
                seen_findings.add(key)
                if impact in by_impact:
                    by_impact[impact] += 1
                findings.append({
                    "_index": index,
                    "id": fid,
                    "item": _clean_text(workitem, 48),
                    "stage": "test",
                    "impact": impact,
                    "finding": _clean_text(row.get("finding"), 200),
                    "next_step": _clean_text(row.get("next_step"), 160),
                    "settled": False,
                })
            for mrow in res.get("mutant_dispositions") or ():
                if not isinstance(mrow, Mapping) or mrow.get("disposition") != "not-exercisable":
                    continue
                mutant = _clean_text(mrow.get("mutant"), 120)
                if not mutant:
                    continue
                mkey = (workitem, mutant)
                if mkey in seen_mutants:
                    continue
                seen_mutants.add(mkey)
                not_exercisable.append({
                    "_index": index,
                    "item": _clean_text(workitem, 48),
                    "mutant": mutant,
                    "evidence": _clean_text(mrow.get("evidence"), 160),
                    "settled_outer": False,
                })

    active_improve = state.get("active_improve")
    if isinstance(active_improve, Mapping) and active_improve.get("stage") == "document":
        imp_action = str(active_improve.get("action_id") or "")
        seed_res = active_improve.get("seed_result")
        if (
            imp_action
            and imp_action not in seen_replans
            and isinstance(seed_res, Mapping)
            and isinstance(seed_res.get("replan_remaining"), Mapping)
        ):
            seen_replans.add(imp_action)
            rp = seed_res["replan_remaining"]
            affects = [_clean_text(a, 48) for a in (rp.get("affects") or ()) if isinstance(a, str) and a.strip()]
            replans.append({
                "item": _clean_text(str(active_improve.get("owner") or ""), 48),
                "action": _clean_text(imp_action, 64),
                "reason": _clean_text(rp.get("reason"), 200),
                "affects": affects[:8],
            })

    findings_settled = 0
    for frow in findings:
        pat = _id_token(frow["id"])
        settled = False
        for later in history[frow["_index"] + 1:]:
            if not isinstance(later, Mapping) or later.get("outcome") != "done":
                continue
            l_stage = str(later.get("stage") or "")
            l_item = str(later.get("workitem") or "")
            if l_stage not in _REPLAN_STATES:
                continue
            l_res = accepted.get(later.get("action")) if isinstance(later.get("action"), str) else None
            if not isinstance(l_res, Mapping):
                continue
            if frow["impact"] == "amend-remaining" and l_stage == "step-plan" and l_item == frow["item"]:
                settled = True
                break
            blob = json.dumps(
                {k: l_res.get(k) for k in ("summary", "replan_remaining", "assumptions", "system_commands")
                 if k in l_res},
                sort_keys=True,
            )
            if pat.search(blob):
                settled = True
                break
        frow["settled"] = settled
        if settled:
            findings_settled += 1
        frow.pop("_index", None)

    outer_settled = 0
    for mrow in not_exercisable:
        pat = _id_token(mrow["mutant"]) if len(mrow["mutant"]) <= 64 else None
        settled = False
        for later in history[mrow["_index"] + 1:]:
            if not isinstance(later, Mapping) or later.get("outcome") != "done":
                continue
            if str(later.get("stage") or "") not in ("system-test-author", "system-test"):
                continue
            l_res = accepted.get(later.get("action")) if isinstance(later.get("action"), str) else None
            if not isinstance(l_res, Mapping):
                continue
            blob = json.dumps(
                {k: l_res.get(k) for k in ("summary", "assumptions", "system_commands") if k in l_res},
                sort_keys=True,
            )
            if (pat is not None and pat.search(blob)) or mrow["mutant"] in blob or "not-exercisable" in blob:
                settled = True
                break
        mrow["settled_outer"] = settled
        if settled:
            outer_settled += 1
        mrow.pop("_index", None)

    auto_subcases: list[dict[str, Any]] = []
    auto_count = 0
    if root is not None:
        item_ids: list[str] = []
        for wid in list(state.get("completed_work_items") or ()) + [
                row.get("id") for row in (state.get("work_items") or ()) if isinstance(row, Mapping)]:
            if isinstance(wid, str) and wid and wid not in item_ids:
                item_ids.append(wid)
        for wid in item_ids:
            by_cmd = test_loop.discovered_subcases(root, state, wid)
            for cmd, ids in by_cmd.items():
                clean_ids = [_clean_text(tid, 64) for tid in ids if _clean_text(tid, 64)]
                if clean_ids:
                    auto_count += len(clean_ids)
                    auto_subcases.append({
                        "item": _clean_text(wid, 48),
                        "command_label": _clean_text(cmd, 80),
                        "ids": clean_ids,
                    })

    rechecks = _count_test_proof_rechecks(root)
    has_evidence = bool(
        findings or replans or auto_count or not_exercisable or rechecks or added_tests_count
    )
    payload = {
        "has_evidence": has_evidence,
        "findings": findings,
        "by_impact": by_impact,
        "findings_settled": findings_settled,
        "replans": replans,
        "added_tests_count": added_tests_count,
        "auto_subcases": auto_subcases,
        "auto_subcases_count": auto_count,
        "not_exercisable_mutants": not_exercisable,
        "not_exercisable_settled_outer": outer_settled,
        "test_proof_rechecks": rechecks,
    }
    return obs_io.screen(payload)


def fingerprint_digest(observability: Mapping[str, Any]) -> str:
    """Stable digest so browser polling refreshes when testing evidence changes."""
    raw = json.dumps(observability, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def status_lines(observability: Mapping[str, Any]) -> list[str]:
    """Return 0 or 1 concise, path-free, command-free summary lines for ``shiploop status``."""
    if not observability or not observability.get("has_evidence"):
        return []
    parts: list[str] = []
    findings = observability.get("findings") or ()
    by_impact = observability.get("by_impact") or {}
    if findings:
        tier_bits = [f"{int(by_impact.get(t, 0))} {t}" for t in _IMPACT_TIERS if int(by_impact.get(t, 0)) > 0]
        tier_note = f" ({', '.join(tier_bits)})" if tier_bits else ""
        settled = int(observability.get("findings_settled") or 0)
        parts.append(f"{len(findings)} finding{'s' if len(findings) != 1 else ''}{tier_note}, {settled} settled")
    replans = observability.get("replans") or ()
    if replans:
        parts.append(f"{len(replans)} fix-forward replan{'s' if len(replans) != 1 else ''}")
    auto_count = int(observability.get("auto_subcases_count") or 0)
    if auto_count:
        parts.append(f"{auto_count} auto-registered sub-case{'s' if auto_count != 1 else ''}")
    added_count = int(observability.get("added_tests_count") or 0)
    if added_count:
        parts.append(f"{added_count} added test{'s' if added_count != 1 else ''}")
    mutants = observability.get("not_exercisable_mutants") or ()
    if mutants:
        m_settled = int(observability.get("not_exercisable_settled_outer") or 0)
        parts.append(f"{len(mutants)} not-exercisable mutant{'s' if len(mutants) != 1 else ''} ({m_settled} outer)")
    rechecks = int(observability.get("test_proof_rechecks") or 0)
    if rechecks:
        parts.append(f"{rechecks} test Proof re-check{'s' if rechecks != 1 else ''}")
    if not parts:
        return []
    line = "Testing evidence: " + " · ".join(parts)
    if privacy.sensitive_text(line):
        return ["Testing evidence: details withheld because credential-like text was found."]
    return [line]


__all__ = ("fingerprint_digest", "status_lines", "testing_observability")
