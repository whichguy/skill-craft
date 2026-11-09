#!/usr/bin/env python3
"""control_policy.py — versioned control-channel policy + redaction for test-harness.

Schema (v1) keys (unknown keys fail closed when loading repo policy):
  known_test_artifacts: [str]
  known_service_calls: [str]
  forbid_network: bool
  control_forbid: [str]          # substrings (case-sensitive by default)
  control_forbid_regex: [str]    # regex patterns
  control_require_on_exit: {str(exit_code): [substr,...]}
  control_allow_forbid: [str]    # substrings that cancel a forbid hit if present on same line

Defaults always include Traceback + secret-shaped patterns for hermetic/fast profiles.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

POLICY_SCHEMA_VERSION = 1

KNOWN_KEYS = frozenset({
    "schema_version",
    "known_test_artifacts",
    "known_service_calls",
    "forbid_network",
    "control_forbid",
    "control_forbid_regex",
    "control_require_on_exit",
    "control_allow_forbid",
    # Discover / product-intent keys (shared .test-harness.yml; ignored by policy merge)
    "cmd",
    "profile",
    "suite_scope",
    "habitat",
    # Classify allowlist note globs (used by classify-side-effects)
    "ignored_write_note_globs",
})

DEFAULT_FORBID = [
    "Traceback (most recent call last)",
]

DEFAULT_FORBID_REGEX = [
    (
        r"(?i)[\"']?(?:[a-z0-9_-]*api[_-]?key|anthropic_auth_token)"
        r"[\"']?\s*[:=]\s*[\"']?[^\s\"',}\]]+"
    ),
    r"(?i)bearer\s+[a-z0-9._\-]{20,}",
    r"(?i)(?<![a-z0-9_-])sk-[a-z0-9_-]{20,}(?![a-z0-9_-])",
]

# Redaction patterns applied to paste surfaces (chat-card, channels_excerpt)
REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)([\"']?(?:[a-z0-9_-]*api[_-]?key|anthropic_auth_token)"
            r"[\"']?\s*[:=]\s*)([\"']?)([^\s\"',}\]]+)([\"']?)"
        ),
        r"\1\2[REDACTED]\4",
    ),
    (re.compile(r"(?i)(bearer\s+)([a-z0-9._\-]{8,})"), r"\1[REDACTED]"),
    (
        re.compile(
            r"(?i)(?<![a-z0-9_-])sk-[a-z0-9_-]{20,}(?![a-z0-9_-])"
        ),
        "[REDACTED_KEY]",
    ),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(password\s*[:=]\s*)(\S+)"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token\s*[:=]\s*)([a-zA-Z0-9._\-]{12,})"), r"\1[REDACTED]"),
]


class PolicyError(Exception):
    """Malformed or unknown policy key."""


def _parse_simple_yaml_policy(text: str) -> dict[str, Any]:
    """Minimal YAML-ish parser for known policy keys (no full YAML dep)."""
    out: dict[str, Any] = {
        "known_test_artifacts": [],
        "known_service_calls": [],
        "control_forbid": [],
        "control_forbid_regex": [],
        "control_allow_forbid": [],
        "control_require_on_exit": {},
    }
    current: str | None = None
    require_exit: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # mapping under control_require_on_exit
        if require_exit is not None and (line.startswith("  ") or line.startswith("\t")):
            if s.startswith("- "):
                out["control_require_on_exit"].setdefault(require_exit, []).append(
                    s[2:].strip().strip("'\"")
                )
            continue
        require_exit = None
        if s.startswith("schema_version:"):
            val = s.split(":", 1)[1].strip()
            out["schema_version"] = int(val) if val.isdigit() else val
            current = None
            continue
        if s.startswith("forbid_network:"):
            out["forbid_network"] = "true" in s.lower()
            current = None
            continue
        for key in (
            "known_test_artifacts",
            "known_service_calls",
            "control_forbid",
            "control_forbid_regex",
            "control_allow_forbid",
            "ignored_write_note_globs",
        ):
            if s.startswith(key + ":"):
                rest = s[len(key) + 1 :].strip()
                current = key
                if rest.startswith("[") and rest.endswith("]"):
                    # inline list not fully supported; ignore
                    current = None
                continue
        if s.startswith("control_require_on_exit:"):
            current = "control_require_on_exit"
            continue
        # nested exit key under control_require_on_exit
        if current == "control_require_on_exit" and s.endswith(":") and not s.startswith("-"):
            key = s[:-1].strip().strip("'\"")
            require_exit = key
            out["control_require_on_exit"].setdefault(key, [])
            continue
        if s.startswith("- ") and current and current != "control_require_on_exit":
            out.setdefault(current, []).append(s[2:].strip().strip("'\""))
            continue
        # unknown top-level key
        if ":" in s and not s.startswith("-") and not line.startswith((" ", "\t")):
            key = s.split(":", 1)[0].strip()
            if key not in KNOWN_KEYS:
                raise PolicyError(f"unknown policy key: {key}")
    return out


def load_repo_policy(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        data = _parse_simple_yaml_policy(text)
    unknown = set(data.keys()) - KNOWN_KEYS
    if unknown:
        raise PolicyError(f"unknown policy key(s): {sorted(unknown)}")
    return data


def resolve_policy(
    *,
    profile: str,
    repo_policy: dict[str, Any] | None = None,
    apply_defaults: bool = True,
) -> dict[str, Any]:
    """Merge defaults + repo policy into a frozen resolved policy dict."""
    repo_policy = repo_policy or {}
    forbid = list(repo_policy.get("control_forbid") or [])
    forbid_re = list(repo_policy.get("control_forbid_regex") or [])
    if apply_defaults and profile in ("fast", "full", "unknown"):
        for item in DEFAULT_FORBID:
            if item not in forbid:
                forbid.append(item)
        for item in DEFAULT_FORBID_REGEX:
            if item not in forbid_re:
                forbid_re.append(item)
    require = {}
    raw_req = repo_policy.get("control_require_on_exit") or {}
    if isinstance(raw_req, dict):
        for k, v in raw_req.items():
            require[str(k)] = list(v) if isinstance(v, list) else [str(v)]
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "profile": profile,
        "known_test_artifacts": list(repo_policy.get("known_test_artifacts") or []),
        "known_service_calls": list(repo_policy.get("known_service_calls") or []),
        "forbid_network": bool(repo_policy.get("forbid_network", False)),
        "control_forbid": forbid,
        "control_forbid_regex": forbid_re,
        "control_require_on_exit": require,
        "control_allow_forbid": list(repo_policy.get("control_allow_forbid") or []),
    }


def redact_text(text: str) -> str:
    out = text or ""
    for pat, repl in REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def cap_text(text: str, max_bytes: int = 4096, max_lines: int = 40) -> str:
    lines = (text or "").splitlines()
    if len(lines) > max_lines:
        lines = lines[: max_lines // 2] + ["…"] + lines[-(max_lines // 2) :]
    body = "\n".join(lines)
    raw = body.encode("utf-8", errors="replace")
    if len(raw) > max_bytes:
        body = raw[:max_bytes].decode("utf-8", errors="replace") + "…"
    return body


def redact_cap_render(text: str, max_bytes: int = 4096, max_lines: int = 40) -> str:
    return cap_text(redact_text(text), max_bytes=max_bytes, max_lines=max_lines)


def evaluate_control(
    *,
    stdout: str,
    stderr: str,
    exit_code: int,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return dispositioned findings for control channel content."""
    findings: list[dict[str, Any]] = []
    if policy.get("forbid_network"):
        findings.append({
            "class": "CONTROL_POLICY_ERROR",
            "disposition": "fail",
            "channel": "policy",
            "needle": "forbid_network",
            "sample": (
                "forbid_network=true requested, but captured-log inspection "
                "cannot prove network isolation"
            ),
            "hint": (
                "run in an externally network-isolated habitat; "
                "the harness fails closed rather than claiming enforcement"
            ),
        })
    # Scan both channels; stderr is checked first
    channels = (("stderr", stderr or ""), ("stdout", stdout or ""))
    allow = list(policy.get("control_allow_forbid") or [])
    for ch_name, text in channels:
        for needle in policy.get("control_forbid") or []:
            if needle and needle in text:
                # allow if any allow substring co-occurs on a matching line
                allowed = False
                for ln in text.splitlines():
                    if needle in ln and any(a in ln for a in allow):
                        allowed = True
                        break
                if allowed:
                    continue
                findings.append({
                    "class": "CONTROL_FORBID_HIT",
                    "disposition": "fail",
                    "channel": ch_name,
                    "needle": needle,
                    "sample": redact_cap_render(
                        next((ln for ln in text.splitlines() if needle in ln), needle),
                        max_bytes=240,
                        max_lines=3,
                    ),
                    "hint": "control-channel forbid list (hermetic/unintended consequence)",
                })
        for pat_s in policy.get("control_forbid_regex") or []:
            try:
                pat = re.compile(pat_s)
            except re.error as e:
                findings.append({
                    "class": "CONTROL_POLICY_ERROR",
                    "disposition": "fail",
                    "channel": ch_name,
                    "needle": pat_s,
                    "sample": f"invalid regex: {e}",
                    "hint": "fix control_forbid_regex in policy",
                })
                continue
            m = pat.search(text)
            if m:
                findings.append({
                    "class": "CONTROL_FORBID_HIT",
                    "disposition": "fail",
                    "channel": ch_name,
                    "needle": pat_s,
                    "sample": redact_cap_render(m.group(0), max_bytes=240, max_lines=2),
                    "hint": "control-channel forbid regex",
                })
    req = policy.get("control_require_on_exit") or {}
    need = req.get(str(exit_code)) or req.get(exit_code)
    if need:
        # requirements checked against stderr first, then stdout
        blob = (stderr or "") + "\n" + (stdout or "")
        for needle in need:
            if needle not in blob:
                findings.append({
                    "class": "CONTROL_REQUIRE_MISS",
                    "disposition": "fail",
                    "channel": "stderr",
                    "needle": needle,
                    "sample": f"missing required marker for exit {exit_code}: {needle!r}",
                    "hint": "control_require_on_exit",
                })
    return findings


def find_repo_policy_file(repo: Path) -> Path | None:
    for name in (".test-harness.yml", "test/harness-allowlist.yml", ".test-harness.json"):
        p = repo / name
        if p.is_file():
            return p
    return None


def write_channels_excerpt(
    path: Path,
    *,
    stdout: str,
    stderr: str,
    exit_code: int,
    findings: list[dict[str, Any]],
) -> None:
    parts = [
        f"# Channels excerpt (redacted) · suite exit {exit_code}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        parts.append("- _(none)_")
    else:
        for f in findings:
            parts.append(
                f"- **{f.get('disposition')}** `{f.get('class')}` "
                f"[{f.get('channel')}] {f.get('sample')}"
            )
    parts += [
        "",
        "## stderr (redacted, capped)",
        "",
        "```",
        redact_cap_render(stderr, max_bytes=6000, max_lines=80),
        "```",
        "",
        "## stdout (redacted, capped)",
        "",
        "```",
        redact_cap_render(stdout, max_bytes=6000, max_lines=80),
        "```",
        "",
    ]
    path.write_text("\n".join(parts), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Resolve/evaluate control policy")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("resolve", help="resolve policy into run dir")
    r.add_argument("--repo", required=True)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--profile", default="fast")
    r.add_argument("--policy-file", default=None)

    e = sub.add_parser("evaluate", help="evaluate channels against resolved policy")
    e.add_argument("--policy", required=True, help="resolved policy json")
    e.add_argument("--stdout-log", required=True)
    e.add_argument("--stderr-log", required=True)
    e.add_argument("--exit-code", type=int, required=True)
    e.add_argument("--out", required=True, help="control-findings.json")
    e.add_argument("--excerpt", default=None, help="optional channels_excerpt.md path")

    t = sub.add_parser("self-test", help="API-free unit checks")

    args = ap.parse_args(argv)

    if args.cmd == "resolve":
        repo = Path(args.repo).resolve()
        run_dir = Path(args.run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        pol_path = Path(args.policy_file) if args.policy_file else find_repo_policy_file(repo)
        try:
            raw = load_repo_policy(pol_path)
        except PolicyError as err:
            print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
            return 2
        resolved = resolve_policy(profile=args.profile, repo_policy=raw)
        resolved["policy_file"] = str(pol_path) if pol_path else None
        out = run_dir / "control-policy.json"
        out.write_text(json.dumps(resolved, indent=2) + "\n")
        print(json.dumps({"ok": True, "policy": str(out), "profile": args.profile}))
        return 0

    if args.cmd == "evaluate":
        policy = json.loads(Path(args.policy).read_text())
        stdout = Path(args.stdout_log).read_text(encoding="utf-8", errors="replace")
        stderr = Path(args.stderr_log).read_text(encoding="utf-8", errors="replace")
        findings = evaluate_control(
            stdout=stdout, stderr=stderr, exit_code=args.exit_code, policy=policy,
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "exit_code": args.exit_code,
            "findings": findings,
            "fail": sum(1 for f in findings if f.get("disposition") == "fail"),
            "ok": all(f.get("disposition") != "fail" for f in findings),
        }
        out.write_text(json.dumps(doc, indent=2) + "\n")
        if args.excerpt and (findings or args.exit_code != 0):
            write_channels_excerpt(
                Path(args.excerpt),
                stdout=stdout,
                stderr=stderr,
                exit_code=args.exit_code,
                findings=findings,
            )
        print(json.dumps({"ok": doc["ok"], "fail": doc["fail"], "out": str(out)}))
        return 0 if doc["ok"] else 1

    if args.cmd == "self-test":
        # unit checks
        pol = resolve_policy(profile="fast", repo_policy={})
        assert "Traceback (most recent call last)" in pol["control_forbid"]
        hits = evaluate_control(
            stdout="PASS\n",
            stderr="Traceback (most recent call last):\n  File x\n",
            exit_code=0,
            policy=pol,
        )
        assert any(f["class"] == "CONTROL_FORBID_HIT" for f in hits), hits
        secret = "Authorization: Bearer " + "supersecret" + "tokenvalue12345"
        red = redact_text(secret)
        assert "supersecret" not in red and "REDACTED" in red, red
        harmless = evaluate_control(
            stdout=(
                "SKIP live check: ANTHROPIC_API_KEY not set\n"
                "SKIP other check: OPENAI_API_KEY not set\n"
                "SKIP auth check: ANTHROPIC_AUTH_TOKEN not set\n"
            ),
            stderr="",
            exit_code=0,
            policy=pol,
        )
        assert not harmless, harmless
        openai_value = "sk-" + "testsecretvalue123456789012345"
        anthropic_json_value = "sk-" + "ant-api03-testvalue123456789012345"
        openai_json_value = "sk-" + "proj-testvalue123456789012345"
        auth_token_value = "auth-token-value-123456789012345"
        for assignment, value in (
            (
                "ANTHROPIC_API_KEY=anthropic-secret-value-1234567890",
                "anthropic-secret-value-1234567890",
            ),
            (
                f"OPENAI_API_KEY: {openai_value}",
                openai_value,
            ),
            (
                f'"ANTHROPIC_API_KEY": "{anthropic_json_value}"',
                anthropic_json_value,
            ),
            (
                f'"OPENAI_API_KEY": "{openai_json_value}"',
                openai_json_value,
            ),
            (
                f'"ANTHROPIC_AUTH_TOKEN": "{auth_token_value}"',
                auth_token_value,
            ),
        ):
            secret_hits = evaluate_control(
                stdout=assignment + "\n",
                stderr="",
                exit_code=0,
                policy=pol,
            )
            assert any(
                f.get("class") == "CONTROL_FORBID_HIT" for f in secret_hits
            ), secret_hits
            assignment_red = redact_text(assignment)
            assert (
                value not in assignment_red and "REDACTED" in assignment_red
            ), assignment_red
        for provider_token in (anthropic_json_value, openai_json_value):
            token_hits = evaluate_control(
                stdout=f"provider diagnostic: {provider_token}\n",
                stderr="",
                exit_code=0,
                policy=pol,
            )
            assert any(
                f.get("class") == "CONTROL_FORBID_HIT" for f in token_hits
            ), token_hits
            token_red = redact_text(f"provider diagnostic: {provider_token}")
            assert (
                provider_token not in token_red and "REDACTED" in token_red
            ), token_red
        network_hits = evaluate_control(
            stdout="PASS\n",
            stderr="",
            exit_code=0,
            policy=resolve_policy(
                profile="fast",
                repo_policy={"forbid_network": True},
            ),
        )
        assert any(
            f.get("class") == "CONTROL_POLICY_ERROR"
            and f.get("needle") == "forbid_network"
            for f in network_hits
        ), network_hits
        pol2 = resolve_policy(
            profile="fast",
            repo_policy={"control_require_on_exit": {"3": ["EXPECTED MARKER"]}},
        )
        miss = evaluate_control(
            stdout='{"code":3}',
            stderr="note: only\n",
            exit_code=3,
            policy=pol2,
        )
        assert any(f["class"] == "CONTROL_REQUIRE_MISS" for f in miss), miss
        # unknown key fail closed
        try:
            load_repo_policy  # noqa: B018
            # inline
            from tempfile import NamedTemporaryFile
            with NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
                fh.write("totally_unknown_key: 1\n")
                p = Path(fh.name)
            try:
                load_repo_policy(p)
                raise SystemExit("expected PolicyError")
            except PolicyError:
                pass
            finally:
                p.unlink(missing_ok=True)
        except Exception:
            raise
        print(json.dumps({"ok": True, "self_test": "pass"}))
        return 0

    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PolicyError as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(2)
