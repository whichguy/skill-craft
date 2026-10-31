#!/usr/bin/env bash
# Stage 3 of docs/shiploop-e2e-closed-loop-plan-2026-10-30.md: the same-build calibration.
#
#   bash docs/experiments/e2e-calibration-20261031/run.sh [COMMIT]
#
# Freezes COMMIT (default HEAD) in a detached worktree beside the output, builds its plugin once, registers a
# promotion/5 calibration epoch (registration.py) and launches every attempt, at most E2E_CALIBRATION_PARALLEL (3) at
# once, through cycle.launch_all. Then it writes the epoch's status and spread.py's calibration.json.
#
# Run it again with the same E2E_CALIBRATION_OUT to continue: it reuses the worktree, build and epoch, and launches only
# attempts never launched. An attempt whose launch was interrupted stays "unknown_launch": seal it with
#   python3 "$out/source/test/shiploop_e2e/epoch.py" reconcile --output "$out/epoch" --attempt ID
# or leave it; it is never relaunched. E2E_CALIBRATION_DRY=1 stops after registration, so the setup can be checked
# without a model call.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo=$(git -C "$here" rev-parse --show-toplevel)
sha=$(git -C "$repo" rev-parse "${1:-HEAD}")
out=${E2E_CALIBRATION_OUT:-$HOME/e2e-runs/calibration-$(date -u +%Y%m%d)}
parallel=${E2E_CALIBRATION_PARALLEL:-3}
mkdir -p "$out"

src="$out/source"
if [ ! -d "$src" ]; then
  git -C "$repo" worktree add --quiet --detach "$src" "$sha"
fi
echo "calibration: source $(git -C "$src" rev-parse HEAD), output $out"

plugin="$out/build/plugins/skill-craft"
if [ ! -d "$plugin" ]; then
  python3 -B "$src/scripts/build-packages.py" "$out/build" >/dev/null
fi

if [ ! -d "$out/epoch" ]; then
  python3 -B "$src/docs/experiments/e2e-calibration-20261031/registration.py" --plugin "$plugin" \
    > "$out/registration-template.json"
  python3 -B "$src/test/shiploop_e2e/epoch.py" init --registration "$out/registration-template.json" \
    --output "$out/epoch" >/dev/null
fi
python3 -B "$src/test/shiploop_e2e/epoch.py" next --output "$out/epoch"

if [ "${E2E_CALIBRATION_DRY:-}" = 1 ]; then
  echo "calibration: dry run, stopped before any launch"
  exit 0
fi

python3 -B - "$src" "$out" "$plugin" "$parallel" <<'PY'
import sys
from pathlib import Path

src, out, plugin, parallel = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, str(src / "test" / "shiploop_e2e"))
import cycle  # noqa: E402

failed = cycle.launch_all(out / "epoch", {"control": plugin, "candidate": plugin}, parallel, out / "launch-logs")
print("calibration: launch processes that exited non-zero:", ", ".join(failed) or "none")
PY

python3 -B "$src/test/shiploop_e2e/epoch.py" status --output "$out/epoch" > "$out/status.json"
python3 -B "$src/test/shiploop_e2e/spread.py" "$out/epoch" --attempts 3 --out "$out/calibration.json" >/dev/null
python3 -B - "$out/calibration.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1]))
print(f"calibration: {report['attempts_sealed']} of {report['attempts_registered']} attempts sealed")
for case, row in report["cases"].items():
    tokens = row["measures"].get("tokens") or {}
    print(f"  {case}: {row['successes']}/{row['attempts']} succeeded, tokens median {tokens.get('median')}, "
          f"range {tokens.get('min')}..{tokens.get('max')}")
recommended = report["recommended"]
print(f"recommended tolerance at {recommended['attempts']} attempts per arm: {recommended['tolerance']}"
      + (f" ({recommended['why']})" if recommended.get("why") else ""))
PY
