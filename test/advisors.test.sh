#!/usr/bin/env bash
# Run the imported advisors skill's own hermetic verify suite.
set -euo pipefail

SKILL="${ADVISORS_SKILL:-$HOME/.cursor/skills/advisors}"
VERIFY="$SKILL/scripts/advisors-verify.sh"

if [[ ! -x "$VERIFY" && ! -f "$VERIFY" ]]; then
  echo "SKIP advisors (not imported at $SKILL)"
  exit 0
fi

echo "advisors.test.sh: running $VERIFY --no-live"
bash "$VERIFY" --no-live
echo "======== advisors: PASS (imported skill verify) ========"
