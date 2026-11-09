#!/usr/bin/env python3
"""supervise.py — supervisor-style interpolation of suite control channels.

Not a second suite runner. Given stdout/stderr + suite exit + FS/control findings,
produce:
  - what was attempted (operator-readable)
  - unintended-consequence signals (blocking / suspicious / informational)
  - observation summary + conclusion

Blocking signals here are for *narrative and optional elevation*; RESULT still
comes from emit-report's existing derive_result. Callers may promote high-severity
supervisor signals into struggles.
"""
from __future__ import annotations

import re
from typing import Any

# (severity, title, regex, why_unintended)
# severity: blocking | suspicious | informational
_SIGNAL_PATTERNS: list[tuple[str, str, re.Pattern[str], str]] = [
    (
        "blocking",
        "traceback",
        re.compile(r"Traceback \(most recent call last\)", re.I),
        "Unhandled exception stack — suite or product blew up mid-run",
    ),
    (
        "blocking",
        "assertion_failure",
        re.compile(r"\b(AssertionError|assert\s+.*failed|ASSERTION FAILED)\b", re.I),
        "Assertion failed — expected behavior did not hold",
    ),
    (
        "blocking",
        "fatal_error",
        re.compile(r"\b(FATAL|panic:|FATAL ERROR)\b"),
        "Fatal/panic signal — process-level failure",
    ),
    (
        "suspicious",
        "exception_on_channel",
        re.compile(r"\b([A-Za-z_]*Error|Exception):\s+\S+", re.I),
        "Named exception printed on a control channel — may be swallowed or logged-only",
    ),
    (
        "suspicious",
        "connection_refused",
        re.compile(r"\b(ECONNREFUSED|Connection refused|connection reset)\b", re.I),
        "Network connect failed — live service hit or missing mock seam",
    ),
    (
        "suspicious",
        "live_http_url",
        re.compile(r"https?://(?!127\.0\.0\.1|localhost|\[::1\])[^\s\"']+", re.I),
        "Non-loopback HTTP(S) URL in suite output — possible live call on a hermetic run",
    ),
    (
        "suspicious",
        "permission_denied",
        re.compile(r"\b(Permission denied|EACCES|Operation not permitted)\b", re.I),
        "Permission failure — sandbox or unintended filesystem access",
    ),
    (
        "suspicious",
        "command_not_found",
        re.compile(r"\b(command not found|No such file or directory|not found:)\b", re.I),
        "Missing binary/path — environment assumption broken",
    ),
    (
        "suspicious",
        "timeout_signal",
        re.compile(r"\b(timed?\s*out|TimeoutError|deadline exceeded)\b", re.I),
        "Timeout language in output — hung dependency or slow path",
    ),
    (
        "informational",
        "warning_flood",
        re.compile(r"\b(WARNING|Warn:|DeprecationWarning)\b", re.I),
        "Warnings present — not failures, but may hide future breakage",
    ),
    (
        "informational",
        "skip_signal",
        re.compile(r"\b(SKIP(?:PED)?|// skip|@unittest\.skip)\b", re.I),
        "Skips reported — coverage thinner than a full green run implies",
    ),
    (
        "informational",
        "todo_fixme",
        re.compile(r"\b(TODO|FIXME|XXX)\b"),
        "TODO/FIXME in output — intentional debt surfaced at runtime",
    ),
]

_ATTEMPT_LINE = re.compile(
    r"^(suite:|running |=======|-----|test session|collected |make\[|"
    r"PASS |FAIL |ok |not ok |\d+ (passed|failed|tests)|"
    r"▸ |=== |Ran \d+|python3 |npm |node |pytest)",
    re.I,
)

# A timeout-oriented test can legitimately include "timeout" in its case name.
# When the runner independently labels that whole line as passed, the word is
# coverage evidence rather than evidence that the enclosing suite hung.
_EXPLICIT_PASS_RESULT_LINE = re.compile(
    r"(?:^\s*PASS\b|(?:✓|✔)\s*$)",
    re.I,
)


def _signal_matches(
    text: str,
    *,
    title: str,
    pat: re.Pattern[str],
) -> list[str]:
    matches: list[str] = []
    for line in (text or "").splitlines():
        if not pat.search(line):
            continue
        if title == "timeout_signal" and _EXPLICIT_PASS_RESULT_LINE.search(line):
            continue
        matches.append(line)
    return matches


def extract_attempted(
    *,
    cmd: str,
    profile: str,
    stdout: str,
    stderr: str,
    suite: dict[str, Any] | None,
) -> list[str]:
    """Human bullets: what the suite appeared to try to do."""
    out: list[str] = []
    suite = suite or {}
    out.append(f"Command under test: `{cmd}` (profile={profile})")
    inv = suite.get("case_inventory") or {}
    if inv.get("real_case_count"):
        out.append(
            f"Executed ~{inv.get('real_case_count')} named test case(s) "
            f"({inv.get('pass_count', 0)} pass / {inv.get('fail_count', 0)} fail / "
            f"{inv.get('skip_count', 0)} skip)"
        )
    for b in (inv.get("verified_bullets") or [])[:6]:
        # strip markdown bold for plain list
        out.append(re.sub(r"\*\*", "", b)[:200])
    for ms in (inv.get("module_summaries") or [])[:4]:
        out.append(f"Module rollup: {ms}")
    # header-ish lines from channels
    headers: list[str] = []
    for ln in (stdout or "").splitlines()[:40]:
        s = ln.strip()
        if not s:
            continue
        if _ATTEMPT_LINE.search(s) or s.lower().startswith("suite:"):
            headers.append(s[:160])
        if len(headers) >= 5:
            break
    if not headers:
        for ln in (stdout or "").splitlines()[:8]:
            if ln.strip():
                headers.append(ln.strip()[:160])
            if len(headers) >= 3:
                break
    for h in headers[:5]:
        out.append(f"Output cue: {h}")
    if suite.get("duration_ms") is not None:
        out.append(f"Wall time: {suite.get('duration_ms')}ms · suite exit {suite.get('exit')}")
    return out


def scan_unintended(
    *,
    stdout: str,
    stderr: str,
    suite_exit: int,
    profile: str,
    side_effects: dict[str, Any] | None,
    consistency: list[str] | None,
) -> list[dict[str, Any]]:
    """Supervisor signals: did anything look unintended beyond green exit?"""
    signals: list[dict[str, Any]] = []
    blob_parts = (("stderr", stderr or ""), ("stdout", stdout or ""))

    for severity, title, pat, why in _SIGNAL_PATTERNS:
        for ch, text in blob_parts:
            matching_lines = _signal_matches(text, title=title, pat=pat)
            n = len(matching_lines)
            if n == 0:
                continue
            # On non-zero exit, traceback/assert are expected failure detail — still report
            # but mark as expected_failure_detail when suite already failed
            expected = suite_exit != 0 and severity == "blocking"
            signals.append({
                "severity": "informational" if expected else severity,
                "title": title,
                "channel": ch,
                "count": n,
                "evidence": matching_lines[0].strip()[:200],
                "why_unintended": (
                    "Expected failure detail (suite already non-zero)"
                    if expected
                    else why
                ),
                "expected_on_fail": expected,
            })
            break  # one entry per title

    # Profile-sensitive: live URL on fast is more serious
    if profile == "fast":
        for s in signals:
            if s["title"] == "live_http_url" and s["severity"] == "suspicious":
                s["severity"] = "blocking"
                s["why_unintended"] = (
                    "Non-loopback URL during profile=fast — hermetic gate expects no live calls"
                )

    # stderr volume on success
    err = stderr or ""
    if suite_exit == 0 and len(err.encode("utf-8", errors="replace")) > 800:
        signals.append({
            "severity": "suspicious",
            "title": "stderr_volume_on_success",
            "channel": "stderr",
            "count": len(err.splitlines()),
            "evidence": f"{len(err)} bytes on stderr while exit 0",
            "why_unintended": (
                "Loud stderr on a green suite often hides real problems "
                "(install help, warnings, swallowed errors)"
            ),
            "expected_on_fail": False,
        })

    # Consistency messages from suite parser
    for msg in consistency or []:
        if msg.startswith("WARN:"):
            signals.append({
                "severity": "suspicious",
                "title": "suite_exit_case_mismatch",
                "channel": "both",
                "count": 1,
                "evidence": msg,
                "why_unintended": "Exit code and parsed case outcomes disagree",
                "expected_on_fail": False,
            })

    # FS / control findings already classified — restate as supervisor view
    se = side_effects or {}
    for f in se.get("fail") or []:
        signals.append({
            "severity": "blocking",
            "title": f.get("class") or "side_effect_fail",
            "channel": f.get("channel") or "fs",
            "count": 1,
            "evidence": str(f.get("path") or f.get("sample") or f.get("needle") or "")[:200],
            "why_unintended": f.get("hint") or "Blocking side-effect finding",
            "expected_on_fail": False,
            "source": "classifier",
        })
    for f in se.get("control") or []:
        if f.get("disposition") == "fail":
            # may already be in fail list
            if any(s.get("title") == f.get("class") for s in signals):
                continue
            signals.append({
                "severity": "blocking",
                "title": f.get("class") or "CONTROL",
                "channel": f.get("channel") or "stderr",
                "count": 1,
                "evidence": str(f.get("sample") or f.get("needle") or "")[:200],
                "why_unintended": f.get("hint") or "Control-channel policy hit",
                "expected_on_fail": False,
                "source": "control_policy",
            })

    # Dedup by title+channel
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for s in signals:
        key = (s.get("title") or "", s.get("channel") or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    # severity order
    order = {"blocking": 0, "suspicious": 1, "informational": 2}
    deduped.sort(key=lambda s: order.get(s.get("severity") or "", 9))
    return deduped


def build_conclusion(
    *,
    result: str,
    suite_exit: int,
    attempted: list[str],
    signals: list[dict[str, Any]],
    material_count: int,
) -> dict[str, Any]:
    blocking = [s for s in signals if s.get("severity") == "blocking"]
    suspicious = [s for s in signals if s.get("severity") == "suspicious"]
    info = [s for s in signals if s.get("severity") == "informational"]

    expected_ok = suite_exit == 0 and result in ("PASS_CLEAN", "PASS_CLEAN_SCOPED")
    unintended_present = bool(blocking or suspicious)

    if result in ("PASS_CLEAN", "PASS_CLEAN_SCOPED") and not blocking and not suspicious:
        verdict = "clean"
        summary = (
            "Supervisor view: expected path held — suite exit 0, no blocking side effects, "
            "and control channels show no strong unintended-consequence signals."
        )
        if info:
            summary += f" {len(info)} informational cue(s) only (warnings/skips/TODO)."
    elif result in ("PASS_CLEAN", "PASS_CLEAN_SCOPED") and suspicious and not blocking:
        verdict = "pass_with_suspicion"
        summary = (
            "Supervisor view: RESULT is pass, but output/FS cues look like possible "
            f"unintended consequences ({len(suspicious)} suspicious signal(s)). "
            "Treat as 'green but investigate' — do not stop at exit 0 alone."
        )
    elif result == "FAIL_SIDE_EFFECTS" or blocking:
        verdict = "unintended_or_side_effects"
        summary = (
            "Supervisor view: suite may have been green or mixed, but blocking "
            "unintended-consequence signals and/or side-effect findings mean the run "
            "is not trustworthy as a clean gate."
        )
    elif result == "FAIL_SUITE":
        verdict = "expected_failed"
        summary = (
            "Supervisor view: suite failed (exit non-zero). Focus on first failure excerpt "
            "and failed cases; side-effect gate may still be clean."
        )
    elif result == "FAIL_BOTH":
        verdict = "failed_and_dirty"
        summary = (
            "Supervisor view: both the suite and the side-effect/unintended gate failed. "
            "Fix product/tests first, then clear unintended writes/control hits."
        )
    else:
        verdict = "incomplete"
        summary = f"Supervisor view: run ended as {result}; cannot fully certify."

    if material_count and material_count > 0 and result in ("PASS_CLEAN", "PASS_CLEAN_SCOPED"):
        summary += f" Note: material_delta={material_count} was still zero-fail classified."

    # Short observation paragraph
    obs_bits = [
        f"RESULT=`{result}`",
        f"suite_exit={suite_exit}",
        f"blocking_signals={len(blocking)}",
        f"suspicious={len(suspicious)}",
        f"informational={len(info)}",
    ]
    observation = (
        "Observed: " + "; ".join(obs_bits) + ". "
        + (attempted[0] if attempted else "No attempt summary.")
    )

    attention: list[str] = []
    for s in blocking[:5]:
        attention.append(f"BLOCKING `{s['title']}` [{s.get('channel')}]: {s.get('evidence', '')[:120]}")
    for s in suspicious[:5]:
        attention.append(f"SUSPICIOUS `{s['title']}` [{s.get('channel')}]: {s.get('evidence', '')[:120]}")
    if not attention and result in ("PASS_CLEAN", "PASS_CLEAN_SCOPED"):
        attention.append("No supervisor follow-ups — gate looks clean.")

    return {
        "verdict": verdict,
        "expected_path_ok": bool(expected_ok and not unintended_present),
        "unintended_present": unintended_present,
        "summary": summary,
        "observation": observation,
        "recommended_attention": attention,
        "counts": {
            "blocking": len(blocking),
            "suspicious": len(suspicious),
            "informational": len(info),
        },
    }


def supervise(
    *,
    cmd: str,
    profile: str,
    suite_exit: int,
    stdout: str,
    stderr: str,
    suite: dict[str, Any] | None,
    side_effects: dict[str, Any] | None,
    material_count: int,
    result: str,
) -> dict[str, Any]:
    suite = suite or {}
    cc = suite.get("control_channels") or {}
    attempted = extract_attempted(
        cmd=cmd, profile=profile, stdout=stdout, stderr=stderr, suite=suite,
    )
    signals = scan_unintended(
        stdout=stdout,
        stderr=stderr,
        suite_exit=suite_exit,
        profile=profile,
        side_effects=side_effects,
        consistency=list(cc.get("consistency") or []),
    )
    conclusion = build_conclusion(
        result=result,
        suite_exit=suite_exit,
        attempted=attempted,
        signals=signals,
        material_count=material_count,
    )
    return {
        "schema_version": 1,
        "what_was_attempted": attempted,
        "unintended_signals": signals,
        "conclusion": conclusion,
    }
