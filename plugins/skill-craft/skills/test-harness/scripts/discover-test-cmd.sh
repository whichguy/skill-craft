#!/usr/bin/env bash
# discover-test-cmd.sh — deterministic discover (config + Makefile / package.json / paths).
# Agent owns tiers 0–1 (explicit --cmd, AGENTS.md/README prose).
# Tier 1.5: .test-harness.yml / .test-harness.json non-empty `cmd` key (source=config).
#
# Usage: discover-test-cmd.sh --repo <path> [--full]
# Exit 0 + JSON on stdout; exit 2 if no candidate.
set -euo pipefail

REPO=""
FULL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --full) FULL=1; shift ;;
    -h|--help)
      echo "Usage: $0 --repo <path> [--full]" >&2
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$REPO" || ! -d "$REPO" ]]; then
  echo '{"error":"invalid_repo"}' >&2
  exit 1
fi

REPO="$(cd "$REPO" && pwd -P)"

emit() {
  local cmd="$1" source="$2" profile="$3"
  local suite_scope="${4:-full}"
  local habitat="${5:-host}"
  python3 -c '
import json,sys
cmd, source, profile, cwd, suite_scope, habitat = sys.argv[1:7]
print(json.dumps({
  "cmd": cmd, "cwd": cwd, "source": source, "profile": profile,
  "suite_scope": suite_scope, "habitat": habitat,
}, separators=(",", ":")))
' "$cmd" "$source" "$profile" "$REPO" "$suite_scope" "$habitat"
  exit 0
}

# --- tier 1.5: package config (.test-harness.yml / .test-harness.json) -------
# Non-empty `cmd` pins product intent ahead of Makefile / package.json / paths.
# Defaults when keys missing: profile=fast, suite_scope=full, habitat=host.
CFG_OUT="$(
  python3 - "$REPO" <<'PY'
import json, sys
from pathlib import Path

repo = Path(sys.argv[1])
candidates = [repo / ".test-harness.yml", repo / ".test-harness.json"]
path = next((p for p in candidates if p.is_file()), None)
if path is None:
    sys.exit(0)

text = path.read_text(encoding="utf-8")
data = {}
if path.suffix == ".json":
    try:
        data = json.loads(text)
    except Exception:
        sys.exit(0)
else:
    # Minimal YAML-ish scalar parse (no full YAML dep)
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("-"):
            continue
        if ":" not in s:
            continue
        # only top-level scalars (no indent)
        if raw.startswith((" ", "\t")):
            continue
        key, _, val = s.partition(":")
        key = key.strip()
        val = val.strip().strip("'\"").strip()
        if key and val:
            data[key] = val

cmd = (data.get("cmd") or "").strip()
if not cmd:
    sys.exit(0)

profile = (data.get("profile") or "fast").strip() or "fast"
if profile not in ("fast", "full", "unknown"):
    profile = "fast"
suite_scope = (data.get("suite_scope") or "full").strip() or "full"
if suite_scope not in ("full", "subset"):
    suite_scope = "full"
habitat = (data.get("habitat") or "host").strip() or "host"
if habitat not in ("host", "container"):
    habitat = "host"

print(json.dumps({
    "cmd": cmd,
    "source": "config",
    "profile": profile,
    "suite_scope": suite_scope,
    "habitat": habitat,
}, separators=(",", ":")))
PY
)"
if [[ -n "$CFG_OUT" ]]; then
  cmd="$(python3 -c "import json,sys; print(json.load(sys.stdin)['cmd'])" <<<"$CFG_OUT")"
  prof="$(python3 -c "import json,sys; print(json.load(sys.stdin)['profile'])" <<<"$CFG_OUT")"
  ss="$(python3 -c "import json,sys; print(json.load(sys.stdin)['suite_scope'])" <<<"$CFG_OUT")"
  hab="$(python3 -c "import json,sys; print(json.load(sys.stdin)['habitat'])" <<<"$CFG_OUT")"
  emit "$cmd" "config" "$prof" "$ss" "$hab"
fi

# --- tier 2: Makefile --------------------------------------------------------
if [[ -f "$REPO/Makefile" || -f "$REPO/makefile" ]]; then
  mf="$REPO/Makefile"
  [[ -f "$REPO/makefile" && ! -f "$REPO/Makefile" ]] && mf="$REPO/makefile"
  # extract target names (simple: lines like "target:")
  targets="$(
    # strip comments / recipes; keep bare target names
    grep -E '^[A-Za-z0-9_./-]+:([^=]|$)' "$mf" 2>/dev/null \
      | sed -E 's/:.*//' \
      | tr ' ' '\n' \
      | grep -vE '^\.PHONY$|^\.DEFAULT$' \
      || true
  )"
  if [[ $FULL -eq 1 ]]; then
    for t in test-all test-ci test check; do
      if echo "$targets" | grep -qx "$t"; then
        case "$t" in
          test-all|test-ci) emit "make $t" "makefile" "full" ;;
          test|check) emit "make $t" "makefile" "unknown" ;;
        esac
      fi
    done
  fi
  # prefer fast-named
  for t in test-fast test:fast; do
    if echo "$targets" | grep -qx "$t"; then
      emit "make $t" "makefile" "fast"
    fi
  done
  # generic — unknown profile
  for t in test check test-ci; do
    if echo "$targets" | grep -qx "$t"; then
      emit "make $t" "makefile" "unknown"
    fi
  done
fi

# --- tier 3: package.json ----------------------------------------------------
if [[ -f "$REPO/package.json" ]]; then
  # Use python for reliable JSON
  eval "$(
    python3 - "$REPO/package.json" "$FULL" <<'PY'
import json, sys, shlex
path, full = sys.argv[1], sys.argv[2] == "1"
try:
    data = json.load(open(path))
except Exception:
    sys.exit(0)
scripts = data.get("scripts") or {}
order_fast = ["test:fast", "test:unit"]
order_full = ["test:all", "test:ci", "test", "check"]
order_unknown = ["test", "check"]
if full:
    for k in order_full:
        if k in scripts:
            prof = "full" if k in ("test:all", "test:ci") else "unknown"
            print(f"emit {shlex.quote('npm run ' + k)} package {shlex.quote(prof)}")
            sys.exit(0)
for k in order_fast:
    if k in scripts:
        print(f"emit {shlex.quote('npm run ' + k)} package fast")
        sys.exit(0)
for k in order_unknown:
    if k in scripts:
        print(f"emit {shlex.quote('npm run ' + k)} package unknown")
        sys.exit(0)
PY
  )" 2>/dev/null || true
fi

# --- tier 3b: hermetic suites (profile=fast) ---------------------------------
# Prefer offline wrappers over generic tests/run.sh. Makefile/package.json above
# still win when present at WORK_ROOT. A layout none of these recognise is pinned
# with a .test-harness.yml (tier 1.5), not with another built-in tier.
# 1) tests/run_*.test.sh offline wrappers (first in name order)
shopt -s nullglob
for f in "$REPO"/tests/run_*.test.sh; do
  base="$(basename "$f")"
  emit "bash tests/$base" "path" "fast" "full" "host"
done
shopt -u nullglob
# 2) tests/run.py
if [[ -f "$REPO/tests/run.py" ]]; then
  emit "python3 tests/run.py" "path" "fast" "full" "host"
fi
# 3) tests/run.sh — prefer fast (document residual live risk in discovery-matrix)
if [[ -f "$REPO/tests/run.sh" ]]; then
  emit "bash tests/run.sh" "path" "fast" "full" "host"
fi

# --- tier 4: conventional runner paths ---------------------------------------
# (tests/run.py and tests/run.sh already handled as fast above)
for rel in test/run-all.sh; do
  if [[ -f "$REPO/$rel" ]]; then
    emit "bash $rel" "path" "unknown"
  fi
done
# harness/*.sh — first executable-looking runner
if [[ -d "$REPO/harness" ]]; then
  while IFS= read -r -d '' f; do
    base="$(basename "$f")"
    case "$base" in
      run*.sh|test*.sh)
        emit "bash harness/$base" "path" "unknown"
        ;;
    esac
  done < <(find "$REPO/harness" -maxdepth 1 -type f -name '*.sh' -print0 2>/dev/null | sort -z)
fi

# --- tier 5: package-local suites --------------------------------------------
for rel in tests/scripts.test.sh; do
  if [[ -f "$REPO/$rel" ]]; then
    emit "bash $rel" "path" "fast"
  fi
done
# a package that carries the harness's own self-test
if [[ -f "$REPO/scripts/test-harness-tests.sh" ]]; then
  emit "bash scripts/test-harness-tests.sh" "path" "fast"
fi

echo '{"error":"no_deterministic_candidate"}'
exit 2
