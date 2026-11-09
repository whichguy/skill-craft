#!/usr/bin/env python3
"""classify-side-effects.py — classify FS delta + log signals into dispositioned findings.

Exit 0 if no disposition:fail; exit 1 if any fail (script-detectable).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Allow sibling imports (control_policy.py) when invoked as a script
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Common test litter globs (basename / path substring match)
DEFAULT_LITTER = [
    r"(^|/)__pycache__(/|$)",
    r"(^|/)\.pytest_cache(/|$)",
    r"(^|/)\.mypy_cache(/|$)",
    r"(^|/)\.ruff_cache(/|$)",
    r"(^|/)\.nyc_output(/|$)",
    r"(^|/)coverage(/|$)",
    r"(^|/)htmlcov(/|$)",
    r"\.pyc$",
    r"\.pyo$",
    r"\.lcov$",
    r"(^|/)\.DS_Store$",
    r"(^|/)node_modules(/|$)",
    r"(^|/)\.turbo(/|$)",
    r"\.tsbuildinfo$",
]

HARNESS_OUTPUT_DIRS = [
    r"(^|/)results(/|$)",
    r"(^|/)reports/runs(/|$)",
    r"(^|/)reports/harness(/|$)",
]

# Live-gate env var name patterns: the common spellings of "run the live variant of this suite".
LIVE_GATE_ENV = re.compile(r"^(.*_LIVE_TEST|LIVE_TEST)$")

PROVIDER_HOST_RE = re.compile(
    r"(api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|"
    r"api\.x\.ai|openai\.azure\.com|api\.cohere\.ai)",
    re.I,
)
LOOPBACK_RE = re.compile(r"(localhost|127\.0\.0\.1|::1)")
ECONN_RE = re.compile(r"ECONNREFUSED")
FIXTURE_PATH_RE = re.compile(r"(fixture|golden|snapshot|testdata|__snapshots__)", re.I)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def load_allowlist(path: str | None) -> dict[str, Any]:
    """Load allowlist/policy file; unknown keys fail closed via control_policy."""
    if not path or not Path(path).is_file():
        return {}
    # Prefer control_policy loader (versioned keys, fail-closed)
    try:
        from control_policy import PolicyError, load_repo_policy
        return load_repo_policy(Path(path))
    except PolicyError:
        raise
    except Exception:
        pass
    text = Path(path).read_text()
    if path.endswith(".json"):
        data = json.loads(text)
        # fail closed on unknown keys when json
        known = {
            "schema_version", "known_test_artifacts", "known_service_calls",
            "forbid_network", "control_forbid", "control_forbid_regex",
            "control_require_on_exit", "control_allow_forbid",
            "cmd", "profile", "suite_scope", "habitat",
            "ignored_write_note_globs",
        }
        unknown = set(data.keys()) - known
        if unknown:
            raise ValueError("unknown policy key(s): %s" % sorted(unknown))
        return data
    allow: dict[str, Any] = {"known_test_artifacts": [], "known_service_calls": []}
    current = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("known_test_artifacts:"):
            current = "known_test_artifacts"
            continue
        if s.startswith("known_service_calls:"):
            current = "known_service_calls"
            continue
        if s.startswith("forbid_network:"):
            allow["forbid_network"] = "true" in s.lower()
            current = None
            continue
        if s.startswith("- ") and current:
            allow[current].append(s[2:].strip().strip("'\""))
    return allow


def matches_any(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        try:
            if re.search(pat, path):
                return True
        except re.error:
            if pat in path:
                return True
    return False


def classify_fs_item(item: dict[str, Any], allow: dict[str, Any]) -> dict[str, Any] | None:
    path = item["path"]
    change = item["change"]
    if change == "unchanged-baseline":
        return {
            "path": path,
            "class": "BASELINE",
            "disposition": "ok",
            "change": change,
        }

    # Safety takes precedence over artifact/allowlist classification. Replacing
    # a path that was already dirty at round pre could erase concurrent WIP,
    # regardless of whether its name normally looks like disposable test litter.
    if item.get("dirty_at_pre") and change in ("content_changed", "deleted"):
        return {
            "path": path,
            "class": "UNINTENDED_WRITE",
            "disposition": "fail",
            "change": change,
            "dirty_at_pre": True,
            "kind": item.get("kind"),
            "restore_policy": "preserve-post-state",
            "resolution": "preserved — dirty at round pre; manual reconciliation required",
        }

    known = allow.get("known_test_artifacts") or []
    # convert glob-ish to regex lightly
    known_re = []
    for k in known:
        k = k.strip()
        if k.endswith("/"):
            known_re.append(re.escape(k.rstrip("/")) + r"(/|$)")
        else:
            known_re.append(re.escape(k).replace(r"\*\*", ".*").replace(r"\*", "[^/]*"))

    if matches_any(path, DEFAULT_LITTER) or matches_any(path, known_re):
        return {
            "path": path,
            "class": "EXPECTED_ARTIFACT",
            "disposition": "note",  # prefer gitignore if unignored
            "change": change,
            "resolution": "gitignore-or-allowlist",
        }

    if matches_any(path, HARNESS_OUTPUT_DIRS) or matches_any(path, known_re):
        return {
            "path": path,
            "class": "HARNESS_OUTPUT",
            "disposition": "note",
            "change": change,
        }

    if not item.get("restorable", True) and change in ("content_changed", "added", "deleted"):
        return {
            "path": path,
            "class": "UNINTENDED_WRITE",
            "disposition": "fail",
            "change": change,
            "resolution": "unrestorable — too large",
        }

    # Default: product write/delete
    if change in ("added", "content_changed", "deleted"):
        return {
            "path": path,
            "class": "UNINTENDED_WRITE",
            "disposition": "fail",
            "change": change,
            "dirty_at_pre": item.get("dirty_at_pre"),
            "kind": item.get("kind"),
        }

    return {
        "path": path,
        "class": "UNKNOWN",
        "disposition": "fail",
        "change": change,
    }


# Ambient run and job dirs: note only (a neighbour's runs in a monorepo must not fail the gate)
AMBIENT_NOTE_GLOBS = [
    r"(^|/)runs(/|$)",           # run output folders; results/runs is handled separately
    r"(^|/)\.worktrees(/|$)",
    r"(^|/)node_modules(/|$)",
    r"(^|/)reports/harness(/|$)",
]

# Product-ish paths under which IGNORED_WRITE stays fail
PRODUCT_FAIL_PREFIXES = [
    r"(^|/)src/",
    r"(^|/)lib/",
    r"(^|/)app/",
]


def classify_ignored(item: dict[str, Any], allow: dict[str, Any] | None = None) -> dict[str, Any]:
    path = item["path"]
    allow = allow or {}
    # Explicit note globs from allowlist
    note_globs = list(AMBIENT_NOTE_GLOBS)
    for g in allow.get("ignored_write_note_globs") or allow.get("known_test_artifacts") or []:
        g = str(g).strip()
        if not g:
            continue
        # glob-ish ** / *
        note_globs.append(
            re.escape(g).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        )

    if matches_any(path, note_globs):
        return {
            "path": path,
            "class": "IGNORED_WRITE",
            "disposition": "note",
            "change": item["change"],
            "hint": "ambient run/job dir — not treated as product pollution",
        }

    # Optional fail-under from allowlist
    fail_under = allow.get("ignored_write_fail_under")
    if fail_under:
        fail_pats = []
        for p in fail_under:
            p = str(p).strip().rstrip("/") + "/"
            fail_pats.append(re.escape(p).replace(r"\*\*", ".*"))
        if matches_any(path, fail_pats):
            return {
                "path": path,
                "class": "IGNORED_WRITE",
                "disposition": "fail",
                "change": item["change"],
                "hint": "ignored write under configured product prefix",
            }
        # if fail_under configured, only those fail
        return {
            "path": path,
            "class": "IGNORED_WRITE",
            "disposition": "note",
            "change": item["change"],
            "hint": "ignored write outside fail_under prefixes",
        }

    # Default: fail only under product-ish prefixes (not run folders)
    if matches_any(path, PRODUCT_FAIL_PREFIXES):
        return {
            "path": path,
            "class": "IGNORED_WRITE",
            "disposition": "fail",
            "change": item["change"],
            "hint": "ignored write under product path",
        }

    return {
        "path": path,
        "class": "IGNORED_WRITE",
        "disposition": "note",
        "change": item["change"],
        "hint": "ignored write (non-product path)",
    }


def scan_logs(log_paths: list[str], profile: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for lp in log_paths:
        p = Path(lp)
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if ECONN_RE.search(line) and not PROVIDER_HOST_RE.search(line):
                # ECONNREFUSED alone is not hard fail
                continue
            if PROVIDER_HOST_RE.search(line):
                if LOOPBACK_RE.search(line):
                    continue
                if FIXTURE_PATH_RE.search(line):
                    continue
                findings.append({
                    "class": "LIVE_CALL_SUSPECT",
                    "disposition": "note",
                    "source": str(p),
                    "line": i,
                    "excerpt": line[:240],
                })
    return findings


def check_live_gates(profile: str) -> list[dict[str, Any]]:
    findings = []
    for k, v in os.environ.items():
        if not v or v in ("0", "false", "False", ""):
            continue
        if LIVE_GATE_ENV.match(k):
            if profile == "fast":
                findings.append({
                    "class": "LIVE_GATE_ON_FAST",
                    "disposition": "fail",
                    "env": k,
                    "value": v[:80],
                })
            else:
                findings.append({
                    "class": "LIVE_CALL_SUSPECT",
                    "disposition": "note",
                    "env": k,
                    "value": v[:80],
                    "reason": f"live gate set under profile={profile}",
                })
    return findings


def _rel_to_run(path: Path, run_dir: Path | None) -> str:
    """Return path relative to run_dir when possible; never prefer absolute home paths."""
    try:
        if run_dir is not None:
            return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        pass
    # Derive run root if tmpdir is …/round-N/tmp
    parts = path.resolve().parts
    for i, part in enumerate(parts):
        if part.startswith("round-") and i + 1 < len(parts) and parts[i + 1] == "tmp":
            # run_dir is parent of round-N
            try:
                run_guess = Path(*parts[:i]) if i > 0 else None
                if run_guess:
                    return path.resolve().relative_to(run_guess.resolve()).as_posix()
            except ValueError:
                break
    # Last resort: keep only round-N/tmp/... suffix if present
    s = path.as_posix()
    idx = s.find("/round-")
    if idx >= 0:
        return s[idx + 1 :]  # strip leading slash → round-N/...
    return path.name


def tmpdir_findings(tmpdir: str | None, run_dir: str | None = None) -> list[dict[str, Any]]:
    if not tmpdir:
        return []
    p = Path(tmpdir)
    if not p.is_dir():
        return []
    rd = Path(run_dir).resolve() if run_dir else None
    leftovers_abs = []
    for root, _dirs, files in os.walk(p):
        for f in files:
            leftovers_abs.append(Path(root) / f)
    if not leftovers_abs:
        return []
    sample_rel = [_rel_to_run(x, rd) for x in leftovers_abs[:10]]
    return [{
        "class": "TMPDIR_LEAK",
        "disposition": "note",
        "count": len(leftovers_abs),
        "sample": sample_rel,
        "sample_rel": sample_rel,
        "hint": "not repo dirt; optional test cleanup",
    }]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delta", required=True, help="path to delta.json from porcelain-delta")
    ap.add_argument("--profile", default="unknown", choices=["fast", "full", "unknown"])
    ap.add_argument("--allowlist", default=None)
    ap.add_argument(
        "--control-policy",
        default=None,
        help="resolved control-policy.json (from control_policy.py resolve)",
    )
    ap.add_argument("--suite-exit", type=int, default=None, help="suite exit code for control_require_on_exit")
    ap.add_argument("--log", action="append", default=[], help="suite log path (repeatable)")
    ap.add_argument("--tmpdir", default=None)
    ap.add_argument("--run-dir", default=None, help="run root for relative TMPDIR paths")
    ap.add_argument("--out", required=True, help="write side-effects.json here")
    args = ap.parse_args()

    delta_doc = load_json(args.delta)
    try:
        allow = load_allowlist(args.allowlist)
    except Exception as e:
        print(json.dumps({"ok": False, "error": "policy_load: %s" % e}), file=sys.stderr)
        return 2

    # Infer run_dir from out path: …/round-N/side-effects.json → parent of round-N
    run_dir = args.run_dir
    if not run_dir and args.out:
        out_p = Path(args.out).resolve()
        if out_p.parent.name.startswith("round-"):
            run_dir = str(out_p.parent.parent)

    findings: list[dict[str, Any]] = []
    for item in delta_doc.get("delta", []):
        f = classify_fs_item(item, allow)
        if f:
            findings.append(f)

    for item in delta_doc.get("ignored_delta", []):
        findings.append(classify_ignored(item, allow))

    findings.extend(scan_logs(args.log, args.profile))
    findings.extend(check_live_gates(args.profile))
    findings.extend(tmpdir_findings(args.tmpdir, run_dir))

    # Control-channel policy evaluation (affects side_effects_ok)
    control_findings: list[dict[str, Any]] = []
    policy_path = args.control_policy
    if not policy_path and run_dir:
        cand = Path(run_dir) / "control-policy.json"
        if cand.is_file():
            policy_path = str(cand)
    if policy_path and Path(policy_path).is_file():
        try:
            from control_policy import evaluate_control, write_channels_excerpt

            policy = json.loads(Path(policy_path).read_text())
            stdout_t = ""
            stderr_t = ""
            for logp in args.log or []:
                p = Path(logp)
                if not p.is_file():
                    continue
                name = p.name.lower()
                text = p.read_text(encoding="utf-8", errors="replace")
                if "stderr" in name:
                    stderr_t += text
                else:
                    stdout_t += text
            exit_code = args.suite_exit
            if exit_code is None and run_dir:
                meta = Path(run_dir) / "round-1" / "meta.json"
                # try infer from out path parent
                out_parent = Path(args.out).resolve().parent
                if (out_parent / "meta.json").is_file():
                    meta = out_parent / "meta.json"
                if meta.is_file():
                    try:
                        exit_code = int(json.loads(meta.read_text()).get("exit", 0))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        exit_code = 0
            if exit_code is None:
                exit_code = 0
            control_findings = evaluate_control(
                stdout=stdout_t, stderr=stderr_t, exit_code=exit_code, policy=policy,
            )
            findings.extend(control_findings)
            # Write excerpt when control fails or suite failed
            if control_findings or exit_code != 0:
                excerpt = Path(run_dir) / "channels_excerpt.md" if run_dir else None
                if excerpt is None:
                    excerpt = Path(args.out).resolve().parent / "channels_excerpt.md"
                write_channels_excerpt(
                    excerpt,
                    stdout=stdout_t,
                    stderr=stderr_t,
                    exit_code=exit_code,
                    findings=control_findings,
                )
        except Exception as e:
            findings.append({
                "class": "CONTROL_POLICY_ERROR",
                "disposition": "fail",
                "sample": str(e),
                "hint": "control policy evaluation failed closed",
            })

    # Split for report shape
    delta_out = [f for f in findings if f.get("path") is not None and f["class"] in {
        "EXPECTED_ARTIFACT", "HARNESS_OUTPUT", "UNINTENDED_WRITE", "IGNORED_WRITE",
        "BASELINE", "UNKNOWN", "TMPDIR_LEAK",
    } or (f.get("path") and f["class"] != "LIVE_CALL_SUSPECT")]
    # cleaner split:
    fs_findings = [f for f in findings if "path" in f and f["class"] not in (
        "LIVE_CALL_SUSPECT", "LIVE_CALL_UNEXPECTED", "LIVE_CALL_EXPECTED",
        "LIVE_GATE_ON_FAST", "MISSING_INJECTION",
        "CONTROL_FORBID_HIT", "CONTROL_REQUIRE_MISS", "CONTROL_POLICY_ERROR",
    )]
    # TMPDIR_LEAK has no path
    fs_findings += [f for f in findings if f["class"] == "TMPDIR_LEAK"]
    services = [f for f in findings if f["class"] in (
        "LIVE_CALL_SUSPECT", "LIVE_CALL_UNEXPECTED", "LIVE_CALL_EXPECTED",
        "LIVE_GATE_ON_FAST", "MISSING_INJECTION",
    )]
    control_out = [f for f in findings if f["class"] in (
        "CONTROL_FORBID_HIT", "CONTROL_REQUIRE_MISS", "CONTROL_POLICY_ERROR",
    )]

    fail_count = sum(1 for f in findings if f.get("disposition") == "fail")
    note_count = sum(1 for f in findings if f.get("disposition") == "note")

    doc = {
        "profile": args.profile,
        "fs_scope": delta_doc.get("fs_scope", "full"),
        "audit_prefix": delta_doc.get("audit_prefix") or "",
        "git_root": delta_doc.get("git_root"),
        "delta": fs_findings,
        "services": services,
        "control": control_out,
        "summary": {
            "fail": fail_count,
            "note": note_count,
            "ok": sum(1 for f in findings if f.get("disposition") == "ok"),
            "total": len(findings),
            "control_fail": sum(1 for f in control_out if f.get("disposition") == "fail"),
        },
        "side_effects_ok": fail_count == 0,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({
        "ok": fail_count == 0,
        "fail": fail_count,
        "note": note_count,
        "out": args.out,
    }))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(2)
