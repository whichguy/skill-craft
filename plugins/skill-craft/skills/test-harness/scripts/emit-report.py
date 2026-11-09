#!/usr/bin/env python3
"""emit-report.py — pure report writer for test-harness runs.

Reads on-disk artifacts only. No --result override.

Writes: report.json, results.md, chat-card.md
Prints: test-harness RESULT=… line
Exit 0 on successful emit (including FAIL_*); exit 2 on INCOMPLETE_RUN / I/O error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MANIFEST_REQUIRED = (
    "repo", "repo_slug", "cmd", "profile", "source", "mode",
    "rounds_max", "run_dir",
)

RESULT_PASS = {"PASS_CLEAN", "PASS_CLEAN_SCOPED"}


def load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def list_rounds(run_dir: Path) -> list[int]:
    nums = []
    for p in run_dir.iterdir() if run_dir.is_dir() else []:
        if p.is_dir() and p.name.startswith("round-"):
            try:
                nums.append(int(p.name.split("-", 1)[1]))
            except ValueError:
                pass
    return sorted(nums)


# --- suite / control-channel parsing -----------------------------------------

# Result lines (ordered by specificity)
_CASE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "PASS test/foo.test.js" / "FAIL test/foo.js"
    ("pass", re.compile(r"^PASS\s+(\S+)")),
    ("fail", re.compile(r"^FAIL\s+(\S+)")),
    ("skip", re.compile(r"^SKIP(?:PED)?\s+(\S+)", re.I)),
    # "  PASS  case name" (indented, two spaces around the status)
    ("pass", re.compile(r"^\s{2,}PASS\s{2,}(.+?)\s*$")),
    ("fail", re.compile(r"^\s{2,}FAIL\s{2,}(.+?)\s*$")),
    # One padded label per suite: two-space indented label + trailing status.
    # Long labels can consume the full pad width, so whitespace before status
    # is optional.
    ("pass", re.compile(r"^\s{2}(.+?)[ \t]*[✓✔]\s*$")),
    ("fail", re.compile(r"^\s{2}(.+?)[ \t]*[×✗✕]\s*$")),
    ("skip", re.compile(r"^\s{2}(.+?)[ \t]*SKIP\s*$")),
    # "ok 1 - name" / "not ok 2 - name" (TAP)
    ("pass", re.compile(r"^ok\s+\d+\s+-?\s*(.*)$")),
    ("fail", re.compile(r"^not ok\s+\d+\s+-?\s*(.*)$")),
    # "✓ name" / "× name" / "✔"
    ("pass", re.compile(r"^[✓✔]\s+(.+)$")),
    ("fail", re.compile(r"^[×✗✕]\s+(.+)$")),
    # mocha-ish "  1) name"
    ("fail", re.compile(r"^\s+\d+\)\s+(.+)$")),
]

_SUMMARY_PATTERNS = [
    re.compile(r"Results:\s*(\d+)\s*passed,\s*(\d+)\s*failed", re.I),
    re.compile(r"(\d+)\s+passing", re.I),
    re.compile(r"#\s*tests\s+(\d+)", re.I),
]

_SUITE_ROLLUP = re.compile(
    r"^[✓✔×✗✕]\s+\d+/\d+\s+suites?\s+(?:passed|failed)\b",
    re.I | re.M,
)

# A runner's own diagnostics channel: "[tag] text" (a short bracketed tag at the start of the line).
_CONTROL_TAG = r"\[[A-Za-z][A-Za-z0-9_-]{0,15}\]"
_CONTROL_TAG_LINE = re.compile(r"^" + _CONTROL_TAG)

_OBS_KEEP = re.compile(
    r"(all assertions passed|Usage:|error|warning|WARN|assert|passed|failed|timeout|fallback)",
    re.I,
)

_PASSING_SIGNAL_PREFIX = re.compile(r"^\s*(?:PASS\b|ok\b|[✓✔])", re.I)
_PRIMARY_FAILURE_SIGNAL = re.compile(
    r"(?:\bError:|\bERROR\b|\bAssertionError\b|\bTraceback\b|\bpanic:|\bFATAL\b)",
    re.I,
)
_NAMED_FAILURE_SIGNAL = re.compile(
    r"^\s*(?:FAIL\b|not ok\b|[×✗✕])",
    re.I,
)
_SECONDARY_FAILURE_SIGNAL = re.compile(
    r"\b(?:failed|failure|timeout|timed out)\b",
    re.I,
)


def _failure_signal_rank(line: str) -> int | None:
    """Rank a genuine failure line; passing case descriptions are never signals."""
    if not line.strip() or _PASSING_SIGNAL_PREFIX.match(line):
        return None
    if _PRIMARY_FAILURE_SIGNAL.search(line):
        return 0
    if _NAMED_FAILURE_SIGNAL.match(line):
        return 1
    if _SECONDARY_FAILURE_SIGNAL.search(line):
        return 2
    return None


def _select_failure_signature(stderr: str, stdout: str) -> str | None:
    candidates: list[tuple[int, int, int, str]] = []
    for source_order, text in enumerate((stderr or "", stdout or "")):
        for line_order, line in enumerate(text.splitlines()):
            rank = _failure_signal_rank(line)
            if rank is not None:
                candidates.append((rank, source_order, line_order, line))
    if not candidates:
        return None
    return min(candidates)[3].replace("\r", "")[:200]


def _channel_stats(text: str, name: str, exit_code: int) -> dict[str, Any]:
    raw = text or ""
    lines = raw.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    bytes_n = len(raw.encode("utf-8", errors="replace"))
    # tagged control lines ("[tag] text")
    tagged_n = sum(1 for ln in nonempty if _CONTROL_TAG_LINE.match(ln))
    errorish = [
        ln for ln in lines
        if _failure_signal_rank(ln) is not None
    ]
    # Evaluation of the channel relative to exit code
    if bytes_n == 0:
        if name == "stderr" and exit_code == 0:
            status = "empty_ok"
            eval_s = "empty on success — normal for quiet suites"
        elif name == "stderr" and exit_code != 0:
            status = "empty_unexpected"
            eval_s = "empty on failure — failure detail may be on stdout only"
        elif name == "stdout" and exit_code != 0:
            status = "empty_unexpected"
            eval_s = "empty on failure — check stderr"
        else:
            status = "empty"
            eval_s = "no output captured"
    else:
        ctrl_ratio = (tagged_n / len(nonempty)) if nonempty else 0.0
        if (
            name == "stderr"
            and exit_code == 0
            and not errorish
            and tagged_n >= 5
            and ctrl_ratio >= 0.80
        ):
            # Tagged control channel ("[tag] …" lines) — intentional, not failure noise
            status = "control_ok"
            eval_s = (
                f"tagged control channel ({tagged_n}/{len(nonempty)} lines "
                f"[tag]) — not a failure signal"
            )
        elif name == "stderr" and exit_code == 0 and errorish:
            status = "noise_on_success"
            eval_s = (
                f"non-empty on success with {len(errorish)} error-shaped line(s) — "
                "reviewed as control-channel noise unless suite failed"
            )
        elif name == "stderr" and exit_code == 0:
            status = "noise_on_success"
            eval_s = (
                f"non-empty on success ({len(nonempty)} lines) — "
                "informational/control output, not treated as suite failure"
            )
        elif exit_code != 0 and errorish:
            status = "failure_signal"
            eval_s = f"contains {len(errorish)} error-shaped line(s); used for failure excerpt"
        elif exit_code != 0:
            status = "present"
            eval_s = "non-empty; scanned for failure signals"
        else:
            status = "present"
            eval_s = f"captured ({len(nonempty)} non-empty lines); primary suite narrative channel"

    return {
        "channel": name,
        "bytes": bytes_n,
        "lines": len(lines),
        "nonempty_lines": len(nonempty),
        "empty": bytes_n == 0,
        "tagged_control_lines": tagged_n if name == "stderr" else 0,
        "error_shaped_lines": len(errorish),
        # Previews for paste surfaces must be redacted (raw logs stay on disk)
        "error_shaped_sample": [
            _safe_redact(ln)[:240] for ln in errorish[:8]
        ],
        "status": status,
        "evaluation": eval_s,
        "preview_head": _safe_redact("\n".join(lines[:12])[:1500]) if lines else "",
        "preview_tail": _safe_redact("\n".join(lines[-12:])[:1500]) if lines else "",
    }


def _safe_redact(text: str) -> str:
    try:
        scripts = Path(__file__).resolve().parent
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from control_policy import redact_text
        return redact_text(text or "")
    except Exception:
        return text or ""


def _is_rollup_line(name: str, raw: str) -> bool:
    """Module summary lines (e.g. 'PASS 15 foo tests') are not real cases."""
    n = (name or "").strip()
    r = (raw or "").strip()
    if re.fullmatch(r"\d+", n):
        return True
    # "PASS 15 parser tests" / "PASS 5 …"
    if re.match(r"^(PASS|FAIL|SKIP(?:PED)?)\s+\d+\s+\S", r, re.I):
        return True
    if _SUITE_ROLLUP.match(r):
        return True
    return False


def _humanize_case_name(name: str) -> str:
    """test_foo_bar_baz → foo bar baz (readable claim sketch)."""
    n = (name or "").strip()
    n = re.sub(r"\.(js|ts|py|go|rs)$", "", n)
    n = n.split("/")[-1]
    if n.startswith("test_"):
        n = n[5:]
    n = n.replace("_", " ").replace("-", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n or (name or "").strip()


# Ordered group rules: first match wins. (id, name_regex, title, verifies claim).
# None ship by default. A rule states what a test "verifies" from its name alone, which only the project that owns the
# naming convention can know; a wrong rule would put a false claim in every report. Cases fall back to the path-shaped
# group or the generic one in _group_for_case.
_CASE_GROUP_RULES: list[tuple[str, re.Pattern[str], str, str]] = []


def _group_for_case(name: str) -> tuple[str, str, str]:
    """Return (group_id, title, verifies)."""
    n = name or ""
    for gid, pat, title, verifies in _CASE_GROUP_RULES:
        if pat.search(n):
            return gid, title, verifies
    # path-ish groups (file-based runners)
    if "/" in n or n.endswith((".js", ".ts", ".py", ".go")):
        return "file_suite", "File / module suite", "per-file or per-module assertions from the runner"
    return "other", "Other cases", "suite-reported case (see name)"


def build_case_inventory(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Group real cases for operator narrative: what ran + what was verified."""
    real = [c for c in cases if c.get("kind") != "rollup"]
    rollups = [c for c in cases if c.get("kind") == "rollup"]
    groups_map: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for c in real:
        name = c.get("name") or ""
        gid, title, verifies = _group_for_case(name)
        if gid not in groups_map:
            groups_map[gid] = {
                "id": gid,
                "title": title,
                "verifies": verifies,
                "pass": 0,
                "fail": 0,
                "skip": 0,
                "cases": [],
            }
            order.append(gid)
        g = groups_map[gid]
        st = c.get("status") or "pass"
        if st == "fail":
            g["fail"] += 1
        elif st == "skip":
            g["skip"] += 1
        else:
            g["pass"] += 1
        g["cases"].append({
            "name": name,
            "status": st,
            "claim": _humanize_case_name(name),
            "observation": c.get("observation"),
            "raw": c.get("raw"),
        })

    groups = [groups_map[k] for k in order]
    pass_n = sum(g["pass"] for g in groups)
    fail_n = sum(g["fail"] for g in groups)
    skip_n = sum(g["skip"] for g in groups)

    verified_bullets: list[str] = []
    for g in groups:
        status_word = "all PASS" if g["fail"] == 0 and g["pass"] else (
            f"{g['fail']} FAIL" if g["fail"] else "mixed"
        )
        verified_bullets.append(
            f"**{g['title']}** ({g['pass']} pass"
            + (f", {g['fail']} fail" if g["fail"] else "")
            + (f", {g['skip']} skip" if g["skip"] else "")
            + f") — {status_word}: {g['verifies']}"
        )

    module_summaries = []
    for r in rollups:
        raw = (r.get("raw") or "").strip()
        # strip leading PASS/FAIL
        body = re.sub(
            r"^(?:(?:PASS|FAIL|SKIP(?:PED)?)|[✓✔×✗✕])\s+",
            "",
            raw,
            flags=re.I,
        )
        if body:
            module_summaries.append(body[:160])

    return {
        "real_case_count": len(real),
        "rollup_count": len(rollups),
        "pass_count": pass_n,
        "fail_count": fail_n,
        "skip_count": skip_n,
        "groups": groups,
        "verified_bullets": verified_bullets,
        "module_summaries": module_summaries,
        "failed_names": [c.get("name") for c in real if c.get("status") == "fail"],
        "passed_names": [c.get("name") for c in real if c.get("status") == "pass"],
        "skipped_names": [c.get("name") for c in real if c.get("status") == "skip"],
    }


def _extract_cases(stdout: str, stderr: str) -> list[dict[str, Any]]:
    """Ordered unique-ish list of test cases with status and observation."""
    cases: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    pending_obs: list[str] = []

    def flush_obs() -> str | None:
        nonlocal pending_obs
        if not pending_obs:
            return None
        # keep last 3 observation lines
        obs = " | ".join(pending_obs[-3:])
        pending_obs = []
        return obs[:300]

    for src_name, text in (("stdout", stdout or ""), ("stderr", stderr or "")):
        for ln in text.splitlines():
            matched = False
            for status, pat in _CASE_PATTERNS:
                m = pat.match(ln)
                if not m:
                    continue
                name = (m.group(1) if m.lastindex else ln).strip()
                # TAP plan lines etc.
                if not name or name.startswith("#"):
                    matched = True
                    break
                raw = ln.strip()[:240]
                kind = "rollup" if _is_rollup_line(name, raw) else "case"
                if kind == "rollup":
                    # Keep full remainder so "PASS 2 foo" and "PASS 2 bar" are distinct
                    name = re.sub(
                        r"^(PASS|FAIL|SKIP(?:PED)?)\s+", "", raw, count=1, flags=re.I
                    ).strip() or name
                    key = ("rollup", status, raw)
                else:
                    key = (status, name)
                obs = flush_obs()
                if key not in seen:
                    seen.add(key)
                    cases.append({
                        "name": name,
                        "status": status,
                        "source": src_name,
                        "raw": raw,
                        "observation": obs,
                        "kind": kind,
                        "claim": None if kind == "rollup" else _humanize_case_name(name),
                    })
                matched = True
                break
            if matched:
                continue
            # accumulate observation context (detail lines before a PASS)
            if ln.strip() and _OBS_KEEP.search(ln) and not re.match(r"^\s*#", ln):
                # skip pure PASS/FAIL already handled
                if not re.match(r"^\s*(PASS|FAIL|ok |not ok )", ln):
                    pending_obs.append(ln.strip()[:200])
                    if len(pending_obs) > 6:
                        pending_obs = pending_obs[-6:]
    return cases


def _summary_from_text(text: str) -> dict[str, int | None]:
    for pat in _SUMMARY_PATTERNS:
        m = pat.search(text or "")
        if not m:
            continue
        if pat.pattern.lower().startswith("results:"):
            return {
                "summary_passed": int(m.group(1)),
                "summary_failed": int(m.group(2)),
            }
        if "passing" in pat.pattern:
            return {"summary_passed": int(m.group(1)), "summary_failed": None}
    return {"summary_passed": None, "summary_failed": None}


def _parse_result_json(text: str) -> dict[str, Any] | None:
    """Extract the last RESULT_JSON {…} line (an optional machine-readable summary a runner may print)."""
    if not text:
        return None
    last = None
    for ln in text.splitlines():
        s = ln.strip()
        if not s.startswith("RESULT_JSON "):
            continue
        payload = s[len("RESULT_JSON ") :].strip()
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if isinstance(obj, dict) and "total" in obj:
            last = obj
    return last


def parse_suite_logs(stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    """Full suite + control-channel evaluation from stdout/stderr."""
    out = stdout or ""
    err = stderr or ""
    combined = out + "\n" + err
    rollup_stdout_is_authoritative = bool(_SUITE_ROLLUP.search(out))
    # A suite rollup line may be followed by a replay of a failing suite's raw log on stderr. Those
    # internal PASS/FAIL lines are diagnostics, not additional top-level
    # suites, so only the top-level stdout inventory is public case data.
    cases = _extract_cases(out, "" if rollup_stdout_is_authoritative else err)

    # Prefer real cases (exclude module rollups like "PASS 15 foo tests")
    real = [c for c in cases if c.get("kind") != "rollup"]
    pass_n = sum(1 for c in real if c["status"] == "pass")
    fail_n = sum(1 for c in real if c["status"] == "fail")
    skip_n = sum(1 for c in real if c["status"] == "skip")
    if pass_n == 0 and fail_n == 0 and not real:
        # fall back to crude line counts (still exclude rollup-shaped lines)
        crude_pass = crude_fail = crude_skip = 0
        for ln in combined.splitlines():
            if re.match(r"^\s*PASS\b", ln):
                name = ln.strip()[4:].strip()
                raw = ln.strip()[:240]
                if _is_rollup_line(name.split()[0] if name else "", raw):
                    continue
                crude_pass += 1
                if not cases:
                    cases.append({
                        "name": name or ln.strip(),
                        "status": "pass",
                        "source": "stdout",
                        "raw": raw,
                        "observation": None,
                        "kind": "case",
                        "claim": _humanize_case_name(name),
                    })
            elif re.match(r"^\s*FAIL\b", ln):
                name = ln.strip()[4:].strip()
                raw = ln.strip()[:240]
                if _is_rollup_line(name.split()[0] if name else "", raw):
                    continue
                crude_fail += 1
                if not any(c.get("status") == "fail" for c in cases):
                    cases.append({
                        "name": name or ln.strip(),
                        "status": "fail",
                        "source": "stdout",
                        "raw": raw,
                        "observation": None,
                        "kind": "case",
                        "claim": _humanize_case_name(name),
                    })
            elif re.search(r"\bSKIP(?:PED)?\b", ln, re.I):
                crude_skip += 1
        if crude_pass == 0 and crude_fail == 0:
            pass_count = fail_count = skip_count = None
        else:
            pass_count, fail_count, skip_count = crude_pass, crude_fail, crude_skip
            real = [c for c in cases if c.get("kind") != "rollup"]
    else:
        pass_count, fail_count, skip_count = pass_n, fail_n, skip_n

    summ = _summary_from_text(combined)
    # Prefer explicit Results: line when present and it covers real cases
    # (do not let rollup-inflated lines win over named case inventory)
    if summ.get("summary_passed") is not None and pass_count is not None:
        # Only adopt summary if we have no named real cases, or summary matches
        if not real:
            pass_count = summ["summary_passed"]
            if summ.get("summary_failed") is not None:
                fail_count = summ["summary_failed"]
        elif summ.get("summary_failed") is not None and summ["summary_failed"] > (fail_count or 0):
            # trust explicit fail count if higher (runner summary can be SoT for fails)
            fail_count = summ["summary_failed"]

    failure_signature = (
        _select_failure_signature(err, out) if exit_code != 0 else None
    )
    excerpt = None
    if exit_code != 0:
        lines = combined.splitlines()
        idx = None
        for i, ln in enumerate(lines):
            if _failure_signal_rank(ln) is not None:
                idx = i
                break
        if idx is not None:
            excerpt = "\n".join(lines[max(0, idx - 2) : idx + 18])[:2000]
        else:
            nonempty = [ln for ln in lines if ln.strip()]
            excerpt = "\n".join(nonempty[-20:])[:2000] if nonempty else None

    stdout_ch = _channel_stats(out, "stdout", exit_code)
    stderr_ch = _channel_stats(err, "stderr", exit_code)

    inventory = build_case_inventory(cases)
    # Align public counts with inventory (real cases only)
    if inventory["real_case_count"] > 0:
        pass_count = inventory["pass_count"]
        fail_count = inventory["fail_count"]
        skip_count = inventory["skip_count"]

    # Prefer RESULT_JSON (an optional runner summary) for suite-level counts.
    # Named case inventory may be empty when runner uses dots-only or CI quiet.
    result_json = _parse_result_json(
        out if rollup_stdout_is_authoritative else combined
    )
    suite_summary_source = (
        "rollup_stdout" if rollup_stdout_is_authoritative else None
    )
    if result_json is not None:
        total = int(result_json.get("total") or 0)
        failures = int(result_json.get("failures") or 0)
        errors = int(result_json.get("errors") or 0)
        skipped = int(result_json.get("skipped") or 0)
        rj_fail = failures + errors
        rj_pass = max(0, total - failures - errors - skipped)
        # Prefer RESULT_JSON when it is more informative than case inventory
        if total > 0 and (
            inventory.get("real_case_count", 0) == 0
            or total >= (inventory.get("real_case_count") or 0)
        ):
            pass_count = rj_pass
            fail_count = rj_fail
            skip_count = skipped
            suite_summary_source = "result_json"
            # Annotate inventory so cards show RESULT_JSON totals
            inventory = dict(inventory)
            inventory["pass_count"] = pass_count
            inventory["fail_count"] = fail_count
            inventory["skip_count"] = skip_count
            inventory["real_case_count"] = total
            inventory["result_json"] = result_json
            inventory["module_summaries"] = list(inventory.get("module_summaries") or []) + [
                f"RESULT_JSON total={total} failures={failures} errors={errors} skipped={skipped}"
            ]

    # Cross-check: exit vs parsed fails
    consistency = []
    if exit_code == 0 and (fail_count or 0) > 0:
        consistency.append(
            f"WARN: exit 0 but parser found {fail_count} FAIL case line(s) — review cases list"
        )
    if exit_code != 0 and (fail_count or 0) == 0 and not excerpt:
        consistency.append(
            "WARN: non-zero exit but no FAIL cases/excerpt parsed — see raw channel previews"
        )
    if exit_code == 0 and (fail_count or 0) == 0:
        consistency.append("OK: exit 0 consistent with zero parsed FAIL cases")
    if exit_code != 0 and ((fail_count or 0) > 0 or excerpt):
        consistency.append("OK: non-zero exit supported by FAIL cases and/or failure excerpt")
    if suite_summary_source == "result_json":
        consistency.append(
            f"OK: suite counts from RESULT_JSON total={result_json.get('total')} "
            f"fail={fail_count} skip={skip_count}"
        )
    elif suite_summary_source == "rollup_stdout":
        consistency.append(
            "OK: suite counts from the top-level stdout rollup; "
            "stderr treated as replay diagnostics"
        )

    real_cases = [c for c in cases if c.get("kind") != "rollup"]
    case_count = (
        inventory.get("real_case_count")
        if suite_summary_source == "result_json"
        else (len(real_cases) if real_cases else len(cases))
    )
    return {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
        "case_count": case_count,
        "cases": cases,  # full list including rollups (kind marked)
        "case_inventory": inventory,
        "suite_summary_source": suite_summary_source,
        "result_json": result_json,
        "failure_signature": failure_signature,
        "first_failure_excerpt": excerpt,
        "pass_tail": [
            c["raw"] for c in real_cases if c["status"] == "pass"
        ][-15:] or None,
        "control_channels": {
            "stdout": stdout_ch,
            "stderr": stderr_ch,
            "consistency": consistency,
            "evaluated": True,
        },
        "summary_line": summ,
    }


def split_findings(se: dict[str, Any] | None) -> tuple[list, list, list, list]:
    """Return fail, note, baseline, services_all."""
    if not se:
        return [], [], [], []
    fails, notes, baseline = [], [], []
    for item in se.get("delta") or []:
        cls = item.get("class")
        disp = item.get("disposition")
        if cls == "BASELINE" or item.get("change") == "unchanged-baseline":
            baseline.append(item)
            continue
        if disp == "fail":
            fails.append(item)
        elif disp == "note":
            notes.append(item)
    services = se.get("services") or []
    for s in services:
        if s.get("disposition") == "fail":
            fails.append(s)
        elif s.get("disposition") == "note":
            notes.append(s)
    # Control-channel policy findings affect side_effects_ok / FAIL_SIDE_EFFECTS
    for c in se.get("control") or []:
        if c.get("disposition") == "fail":
            fails.append(c)
        elif c.get("disposition") == "note":
            notes.append(c)
    return fails, notes, baseline, services


def material_from_delta(delta: dict[str, Any] | None) -> tuple[list, list]:
    if not delta:
        return [], []
    material, baseline = [], []
    for d in delta.get("delta") or []:
        if d.get("change") == "unchanged-baseline":
            baseline.append(d)
        else:
            material.append(d)
    return material, baseline


def derive_result(
    manifest: dict[str, Any] | None,
    metas: list[dict[str, Any]],
    se: dict[str, Any] | None,
    terminal: dict[str, Any] | None,
    se_missing_after_meta: bool,
) -> tuple[str, list[str]]:
    annotations: list[str] = []
    if not manifest:
        return "INCOMPLETE_RUN", ["missing_manifest"]
    for k in MANIFEST_REQUIRED:
        if k not in manifest or manifest[k] in (None, ""):
            return "INCOMPLETE_RUN", [f"missing_manifest_field:{k}"]

    if se_missing_after_meta:
        return "INCOMPLETE_RUN", ["missing_classifier_output"]

    if terminal:
        if terminal.get("stop") == "timeout_budget_exhausted":
            return "STOPPED_TIMEOUT_BUDGET", []
        if terminal.get("stop") == "no_progress":
            return "STOPPED_NO_PROGRESS", []

    rounds_completed = len(metas)
    rounds_max = int(manifest.get("rounds_max") or 1)

    # same-error ×3
    if rounds_completed >= 3:
        sigs = [m.get("error_sig") or "none" for m in metas[-3:]]
        if all(s != "none" for s in sigs) and len(set(sigs)) == 1:
            return "STOPPED_SAME_ERROR", []

    suite_ok = bool(metas) and int(metas[-1].get("exit", 1)) == 0
    if se is None:
        side_ok = False
    else:
        side_ok = bool(se.get("side_effects_ok", se.get("summary", {}).get("fail", 1) == 0))

    fs_scope = "full"
    if se:
        fs_scope = se.get("fs_scope") or "full"

    # max-rounds stop only when not pass
    would_pass = suite_ok and side_ok
    if rounds_completed >= rounds_max and rounds_completed >= 1 and not would_pass:
        # A failed last round that used the whole budget keeps its specific FAIL_* result here;
        # the STOPPED_MAX_ROUNDS upgrade for fix-loop runs is applied after the result is derived.
        pass

    if suite_ok and side_ok:
        if fs_scope == "full":
            result = "PASS_CLEAN"
        else:
            result = "PASS_CLEAN_SCOPED"
    elif suite_ok and not side_ok:
        result = "FAIL_SIDE_EFFECTS"
    elif (not suite_ok) and side_ok:
        result = "FAIL_SUITE"
    else:
        result = "FAIL_BOTH"

    if (
        result not in RESULT_PASS
        and rounds_completed >= rounds_max
        and rounds_completed >= 1
    ):
        # Only upgrade to STOPPED_MAX if we actually exhausted budget mid-loop;
        # for once mode rounds_max=1 a single FAIL is FAIL_* not STOPPED.
        mode = manifest.get("mode") or "once"
        if mode == "fix-loop" and rounds_completed >= rounds_max:
            result = "STOPPED_MAX_ROUNDS"

    if manifest.get("mode") == "once":
        annotations.append("audit_only")
    if manifest.get("profile") == "unknown":
        annotations.append("profile_unknown")
    if manifest.get("assume_fast"):
        annotations.append("assume_fast")

    return result, annotations


def next_steps_for(
    result: str,
    manifest: dict[str, Any],
    has_worktree_patch: bool,
    notes: list,
) -> list[str]:
    steps: list[str] = []
    mode = manifest.get("mode") or "once"
    if result in RESULT_PASS:
        steps.append("done — suite green, checkout clean")
        if any(n.get("class") == "TMPDIR_LEAK" for n in notes):
            steps.append("optional: tighten test cleanup for TMPDIR leftovers (sandbox only)")
        return steps
    if result == "FAIL_SUITE":
        steps.append("fix product/tests for the suite failure; re-run the harness")
        return steps
    if result == "FAIL_SIDE_EFFECTS":
        if mode == "once":
            steps.append(
                "audit-only mode — re-run with --mode fix-loop (add --assume-fast when the profile is unknown); "
                "or isolate writes under TMPDIR / restore fixtures"
            )
        else:
            steps.append("fix test isolation or product writes; restore-first then re-run")
        if has_worktree_patch:
            steps.append("apply fixes.patch or open worktree path")
        return steps
    if result == "FAIL_BOTH":
        steps.append("fix suite failures and unintended writes; re-run harness")
        return steps
    if result == "INCOMPLETE_RUN":
        steps.append("ensure init-run + full phase pipeline (pre → run → post → classify → emit-report)")
        return steps
    if result.startswith("STOPPED_"):
        steps.append(f"stopped ({result}); inspect round logs and decide next campaign")
        return steps
    steps.append("inspect report.json and re-run")
    return steps


def verdict_narrative(
    result: str,
    suite_ok: bool,
    material_count: int,
    fail_n: int,
    note_n: int,
) -> str:
    if result == "PASS_CLEAN":
        base = "Suite passed. No product paths changed."
        if note_n:
            base += f" {note_n} non-blocking note(s) (see Notes)."
        return base
    if result == "PASS_CLEAN_SCOPED":
        return (
            "Suite passed within scoped FS audit "
            "(package prefix and/or git-visible + TMPDIR; not a full monorepo checkout claim)."
        )
    if result == "FAIL_SUITE":
        return "Suite failed. Side-effect gate is clean — pure test/product failure."
    if result == "FAIL_SIDE_EFFECTS":
        return (
            f"Suite passed but {fail_n} blocking side-effect finding(s); "
            f"material repo delta count={material_count}."
        )
    if result == "FAIL_BOTH":
        return "Suite failed and blocking side effects were detected."
    if result == "INCOMPLETE_RUN":
        return "Run artifacts incomplete; cannot certify suite or side effects."
    return f"Run ended with {result}."


def build_story(rep: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    """Operator narrative: final result, worked well, struggles, dive-in."""
    suite = rep.get("suite") or {}
    se = rep.get("side_effects") or {}
    fails = se.get("fail") or []
    notes = se.get("note") or []
    cases = suite.get("cases") or []
    inv = suite.get("case_inventory") or build_case_inventory(cases)
    cc = suite.get("control_channels") or {}
    pc = inv.get("pass_count", suite.get("pass_count"))
    fc = inv.get("fail_count", suite.get("fail_count")) or 0
    case_n = inv.get("real_case_count") or suite.get("case_count") or len(
        [c for c in cases if c.get("kind") != "rollup"]
    )
    material = rep.get("repo_fs", {}).get("material_count", 0)
    result = rep.get("result") or "INCOMPLETE_RUN"
    exit_c = suite.get("exit")

    worked: list[str] = []
    if exit_c == 0:
        worked.append(f"Suite exit 0 in {suite.get('duration_ms')}ms")
    if pc is not None:
        worked.append(
            f"{pc} real test case(s) PASS"
            + (f" (0 FAIL)" if not fc else f", {fc} FAIL")
            + (f" · {case_n} named cases executed" if case_n else "")
        )
    elif case_n:
        worked.append(f"{case_n} case line(s) parsed from control channels")
    if inv.get("rollup_count"):
        worked.append(
            f"filtered {inv['rollup_count']} module rollup line(s) "
            "(e.g. 'PASS N … tests') out of case counts"
        )
    for g in inv.get("groups") or []:
        if g.get("fail"):
            continue
        if g.get("pass"):
            worked.append(f"{g['title']}: {g['pass']} PASS — {g['verifies'][:120]}")
    out_st = (cc.get("stdout") or {}).get("status")
    err_st = (cc.get("stderr") or {}).get("status")
    if out_st in ("present", "empty_ok"):
        worked.append(f"stdout `{out_st}` — {(cc.get('stdout') or {}).get('evaluation', '')[:100]}")
    if err_st == "empty_ok":
        worked.append("stderr empty on success — normal for quiet suites")
    for msg in cc.get("consistency") or []:
        if msg.startswith("OK:"):
            worked.append(msg)
    if material == 0 and result in RESULT_PASS:
        worked.append("material_delta=0 (no product path changes during suite)")
    ap = rep.get("audit_prefix") or ""
    if ap:
        worked.append(f"package-scoped FS audit under `{ap}`")
    elif (rep.get("fs_scope") or "") == "package":
        worked.append("package-scoped FS audit")
    if not worked:
        worked.append("See suite evidence and control channels below")

    struggles: list[dict[str, str]] = []
    for f in fails:
        struggles.append({
            "severity": "blocking",
            "title": f.get("class") or "FINDING",
            "detail": f.get("path") or f.get("env") or f.get("change") or "",
            "impact": f.get("hint") or "blocking side-effect — needs action",
        })
    for c in cases:
        if c.get("status") == "fail" and c.get("kind") != "rollup":
            struggles.append({
                "severity": "blocking",
                "title": "TEST_CASE_FAIL",
                "detail": c.get("name") or c.get("raw") or "",
                "impact": c.get("observation") or c.get("claim") or "failed case from control channel",
            })
    if exit_c not in (0, None) and not any(s["title"] == "TEST_CASE_FAIL" for s in struggles):
        struggles.append({
            "severity": "blocking",
            "title": "SUITE_EXIT_NONZERO",
            "detail": f"exit={exit_c} error_sig={suite.get('error_sig')}",
            "impact": "suite failure — see first_failure_excerpt",
        })
    for n in notes:
        title = n.get("class") or "NOTE"
        if title == "TMPDIR_LEAK":
            sample = (n.get("sample_rel") or n.get("sample") or [""])[0]
            detail = f"×{n.get('count', 1)} {sample}"
            impact = n.get("hint") or "sandbox only — not repo dirt"
        else:
            detail = n.get("path") or n.get("env") or (n.get("excerpt") or "")[:120]
            impact = n.get("hint") or "non-blocking note"
        struggles.append({
            "severity": "note",
            "title": title,
            "detail": str(detail),
            "impact": impact,
        })
    if err_st == "noise_on_success":
        ch = cc.get("stderr") or {}
        struggles.append({
            "severity": "note",
            "title": "stderr_noise_on_success",
            "detail": f"{ch.get('bytes', 0)} bytes / {ch.get('nonempty_lines', 0)} nonempty lines",
            "impact": "informational/control output — not treated as suite failure",
        })
    elif err_st == "control_ok":
        ch = cc.get("stderr") or {}
        worked.append(
            f"stderr control_ok — tagged control channel "
            f"({ch.get('tagged_control_lines', '?')} [tag] lines)"
        )
    for msg in cc.get("consistency") or []:
        if msg.startswith("WARN"):
            struggles.append({
                "severity": "friction",
                "title": "consistency_warn",
                "detail": msg,
                "impact": "parser/exit mismatch — inspect raw logs",
            })
    if rep.get("rounds_completed", 1) > 1:
        struggles.append({
            "severity": "friction",
            "title": "multi_round",
            "detail": f"completed {rep.get('rounds_completed')}/{rep.get('rounds_max')} rounds",
            "impact": "earlier rounds may have failed — see round metas",
        })

    # Supervisor: extra unintended cues not already listed as classifier fails
    sup = rep.get("supervisor") or {}
    existing_titles = {s.get("title") for s in struggles}
    for s in (sup.get("unintended_signals") or [])[:12]:
        sev = s.get("severity") or "note"
        if sev == "informational":
            continue
        title = s.get("title") or "signal"
        if title in existing_titles:
            continue
        if any((f.get("class") or "") == title for f in fails):
            continue
        struggles.append({
            "severity": "blocking" if sev == "blocking" else "friction",
            "title": title,
            "detail": f"[{s.get('channel')}] {s.get('evidence') or ''}"[:200],
            "impact": s.get("why_unintended") or "supervisor unintended-consequence cue",
        })
        existing_titles.add(title)

    # final sentence — prefer supervisor conclusion when available
    conc = (sup.get("conclusion") or {})
    if conc.get("summary"):
        final = conc["summary"]
    elif result in RESULT_PASS:
        final = f"Suite passed"
        if pc is not None:
            final += f" ({pc} PASS"
            if fc:
                final += f", {fc} FAIL"
            final += ")"
        final += ". Checkout clean." if material == 0 else f". material_delta={material}."
        if notes:
            final += f" {len(notes)} non-blocking note(s)."
    elif result == "FAIL_SUITE":
        final = f"Suite failed (exit {exit_c}). Side-effect gate clean."
    elif result == "FAIL_SIDE_EFFECTS":
        final = f"Suite green but {len(fails)} blocking side-effect(s)."
    elif result == "FAIL_BOTH":
        final = "Suite failed and blocking side effects present."
    else:
        final = verdict_narrative(result, exit_c == 0, material, len(fails), len(notes))

    rd = str(run_dir)
    last_round = max(rep.get("rounds_completed") or 1, 1)
    dive = {
        "html": f"{rd}/report.html",
        "results_md": f"{rd}/results.md",
        "report_json": f"{rd}/report.json",
        "chat_card": f"{rd}/chat-card.md",
        "stdout": f"{rd}/round-{last_round}/stdout.log",
        "stderr": f"{rd}/round-{last_round}/stderr.log",
        "side_effects_round": f"{rd}/round-{last_round}/side-effects.json",
        "commands": [
            f"# open in a browser: {rd}/report.html",
            f"less '{rd}/results.md'",
            f"jq . '{rd}/report.json'",
            f"less '{rd}/round-{last_round}/stdout.log'",
            f"less '{rd}/round-{last_round}/stderr.log'",
        ],
    }
    return {
        "final_result": result,
        "final_sentence": final,
        "worked_well": worked,
        "struggles": struggles,
        "dive_in": dive,
        "case_inventory": inv,
        "what_was_attempted": list(sup.get("what_was_attempted") or []),
        "supervisor_conclusion": conc,
    }


def _html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(rep: dict[str, Any]) -> str:
    story = rep.get("story") or {}
    result = rep.get("result") or "?"
    badge = {
        "PASS_CLEAN": "#1a7f37",
        "PASS_CLEAN_SCOPED": "#3d8b40",
        "FAIL_SUITE": "#cf222e",
        "FAIL_SIDE_EFFECTS": "#bf8700",
        "FAIL_BOTH": "#cf222e",
        "INCOMPLETE_RUN": "#6e7781",
    }.get(result, "#6e7781")
    if result.startswith("STOPPED_"):
        badge = "#bf8700"

    suite = rep.get("suite") or {}
    se = rep.get("side_effects") or {}
    cases = suite.get("cases") or []
    inv = _inventory_from_rep(rep)
    struggles = story.get("struggles") or []
    worked = story.get("worked_well") or []
    dive = story.get("dive_in") or {}

    def li_list(items: list[str]) -> str:
        if not items:
            return "<li><em>none</em></li>"
        return "\n".join(f"<li>{_html_escape(x)}</li>" for x in items)

    struggle_rows = []
    for s in struggles:
        sev = s.get("severity") or "note"
        color = {"blocking": "#cf222e", "friction": "#bf8700", "note": "#0969da"}.get(sev, "#0969da")
        struggle_rows.append(
            f"<tr><td style='color:{color};font-weight:600'>{_html_escape(sev)}</td>"
            f"<td><code>{_html_escape(s.get('title',''))}</code></td>"
            f"<td>{_html_escape(s.get('detail',''))}</td>"
            f"<td>{_html_escape(s.get('impact',''))}</td></tr>"
        )
    if not struggle_rows:
        struggle_rows.append("<tr><td colspan='4'><em>No struggles recorded</em></td></tr>")

    group_rows = []
    for g in inv.get("groups") or []:
        res = f"{g.get('pass', 0)} PASS"
        if g.get("fail"):
            res += f" · {g['fail']} FAIL"
        if g.get("skip"):
            res += f" · {g['skip']} SKIP"
        group_rows.append(
            f"<tr><td><strong>{_html_escape(g.get('title',''))}</strong></td>"
            f"<td>{_html_escape(res)}</td>"
            f"<td>{_html_escape(g.get('verifies',''))}</td></tr>"
        )
    if not group_rows:
        group_rows.append(
            "<tr><td colspan='3'><em>No case groups — see flat table / raw logs</em></td></tr>"
        )

    inv_case_blocks = []
    for g in inv.get("groups") or []:
        rows = []
        for c in g.get("cases") or []:
            st = (c.get("status") or "pass").upper()
            rows.append(
                f"<tr><td>{st}</td>"
                f"<td><code>{_html_escape(c.get('name',''))}</code></td>"
                f"<td>{_html_escape(c.get('claim') or '')}</td></tr>"
            )
        fail_bit = f", {g.get('fail')} fail" if g.get("fail") else ""
        inv_case_blocks.append(
            f"<h3>{_html_escape(g.get('title',''))} "
            f"<span class='muted'>({g.get('pass', 0)} pass{fail_bit})</span></h3>"
            f"<table><thead><tr><th>Status</th><th>Name</th><th>Claim / achieved</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    inv_cases_html = "\n".join(inv_case_blocks) if inv_case_blocks else "<p class='muted'>No cases</p>"

    case_rows = []
    for i, c in enumerate(cases, 1):
        st = c.get("status") or ""
        mark = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}.get(st, st)
        kind = c.get("kind") or "case"
        case_rows.append(
            f"<tr><td>{i}</td><td>{mark}</td><td>{_html_escape(kind)}</td>"
            f"<td><code>{_html_escape(c.get('name',''))}</code></td>"
            f"<td>{_html_escape(c.get('claim') or '')}</td>"
            f"<td>{_html_escape(c.get('source',''))}</td>"
            f"<td>{_html_escape(c.get('observation') or '')}</td></tr>"
        )
    if not case_rows:
        case_rows.append("<tr><td colspan='7'><em>No cases parsed — see raw logs</em></td></tr>")

    cc = suite.get("control_channels") or {}
    ch_rows = []
    for name in ("stdout", "stderr"):
        ch = cc.get(name) or {}
        ch_rows.append(
            f"<tr><td>{name}</td><td><code>{_html_escape(ch.get('status',''))}</code></td>"
            f"<td>{ch.get('bytes', 0)}</td><td>{ch.get('nonempty_lines', 0)}</td>"
            f"<td>{_html_escape(ch.get('evaluation',''))}</td></tr>"
        )

    cmds = dive.get("commands") or []
    cmd_lis = "\n".join(f"<li><code>{_html_escape(c)}</code></li>" for c in cmds)
    real_n = inv.get("real_case_count") or 0
    roll_n = inv.get("rollup_count") or 0

    sup = rep.get("supervisor") or {}
    conc = sup.get("conclusion") or {}
    att_lis = "\n".join(
        f"<li>{_html_escape(a)}</li>" for a in (sup.get("what_was_attempted") or [])[:12]
    ) or "<li><em>none</em></li>"
    sig_rows = []
    for s in (sup.get("unintended_signals") or [])[:20]:
        sev = s.get("severity") or "informational"
        sig_rows.append(
            f"<tr><td class='sev-{_html_escape(sev)}'>{_html_escape(sev)}</td>"
            f"<td><code>{_html_escape(s.get('title',''))}</code></td>"
            f"<td>{_html_escape(s.get('channel',''))}</td>"
            f"<td><code>{_html_escape((s.get('evidence') or '')[:160])}</code></td>"
            f"<td>{_html_escape(s.get('why_unintended') or '')}</td></tr>"
        )
    if not sig_rows:
        sig_rows.append(
            "<tr><td colspan='5'><em>No unintended-consequence signals detected</em></td></tr>"
        )
    sup_summary = _html_escape(conc.get("summary") or story.get("final_sentence") or "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>test-harness · {_html_escape(rep.get('repo_slug',''))} · {_html_escape(result)}</title>
<style>
  :root {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
  body {{ margin: 0; background: #0d1117; color: #e6edf3; line-height: 1.45; }}
  main {{ max-width: 960px; margin: 0 auto; padding: 1.25rem; }}
  h1 {{ font-size: 1.35rem; margin: 0 0 .35rem; }}
  h2 {{ font-size: 1.05rem; margin: 1.25rem 0 .5rem; }}
  h3 {{ font-size: .95rem; margin: 1rem 0 .35rem; color: #c9d1d9; }}
  .hero {{ border-radius: 12px; padding: 1rem 1.15rem; background: #161b22; border: 1px solid #30363d; }}
  .badge {{ display: inline-block; padding: .2rem .65rem; border-radius: 999px; background: {badge};
            color: #fff; font-weight: 700; letter-spacing: .02em; }}
  .muted {{ color: #8b949e; font-size: .92rem; }}
  .panel {{ border-radius: 12px; padding: .9rem 1.1rem; margin-top: 1rem; border: 1px solid #30363d; }}
  .well {{ background: #12261e; border-color: #238636; }}
  .struggle {{ background: #2a2111; border-color: #9e6a03; }}
  .dive {{ background: #0d2137; border-color: #1f6feb; }}
  .sup {{ background: #1a1f2e; border-color: #6e40c9; }}
  .sev-blocking {{ color: #ff7b72; font-weight: 600; }}
  .sev-suspicious {{ color: #d29922; font-weight: 600; }}
  .sev-informational {{ color: #79c0ff; }}
  .inventory {{ background: #161b22; border-color: #388bfd; }}
  ul {{ margin: .35rem 0 .2rem 1.1rem; padding: 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th, td {{ text-align: left; padding: .35rem .45rem; border-bottom: 1px solid #30363d; vertical-align: top; }}
  th {{ color: #8b949e; font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85em; }}
  details {{ margin-top: .75rem; }}
  summary {{ cursor: pointer; color: #58a6ff; }}
  footer {{ margin-top: 1.5rem; color: #8b949e; font-size: .85rem; }}
  .sentence {{ margin-top: .55rem; font-size: 1.02rem; }}
</style>
</head>
<body>
<main>
  <section class="hero">
    <div class="badge">{_html_escape(result)}</div>
    <h1>{_html_escape(rep.get('repo_slug',''))} · test-harness</h1>
    <div class="muted"><code>{_html_escape(rep.get('cmd',''))}</code>
      · profile <strong>{_html_escape(rep.get('profile',''))}</strong>
      · mode {_html_escape(rep.get('mode',''))}
      · {suite.get('duration_ms')}ms · exit {suite.get('exit')}</div>
    <p class="sentence">{_html_escape(story.get('final_sentence',''))}</p>
    <p class="muted">{_html_escape(rep.get('result_line',''))}</p>
  </section>

  <section class="panel inventory">
    <h2>What ran &amp; was verified</h2>
    <p class="muted">
      <strong>{real_n}</strong> real cases
      ({inv.get('pass_count', 0)} PASS · {inv.get('fail_count', 0)} FAIL · {inv.get('skip_count', 0)} SKIP)
      · rollups filtered: {roll_n}
    </p>
    <table>
      <thead><tr><th>Group</th><th>Result</th><th>What was verified</th></tr></thead>
      <tbody>{''.join(group_rows)}</tbody>
    </table>
    {inv_cases_html}
  </section>

  <section class="panel well">
    <h2>✓ Worked well (hygiene)</h2>
    <ul>{li_list(worked)}</ul>
  </section>

  <section class="panel struggle">
    <h2>~ Struggles (along the way)</h2>
    <table>
      <thead><tr><th>Severity</th><th>Title</th><th>Detail</th><th>Impact</th></tr></thead>
      <tbody>
        {''.join(struggle_rows)}
      </tbody>
    </table>
  </section>

  <section class="panel sup">
    <h2>◎ Supervisor conclusion</h2>
    <p>{sup_summary}</p>
    <p class="muted">
      verdict=<code>{_html_escape(str(conc.get('verdict','')))}</code>
      · expected_path_ok={_html_escape(str(conc.get('expected_path_ok')))}
      · unintended_present={_html_escape(str(conc.get('unintended_present')))}
    </p>
    <h3>What was attempted</h3>
    <ul>{att_lis}</ul>
    <h3>Unintended consequences</h3>
    <table>
      <thead><tr><th>Severity</th><th>Title</th><th>Channel</th><th>Evidence</th><th>Why</th></tr></thead>
      <tbody>{''.join(sig_rows)}</tbody>
    </table>
  </section>

  <section class="panel dive">
    <h2>→ Dive in</h2>
    <p class="muted">You are viewing the easy-read HTML. Use these for full detail:</p>
    <ul>{cmd_lis}</ul>
    <p class="muted">
      results.md · report.json · chat-card.md · round logs under the run dir
    </p>
  </section>

  <section class="panel">
    <h2>Control channels</h2>
    <table>
      <thead><tr><th>Channel</th><th>Status</th><th>Bytes</th><th>Nonempty</th><th>Evaluation</th></tr></thead>
      <tbody>{''.join(ch_rows)}</tbody>
    </table>
    <ul>
      {''.join(f'<li>{_html_escape(m)}</li>' for m in (cc.get('consistency') or []))}
    </ul>
  </section>

  <details open>
    <summary><strong>Flat test case table</strong> ({len(cases)} parsed lines, incl. rollups)</summary>
    <table>
      <thead><tr><th>#</th><th>Status</th><th>Kind</th><th>Name</th><th>Claim</th><th>Source</th><th>Observation</th></tr></thead>
      <tbody>{''.join(case_rows)}</tbody>
    </table>
  </details>

  <footer>
    Run dir: <code>{_html_escape(rep.get('run_dir',''))}</code><br/>
    Generated by test-harness emit-report.py · offline single-file report
  </footer>
</main>
</body>
</html>
"""


def result_line(
    result: str,
    slug: str,
    suite_exit: int | None,
    side_fail: int,
    side_note: int,
    rounds: str,
    dur_ms: int | None,
    run_basename: str,
) -> str:
    se = suite_exit if suite_exit is not None else -1
    dm = dur_ms if dur_ms is not None else 0
    return (
        f"test-harness RESULT={result} repo={slug} suite={se} "
        f"side_fail={side_fail} side_note={side_note} rounds={rounds} "
        f"dur_ms={dm} run={run_basename}"
    )


def _redact_cap(text: str, max_bytes: int = 1200) -> str:
    """Redact then cap for paste surfaces; raw logs remain on disk."""
    try:
        scripts = Path(__file__).resolve().parent
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from control_policy import redact_cap_render
        return redact_cap_render(text or "", max_bytes=max_bytes, max_lines=16)
    except Exception:
        # fail safe: strip obvious secrets with a minimal filter
        import re as _re
        t = text or ""
        t = _re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)(\S+)", r"\1[REDACTED]", t)
        t = _re.sub(r"(?i)(bearer\s+)([a-z0-9._\-]{8,})", r"\1[REDACTED]", t)
        return t[:max_bytes]


def _inventory_from_rep(rep: dict[str, Any]) -> dict[str, Any]:
    story = rep.get("story") or {}
    suite = rep.get("suite") or {}
    inv = story.get("case_inventory") or suite.get("case_inventory")
    if inv:
        return inv
    return build_case_inventory(suite.get("cases") or [])


def _render_inventory_md(inv: dict[str, Any], *, compact: bool = False) -> list[str]:
    """Markdown lines for what-ran / what-was-verified (chat-card + results)."""
    lines: list[str] = [
        "## What ran & was verified",
        "",
    ]
    real_n = inv.get("real_case_count") or 0
    if real_n == 0 and not inv.get("groups"):
        lines.append(
            "_No individual test cases parsed from suite stdout/stderr. "
            "See control-channel previews and raw `round-*/stdout.log`._"
        )
        lines.append("")
        return lines

    lines += [
        "| | |",
        "|---|---|",
        f"| **Real cases** | {inv.get('pass_count', 0)} PASS · "
        f"{inv.get('fail_count', 0)} FAIL · {inv.get('skip_count', 0)} SKIP "
        f"(**{real_n}** named) |",
    ]
    if inv.get("rollup_count"):
        lines.append(
            f"| **Rollups filtered** | {inv['rollup_count']} module summary line(s) "
            f"(e.g. `PASS N … tests`) — not counted as cases |"
        )
    lines.append("")

    groups = inv.get("groups") or []
    if groups:
        lines += [
            "### Groups — what was verified",
            "",
            "| Group | Result | What was verified |",
            "|---|---|---|",
        ]
        for g in groups:
            res = (
                f"{g.get('pass', 0)} PASS"
                + (f" · {g['fail']} FAIL" if g.get("fail") else "")
                + (f" · {g['skip']} SKIP" if g.get("skip") else "")
            )
            if g.get("fail"):
                res = f"**{res}**"
            ver = (g.get("verifies") or "").replace("|", "\\|")
            lines.append(f"| **{g.get('title')}** | {res} | {ver} |")
        lines.append("")

    if inv.get("module_summaries") and not compact:
        lines += ["### Module rollups (from suite)", ""]
        for m in inv["module_summaries"]:
            lines.append(f"- {m}")
        lines.append("")

    lines += ["### Case inventory (executed)", ""]
    if inv.get("failed_names"):
        lines.append("**FAILED:**")
        for n in inv["failed_names"]:
            lines.append(f"- FAIL `{n}`")
        lines.append("")

    for g in groups:
        status_label = "all PASS" if not g.get("fail") else f"{g.get('fail')} FAIL"
        lines.append(f"#### {g.get('title')} — {status_label}")
        lines.append("")
        cases = g.get("cases") or []
        if compact and len(cases) > 12 and not g.get("fail"):
            # compact: first 8 + count, always list fails
            for c in cases[:8]:
                st = (c.get("status") or "pass").upper()
                claim = c.get("claim") or _humanize_case_name(c.get("name") or "")
                lines.append(f"- `{st}` `{c.get('name')}` — {claim}")
            lines.append(f"- _… +{len(cases) - 8} more (full list in results.md / report.html)_")
        else:
            for c in cases:
                st = (c.get("status") or "pass").upper()
                claim = c.get("claim") or _humanize_case_name(c.get("name") or "")
                obs = c.get("observation")
                extra = f" · _{obs}_" if obs else ""
                lines.append(f"- `{st}` `{c.get('name')}` — {claim}{extra}")
        lines.append("")

    return lines


def render_chat_card(rep: dict[str, Any]) -> str:
    """Operator card: Final result / What ran / Worked well / Struggles / Dive in."""
    story = rep.get("story") or {}
    result = rep.get("result") or "?"
    suite = rep.get("suite") or {}
    inv = _inventory_from_rep(rep)
    dive = story.get("dive_in") or {}
    html_path = dive.get("html") or f"{rep.get('run_dir')}/report.html"
    ch = (suite.get("control_channels") or {}) if isinstance(suite, dict) else {}
    stderr_stats = ch.get("stderr") or {}
    stdout_stats = ch.get("stdout") or {}
    se = rep.get("side_effects") or {}
    # control list may be on side_effects.control or mixed into fail findings
    control = list(se.get("control") or [])
    if not control:
        control = [
            f for f in (se.get("fail") or [])
            if str(f.get("class") or "").startswith("CONTROL_")
        ]
    suite_scope = rep.get("suite_scope") or "full"
    habitat = rep.get("habitat") or "host"
    fs_scope = rep.get("fs_scope") or "full"
    audit_prefix = rep.get("audit_prefix") or ""
    fs_audit_line = f"fs_scope=`{fs_scope}`"
    if audit_prefix:
        fs_audit_line += f" · package-scoped audit under `{audit_prefix}`"
    elif fs_scope == "package":
        fs_audit_line += " · package-scoped audit"
    real_n = inv.get("real_case_count") or suite.get("case_count")
    lines = [
        f"### 🧪 Test harness · {rep.get('repo_slug', '')}",
        "",
        "## Final result",
        "",
        "| | |",
        "|---|---|",
        f"| **Result** | `{result}` |",
        f"| **One-liner** | {story.get('final_sentence') or rep.get('verdict_narrative') or ''} |",
        f"| **Command** | `{rep.get('cmd')}` · **{rep.get('profile')}** · {rep.get('mode')} |",
        f"| **Scope / habitat** | suite_scope=`{suite_scope}` · habitat=`{habitat}` |",
        f"| **FS audit** | {fs_audit_line} |",
        f"| **Suite** | exit {suite.get('exit')} · {suite.get('duration_ms')}ms · "
        f"pass={inv.get('pass_count', suite.get('pass_count'))} "
        f"fail={inv.get('fail_count', suite.get('fail_count'))} "
        f"cases={real_n} |",
        f"| **stderr** | {stderr_stats.get('bytes', '?')} bytes · "
        f"errorish={stderr_stats.get('error_shaped_lines', '?')} · "
        f"status=`{stderr_stats.get('status', '?')}` |",
        f"| **stdout** | {stdout_stats.get('bytes', '?')} bytes · "
        f"status=`{stdout_stats.get('status', '?')}` |",
        f"| **HTML** | `{html_path}` |",
        f"| **Run dir** | `{rep.get('run_dir')}` |",
        "",
    ]
    # Case inventory first — answers "what ran / what was verified"
    lines.extend(_render_inventory_md(inv, compact=True))

    # Supervisor conclusion + unintended (interp of control channels / FS)
    sup = rep.get("supervisor") or {}
    conc = sup.get("conclusion") or story.get("supervisor_conclusion") or {}
    lines += ["## Conclusion (supervisor)", ""]
    if conc.get("summary"):
        lines.append(conc["summary"])
        lines.append("")
        lines.append(
            f"_verdict=`{conc.get('verdict')}` · "
            f"expected_path_ok={conc.get('expected_path_ok')} · "
            f"unintended_present={conc.get('unintended_present')} · "
            f"signals b/s/i="
            f"{(conc.get('counts') or {}).get('blocking', 0)}/"
            f"{(conc.get('counts') or {}).get('suspicious', 0)}/"
            f"{(conc.get('counts') or {}).get('informational', 0)}_"
        )
    else:
        lines.append(story.get("final_sentence") or "_(see results.md)_")
    lines += ["", "## What was attempted", ""]
    attempted = list(sup.get("what_was_attempted") or story.get("what_was_attempted") or [])
    if attempted:
        for a in attempted[:10]:
            lines.append(f"- {a}")
    else:
        lines.append(f"- Command: `{rep.get('cmd')}`")
    lines += ["", "## Unintended consequences", ""]
    signals = list(sup.get("unintended_signals") or [])
    shown = 0
    for s in signals:
        if s.get("severity") == "informational" and shown >= 6:
            continue
        lines.append(
            f"- **{s.get('severity')}** `{s.get('title')}` [{s.get('channel')}] — "
            f"{(s.get('evidence') or '')[:140]}"
        )
        lines.append(f"  - _why:_ {s.get('why_unintended', '')}")
        shown += 1
        if shown >= 12:
            break
    if not signals:
        lines.append("- _none detected by supervisor heuristics_")
    for att in (conc.get("recommended_attention") or [])[:5]:
        if att and "No supervisor follow-ups" not in att:
            lines.append(f"- **attention:** {att}")

    lines += [
        "",
        "## Worked well (hygiene)",
        "",
    ]
    # Avoid duplicating full group verifies already in inventory
    hygiene = []
    for w in story.get("worked_well") or []:
        if "PASS —" in w and ":" in w:
            continue  # group verifies already in inventory
        hygiene.append(w)
    for w in hygiene[:10]:
        lines.append(f"- {w}")
    if not hygiene:
        lines.append("- _(see inventory above / results.md)_")
    lines += ["", "## Struggles (along the way)", ""]
    struggles = story.get("struggles") or []
    if not struggles:
        lines.append("- _none recorded_")
    else:
        for s in struggles[:10]:
            lines.append(
                f"- **{s.get('severity')}** `{s.get('title')}` — {s.get('detail')} "
                f"_({s.get('impact')})_"
            )
        if len(struggles) > 10:
            lines.append(f"- _… +{len(struggles) - 10} more in report.html / results.md_")
    # Control findings (never paste raw secrets)
    lines += ["", "## Control channel (redacted)", ""]
    if control:
        for f in control[:8]:
            lines.append(
                f"- **{f.get('disposition')}** `{f.get('class')}` "
                f"[{f.get('channel')}] {_redact_cap(str(f.get('sample') or ''), 200)}"
            )
    else:
        lines.append("- _no control-policy fail findings_")
    err_prev = stderr_stats.get("error_shaped_sample") or []
    if isinstance(err_prev, list) and err_prev:
        lines.append("")
        lines.append("Error-shaped stderr sample (redacted):")
        lines.append("```")
        lines.append(_redact_cap("\n".join(str(x) for x in err_prev[:6]), 800))
        lines.append("```")
    elif stderr_stats.get("preview_tail"):
        lines.append("")
        lines.append("stderr tail (redacted):")
        lines.append("```")
        lines.append(_redact_cap(str(stderr_stats.get("preview_tail") or ""), 800))
        lines.append("```")

    lines += ["", "## Dive in", ""]
    run_dir = rep.get("run_dir") or ""
    excerpt = f"{run_dir}/channels_excerpt.md" if run_dir else ""
    if excerpt and Path(excerpt).is_file():
        lines.append(f"- **Channels excerpt (redacted):** `{excerpt}` — open when RESULT ≠ PASS_*")
    lines.append(f"- **Easy read:** `{html_path}` (open in a browser)")
    lines.append(f"- **Full text:** `{dive.get('results_md') or rep.get('run_dir') + '/results.md'}`")
    lines.append(f"- **Machine:** `{dive.get('report_json') or rep.get('run_dir') + '/report.json'}`")
    lines.append(f"- **stdout (raw on disk):** `{dive.get('stdout', '')}`")
    lines.append(f"- **stderr (raw on disk):** `{dive.get('stderr', '')}`")
    lines.append("")
    if result not in RESULT_PASS:
        lines.append(
            "**Agent rule:** open `stderr.log` (and channels_excerpt.md if present) "
            "before claiming a fix; do not invent PASS without RESULT line."
        )
        lines.append("")
    lines.append("**Next:** " + "; ".join(rep.get("next_steps") or ["inspect report.html"]))
    lines.append("")
    lines.append(f"`{rep.get('result_line', '')}`")
    lines.append("")
    return "\n".join(lines)


def render_results_md(rep: dict[str, Any]) -> str:
    rl = rep["result_line"]
    suite = rep["suite"]
    se = rep["side_effects"]
    story = rep.get("story") or {}
    dive = story.get("dive_in") or {}
    inv = _inventory_from_rep(rep)
    lines = [
        f"# Test harness report — {rep['repo_slug']}",
        "",
        rl,
        "",
        "## Final result",
        "",
        f"**`{rep.get('result')}`** — {story.get('final_sentence') or rep.get('verdict_narrative') or ''}",
        "",
        f"Easy read: `{dive.get('html') or rep.get('run_dir') + '/report.html'}`",
        "",
        f"**Command:** `{rep.get('cmd')}` · suite_scope=`{rep.get('suite_scope') or 'full'}` "
        f"· habitat=`{rep.get('habitat') or 'host'}`",
        "",
    ]
    sup = rep.get("supervisor") or {}
    conc = sup.get("conclusion") or {}
    lines += [
        "## Conclusion (supervisor)",
        "",
        conc.get("summary") or story.get("final_sentence") or "_(none)_",
        "",
        f"- **verdict:** `{conc.get('verdict', '?')}`",
        f"- **expected_path_ok:** {conc.get('expected_path_ok')}",
        f"- **unintended_present:** {conc.get('unintended_present')}",
        f"- **observation:** {conc.get('observation') or ''}",
        "",
        "## What was attempted",
        "",
    ]
    for a in (sup.get("what_was_attempted") or [])[:15]:
        lines.append(f"- {a}")
    if not sup.get("what_was_attempted"):
        lines.append(f"- Command: `{rep.get('cmd')}`")
    lines += ["", "## Unintended consequences (detail)", ""]
    if not sup.get("unintended_signals"):
        lines.append("- _none detected_")
    else:
        lines += [
            "| Severity | Title | Channel | Evidence | Why unintended |",
            "|---|---|---|---|---|",
        ]
        for s in sup.get("unintended_signals") or []:
            lines.append(
                f"| {s.get('severity')} | `{s.get('title')}` | {s.get('channel')} | "
                f"{(s.get('evidence') or '')[:100]} | {s.get('why_unintended') or ''} |"
            )
    lines += [""]
    # Inventory — answers "what ran / what was verified"
    lines.extend(_render_inventory_md(inv, compact=False))
    lines += [
        "## Worked well (hygiene)",
        "",
    ]
    for w in story.get("worked_well") or []:
        lines.append(f"- {w}")
    if not story.get("worked_well"):
        lines.append("- _(none)_")
    lines += ["", "## Struggles (along the way)", ""]
    if not story.get("struggles"):
        lines.append("- _none recorded_")
    else:
        lines += [
            "| Severity | Title | Detail | Impact |",
            "|---|---|---|---|",
        ]
        for s in story["struggles"]:
            lines.append(
                f"| {s.get('severity')} | `{s.get('title')}` | {s.get('detail')} | {s.get('impact')} |"
            )
    lines += [
        "",
        "## Dive in",
        "",
    ]
    for c in dive.get("commands") or []:
        lines.append(f"- `{c}`")
    lines += [
        "",
        "## Summary (machine fields)",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Repo | `{rep['repo']}` |",
        f"| Command | `{rep['cmd']}` |",
        f"| Profile / source | {rep['profile']} / {rep['source']} |",
        f"| Mode | {rep['mode']} |",
        f"| Result | `{rep['result']}` |",
        f"| Rounds | {rep['rounds_completed']} / {rep['rounds_max']} |",
        f"| Suite | exit={suite.get('exit')} · {suite.get('duration_ms')}ms · sig={suite.get('error_sig')} |",
        f"| Suite counts | pass={suite.get('pass_count')} fail={suite.get('fail_count')} skip={suite.get('skip_count')} |",
        f"| Repo FS | material={rep['repo_fs']['material_count']} baseline={rep['repo_fs']['baseline_count']} |",
        f"| Side effects | fail={se['summary']['fail']} note={se['summary']['note']} ok={se['summary']['ok']} |",
        f"| fs_scope | {rep.get('fs_scope')} |",
        f"| Worktree | {rep.get('worktree') or 'n/a'} |",
        f"| Fixes patch | {rep.get('fixes_patch') or 'n/a'} |",
        f"| Annotations | {', '.join(rep.get('annotations') or []) or '—'} |",
        "",
        "## Blocking findings (disposition=fail)",
        "",
    ]
    if not se["fail"]:
        lines.append("_none_")
    else:
        lines += [
            "| # | Class | Path/env | Change | Hint |",
            "|---|---|---|---|---|",
        ]
        for i, f in enumerate(se["fail"], 1):
            path = f.get("path") or f.get("env") or ""
            lines.append(
                f"| {i} | `{f.get('class')}` | `{path}` | {f.get('change') or ''} | {f.get('hint') or ''} |"
            )
    lines += ["", "## Notes (disposition=note)", ""]
    if not se["note"]:
        lines.append("_none_")
    else:
        lines += [
            "| # | Class | Detail | Operator hint |",
            "|---|---|---|---|",
        ]
        for i, n in enumerate(se["note"], 1):
            if n.get("class") == "TMPDIR_LEAK":
                sample = n.get("sample_rel") or n.get("sample") or []
                detail = f"count={n.get('count')} " + ", ".join(f"`{s}`" for s in sample[:5])
                hint = n.get("hint") or "not repo dirt"
            else:
                detail = n.get("path") or n.get("env") or (n.get("excerpt") or "")[:100]
                hint = n.get("hint") or ""
            lines.append(f"| {i} | `{n.get('class')}` | {detail} | {hint} |")

    base = rep["repo_fs"].get("baseline_unchanged") or []
    lines += ["", "## Baseline context (pre-existing dirt, unchanged)", ""]
    if not base:
        lines.append("_none_")
    else:
        lines += ["| Path | Status |", "|---|---|"]
        for b in base[:50]:
            lines.append(f"| `{b.get('path')}` | unchanged during suite |")

    lines += ["", "## Control channels (stdout / stderr)", ""]
    cc = suite.get("control_channels") or {}
    if not cc.get("evaluated"):
        lines.append("_control channels not evaluated (no logs)_")
    else:
        lines += [
            "| Channel | Status | Bytes | Lines | Nonempty | Error-shaped | Evaluation |",
            "|---|---|---|---|---|---|---|",
        ]
        for ch_name in ("stdout", "stderr"):
            ch = cc.get(ch_name) or {}
            lines.append(
                f"| {ch_name} | `{ch.get('status')}` | {ch.get('bytes')} | {ch.get('lines')} | "
                f"{ch.get('nonempty_lines')} | "
                f"{ch.get('error_shaped_lines')} | {ch.get('evaluation')} |"
            )
        lines.append("")
        lines.append("**Consistency checks**")
        lines.append("")
        for cmsg in cc.get("consistency") or []:
            lines.append(f"- {cmsg}")
        lines.append("")
        for ch_name in ("stdout", "stderr"):
            ch = cc.get(ch_name) or {}
            if ch.get("preview_head") or ch.get("preview_tail"):
                lines.append(f"### {ch_name} preview")
                lines.append("")
                if ch.get("preview_head"):
                    lines.append("<details><summary>head (12 lines)</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(ch["preview_head"])
                    lines.append("```")
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")
                if ch.get("preview_tail") and ch.get("preview_tail") != ch.get("preview_head"):
                    lines.append("<details><summary>tail (12 lines)</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(ch["preview_tail"])
                    lines.append("```")
                    lines.append("")
                    lines.append("</details>")
                    lines.append("")
            if ch.get("error_shaped_sample"):
                lines.append(f"**{ch_name} error-shaped sample**")
                lines.append("")
                lines.append("```")
                lines.extend(ch["error_shaped_sample"])
                lines.append("```")
                lines.append("")

    lines += ["", "## Test cases (flat table — all parsed lines)", ""]
    cases = suite.get("cases") or []
    real_cases = [c for c in cases if c.get("kind") != "rollup"]
    rollups = [c for c in cases if c.get("kind") == "rollup"]
    lines.append(
        f"Parsed **{len(real_cases)}** real case(s) "
        f"(+ {len(rollups)} rollup summary line(s)): "
        f"pass={suite.get('pass_count')} fail={suite.get('fail_count')} skip={suite.get('skip_count')}."
    )
    lines.append("")
    lines.append(
        "Grouped inventory with verification claims is under "
        "**What ran & was verified** above."
    )
    lines.append("")
    if not cases:
        lines.append(
            "_No individual case lines recognized. See control-channel previews and raw logs "
            f"under `round-*/stdout.log` / `stderr.log`._"
        )
    else:
        lines += [
            "| # | Status | Kind | Name | Claim | Source | Observation |",
            "|---|---|---|---|---|---|---|",
        ]
        for i, c in enumerate(cases, 1):
            st = c.get("status") or ""
            icon = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}.get(st, st)
            obs = (c.get("observation") or "").replace("|", "\\|")
            name = (c.get("name") or "").replace("|", "\\|")
            claim = (c.get("claim") or "").replace("|", "\\|")
            kind = c.get("kind") or "case"
            lines.append(
                f"| {i} | {icon} | {kind} | `{name}` | {claim} | {c.get('source')} | {obs} |"
            )
        lines.append("")
        # also list fails prominently
        fails_c = [c for c in real_cases if c.get("status") == "fail"]
        if fails_c:
            lines.append("### Failed cases (detail)")
            lines.append("")
            for c in fails_c:
                lines.append(f"- **FAIL** `{c.get('name')}` — {c.get('claim') or ''}")
                lines.append(f"  - raw: `{c.get('raw')}`")
                if c.get("observation"):
                    lines.append(f"  - observation: {c.get('observation')}")
            lines.append("")

    lines += ["", "## Suite evidence (excerpts)", ""]
    lines.append(f"- **error_sig:** {suite.get('error_sig')}")
    lines.append(f"- **case_count:** {suite.get('case_count')}")
    if suite.get("first_failure_excerpt"):
        lines.append("- **First failure excerpt:**")
        lines.append("```")
        lines.append(suite["first_failure_excerpt"])
        lines.append("```")
    # raw log paths
    lines.append("")
    lines.append(
        f"Raw logs: `round-N/stdout.log` and `round-N/stderr.log` under `{rep.get('run_dir')}`."
    )

    lines += ["", "## Operator next steps", ""]
    for s in rep.get("next_steps") or []:
        lines.append(f"- {s}")
    lines.append("")
    return "\n".join(lines)


def build_report(run_dir: Path) -> tuple[dict[str, Any], int]:
    """Return (report_dict, exit_code). exit 2 only for incomplete/hard error."""
    manifest = load_json(run_dir / "manifest.json")
    terminal = load_json(run_dir / "terminal.json")
    round_nums = list_rounds(run_dir)
    metas: list[dict[str, Any]] = []
    last_se = None
    last_delta = None
    last_classifier_failure = None
    last_stdout = ""
    last_stderr = ""
    se_missing_after_meta = False

    for n in round_nums:
        rd = run_dir / f"round-{n}"
        meta = load_json(rd / "meta.json")
        if meta:
            metas.append(meta)
            se = load_json(rd / "side-effects.json")
            if not isinstance(se, dict):
                se = None
            if se is None:
                se_missing_after_meta = True
            else:
                last_se = se
                se_missing_after_meta = False
            classifier_failure = load_json(rd / "classifier-failure.json")
            if classifier_failure is not None:
                last_classifier_failure = classifier_failure
            d = load_json(rd / "delta.json")
            if d:
                last_delta = d
            sp, ep = rd / "stdout.log", rd / "stderr.log"
            if sp.is_file():
                last_stdout = sp.read_text(errors="replace")
            if ep.is_file():
                last_stderr = ep.read_text(errors="replace")

    result, annotations = derive_result(
        manifest, metas, last_se, terminal, se_missing_after_meta
    )
    if last_classifier_failure:
        result = "INCOMPLETE_RUN"
        annotations.append(
            f"classifier_failure:{last_classifier_failure.get('reason') or 'unknown'}"
        )

    # Incomplete without usable manifest still emits a minimal report
    if not manifest:
        manifest = {
            "repo": "",
            "repo_slug": run_dir.parent.name if run_dir.parent else "unknown",
            "cmd": "",
            "profile": "unknown",
            "source": "agent",
            "mode": "once",
            "rounds_max": 1,
            "assume_fast": False,
            "flags": [],
            "run_dir": str(run_dir),
        }

    last_meta = metas[-1] if metas else {}
    suite_exit = last_meta.get("exit")
    dur = last_meta.get("duration_ms")
    parsed = parse_suite_logs(last_stdout, last_stderr, int(suite_exit) if suite_exit is not None else 1)

    fails, notes, baseline_from_se, _services = split_findings(last_se)
    material, baseline_from_delta = material_from_delta(last_delta)
    # prefer SE baseline paths; else delta
    baseline = baseline_from_se or [
        {"path": b.get("path"), "class": "BASELINE", "change": "unchanged-baseline"}
        for b in baseline_from_delta
    ]

    fs_scope = (last_se or {}).get("fs_scope") or (last_delta or {}).get("fs_scope") or "full"
    audit_prefix = (
        (manifest.get("audit_prefix") or "")
        or (last_se or {}).get("audit_prefix")
        or (last_delta or {}).get("audit_prefix")
        or ""
    )
    # Non-empty audit_prefix implies package-scoped audit even if a stale fs_scope slipped through
    if audit_prefix and fs_scope == "full":
        fs_scope = "package"
    if last_se:
        summary = last_se.get("summary") or {
            "fail": len(fails),
            "note": len(notes),
            "ok": 0,
            "total": len(fails) + len(notes),
        }
    else:
        summary = {"fail": len(fails), "note": len(notes), "ok": 0, "total": len(fails) + len(notes)}

    # Recompute fail/note counts from split (exclude baseline from fail/note)
    summary = {
        "fail": len(fails),
        "note": len(notes),
        "ok": summary.get("ok", 0),
        "total": len(fails) + len(notes) + summary.get("ok", 0),
    }

    has_patch = (run_dir / "fixes.patch").is_file()
    worktree = run_dir / "worktree"
    worktree_path = str(worktree) if worktree.is_dir() else None

    steps = next_steps_for(result, manifest, has_patch, notes)
    suite_ok = suite_exit == 0 if suite_exit is not None else False
    narrative = verdict_narrative(
        result, suite_ok, len(material), len(fails), len(notes)
    )

    rounds_completed = len(metas)
    rounds_max = int(manifest.get("rounds_max") or 1)
    rounds_s = f"{rounds_completed}/{rounds_max}"
    rl = result_line(
        result,
        manifest.get("repo_slug") or run_dir.parent.name,
        suite_exit if suite_exit is not None else None,
        len(fails),
        len(notes),
        rounds_s,
        dur if isinstance(dur, int) else None,
        run_dir.name,
    )

    # Normalize TMPDIR samples in notes (ensure relative)
    for n in notes:
        if n.get("class") == "TMPDIR_LEAK":
            samp = n.get("sample_rel") or n.get("sample") or []
            fixed = []
            for s in samp:
                s = str(s)
                if s.startswith("/") and "/round-" in s:
                    fixed.append(s[s.find("round-") :])
                else:
                    fixed.append(s)
            n["sample"] = fixed
            n["sample_rel"] = fixed
            n.setdefault("hint", "not repo dirt; optional test cleanup")

    rep: dict[str, Any] = {
        "schema_version": 1,
        "result": result,
        "repo": manifest.get("repo") or "",
        "repo_slug": manifest.get("repo_slug") or "",
        "cmd": manifest.get("cmd") or "",
        "profile": manifest.get("profile") or "unknown",
        "source": manifest.get("source") or "agent",
        "mode": manifest.get("mode") or "once",
        "rounds_completed": rounds_completed,
        "rounds_max": rounds_max,
        "fs_scope": fs_scope,
        "audit_prefix": audit_prefix,
        "work_root": manifest.get("work_root") or manifest.get("repo") or "",
        "git_root": manifest.get("git_root") or "",
        "suite": {
            "exit": suite_exit,
            "duration_ms": dur,
            "error_sig": (
                parsed.get("failure_signature")
                or last_meta.get("error_sig")
                or ("none" if suite_exit == 0 else "unknown")
            ),
            "pass_count": parsed["pass_count"],
            "fail_count": parsed["fail_count"],
            "skip_count": parsed["skip_count"],
            "case_count": parsed.get("case_count"),
            "cases": parsed.get("cases") or [],
            "case_inventory": parsed.get("case_inventory") or {},
            "first_failure_excerpt": parsed["first_failure_excerpt"],
            "pass_tail": parsed["pass_tail"],
            "control_channels": parsed.get("control_channels") or {},
            "summary_line": parsed.get("summary_line") or {},
            "suite_summary_source": parsed.get("suite_summary_source"),
            "result_json": parsed.get("result_json"),
        },
        "repo_fs": {
            "material_delta": material,
            "baseline_unchanged": baseline,
            "material_count": len(material),
            "baseline_count": len(baseline),
        },
        "suite_scope": manifest.get("suite_scope") or "full",
        "habitat": manifest.get("habitat") or "host",
        "side_effects": {
            "fail": fails,
            "note": notes,
            "control": (last_se or {}).get("control") or [],
            "summary": summary,
        },
        "services": (last_se or {}).get("services") or [],
        "fix_paths": [],
        "worktree": worktree_path,
        "fixes_patch": str(run_dir / "fixes.patch") if has_patch else None,
        "run_dir": str(run_dir),
        "result_line": rl,
        "verdict_narrative": narrative,
        "next_steps": steps,
        "annotations": annotations,
        "classifier_failure": last_classifier_failure,
    }

    # Supervisor: interpolate channels for unintended consequences + attempt summary
    try:
        scripts = Path(__file__).resolve().parent
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from supervise import supervise as _supervise

        se_for_sup = {
            "fail": fails,
            "note": notes,
            "control": (last_se or {}).get("control") or [],
        }
        rep["supervisor"] = _supervise(
            cmd=str(manifest.get("cmd") or ""),
            profile=str(manifest.get("profile") or "unknown"),
            suite_exit=int(suite_exit) if suite_exit is not None else 1,
            stdout=last_stdout,
            stderr=last_stderr,
            suite=rep["suite"],
            side_effects=se_for_sup,
            material_count=len(material),
            result=result,
        )
    except Exception as e:
        rep["supervisor"] = {
            "schema_version": 1,
            "error": str(e),
            "what_was_attempted": [f"Command: `{manifest.get('cmd')}`"],
            "unintended_signals": [],
            "conclusion": {
                "verdict": "incomplete",
                "summary": f"Supervisor analysis failed: {e}",
                "observation": "",
                "recommended_attention": [],
                "expected_path_ok": False,
                "unintended_present": False,
                "counts": {"blocking": 0, "suspicious": 0, "informational": 0},
            },
        }

    # Story after core fields + supervisor exist
    rep["story"] = build_story(rep, run_dir)
    # Prefer story final sentence as verdict_narrative when richer
    if rep["story"].get("final_sentence"):
        rep["verdict_narrative"] = rep["story"]["final_sentence"]
    # Prefer supervisor conclusion summary when present
    sup_c = (rep.get("supervisor") or {}).get("conclusion") or {}
    if sup_c.get("summary"):
        rep["verdict_narrative"] = sup_c["summary"]
        rep["story"]["final_sentence"] = sup_c["summary"]
    exit_code = 2 if result == "INCOMPLETE_RUN" else 0
    return rep, exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit test-harness report package")
    ap.add_argument("--run-dir", required=True)
    # Intentionally NO --result flag
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(
            f"test-harness RESULT=INCOMPLETE_RUN repo=? suite=-1 side_fail=0 side_note=0 "
            f"rounds=0/0 dur_ms=0 run={run_dir.name}",
            file=sys.stderr,
        )
        print(json.dumps({"ok": False, "error": "run_dir_missing"}), file=sys.stderr)
        return 2

    try:
        rep, code = build_report(run_dir)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 2

    (run_dir / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
    (run_dir / "results.md").write_text(render_results_md(rep))
    (run_dir / "chat-card.md").write_text(render_chat_card(rep))
    try:
        (run_dir / "report.html").write_text(render_html(rep))
    except Exception as e:
        # Text artifacts still valid
        print(json.dumps({"html_error": str(e)}), file=sys.stderr)

    print(rep["result_line"])
    print(json.dumps({
        "ok": code == 0,
        "result": rep["result"],
        "report": str(run_dir / "report.json"),
        "results_md": str(run_dir / "results.md"),
        "chat_card": str(run_dir / "chat-card.md"),
        "html": str(run_dir / "report.html"),
    }))
    return code


if __name__ == "__main__":
    sys.exit(main())
