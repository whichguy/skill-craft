#!/bin/bash
# detect_runner.sh — runs each detect config in a separate subprocess with timeout.
# Silent on no-change (watchdog pattern). Errors are logged, NOT swallowed.
#
# Usage: detect_runner.sh [--dry-run] [--self-check]
# Bind runtime dirs with POC_STATE_DIR / DETECT_DIR / PYTHON / ENGINE / LOG_FILE.
# Hermes adapter example:
#   POC_STATE_DIR=/opt/data/cron/state DETECT_DIR=/opt/data/cron/prompt-on-change/configs \
#   PYTHON=/opt/data/.venv-sync/bin/python ./detect_runner.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="${SKILL_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
POC_STATE_DIR="${POC_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/prompt-on-change}"
DETECT_DIR="${DETECT_DIR:-$POC_STATE_DIR/configs}"
PYTHON="${PYTHON:-python3}"
ENGINE="${ENGINE:-$SKILL_ROOT/scripts/detect_engine.py}"
LOG_FILE="${LOG_FILE:-$POC_STATE_DIR/detect-runner.log}"
STATE_DIR="${STATE_DIR:-$POC_STATE_DIR}"
ESCALATION_DIR="${DETECT_ENGINE_ESCALATION_DIR:-$STATE_DIR/escalations}"
export SKILL_ROOT POC_STATE_DIR
export DETECT_ENGINE_HEALTH_DIR="${DETECT_ENGINE_HEALTH_DIR:-$STATE_DIR}"
export DETECT_ENGINE_ESCALATION_DIR="$ESCALATION_DIR"
export DETECT_ENGINE_LOG_FILE="${DETECT_ENGINE_LOG_FILE:-$POC_STATE_DIR/detect-engine.log}"
TIMEOUT=120  # seconds per config
EVIDENCE_RETENTION_DAYS=30
ORPHAN_TMP_RETENTION_MIN=60
# Age top-level pending (unclaimed) escalations: alert + quarantine, never silent-delete.
PENDING_ALERT_DAYS="${PENDING_ALERT_DAYS:-7}"

mkdir -p "$(dirname "$LOG_FILE")"

# ── Self-check mode: verify engine + configs are valid ──
if [ "$1" = "--self-check" ]; then
    echo "Detect engine self-check:"
    echo "  Engine: $ENGINE"
    if [ ! -f "$ENGINE" ]; then
        echo "  ❌ Engine file not found!"
        exit 1
    fi
    echo "  ✅ Engine file exists"
    if ! "$PYTHON" -c "import sys; sys.path.insert(0, '$(dirname "$ENGINE")'); import detect_engine; print('  ✅ Engine imports OK')" 2>/dev/null; then
        echo "  ❌ Engine import failed!"
        exit 1
    fi
    # Missing/unsearchable DETECT_DIR is a hard failure (not the same as empty).
    if [ ! -d "$DETECT_DIR" ]; then
        echo "  ❌ DETECT_DIR is missing or not a directory: $DETECT_DIR"
        exit 1
    fi
    if [ ! -r "$DETECT_DIR" ] || [ ! -x "$DETECT_DIR" ]; then
        echo "  ❌ DETECT_DIR is not searchable: $DETECT_DIR"
        exit 1
    fi
    VALID=0
    INVALID=0
    CONFIG_COUNT=0
    while IFS= read -r -d '' CONFIG; do
        CONFIG_COUNT=$((CONFIG_COUNT + 1))
        if "$PYTHON" "$ENGINE" --config "$CONFIG" --validate >/dev/null 2>&1; then
            VALID=$((VALID + 1))
        else
            INVALID=$((INVALID + 1))
            echo "  ❌ Invalid config: $(basename "$CONFIG")"
        fi
    done < <(find "$DETECT_DIR" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" \) -print0 2>/dev/null)
    if [ "$CONFIG_COUNT" -eq 0 ]; then
        echo "  ⚠️  No config files found in $DETECT_DIR"
        exit 0
    fi
    DUPLICATES=0
    if ! "$PYTHON" - "$DETECT_DIR" "$(dirname "$ENGINE")" <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, sys.argv[2])
from detect_engine import _canonical_slug
import yaml


config_dir = Path(sys.argv[1])
names = {}
state_files = {}
duplicates = False
configs = sorted([*config_dir.glob("*.yaml"), *config_dir.glob("*.yml")])

for config_path in configs:
    try:
        data = yaml.safe_load(config_path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        print(f"  ❌ Failed to parse config for duplicate check: {config_path} ({exc})")
        duplicates = True
        continue

    if isinstance(data, dict) and not data.get("enabled", True):
        continue

    name = data.get("name") if isinstance(data, dict) else None
    if isinstance(name, str):
        slug = _canonical_slug(name)
        previous = names.get(slug)
        if previous is not None:
            previous_name, previous_path = previous
            print(
                f"  ❌ duplicate config slug '{slug}': "
                f"'{previous_name}' ({previous_path}) and '{name}' ({config_path})"
            )
            duplicates = True
        else:
            names[slug] = (name, config_path)

    state = data.get("state") if isinstance(data, dict) else None
    state_file = state.get("file") if isinstance(state, dict) else None
    if isinstance(state_file, str):
        resolved_state_file = (config_path.parent / state_file).expanduser().resolve()
        previous = state_files.get(resolved_state_file)
        if previous is not None:
            print(
                f"  ❌ duplicate state.file: {resolved_state_file} "
                f"({previous}, {config_path})"
            )
            duplicates = True
        else:
            state_files[resolved_state_file] = config_path

sys.exit(1 if duplicates else 0)
PY
    then
        DUPLICATES=1
    fi
    echo "  ✅ $VALID valid config(s), $INVALID invalid"
    if [ $INVALID -eq 0 ] && [ $DUPLICATES -eq 0 ]; then
        echo "  ✅ Self-check passed"
        exit 0
    fi
    echo "  ❌ Self-check failed"
    [ $INVALID -eq 0 ] || exit $INVALID
    exit $DUPLICATES
fi

# ── Lint mode: ruff check-only by default; --lint --fix or --lint-fix for auto-fix ──
# P2: never rewrite the deployed tree unless explicitly requested.
if [ "$1" = "--lint" ] || [ "$1" = "--lint-fix" ]; then
    LINT_FIX=0
    if [ "$1" = "--lint-fix" ] || [ "${2:-}" = "--fix" ]; then
        LINT_FIX=1
    fi
    ENGINE_DIR="$(dirname "$ENGINE")"
    LINT_TARGETS=("$ENGINE" "$ENGINE_DIR/gws_utils.py" "$ENGINE_DIR/../tests/test_detect_engine.py")
    if [ $LINT_FIX -eq 1 ]; then
        echo "Running ruff check --fix on detect engine files..."
        "$PYTHON" -m ruff check --fix "${LINT_TARGETS[@]}"
    else
        echo "Running ruff check (no --fix) on detect engine files..."
        "$PYTHON" -m ruff check "${LINT_TARGETS[@]}"
    fi
    RUFF_EXIT=$?
    if [ $RUFF_EXIT -ne 0 ]; then
        echo "❌ Ruff found issues (exit $RUFF_EXIT)"
        exit $RUFF_EXIT
    fi
    echo "✅ Ruff clean"
    exit 0
fi

EXTRA_ARGS=()
if [ "$1" = "--dry-run" ]; then
    EXTRA_ARGS=(--dry-run)
fi

# Best-effort retention of escalation evidence and interrupted-write remnants.
[ -d "$ESCALATION_DIR/processed" ] && find "$ESCALATION_DIR/processed" -maxdepth 1 -name '*.json' -mtime +$EVIDENCE_RETENTION_DAYS -delete
[ -d "$ESCALATION_DIR/failed" ] && find "$ESCALATION_DIR/failed" -maxdepth 1 -name '*.json' -mtime +$EVIDENCE_RETENTION_DAYS -delete
[ -d "$ESCALATION_DIR" ] && find "$ESCALATION_DIR" -maxdepth 1 -name '*.tmp' -mmin +$ORPHAN_TMP_RETENTION_MIN -delete

# P2: age top-level pending/unclaimed escalations — LOUD alert + quarantine to stale/, never silent-delete.
if [ -d "$ESCALATION_DIR" ]; then
    STALE_DIR="$ESCALATION_DIR/stale"
    mkdir -p "$STALE_DIR"
    while IFS= read -r -d '' PENDING; do
        msg="[$(date -u)] WARNING: pending escalation older than ${PENDING_ALERT_DAYS}d (Layer-2 outage?), quarantining to stale/: $PENDING"
        echo "$msg" >> "$LOG_FILE"
        echo "$msg" >&2
        mv "$PENDING" "$STALE_DIR/" 2>/dev/null || true
    done < <(find "$ESCALATION_DIR" -maxdepth 1 -name '*.json' -mtime +"$PENDING_ALERT_DAYS" -print0 2>/dev/null)
fi

# Missing/unsearchable DETECT_DIR is a hard failure (not the same as empty).
if [ ! -d "$DETECT_DIR" ]; then
    echo "[$(date -u)] ERROR: DETECT_DIR is missing or not a directory: $DETECT_DIR" >> "$LOG_FILE"
    exit 1
fi
if [ ! -r "$DETECT_DIR" ] || [ ! -x "$DETECT_DIR" ]; then
    echo "[$(date -u)] ERROR: DETECT_DIR is not searchable: $DETECT_DIR" >> "$LOG_FILE"
    exit 1
fi

EXIT_CODE=0
OUTPUT=""
CONFIG_COUNT=0

# NUL-delimited find so config filenames with spaces/newlines are safe.
while IFS= read -r -d '' CONFIG; do
    CONFIG_COUNT=$((CONFIG_COUNT + 1))
    CONFIG_NAME=$(basename "$CONFIG" .yaml)
    [ "$CONFIG_NAME" = "$(basename "$CONFIG" .yml)" ] || CONFIG_NAME=$(basename "$CONFIG" .yml)

    # Run each config in a subprocess with timeout
    # stderr goes to log file (not swallowed), stdout captured for LLM_ESCALATION lines
    RESULT=$(timeout "$TIMEOUT" "$PYTHON" "$ENGINE" --config "$CONFIG" "${EXTRA_ARGS[@]}" 2>>"$LOG_FILE")
    EXIT_STATUS=$?

    if [ $EXIT_STATUS -eq 124 ]; then
        echo "[$(date -u)] ERROR: config '$CONFIG_NAME' timed out (TIMEOUT=${TIMEOUT}s)" >> "$LOG_FILE"
        EXIT_CODE=1
    elif [ $EXIT_STATUS -ne 0 ]; then
        echo "[$(date -u)] ERROR: config '$CONFIG_NAME' exited with status $EXIT_STATUS" >> "$LOG_FILE"
        EXIT_CODE=1
    fi

    # Capture any output (LLM_ESCALATION lines or dry-run messages)
    if [ -n "$RESULT" ]; then
        OUTPUT="${OUTPUT}${RESULT}\n"
    fi
done < <(find "$DETECT_DIR" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" \) -print0 2>/dev/null)

if [ "$CONFIG_COUNT" -eq 0 ]; then
    # No configs in an existing dir — silent success (watchdog pattern)
    exit 0
fi

# Print output (cron delivers stdout to chat)
if [ -n "$OUTPUT" ]; then
    printf "%b" "$OUTPUT"
fi

exit $EXIT_CODE
